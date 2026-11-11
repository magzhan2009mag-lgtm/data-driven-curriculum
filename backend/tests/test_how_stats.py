import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics.data import load_results
from app.main import app, get_db
from app.models import ItemResponse

HOW_KEYS = {"method", "n_students", "n_results", "tests"}
TEST_KEYS = {"label", "p_value", "effect_name", "effect_size", "effect_label"}


@pytest.fixture(scope="module")
def results(seeded_engine) -> pd.DataFrame:
    with Session(seeded_engine) as session:
        return load_results(session)


@pytest.fixture(scope="module")
def client(seeded_engine):
    def override_get_db():
        with Session(seeded_engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def check_how(how: dict) -> None:
    assert set(how) == HOW_KEYS
    assert how["method"] and how["n_students"] > 0 and how["n_results"] >= how["n_students"]
    assert all(set(test) == TEST_KEYS for test in how["tests"])


def test_stats_all_schools(client, results, seeded_engine):
    body = client.get("/stats").json()
    with Session(seeded_engine) as session:
        responses = session.execute(select(func.count(ItemResponse.id))).scalar_one()
    assert body == {
        "n_results": len(results),
        "n_item_responses": responses,
        "n_students": results["student_id"].nunique(),
        "n_classes": results["class_id"].nunique(),
        "n_schools": 5,
        "n_topics": 12,
        "archive_from": 2022,
        "archive_to": 2025,
    }


def test_stats_follow_school(client, results):
    body = client.get("/stats?school_id=5").json()
    school = results[results["school_id"] == 5]
    assert (body["n_results"], body["n_students"], body["n_classes"], body["n_schools"]) == (
        len(school), school["student_id"].nunique(), school["class_id"].nunique(), 1
    )
    # По 8 заданий в каждом тесте: ответов на задания в 8 раз больше, чем результатов тестов.
    assert body["n_item_responses"] == 8 * len(school)
    assert client.get("/stats?school_id=999").status_code == 404


def test_difficulty_how(client, results):
    topic = next(item for item in client.get("/topics/difficulty").json() if item["topic_id"] == 3)
    check_how(topic["how"])
    fractions = results[results["topic_id"] == 3]
    assert (topic["how"]["n_students"], topic["how"]["n_results"]) == (fractions["student_id"].nunique(), len(fractions))


def test_comparison_how_has_p_and_effect(client):
    body = client.get("/textbooks/compare?topic_id=3").json()
    check_how(body["how"])
    assert [test["p_value"] for test in body["how"]["tests"]] == [pair["p_adjusted"] for pair in body["comparisons"]]
    assert [test["effect_size"] for test in body["how"]["tests"]] == [pair["cohens_d"] for pair in body["comparisons"]]
    assert body["how"]["n_students"] == sum(book["n_students"] for book in body["textbooks"])


def test_decision_how(client, results):
    b = next(item for item in client.get("/textbooks/decisions").json()["textbooks"] if item["textbook"] == "Учебник B")
    check_how(b["how"])
    assert b["how"]["n_results"] == int((results["textbook"] == "Учебник B").sum())
    assert len(b["how"]["tests"]) == len(b["weaker"]) + len(b["stronger"])
    assert all(test["p_value"] < 0.05 and test["effect_name"] == "d Коэна" for test in b["how"]["tests"])


def test_hours_how(client):
    topics = {item["topic_id"]: item for item in client.get("/topics/difficulty").json()}
    for item in client.get("/recommendations").json()["items"]:
        check_how(item["how"])
        assert item["how"]["n_results"] == topics[item["topic_id"]]["how"]["n_results"]
        assert item["how"]["tests"][0]["effect_size"] == topics[item["topic_id"]]["difficulty_index"]


def test_root_how_lists_its_links(client):
    body = client.get("/topics/prerequisites").json()
    fractions = next(root for root in body["roots"] if root["topic"] == "Дроби")
    check_how(fractions["how"])
    links = [link for link in body["links"] if link["from_topic"] == "Дроби"]
    assert [test["p_value"] for test in fractions["how"]["tests"]] == [link["p_adjusted"] for link in links]
    assert fractions["how"]["tests"][0]["effect_label"] == "2,7 балла на каждые 10"
    assert fractions["how"]["n_students"] == body["n_students"]


def test_outlier_how(client, results):
    outlier = client.get("/classes/outliers").json()["outliers"][0]
    check_how(outlier["how"])
    cell = results[(results["class_id"] == outlier["class_id"]) & (results["topic_id"] == outlier["topic_id"])]
    assert (outlier["how"]["n_students"], outlier["how"]["n_results"]) == (cell["student_id"].nunique(), len(cell))
    assert outlier["how"]["tests"][0]["effect_size"] == outlier["robust_z"]
    assert outlier["how"]["tests"][0]["effect_label"] == "−9,1 балла от ожидаемого"
