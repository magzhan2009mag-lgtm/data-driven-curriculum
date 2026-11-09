import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.analytics.data import load_results
from app.analytics.difficulty import topic_difficulty
from app.analytics.hours_effect import CAVEAT, hours_effect
from app.analytics.recommendations import MIN_HOURS, change_limit, recommend_optimal_hours
from app.analytics.regression import textbook_regression
from app.main import app, get_db


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


def topic_id_of(results: pd.DataFrame, name: str) -> int:
    return int(results.loc[results["topic"] == name, "topic_id"].iloc[0])


def regression_table(difference: float) -> pd.DataFrame:
    """Шесть классов в двух школах; учебник B хуже A ровно на difference баллов."""
    rows = []
    classes = [(1, "A", 0.6), (1, "B", -0.4), (1, "A", -0.2), (2, "B", 0.3), (2, "A", -0.5), (2, "B", 0.2)]
    for class_id, (school_id, textbook, class_effect) in enumerate(classes, start=1):
        for offset in (-3, -1, 1, 3):
            base = 60 + 5 * (school_id - 1)
            score = base + class_effect + offset - (difference if textbook == "B" else 0)
            rows.append({"topic_id": 1, "topic": "Тема", "textbook": textbook, "school_id": school_id,
                         "class_id": class_id, "score": score})
    return pd.DataFrame(rows)


def test_regression_recovers_known_difference():
    effect = textbook_regression(regression_table(7))["effects"][0]
    assert effect["textbook"] == "B"
    assert effect["coef"] == pytest.approx(-7, abs=1)
    assert effect["ci_low"] < effect["coef"] < effect["ci_high"]
    assert effect["significant"] is True


def test_regression_needs_two_textbooks():
    table = regression_table(7)
    result = textbook_regression(table[table["textbook"] == "A"])
    assert result["effects"] == []
    assert "недостаточно" in result["conclusion"]


def test_regression_finds_weak_textbook_on_seed(results):
    result = textbook_regression(results, topic_id_of(results, "Дроби"))
    assert result["reference"] == "Учебник A"
    effect = next(item for item in result["effects"] if item["textbook"] == "Учебник B")
    assert effect["ci_low"] < -8 < effect["ci_high"]
    assert effect["significant"] is True
    assert "Учебник B ниже, чем Учебник A" in result["conclusion"]
    assert result["n_classes"] == 20


def test_regression_without_topic(results):
    result = textbook_regression(results)
    assert result["topic"] is None
    assert len(result["effects"]) == 2


def test_hours_effect_known_line():
    topics = [{"hours_planned": hours, "avg_score": 40 + 2 * hours} for hours in (3, 5, 8, 10)]
    result = hours_effect(topics)
    assert result["spearman_rho"] == 1.0
    assert result["slope"] == pytest.approx(2)
    assert "выше" in result["interpretation"]
    assert result["caveat"] == CAVEAT


def test_hours_effect_with_equal_hours_gives_no_numbers():
    result = hours_effect([{"hours_planned": 5, "avg_score": score} for score in (50, 60, 70)])
    assert result["spearman_rho"] is None and result["slope"] is None
    assert "недостаточно" in result["interpretation"]


def test_hours_effect_on_seed_keeps_caveat(results):
    result = hours_effect(topic_difficulty(results))
    assert result["n_topics"] == 12
    assert "прирост" in result["caveat"]


def topic(topic_id, level, hours, index) -> dict:
    return {"topic_id": topic_id, "topic": f"Тема {topic_id}", "level": level, "hours_planned": hours,
            "difficulty_index": index, "avg_score": 60.0, "fail_rate": 0.2}


def test_optimal_gives_hours_to_hardest_topic_first():
    topics = [topic(1, "hard", 5, 0.6), topic(2, "hard", 5, 0.45), topic(3, "easy", 9, 0.1)]
    items = {item["topic_id"]: item["delta"] for item in recommend_optimal_hours(topics)["items"]}
    assert items[3] == -3
    assert items[1] == 2 and items[2] == 1


def test_optimal_respects_minimum_hours():
    items = recommend_optimal_hours([topic(1, "hard", 5, 0.6), topic(2, "easy", 2, 0.1)])["items"]
    assert items[1]["hours_recommended"] == MIN_HOURS
    assert items[0]["delta"] == 1


def test_optimal_on_seed_keeps_all_constraints(results):
    response = recommend_optimal_hours(topic_difficulty(results))
    assert response["method"] == "linprog"
    assert sum(item["hours_recommended"] for item in response["items"]) == 84
    for item in response["items"]:
        assert isinstance(item["delta"], int)
        assert abs(item["delta"]) <= change_limit(item["hours_current"])
        if item["level"] == "medium":
            assert item["delta"] == 0
        if item["delta"] > 0:
            assert item["level"] == "hard"
        if item["delta"] < 0:
            assert item["level"] == "easy"


def test_new_endpoints_answer(client):
    assert client.get("/recommendations/optimal").json()["total_hours"] == 84
    assert client.get("/hours/effect").json()["n_topics"] == 12
    assert len(client.get("/textbooks/regression").json()["effects"]) == 2


def test_regression_unknown_topic(client):
    assert client.get("/textbooks/regression", params={"topic_id": 999}).status_code == 404
