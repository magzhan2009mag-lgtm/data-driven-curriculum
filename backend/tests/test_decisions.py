import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.analytics.data import load_results
from app.analytics.decisions import REPLACE_EFFECT, textbook_decisions
from app.main import app, get_db

GEOMETRY = ["Геометрические фигуры", "Площадь и объём"]


@pytest.fixture(scope="module")
def decisions(seeded_engine) -> dict[str, dict]:
    with Session(seeded_engine) as session:
        body = textbook_decisions(load_results(session))
    return {item["textbook"]: item for item in body["textbooks"]}


@pytest.fixture(scope="module")
def client(seeded_engine):
    def override_get_db():
        with Session(seeded_engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_b_gets_replacement_advice_for_fractions(decisions):
    b = decisions["Учебник B"]
    assert b["verdict"] == "replace"
    serious = {gap["topic"] for gap in b["weaker"] if gap["cohens_d"] >= REPLACE_EFFECT}
    assert {"Дроби", "Проценты"} <= serious
    assert b["alternatives"] == ["Учебник A", "Учебник C"]
    assert b["advice"].startswith("При следующем выборе учебника рассмотреть A или C")
    assert "«Дроби»" in b["advice"] and "дополнительные материалы" in b["advice"]


def test_a_and_c_are_equal_except_geometry(decisions):
    a, c = decisions["Учебник A"], decisions["Учебник C"]
    assert a["equivalent"] == [{"textbook": "Учебник C", "except_topics": GEOMETRY}]
    assert c["equivalent"] == [{"textbook": "Учебник A", "except_topics": GEOMETRY}]
    assert sorted(gap["topic"] for gap in a["weaker"]) == GEOMETRY
    assert all(gap["stronger"] == "Учебник C" for gap in a["weaker"])
    # Отставание A в геометрии малое: совет не про замену, а про материалы.
    assert a["verdict"] == "strengthen" and a["alternatives"] == []
    assert c["verdict"] == "strong" and c["weaker"] == []
    assert "В остальных темах равноценен учебнику C: выбирайте по цене и удобству." in a["text"]


def test_only_significant_gaps_with_holm(decisions, client):
    for decision in decisions.values():
        for gap in decision["weaker"] + decision["stronger"]:
            assert gap["p_adjusted"] < 0.05
    fractions = client.get("/textbooks/compare?topic_id=3").json()
    pair = next(item for item in fractions["comparisons"] if {item["a"], item["b"]} == {"Учебник A", "Учебник B"})
    gap = next(item for item in decisions["Учебник B"]["weaker"] if item["topic"] == "Дроби" and item["stronger"] == "Учебник A")
    assert gap["p_adjusted"] == pair["p_adjusted"]
    assert gap["points"] == 8.3


def test_no_replacement_without_textbook_effect(no_textbook_effect_engine):
    with Session(no_textbook_effect_engine) as session:
        body = textbook_decisions(load_results(session))
    assert all(item["verdict"] != "replace" for item in body["textbooks"])
    assert all(item["alternatives"] == [] for item in body["textbooks"])


def test_school_without_data_gets_all_schools_decision(client):
    body = client.get("/textbooks/decisions?school_id=5").json()
    assert body["all_schools"] is True
    assert body["note"] == "В Школе №5 у учебников мало учеников, поэтому решение по всем школам."
    overall = client.get("/textbooks/decisions").json()
    assert [item["text"] for item in body["textbooks"]] == [item["text"] for item in overall["textbooks"]]
    assert overall["all_schools"] is False and overall["note"] is None


def test_weakest_card_has_advice(client):
    for query in ("", "?school_id=5"):
        card = next(item for item in client.get(f"/summary{query}").json()["cards"] if item["kind"] == "weakest_textbook")
        assert card["advice"] == "Совет: при следующем выборе рассмотреть A или C; пока — больше часов на «Проценты» и «Дроби»."
