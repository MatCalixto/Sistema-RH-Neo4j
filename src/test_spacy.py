from pathlib import Path
import spacy
import re

# 1. Carrega o modelo de português
nlp = spacy.load("pt_core_news_lg")

# 2. Configura o reconhecimento personalizado de entidades
ruler = nlp.add_pipe("entity_ruler", before="ner")

patterns = [
    {"label": "DEPARTMENT", "pattern": "Human Resources"},
    {"label": "DEPARTMENT", "pattern": "Recursos Humanos"},
    {"label": "DEPARTMENT", "pattern": "Research & Development"},
    {"label": "DEPARTMENT", "pattern": "Departamento de Recursos Humanos"},
    {"label": "DEPARTMENT", "pattern": "Sales"},
    {"label": "DEPARTMENT", "pattern": "RH"},

    {"label": "WORK_CONCEPT", "pattern": "horas extras"},
    {"label": "WORK_CONCEPT", "pattern": "jornada de trabalho"},
    {"label": "WORK_CONCEPT", "pattern": "bem-estar"},
    {"label": "WORK_CONCEPT", "pattern": "sobrecarga de trabalho"},
    {"label": "WORK_CONCEPT", "pattern": "equilíbrio entre vida pessoal e trabalho"},
    {"label": "WORK_CONCEPT", "pattern": "satisfação com o ambiente de trabalho"},
    {"label": "WORK_CONCEPT", "pattern": "ambiente de trabalho"},
    {"label": "WORK_CONCEPT", "pattern": "carga de atividades"},
    {"label": "WORK_CONCEPT", "pattern": "custos"},
    {"label": "WORK_CONCEPT", "pattern": "registros de horas extras"},

    {"label": "ROLE", "pattern": "gestor"},
    {"label": "WORK_CONCEPT", "pattern": "satisfação profissional"},

]

ruler.add_patterns(patterns)

# 3. Verifica se o verbo está negado
def verbo_negado(verbo):
    return any(
        filho.dep_ == "advmod"
        and filho.text.lower() in ["não", "nunca", "jamais"]
        for filho in verbo.children
    )

# 4. Identifica departamentos associados ao sujeito da ação
def departamentos_do_sujeito(verbo, departamentos):
    sujeitos = []

    for departamento in departamentos:
        raiz = departamento.root

        if raiz.head in verbo.children:
            if raiz.head.dep_ in ["nsubj", "nsubj:pass"]:
                sujeitos.append(departamento)

    return sujeitos


# 5. Identifica conceitos relacionados à ação
def conceitos_da_acao(verbo, entidades):
    conceitos = []
    palavras_relacionadas = set(verbo.subtree)

    for entidade in entidades:

        if entidade.label_ != "WORK_CONCEPT":
            continue
        if entidade.root in palavras_relacionadas:
            conceitos.append(entidade)

    return conceitos

# 6. Extrai as relações do documento

# 6. Extrai relações de todos os documentos da pasta
def extrair_relacoes():
    pasta_documentos = Path("documents")

    if not pasta_documentos.exists():
        raise FileNotFoundError(
            f"Pasta de documentos não encontrada: {pasta_documentos}"
        )

    arquivos = sorted(pasta_documentos.glob("*.txt"))

    if not arquivos:
        raise FileNotFoundError(
            "Nenhum documento .txt encontrado na pasta documents."
        )

    relacoes = []

    for caminho_documento in arquivos:
        print(f"\nProcessando: {caminho_documento.name}")
        
        texto = caminho_documento.read_text(encoding="utf-8")
        texto = re.sub(r"(?m)^\s*\d+\.\s*(?:[A-ZÁÉÍÓÚÂÊÔÃÕÇ][^\n]*)?\s*$","",texto)

        doc = nlp(texto)

        for sent in doc.sents:
            entidades = [
                ent for ent in sent.ents
                if ent.label_ in ["DEPARTMENT", "WORK_CONCEPT", "ROLE"]
            ]
            departamentos = [
                ent for ent in entidades
                if ent.label_ == "DEPARTMENT"
            ]
            funcoes = [
                ent for ent in entidades
                if ent.label_ == "ROLE"
            ]
            for verbo in sent:
                if verbo.pos_ != "VERB":
                    continue
                acao = verbo.lemma_.lower()
                
                if verbo_negado(verbo):
                    continue

                if acao == "acompanhar":
                    tipo_relacao = "ACOMPANHA"
                    sujeitos = departamentos_do_sujeito(
                        verbo, departamentos
                    )
                elif acao == "avaliar":
                    tipo_relacao = "AVALIA"
                    sujeitos = funcoes if funcoes else departamentos
                else:
                    continue

                # Identifica conceitos ligados à ação
                conceitos = conceitos_da_acao(verbo, entidades)

                # Armazena as relações encontradas
                for sujeito in sujeitos:
                    for conceito in conceitos:
                        relacoes.append({
                            "origem": sujeito.text,
                            "origem_tipo": (
                                "Role" if sujeito.label_ == "ROLE" else "Department"
                            ),
                            "relacao": tipo_relacao,
                            "destino": conceito.text,
                            "evidencia": sent.text.strip(),
                            "documento": caminho_documento.name
                        })
    return relacoes

# 7. Executa o teste somente quando este arquivo
# for executado diretamente.
if __name__ == "__main__":
    relacoes = extrair_relacoes()
    print("\nRELAÇÕES ARMAZENADAS:")

    for relacao in relacoes:
        print(relacao)
