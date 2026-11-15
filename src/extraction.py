"""Extração conservadora baseada em entidades e dependências do português.

As relações são afirmações textuais com evidência, não inferências de gestão.
Role (papel genérico de gestor) não equivale ao JobRole do CSV.
"""
import re
from functools import lru_cache
from .config import DOCUMENTS

VOCABULARY = {
    "Department": {
        "Human Resources": ["Human Resources", "Recursos Humanos", "RH"],
        "Research & Development": ["Research & Development", "Pesquisa e Desenvolvimento"],
        "Sales": ["Sales", "Vendas"],
    },
    "Role": {"gestor": ["gestor", "gestores", "gestora", "gestoras"]},
    "WorkConcept": {
        "horas extras": ["horas extras", "registros de horas extras"],
        "jornada de trabalho": ["jornada de trabalho"],
        "bem-estar": ["bem-estar", "bem estar"],
        "sobrecarga de trabalho": ["sobrecarga de trabalho", "sobrecarga"],
        "equilíbrio entre vida pessoal e trabalho": ["equilíbrio entre vida pessoal e trabalho"],
        "satisfação com o ambiente de trabalho": ["satisfação com o ambiente de trabalho", "satisfação no ambiente de trabalho"],
        "ambiente de trabalho": ["ambiente de trabalho"],
        "carga de atividades": ["carga de atividades", "volume de trabalho"],
        "custos": ["custos"],
        "satisfação profissional": ["satisfação profissional"],
        "apoio aos funcionários": ["necessidades de apoio dos funcionários"],
        "necessidade da atividade": ["necessidade da atividade"],
        "necessidades extraordinárias da equipe": ["necessidades extraordinárias de sua equipe"],
    },
}
LABELS = {"DEPARTMENT": "Department", "ROLE": "Role", "WORK_CONCEPT": "WorkConcept"}
ACTIONS = {"acompanhar": "ACOMPANHA", "avaliar": "AVALIA"}
NEGATIONS = {"não", "nunca", "jamais", "nem"}


@lru_cache(maxsize=1)
def load_nlp():
    import spacy
    try:
        nlp = spacy.load("pt_core_news_lg")
    except OSError as exc:
        raise RuntimeError("Instale o modelo: python -m spacy download pt_core_news_lg") from exc
    ruler = nlp.add_pipe("entity_ruler", before="ner",
                         config={"phrase_matcher_attr": "LOWER", "overwrite_ents": True})
    labels = {value: key for key, value in LABELS.items()}
    ruler.add_patterns([
        {"label": labels[kind], "pattern": alias, "id": canonical}
        for kind, concepts in VOCABULARY.items()
        for canonical, aliases in concepts.items() for alias in aliases
    ])
    return nlp


def _negated(verb):
    # Inclui negação do auxiliar/modal que governa o infinitivo.
    current = verb
    while True:
        if any(t.lower_ in NEGATIONS for t in current.children):
            return True
        if current.dep_ not in {"xcomp", "ccomp", "conj"} or current.head == current:
            return False
        current = current.head


def _subject_heads(verb):
    subjects = [t for t in verb.children if t.dep_ in {"nsubj", "csubj", "nsubj:pass"}]
    if not subjects and (verb.dep_ in {"xcomp", "conj"}
                         or (verb.dep_ == "advcl" and verb.head.lemma_ == "responsável")) and verb.head != verb:
        return _subject_heads(verb.head)
    return subjects


def _within(entity, heads):
    return any(entity.root in set(head.subtree) for head in heads)


def extract_text(text, document="texto", nlp=None):
    # Remove cabeçalhos e normaliza espaços antes do parser, mantendo um mapa
    # para recuperar offsets e evidências exatos do documento original.
    cleaned = re.sub(r"(?m)^\s*\d+\.\s+[^\n]+$", lambda m: " " * len(m[0]), text)
    words = list(re.finditer(r"\S+", cleaned))
    normalized, offsets = [], []
    for word in words:
        if normalized:
            normalized.append(" ")
            offsets.append(word.start() - 1)
        normalized.extend(word[0])
        offsets.extend(range(word.start(), word.end()))
    doc = (nlp if nlp is not None else load_nlp())("".join(normalized))
    entities = [{"tipo": LABELS[e.label_], "nome": e.ent_id_ or e.text,
                 "texto": text[offsets[e.start_char]:offsets[e.end_char - 1] + 1],
                 "inicio": offsets[e.start_char], "fim": offsets[e.end_char - 1] + 1,
                 "documento": document}
                for e in doc.ents if e.label_ in LABELS]
    relations, seen = [], set()
    for sentence in doc.sents:
        ents = [e for e in sentence.ents if e.label_ in LABELS]
        for verb in sentence:
            action = ACTIONS.get(verb.lemma_.lower())
            if not action or verb.pos_ != "VERB" or _negated(verb):
                continue
            heads = _subject_heads(verb)
            passive = any(t.dep_ in {"nsubj:pass", "aux:pass"} for t in verb.children)
            if passive:
                agents = [t for t in verb.children
                          if t.dep_ in {"obl:agent", "agent"}
                          or (t.dep_ == "obl" and any(c.lower_ in {"por", "pelo", "pela"}
                                                                   for c in t.children))]
                sources = [e for e in ents if e.label_ in {"DEPARTMENT", "ROLE"} and _within(e, agents)]
                targets = [e for e in ents if e.label_ == "WORK_CONCEPT" and _within(e, heads)]
            else:
                sources = [e for e in ents if e.label_ in {"DEPARTMENT", "ROLE"} and _within(e, heads)]
                # Um departamento dentro do sujeito 'gestor da área de X'
                # é contexto do gestor, não um segundo agente.
                if any(e.label_ == "ROLE" for e in sources):
                    sources = [e for e in sources if e.label_ == "ROLE"]
                targets = []
                for e in ents:
                    if e.label_ != "WORK_CONCEPT" or _within(e, heads):
                        continue
                    # Não atravessa outro verbo: evita atribuir o objeto de
                    # 'avaliar' a 'acompanhar' em orações coordenadas.
                    current = e.root
                    while current != verb and current.head != current:
                        if current.pos_ == "VERB" and not (
                            current.dep_ == "acl" and current.lemma_ == "relacionar"
                        ):
                            break
                        current = current.head
                    if current == verb:
                        targets.append(e)
            for source in sources:
                for target in targets:
                    key = (source.ent_id_ or source.text, action, target.ent_id_ or target.text,
                           sentence.start_char)
                    if key in seen:
                        continue
                    seen.add(key)
                    relations.append({"origem": key[0], "origem_tipo": LABELS[source.label_],
                                      "relacao": action, "destino": key[2],
                                      "evidencia": text[offsets[sentence.start_char]:offsets[sentence.end_char - 1] + 1].strip(),
                                      "documento": document})
    return {"entidades": entities, "relacoes": relations}


def extract_documents(folder=DOCUMENTS, nlp=None):
    files = sorted(folder.glob("*.txt"))
    if not files:
        raise FileNotFoundError(f"Nenhum documento .txt em {folder}.")
    return {path.name: extract_text(path.read_text(encoding="utf-8"), path.name, nlp)
            for path in files}


def extrair_relacoes():
    return [relation for result in extract_documents().values() for relation in result["relacoes"]]
