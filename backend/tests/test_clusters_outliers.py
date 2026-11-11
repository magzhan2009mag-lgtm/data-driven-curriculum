import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.analytics.clusters import cluster_schools, cluster_topics
from app.analytics.data import load_results
from app.analytics.difficulty import topic_difficulty
from app.analytics.outliers import class_outliers
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


def topic(topic_id: int, avg_score: float, fail_rate: float, std_score: float = 10.0) -> dict:
    return {"topic_id": topic_id, "topic": f"Тема {topic_id}", "avg_score": avg_score,
            "fail_rate": fail_rate, "std_score": std_score}


def test_kmeans_separates_clear_groups():
    topics = [topic(1, 40, 0.6), topic(2, 42, 0.58), topic(3, 65, 0.2), topic(4, 66, 0.22),
              topic(5, 90, 0.01), topic(6, 92, 0.0)]
    groups = {group["group"]: {member["id"] for member in group["members"]} for group in cluster_topics(topics)}
    assert groups == {"Слабые результаты": {1, 2}, "Средние результаты": {3, 4}, "Сильные результаты": {5, 6}}


def test_too_few_topics_are_not_clustered():
    assert cluster_topics([topic(1, 40, 0.6)]) == []


def school_rows(school_id: int, level: int) -> list[dict]:
    return [{"school_id": school_id, "school": f"Школа №{school_id}", "topic_id": topic_id, "score": level + topic_id}
            for topic_id in range(1, 5)]


def test_schools_split_by_level():
    frame = pd.DataFrame([row for school_id, level in [(1, 50), (2, 52), (3, 80), (4, 82)]
                          for row in school_rows(school_id, level)])
    groups = {group["group"]: {member["id"] for member in group["members"]} for group in cluster_schools(frame)}
    assert groups == {"Результаты ниже": {1, 2}, "Результаты выше": {3, 4}}


def test_clusters_on_seed_cover_everything(results):
    topics = cluster_topics(topic_difficulty(results))
    assert sum(len(group["members"]) for group in topics) == 12
    assert [group["avg_score"] for group in topics] == sorted(group["avg_score"] for group in topics)
    assert sum(len(group["members"]) for group in cluster_schools(results)) == 5


def class_table(levels: list[float], dip: dict[tuple[int, int], float] | None = None) -> pd.DataFrame:
    """Классы разного уровня, 4 темы разной сложности, шум около 1 балла; dip сдвигает одну пару «класс × тема»."""
    dip = dip or {}
    rng = np.random.default_rng(0)
    topic_bases = {1: 0, 2: -10, 3: 5, 4: -3}
    rows = []
    for class_id, level in enumerate(levels, start=1):
        for topic_id, base in topic_bases.items():
            cell = level + base + rng.normal(0, 1) + dip.get((class_id, topic_id), 0)
            for offset in (-4, 0, 4):
                rows.append({"class_id": class_id, "class": f"6-{class_id}", "school_id": 1, "school": "Школа №1",
                             "textbook": "A", "topic_id": topic_id, "topic": f"Тема {topic_id}",
                             "score": cell + offset})
    return pd.DataFrame(rows)


def test_failed_topic_in_one_class_is_found():
    levels = [60, 64, 57, 70, 62, 55, 66, 59, 63, 61, 58, 65]
    result = class_outliers(class_table(levels, dip={(3, 2): -12}))
    assert [(item["class"], item["topic"]) for item in result["outliers"]] == [("6-3", "Тема 2")]
    item = result["outliers"][0]
    assert item["direction"] == "ниже ожидаемого"
    assert item["difference"] < -8
    assert "Тема 2" in item["text"] and "6-3" in item["text"]


def test_class_level_alone_is_not_an_outlier():
    # Класс 6-4 сильнее остальных по всем темам: это его уровень, а не аномалия темы.
    result = class_outliers(class_table([60, 61, 59, 85, 62, 58, 63, 57, 64, 60]))
    assert result["outliers"] == []
    assert "не найдено" in result["conclusion"]


def test_too_few_topics_give_no_outliers():
    table = class_table([60, 61, 20])
    result = class_outliers(table[table["topic_id"] <= 2])
    assert result["outliers"] == []
    assert "недостаточно" in result["conclusion"]


def test_seed_anomaly_is_the_only_outlier(results):
    from scripts.seed import ANOMALY

    school_no, class_name, topic = ANOMALY
    found = [(item["school"], item["class"], item["topic"]) for item in class_outliers(results)["outliers"]]
    assert found == [(f"Школа №{school_no}", class_name, topic)]


def test_new_endpoints_answer(client):
    clusters = client.get("/clusters").json()
    assert set(clusters) == {"topics", "schools"}
    assert client.get("/classes/outliers").json()["n_classes"] == 22
