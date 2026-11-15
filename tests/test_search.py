import pytest
from src.search import reciprocal_rank_fusion, lexical_query, hybrid_search


def doc(key, score=0.5):
    return {"id": key, "title": key, "content": "texto", "score": score}


def test_fusion_rewards_agreement_and_keeps_channel_scores():
    rows = reciprocal_rank_fusion([doc("a"), doc("b")], [doc("b", 7), doc("c")])
    assert [row["id"] for row in rows] == ["b", "a", "c"]
    assert rows[0]["hybrid_score"] == pytest.approx(1/62 + 1/61)
    assert rows[0]["lexical_score"] == 7
    assert rows[0]["vector_rank"] == 2


def test_fusion_empty_limit_and_duplicates():
    assert reciprocal_rank_fusion([], []) == []
    rows = reciprocal_rank_fusion([doc("a"), doc("a")], [], limit=1)
    assert len(rows) == 1
    assert rows[0]["hybrid_score"] == pytest.approx(1/61)
    assert rows[0]["lexical_rank"] is None


def test_query_escapes_lucene_syntax():
    query = lexical_query('horas: (extras*) +"bem-estar"')
    assert query == '"horas" OR "extras" OR "bem" OR "estar"'


@pytest.mark.parametrize("question", ["", "  ", "!():"])
def test_invalid_search_before_io(question):
    with pytest.raises(ValueError):
        hybrid_search(None, None, question)
