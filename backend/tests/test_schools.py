import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.analytics import explain
from app.analytics.data import load_item_responses, load_results, load_year_stats
from app.analytics.difficulty import topic_difficulty
from app.analytics.hours_effect import hours_effect
from app.analytics.prerequisites import root_dependents, topic_prerequisites
from app.analytics.recommendations import recommend_by_textbook, recommend_optimal_hours
from app.analytics.schools import roots_in_school
from app.main import app, get_db

SCHOOL_ID = 5
SCHOOL = "Школа №5"
ENDPOINTS = [
    "/topics/difficulty",
    "/topics/trends",
    "/topics/prerequisites",
    "/textbooks/compare",
    "/textbooks/compare?topic_id=3",
    "/textbooks/regression",
    "/textbooks/matching",
    "/recommendations",
    "/recommendations/optimal",
    "/recommendations/explanation",
    "/hours/effect",
    "/clusters",
    "/classes/outliers",
    "/items/quality?topic_id=3",
    "/summary",
    "/textbooks/decisions",
    "/recommendations/export.csv",
]


@pytest.fixture(scope="module")
def results(seeded_engine) -> pd.DataFrame:
    with Session(seeded_engine) as session:
        return load_results(session)


@pytest.fixture(scope="module")
def school(results) -> pd.DataFrame:
    return results[results["school_id"] == SCHOOL_ID]


@pytest.fixture(scope="module")
def client(seeded_engine):
    def override_get_db():
        with Session(seeded_engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def no_claude(monkeypatch):
    # Пояснения ИИ в этих тестах не нужны: без ответа Claude эндпоинт отдаёт шаблоны.
    monkeypatch.setattr(explain, "request_explanations", lambda facts: None)


def with_school(path: str, school_id: int) -> str:
    return f"{path}{'&' if '?' in path else '?'}school_id={school_id}"


def test_schools_list(client, results):
    body = client.get("/schools").json()
    assert [item["school"] for item in body] == [f"Школа №{number}" for number in range(1, 6)]
    assert sum(item["n_classes"] for item in body) == results["class_id"].nunique()
    assert sum(item["n_students"] for item in body) == results["student_id"].nunique()
    assert set(body[0]) == {"school_id", "school", "n_classes", "n_students"}


@pytest.mark.parametrize("path", ENDPOINTS)
def test_every_endpoint_accepts_school(client, path):
    assert client.get(with_school(path, SCHOOL_ID)).status_code == 200


@pytest.mark.parametrize("path", ENDPOINTS)
def test_unknown_school_is_404(client, path):
    response = client.get(with_school(path, 999))
    assert response.status_code == 404
    assert response.json()["detail"] == "Школа не найдена"


def test_difficulty_uses_only_school(client, results, school):
    body = client.get(with_school("/topics/difficulty", SCHOOL_ID)).json()
    overall = {item["topic_id"]: item for item in client.get("/topics/difficulty").json()}
    class_ids = set(school["class_id"])
    for item in body:
        assert item["avg_score"] == round(school.loc[school["topic_id"] == item["topic_id"], "score"].mean(), 1)
        assert [row["school"] for row in item["by_school"]] == [SCHOOL]
        assert {row["class_id"] for row in item["by_class"]} == class_ids
        assert item["avg_score_all"] == overall[item["topic_id"]]["avg_score"]
        assert item["fail_rate_all"] == overall[item["topic_id"]]["fail_rate"]


def test_items_use_only_school_students(client, seeded_engine, school):
    body = client.get(with_school("/items/quality?topic_id=3", SCHOOL_ID)).json()
    with Session(seeded_engine) as session:
        responses = load_item_responses(session, 3)
    own = responses[responses["student_id"].isin(set(school["student_id"]))]
    expected = own.groupby("item_id")["correct"].mean().round(3)
    assert {item["item_id"]: item["p_correct"] for item in body["items"]} == expected.to_dict()


def test_trends_use_only_school(client, seeded_engine, school):
    fractions = next(item for item in client.get(with_school("/topics/trends", SCHOOL_ID)).json() if item["topic_id"] == 3)
    with Session(seeded_engine) as session:
        archive = load_year_stats(session)
    archive = archive[(archive["school_id"] == SCHOOL_ID) & (archive["topic_id"] == 3)].set_index("year")["avg_score"]
    by_year = {row["year"]: row["avg_score"] for row in fractions["by_year"]}
    for year, value in archive.items():
        assert by_year[year] == pytest.approx(value, abs=0.05)
    current = max(by_year)
    assert by_year[current] == round(school.loc[school["topic_id"] == 3, "score"].mean(), 1)


def test_recommendations_use_only_school(client, results, school):
    body = client.get(with_school("/recommendations", SCHOOL_ID)).json()
    roots = roots_in_school(root_dependents(topic_prerequisites(results)), topic_difficulty(school))
    expected = recommend_by_textbook(school, roots, SCHOOL)
    assert [item["delta"] for item in body["items"]] == [item["delta"] for item in expected["items"]]
    assert sum(item["hours_recommended"] for item in body["items"]) == 84
    assert body["hours_moved_all"] == client.get("/recommendations").json()["hours_moved"]
    assert all("delta_all" in item and "hours_recommended_all" in item for item in body["items"])


def test_few_students_rule_in_one_school(client):
    compare = client.get(with_school("/textbooks/compare", SCHOOL_ID)).json()
    assert all(pair["p_adjusted"] is None for pair in compare["comparisons"])
    assert compare["school_note"].startswith("В Школе №5 у учебников A и B меньше 30 учеников")
    assert "Смотрите сравнение по всем школам" in compare["school_note"]
    assert all(book["adjusted_score_all"] is not None for book in compare["textbooks"])
    assert {book["name"]: book["enough_data"] for book in compare["textbooks"]} == {
        "Учебник A": False, "Учебник B": False, "Учебник C": True
    }

    plans = {plan["textbook"]: plan for plan in client.get(with_school("/recommendations", SCHOOL_ID)).json()["textbook_plans"]}
    assert not plans["Учебник A"]["enough_data"] and not plans["Учебник B"]["enough_data"]
    assert plans["Учебник C"]["enough_data"]
    assert "этого мало для отдельного плана" in plans["Учебник A"]["text"]

    regression = client.get(with_school("/textbooks/regression", SCHOOL_ID)).json()
    assert regression["effects"] == []
    assert regression["school_note"]


def test_without_school_nothing_changes(client):
    compare = client.get("/textbooks/compare").json()
    assert compare["school_note"] is None
    assert all(book["enough_data"] for book in compare["textbooks"])
    assert all(plan["enough_data"] for plan in client.get("/recommendations").json()["textbook_plans"])


def test_outliers_are_found_on_all_schools_and_shown_for_one(client):
    fourth = client.get(with_school("/classes/outliers", 4)).json()
    assert [(item["class"], item["school_id"]) for item in fourth["outliers"]] == [("6Д", 4)]
    assert fourth["scope_note"]
    fifth = client.get(with_school("/classes/outliers", SCHOOL_ID)).json()
    assert fifth["outliers"] == []
    assert fifth["conclusion"].startswith("В Школе №5")


def test_prerequisites_and_clusters_use_all_schools(client):
    prerequisites = client.get(with_school("/topics/prerequisites", SCHOOL_ID)).json()
    assert len(prerequisites["links"]) == 3
    assert prerequisites["scope_note"]
    clusters = client.get(with_school("/clusters", SCHOOL_ID)).json()
    assert [member["id"] for group in clusters["schools"] for member in group["members"]] == [SCHOOL_ID]


def test_compare_uses_only_school(client, school):
    body = client.get(with_school("/textbooks/compare?topic_id=3", SCHOOL_ID)).json()
    fractions = school[school["topic_id"] == 3]
    expected = fractions.groupby("textbook")["student_id"].nunique().to_dict()
    assert {book["name"]: book["n_students"] for book in body["textbooks"]} == expected
    for book in body["textbooks"]:
        own = fractions.loc[fractions["textbook"] == book["name"], "score"].mean()
        assert book["avg_score"] == round(own, 1)


def test_optimal_and_hours_effect_use_only_school(client, results, school):
    roots = roots_in_school(root_dependents(topic_prerequisites(results)), topic_difficulty(school))
    optimal = client.get(with_school("/recommendations/optimal", SCHOOL_ID)).json()
    expected = recommend_optimal_hours(topic_difficulty(school), roots)
    assert [item["delta"] for item in optimal["items"]] == [item["delta"] for item in expected["items"]]
    effect = client.get(with_school("/hours/effect", SCHOOL_ID)).json()
    assert effect == hours_effect(topic_difficulty(school))


def test_matching_uses_only_school_students(client, school):
    body = client.get(with_school("/textbooks/matching", SCHOOL_ID)).json()
    assert body["school_note"].startswith("В Школе №5")
    overall = client.get("/textbooks/matching").json()
    assert "school_note" not in overall
    assert body["pairs"] != overall["pairs"]


def test_explanation_skips_textbooks_without_plan(client):
    body = client.get(with_school("/recommendations", SCHOOL_ID)).json()
    facts = explain.build_facts(body["items"])
    assert all(row["textbook"] == "Учебник C" for fact in facts for row in fact["by_textbook"])


def test_root_gets_hour_only_if_dependent_is_hard_in_school(client):
    # В Школе №5 сложных тем нет: «Дроби» — корень по всем школам, но лишний час им здесь не нужен.
    fifth = {item["topic"]: item for item in client.get(with_school("/recommendations", SCHOOL_ID)).json()["items"]}
    assert fifth["Дроби"]["delta"] == 0
    assert "зависят" not in fifth["Дроби"]["reason"]
    root_card = next(card for card in client.get(with_school("/summary", SCHOOL_ID)).json()["cards"] if card["kind"] == "root")
    assert "В Школе №5 зависимые темы не сложные" in root_card["text"]

    # В Школе №1 «Проценты» и «Десятичные дроби» сложные: «Дроби» получают час как корень.
    first = {item["topic"]: item for item in client.get(with_school("/recommendations", 1)).json()["items"]}
    assert "поэтому ей нужен ещё час" in first["Дроби"]["reason"]
    root_card = next(card for card in client.get(with_school("/summary", 1)).json()["cards"] if card["kind"] == "root")
    assert "лишний час" not in root_card["text"]


def test_roots_in_school_keeps_root_with_hard_dependent():
    roots = {3: ["Проценты", "Десятичные дроби"], 7: ["Уравнения"]}
    topics = [{"topic": "Проценты", "level": "hard"}, {"topic": "Десятичные дроби", "level": "medium"},
              {"topic": "Уравнения", "level": "medium"}]
    assert roots_in_school(roots, topics) == {3: ["Проценты", "Десятичные дроби"]}


def test_all_schools_plan_keeps_all_roots(client):
    body = client.get(with_school("/recommendations", SCHOOL_ID)).json()
    overall = {item["topic"]: item for item in client.get("/recommendations").json()["items"]}
    assert {item["topic"]: item["delta_all"] for item in body["items"]} == {name: item["delta"] for name, item in overall.items()}
