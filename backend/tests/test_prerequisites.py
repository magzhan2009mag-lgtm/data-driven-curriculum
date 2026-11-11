import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.analytics.data import RESULT_COLUMNS, load_results
from app.analytics.difficulty import topic_difficulty
from app.analytics.prerequisites import (
    MIN_STD_COEF,
    format_points,
    root_dependents,
    topic_prerequisites,
    unique_cov,
)
from app.analytics.recommendations import (
    change_limit,
    recommend_by_textbook,
    recommend_hours,
    recommend_optimal_hours,
)
from app.main import app, get_db

PLANTED = {("Дроби", "Проценты"), ("Дроби", "Десятичные дроби"), ("Отрицательные числа", "Уравнения")}


@pytest.fixture(scope="module")
def results(seeded_engine) -> pd.DataFrame:
    with Session(seeded_engine) as session:
        return load_results(session)


@pytest.fixture(scope="module")
def prerequisites(results) -> dict:
    return topic_prerequisites(results)


@pytest.fixture(scope="module")
def client(seeded_engine):
    def override_get_db():
        with Session(seeded_engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def topic(topic_id, level, hours, index) -> dict:
    return {"topic_id": topic_id, "topic": f"Тема {topic_id}", "level": level, "hours_planned": hours,
            "difficulty_index": index, "avg_score": 60.0, "fail_rate": 0.2}


def test_seed_has_exactly_the_planted_links(prerequisites):
    found = {(link["from_topic"], link["to_topic"]) for link in prerequisites["links"]}
    assert found == PLANTED
    assert all(link["std_coef"] >= MIN_STD_COEF and link["p_adjusted"] < 0.05 for link in prerequisites["links"])
    # Ранняя тема всегда раньше по программе.
    assert all(link["from_topic_id"] < link["to_topic_id"] for link in prerequisites["links"])


def test_seed_roots_are_fractions_and_negative_numbers(prerequisites):
    roots = {root["topic"]: root for root in prerequisites["roots"]}
    assert set(roots) == {"Дроби", "Отрицательные числа"}
    assert roots["Отрицательные числа"]["level"] == "medium"
    assert {item["topic"] for item in roots["Дроби"]["dependents"]} == {"Проценты", "Десятичные дроби"}
    assert roots["Дроби"]["text"] == (
        "Тема «Проценты» сложная, но корень — тема «Дроби»: пробелы в ней переходят в «Десятичные дроби» "
        "и «Проценты». Сама тема «Дроби» тоже сложная."
    )
    assert "Сама она средней сложности" in roots["Отрицательные числа"]["text"]


def test_no_links_without_dependencies(independent_engine):
    with Session(independent_engine) as session:
        response = topic_prerequisites(load_results(session))
    assert response["links"] == []
    assert response["roots"] == []
    assert response["conclusion"].startswith("Связей между темами не найдено")


def test_link_text_is_in_points(prerequisites):
    link = next(link for link in prerequisites["links"] if link["to_topic"] == "Проценты")
    assert link["points"] == pytest.approx(10 * link["coef"], abs=0.05)
    assert link["text"].startswith("Ученики, которые написали «Дроби» на 10 баллов хуже, чем ученики их уровня")
    assert "пишут «Проценты» в среднем на" in link["text"]


@pytest.mark.parametrize(
    ("value", "text"),
    [(2.5, "2,5 балла"), (3.0, "3 балла"), (1.0, "1 балл"), (5.0, "5 баллов"), (2.04, "2 балла")],
)
def test_format_points(value, text):
    assert format_points(value) == text


def test_unique_cov_removes_common_level():
    # Один общий уровень и шум: после вычитания общего уровня темы почти не связаны.
    rng = np.random.default_rng(0)
    level = rng.normal(0, 10, (2000, 1))
    scores = 60 + level + rng.normal(0, 6, (2000, 6))
    unique = unique_cov(np.cov(scores, rowvar=False))
    off_diagonal = unique[~np.eye(6, dtype=bool)]
    assert np.abs(off_diagonal).max() < 0.1 * np.diag(unique).min()


def test_too_few_students_give_no_links():
    frame = pd.DataFrame(
        [
            {"student_id": student, "topic_id": topic_id, "topic": f"Тема {topic_id}", "hours_planned": 6,
             "textbook_id": 1, "textbook": "Учебник A", "school_id": 1, "school": "Школа №1",
             "class_id": 1, "class": "6А", "score": 50 + student + topic_id}
            for student in range(10)
            for topic_id in range(1, 5)
        ],
        columns=RESULT_COLUMNS,
    )
    response = topic_prerequisites(frame)
    assert response["links"] == []
    assert response["conclusion"] == "Мало данных, чтобы искать связи между темами."


def test_api_format(client):
    body = client.get("/topics/prerequisites").json()
    assert set(body) == {"topics", "links", "roots", "n_students", "conclusion", "note"}
    assert [item["topic_id"] for item in body["topics"]] == sorted(item["topic_id"] for item in body["topics"])
    assert set(body["topics"][0]) == {"topic_id", "topic", "level"}
    assert set(body["links"][0]) == {
        "from_topic_id", "from_topic", "to_topic_id", "to_topic", "coef", "std_coef", "p_value", "p_adjusted",
        "points", "text",
    }
    assert set(body["roots"][0]) == {"topic_id", "topic", "level", "dependents", "text", "how"}
    assert set(body["roots"][0]["dependents"][0]) == {"topic_id", "topic", "level"}
    assert body["n_students"] > 500
    assert body["conclusion"] == "Найдено связей между темами: 3. Корни проблемы: «Дроби» и «Отрицательные числа»."


def test_medium_root_gets_one_hour():
    topics = [topic(1, "medium", 7, 0.3), topic(2, "hard", 6, 0.45), topic(3, "easy", 9, 0.1)]
    response = recommend_hours(topics, {1: ["Тема 2"]})
    items = {item["topic_id"]: item for item in response["items"]}
    assert items[1]["delta"] == 1
    assert "От неё зависит тема «Тема 2»" in items[1]["reason"]
    assert sum(item["hours_recommended"] for item in response["items"]) == 22


def test_hard_root_gets_extra_hour_within_limit():
    topics = [topic(1, "hard", 5, 0.42), topic(2, "hard", 5, 0.6), topic(3, "easy", 9, 0.1), topic(4, "easy", 9, 0.1)]
    plain = {item["topic_id"]: item["delta"] for item in recommend_hours(topics)["items"]}
    rooted = recommend_hours(topics, {1: ["Тема 2"], 2: ["Тема 1"]})
    deltas = {item["topic_id"]: item["delta"] for item in rooted["items"]}
    assert deltas[1] == plain[1] + 1
    # У темы 2 нужда уже равна лимиту: корень не может получить больше.
    assert deltas[2] == plain[2] == change_limit(5)
    reason = next(item["reason"] for item in rooted["items"] if item["topic_id"] == 2)
    assert "поэтому ей нужен ещё час" in reason
    assert "чтобы не менять программу резко" in reason


def test_easy_topic_is_never_a_root():
    topics = [topic(1, "easy", 7, 0.2), topic(2, "hard", 6, 0.45), topic(3, "easy", 9, 0.1)]
    items = {item["topic_id"]: item["delta"] for item in recommend_hours(topics, {1: ["Тема 2"]})["items"]}
    assert items[1] <= 0


def test_seed_hours_include_roots(results, prerequisites):
    response = recommend_by_textbook(results)
    deltas = {item["topic"]: item["delta"] for item in response["items"]}
    assert deltas["Дроби"] == 2
    assert deltas["Отрицательные числа"] == 1
    assert sum(item["hours_recommended"] for item in response["items"]) == 84
    negative = next(item for item in response["items"] if item["topic"] == "Отрицательные числа")
    assert "От неё зависит тема «Уравнения»" in negative["reason"]

    # Линейное программирование с теми же корнями даёт тот же ответ.
    optimal = recommend_optimal_hours(topic_difficulty(results), root_dependents(prerequisites))
    assert {item["topic"]: item["delta"] for item in optimal["items"]} == deltas
