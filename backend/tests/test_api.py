import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app, get_db


@pytest.fixture(scope="module")
def client(seeded_engine):
    def override_get_db():
        with Session(seeded_engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def topics(client) -> list[dict]:
    return client.get("/topics/difficulty").json()


def topic_id_of(topics: list[dict], name: str) -> int:
    return next(item["topic_id"] for item in topics if item["topic"] == name)


def test_difficulty_format(topics):
    assert len(topics) == 12
    assert set(topics[0]) == {
        "topic_id", "topic", "hours_planned", "avg_score", "median_score", "std_score", "fail_rate",
        "difficulty_index", "difficulty_z", "is_anomalous", "level", "by_school", "score_distribution",
    }
    assert set(topics[0]["by_school"][0]) == {"school_id", "school", "avg_score"}
    assert len(topics[0]["by_school"]) == 5


def test_hardest_topic_is_first(topics):
    indexes = [item["difficulty_index"] for item in topics]
    assert indexes == sorted(indexes, reverse=True)
    assert topics[0]["level"] == "hard"


def test_compare_format(client, topics):
    topic_id = topic_id_of(topics, "Дроби")
    body = client.get("/textbooks/compare", params={"topic_id": topic_id}).json()
    assert body["topic_id"] == topic_id
    assert body["topic"] == "Дроби"
    assert set(body["textbooks"][0]) == {"textbook_id", "name", "n_students", "avg_score", "adjusted_score", "mean_z"}
    assert len(body["comparisons"]) == 3
    assert set(body["comparisons"][0]) == {
        "a", "b", "p_value", "p_adjusted", "cohens_d", "effect", "significant",
        "mann_whitney_p", "mann_whitney_p_adjusted", "ci_low", "ci_high",
    }
    assert body["conclusion"].startswith("Тема «Дроби»")
    assert body["limitation"]
    assert "Учебник C выглядит сильнее" in body["confounding_note"]


def test_compare_without_topic(client):
    body = client.get("/textbooks/compare").json()
    assert body["topic_id"] is None
    assert body["topic"] is None


def test_compare_unknown_topic(client):
    response = client.get("/textbooks/compare", params={"topic_id": 999})
    assert response.status_code == 404
    assert response.json()["detail"] == "Тема не найдена"


def test_recommendations_keep_total_hours(client):
    body = client.get("/recommendations").json()
    assert body["total_hours"] == 84
    assert sum(item["hours_recommended"] for item in body["items"]) == 84
    assert set(body["items"][0]) == {
        "topic_id", "topic", "level", "hours_current", "hours_recommended", "delta", "reason", "by_textbook",
    }
    assert len(body["textbook_plans"]) == 3
