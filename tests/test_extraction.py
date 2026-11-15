"""Testes com o modelo real; requer pt_core_news_lg instalado."""
import pytest
from src.extraction import load_nlp, extract_text, extract_documents


@pytest.fixture(scope="module")
def nlp():
    pytest.importorskip("spacy")
    try:
        return load_nlp()
    except RuntimeError as exc:
        pytest.skip(str(exc))


def triples(text, nlp):
    return {(r["origem"], r["relacao"], r["destino"])
            for r in extract_text(text, nlp=nlp)["relacoes"]}


def test_direct_and_alias(nlp):
    assert ("Human Resources", "ACOMPANHA", "horas extras") in triples(
        "O setor de Recursos Humanos acompanha as horas extras.", nlp)


def test_negated_and_modal_negation(nlp):
    assert not triples("O setor de Human Resources não acompanha as horas extras.", nlp)
    assert not triples("O setor de Human Resources não deve acompanhar as horas extras.", nlp)


def test_passive(nlp):
    assert ("Human Resources", "ACOMPANHA", "horas extras") in triples(
        "As horas extras são acompanhadas pelo setor de Human Resources.", nlp)


def test_separate_verbs(nlp):
    result = triples("O setor de Human Resources acompanha as horas extras e avalia o bem-estar.", nlp)
    assert ("Human Resources", "ACOMPANHA", "horas extras") in result
    assert ("Human Resources", "AVALIA", "bem-estar") in result
    assert ("Human Resources", "ACOMPANHA", "bem-estar") not in result


def test_department_qualifying_manager_is_not_agent(nlp):
    result = triples("O gestor da área de Research & Development avalia o bem-estar.", nlp)
    assert ("gestor", "AVALIA", "bem-estar") in result
    assert ("Research & Development", "AVALIA", "bem-estar") not in result


def test_entities_offsets_and_no_unstated_relations(nlp):
    text = "Human Resources e Sales são áreas. Há horas extras."
    result = extract_text(text, nlp=nlp)
    assert not result["relacoes"]
    assert {e["nome"] for e in result["entidades"]} >= {"Human Resources", "Sales", "horas extras"}
    assert all(text[e["inicio"]:e["fim"]] == e["texto"] for e in result["entidades"])


def test_bundled_documents(nlp):
    results = extract_documents(nlp=nlp)
    assert len(results) == 2
    for name, result in results.items():
        assert result["entidades"] and result["relacoes"]
        assert all(r["documento"] == name and r["evidencia"] for r in result["relacoes"])


def test_gold_relations_in_bundled_documents(nlp):
    expected = {
        "politica_bem_estar.txt": {
            ("Human Resources", "ACOMPANHA", "bem-estar"),
            ("Human Resources", "ACOMPANHA", "ambiente de trabalho"),
            ("Human Resources", "AVALIA", "satisfação profissional"),
            ("Human Resources", "AVALIA", "equilíbrio entre vida pessoal e trabalho"),
            ("Human Resources", "AVALIA", "satisfação com o ambiente de trabalho"),
            ("gestor", "ACOMPANHA", "sobrecarga de trabalho"),
            ("gestor", "AVALIA", "apoio aos funcionários"),
            ("Research & Development", "ACOMPANHA", "satisfação com o ambiente de trabalho"),
            ("Research & Development", "ACOMPANHA", "carga de atividades"),
        },
        "politica_horas_extras.txt": {
            ("gestor", "AVALIA", "necessidade da atividade"),
            ("Human Resources", "ACOMPANHA", "horas extras"),
            ("gestor", "AVALIA", "necessidades extraordinárias da equipe"),
            ("Human Resources", "ACOMPANHA", "jornada de trabalho"),
            ("Human Resources", "ACOMPANHA", "bem-estar"),
            ("Sales", "ACOMPANHA", "custos"),
            ("Sales", "ACOMPANHA", "horas extras"),
        },
    }
    for name, result in extract_documents(nlp=nlp).items():
        actual = {(r["origem"], r["relacao"], r["destino"]) for r in result["relacoes"]}
        assert actual == expected[name]
    # Uma relação tem duas frases de evidência independentes no segundo texto.
    assert sum(len(x["relacoes"]) for x in extract_documents(nlp=nlp).values()) == 17


def test_multiline_entities_keep_original_offsets(nlp):
    text = "O setor de Human Resources deve acompanhar as horas\nextras."
    result = extract_text(text, nlp=nlp)
    assert result["relacoes"][0]["destino"] == "horas extras"
    for entity in result["entidades"]:
        assert text[entity["inicio"]:entity["fim"]] == entity["texto"]
