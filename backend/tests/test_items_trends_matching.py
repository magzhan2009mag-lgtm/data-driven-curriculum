import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from scipy.special import expit
from sqlalchemy.orm import Session

from app.analytics.data import load_item_responses, load_results, load_students, load_year_stats
from app.analytics.items import item_quality, point_biserial, rasch_difficulties
from app.analytics.matching import match_pair, match_textbooks
from app.analytics.trends import IMPROVING, STABLE, WORSENING, topic_trends
from app.main import app, get_db
from scripts.seed import BAD_ITEMS, TESTS_PER_TOPIC, TOPICS, item_difficulties


@pytest.fixture(scope="module")
def db(seeded_engine):
    with Session(seeded_engine) as session:
        yield session


@pytest.fixture(scope="module")
def results(db) -> pd.DataFrame:
    return load_results(db)


@pytest.fixture(scope="module")
def client(seeded_engine):
    def override_get_db():
        with Session(seeded_engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def topic_ids(results: pd.DataFrame) -> dict[str, int]:
    return {row["topic"]: int(row["topic_id"]) for row in results.drop_duplicates("topic_id").to_dict("records")}


def simulated_rasch(difficulties: np.ndarray, students: int = 800) -> pd.DataFrame:
    rng = np.random.default_rng(3)
    abilities = rng.normal(0, 1, students)
    answers = rng.random((students, len(difficulties))) < expit(abilities[:, None] - difficulties)
    return pd.DataFrame(answers.astype(float))


def test_rasch_recovers_simulated_difficulties():
    difficulties = np.linspace(-1.5, 1.5, 12)
    estimate = rasch_difficulties(simulated_rasch(difficulties))
    assert np.corrcoef(estimate, difficulties)[0, 1] > 0.98
    assert estimate.mean() == pytest.approx(0, abs=1e-6)
    assert estimate.to_numpy() == pytest.approx(difficulties, abs=0.3)


def test_rasch_handles_missing_answers():
    difficulties = np.linspace(-1, 1, 8)
    matrix = simulated_rasch(difficulties)
    matrix = matrix.mask(np.random.default_rng(4).random(matrix.shape) < 0.1)
    assert np.corrcoef(rasch_difficulties(matrix), difficulties)[0, 1] > 0.95


def test_rasch_leaves_item_without_errors_empty():
    matrix = simulated_rasch(np.array([-1.0, 0.0, 1.0]))
    matrix[99] = 1.0
    estimate = rasch_difficulties(matrix)
    assert np.isnan(estimate[99])
    assert estimate.drop(99).notna().all()


def item_rows() -> pd.DataFrame:
    """Задание 1 совпадает с сильными учениками, задание 2 от них не зависит."""
    rows = []
    for student, (first, second, others) in enumerate(
        (first, second, others) for first, others in [(0, 0), (0, 1), (1, 3), (1, 4)] for second in (0, 1)
    ):
        answers = [first, second, *([1] * others), *([0] * (4 - others))]
        for number, answer in enumerate(answers, start=1):
            rows.append({"topic": "Тема", "test_id": 1, "test_number": 1, "item_id": number, "item_number": number,
                         "student_id": student, "correct": bool(answer)})
    return pd.DataFrame(rows)


def test_point_biserial_separates_good_and_useless_item():
    correlations = point_biserial(item_rows())
    assert correlations[1] > 0.6
    assert abs(correlations[2]) < 0.2


def test_seed_bad_items_are_found(db, results):
    found = set()
    for name, topic_id in topic_ids(results).items():
        quality = item_quality(load_item_responses(db, topic_id), topic_id)
        found |= {(name, item["test_number"], item["item_number"]) for item in quality["items"] if item["is_bad"]}
    assert found == BAD_ITEMS


def test_seed_rasch_matches_planted_difficulties(db, results):
    position = [name for name, _, _ in TOPICS].index("Проценты")
    planted = item_difficulties()[position * TESTS_PER_TOPIC:(position + 1) * TESTS_PER_TOPIC]
    topic_id = topic_ids(results)["Проценты"]
    items = item_quality(load_item_responses(db, topic_id), topic_id)["items"]
    expected = [planted[item["test_number"] - 1, item["item_number"] - 1] for item in items]
    estimated = [item["rasch_difficulty"] for item in items]
    assert np.corrcoef(expected, estimated)[0, 1] > 0.9


def trend_tables(slope: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(5)
    results = pd.DataFrame(
        [{"school_id": school, "topic_id": 1, "topic": "Тема", "score": 60 + school + offset}
         for school in range(1, 5) for offset in (-2, 2)]
    )
    archive = pd.DataFrame(
        [{"topic_id": 1, "school_id": school, "year": 2026 - back,
          "avg_score": 60 + school - slope * back + rng.normal(0, 0.2)}
         for school in range(1, 5) for back in range(1, 5)]
    )
    return results, archive


@pytest.mark.parametrize(("slope", "direction"), [(-2.0, WORSENING), (2.0, IMPROVING), (0.0, STABLE)])
def test_trend_direction(slope, direction):
    item = topic_trends(*trend_tables(slope))[0]
    assert item["direction"] == direction
    assert item["slope_per_year"] == pytest.approx(slope, abs=0.2)
    assert [row["year"] for row in item["by_year"]] == [2022, 2023, 2024, 2025, 2026]


def test_trends_without_archive():
    results, archive = trend_tables(1.0)
    assert topic_trends(results, archive.iloc[0:0]) == []


def test_seed_trends_find_planted_directions(db, results):
    items = {item["topic"]: item for item in topic_trends(results, load_year_stats(db))}
    assert len(items) == 12
    assert items["Дроби"]["direction"] == WORSENING
    assert items["Геометрические фигуры"]["direction"] == IMPROVING
    assert "ухудшается" in items["Дроби"]["text"]
    others = [item for name, item in items.items() if name not in {"Дроби", "Геометрические фигуры"}]
    assert all(item["direction"] == STABLE for item in others)


def confounded_students() -> pd.DataFrame:
    """Учебник A чаще у сильных учеников, а самого эффекта учебника нет."""
    rng = np.random.default_rng(6)
    pretest = rng.normal(65, 12, 800)
    gets_a = rng.random(800) < expit((pretest - 65) / 8)
    return pd.DataFrame(
        {
            "student_id": range(800),
            "textbook": np.where(gets_a, "A", "B"),
            "z": (pretest - 65) / 12 + rng.normal(0, 0.5, 800),
            "pretest_score": pretest,
            "school_id": rng.integers(1, 4, 800),
        }
    )


def test_matching_removes_confounding():
    data = confounded_students()
    raw_difference = data.loc[data["textbook"] == "A", "z"].mean() - data.loc[data["textbook"] == "B", "z"].mean()
    pair = match_pair(data, "A", "B")
    assert raw_difference > 0.8
    assert abs(pair["smd_before"]) > 0.8
    assert abs(pair["smd_after"]) < 0.1
    assert abs(pair["mean_difference"]) < 0.15
    assert pair["n_matched"] >= 30


def test_matching_is_one_to_one():
    data = confounded_students()
    pair = match_pair(data, "A", "B")
    assert pair["n_matched"] <= min(pair["n_a"], pair["n_b"])


def test_seed_matching_agrees_with_planted_effect(db, results):
    topic_id = topic_ids(results)["Дроби"]
    response = match_textbooks(results, load_students(db), topic_id)
    pair = next(item for item in response["pairs"] if {item["a"], item["b"]} == {"Учебник A", "Учебник B"})
    assert pair["significant"] is True
    assert pair["mean_difference"] > 0
    assert abs(pair["smd_after"]) < 0.1
    assert "Учебник A выше, чем Учебник B" in response["conclusion"]


def test_endpoints_answer(client, results):
    topic_id = topic_ids(results)["Дроби"]
    quality = client.get("/items/quality", params={"topic_id": topic_id}).json()
    assert len(quality["items"]) == 16
    assert quality["n_bad"] == 1
    assert len(client.get("/topics/trends").json()) == 12
    assert len(client.get("/textbooks/matching", params={"topic_id": topic_id}).json()["pairs"]) == 3


def test_unknown_topic_is_404(client):
    assert client.get("/items/quality", params={"topic_id": 999}).status_code == 404
    assert client.get("/textbooks/matching", params={"topic_id": 999}).status_code == 404
