import numpy as np
import pandas as pd
import pytest
from sqlalchemy.orm import Session

from app.analytics.data import RESULT_COLUMNS, load_results
from app.analytics.difficulty import compute_index, difficulty_level, topic_difficulty
from app.analytics.recommendations import change_limit, hours_word, recommend_hours
from app.analytics.textbooks import MIN_STUDENTS, bootstrap_ci, compare_textbooks, effect_label, holm_adjust


@pytest.fixture(scope="module")
def results(seeded_engine) -> pd.DataFrame:
    with Session(seeded_engine) as session:
        return load_results(session)


def rows(scores, topic_id=1, topic="Тема", textbook="Учебник A", textbook_id=1, first_student=1) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "student_id": first_student + offset,
                "topic_id": topic_id,
                "topic": topic,
                "hours_planned": 6,
                "textbook_id": textbook_id,
                "textbook": textbook,
                "school_id": 1,
                "school": "Школа №1",
                "class_id": 1,
                "class": "6А",
                "score": score,
            }
            for offset, score in enumerate(scores)
        ],
        columns=RESULT_COLUMNS,
    )


def topic(topic_id, level, hours, index=0.3) -> dict:
    return {"topic_id": topic_id, "topic": f"Тема {topic_id}", "level": level, "hours_planned": hours,
            "difficulty_index": index, "avg_score": 60.0, "fail_rate": 0.2}


def test_difficulty_formula():
    assert compute_index(50, 0.5) == pytest.approx(0.5)


@pytest.mark.parametrize(
    ("index", "level"),
    [(0.40, "hard"), (0.399, "medium"), (0.25, "medium"), (0.249, "easy")],
)
def test_difficulty_thresholds(index, level):
    assert difficulty_level(index) == level


def test_topic_difficulty_counts_fail_rate_below_50():
    item = topic_difficulty(rows([49, 50, 60, 41]))[0]
    assert item["avg_score"] == 50.0
    assert item["fail_rate"] == 0.5


def test_score_distribution_includes_100_in_last_bin():
    distribution = topic_difficulty(rows([100, 90, 0]))[0]["score_distribution"]
    assert len(distribution) == 10
    assert distribution[-1] == {"range": "90–100", "count": 2, "failing": False}
    assert distribution[0] == {"range": "0–9", "count": 1, "failing": True}
    assert [row["failing"] for row in distribution].count(True) == 5


def test_descriptive_statistics():
    item = topic_difficulty(rows([40, 50, 60, 90]))[0]
    assert item["median_score"] == 55.0
    assert item["std_score"] == pytest.approx(21.6, abs=0.05)


def test_single_result_has_zero_spread():
    item = topic_difficulty(rows([70]))[0]
    assert item["std_score"] == 0.0
    assert item["difficulty_z"] == 0.0
    assert item["is_anomalous"] is False


def test_anomalous_topic_is_flagged():
    easy = [rows([90, 92], topic_id=i, topic=f"Тема {i}") for i in range(1, 12)]
    hard = rows([10, 12], topic_id=12, topic="Провальная")
    items = topic_difficulty(pd.concat([*easy, hard]))
    assert items[0]["topic"] == "Провальная" and items[0]["is_anomalous"] is True
    assert not any(item["is_anomalous"] for item in items[1:])


def test_bootstrap_interval_contains_difference_and_repeats():
    rng = np.random.default_rng(1)
    a, b = rng.normal(1, 1, 200), rng.normal(0, 1, 200)
    low, high = bootstrap_ci(a, b)
    assert low < a.mean() - b.mean() < high
    assert 0 < low
    assert (low, high) == bootstrap_ci(a, b)


def test_mann_whitney_is_reported_but_welch_decides(results):
    topic_id = int(results.loc[results["topic"] == "Дроби", "topic_id"].iloc[0])
    pairs = compare_textbooks(results, topic_id)["comparisons"]
    pair = next(p for p in pairs if {p["a"], p["b"]} == {"Учебник A", "Учебник B"})
    assert pair["mann_whitney_p_adjusted"] < 0.05
    assert pair["mann_whitney_p_adjusted"] >= pair["mann_whitney_p"]
    assert pair["ci_low"] > 0


def test_seed_hard_topics(results):
    hard = {item["topic"] for item in topic_difficulty(results) if item["level"] == "hard"}
    assert hard == {"Дроби", "Проценты", "Уравнения"}


def test_holm_known_example():
    assert holm_adjust([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])


def test_holm_caps_at_one():
    assert holm_adjust([0.9, 0.8]) == [1.0, 1.0]


@pytest.mark.parametrize(
    ("d", "label"),
    [(0.19, "пренебрежимо мал"), (-0.2, "малый"), (0.5, "средний"), (-0.8, "большой")],
)
def test_effect_labels(d, label):
    assert effect_label(d) == label


def test_too_few_students_gives_no_conclusion():
    rng = np.random.default_rng(0)
    many = rows(rng.integers(40, 90, MIN_STUDENTS).tolist())
    few = rows([60, 70, 80], textbook="Учебник B", textbook_id=2, first_student=1000)
    result = compare_textbooks(pd.concat([many, few]))
    pair = result["comparisons"][0]
    assert pair["p_value"] is None and pair["significant"] is False
    assert pair["effect"] == "мало данных"
    assert "мало данных" in result["conclusion"]


def test_two_tests_of_one_student_count_once():
    data = pd.concat([rows([50, 60]), rows([70, 80])])
    assert compare_textbooks(data)["textbooks"][0]["n_students"] == 2


def test_equal_scores_do_not_break_comparison():
    data = pd.concat(
        [rows([70] * MIN_STUDENTS), rows([70] * MIN_STUDENTS, textbook="Учебник B", textbook_id=2, first_student=1000)]
    )
    pair = compare_textbooks(data)["comparisons"][0]
    assert pair["significant"] is False
    assert pair["cohens_d"] == 0
    assert pair["mann_whitney_p"] == 1.0


def test_textbook_b_is_worse_on_fractions(results):
    topic_id = int(results.loc[results["topic"] == "Дроби", "topic_id"].iloc[0])
    compared = compare_textbooks(results, topic_id)
    pair = next(p for p in compared["comparisons"] if {p["a"], p["b"]} == {"Учебник A", "Учебник B"})
    assert pair["significant"] is True
    assert pair["cohens_d"] > 0
    assert "Учебник A выше, чем Учебник B" in compared["conclusion"]


def test_comparison_without_topic_covers_all_topics(results):
    compared = compare_textbooks(results)
    assert compared["topic_id"] is None
    assert sum(book["n_students"] for book in compared["textbooks"]) == results["student_id"].nunique()


def test_hours_sum_is_preserved_on_seed(results):
    recommendations = recommend_hours(topic_difficulty(results))
    assert recommendations["total_hours"] == 84
    assert recommendations["hours_moved"] == 6
    assert sum(item["hours_recommended"] for item in recommendations["items"]) == 84
    assert sum(item["delta"] for item in recommendations["items"]) == 0


def test_only_hard_receive_and_only_easy_give(results):
    for item in recommend_hours(topic_difficulty(results))["items"]:
        if item["level"] == "medium":
            assert item["delta"] == 0
        if item["delta"] > 0:
            assert item["level"] == "hard"
        if item["delta"] < 0:
            assert item["level"] == "easy"


def test_limit_is_respected():
    topics = [topic(1, "hard", 5, 0.5), *(topic(i, "easy", 9, 0.1) for i in range(2, 6))]
    items = recommend_hours(topics)["items"]
    assert items[0]["delta"] == change_limit(5) == 2
    assert all(abs(item["delta"]) <= change_limit(item["hours_current"]) for item in items)


def test_stops_when_no_donors():
    items = recommend_hours([topic(1, "hard", 5, 0.5), topic(2, "medium", 6)])["items"]
    assert [item["delta"] for item in items] == [0, 0]
    assert "не осталось лёгких тем" in items[0]["reason"]


def test_hard_with_highest_pressure_gets_hour_first():
    topics = [topic(1, "hard", 10, 0.45), topic(2, "hard", 5, 0.45), topic(3, "easy", 4, 0.1)]
    items = {item["topic_id"]: item for item in recommend_hours(topics)["items"]}
    assert items[2]["delta"] == 2 and items[1]["delta"] == 0


def test_reason_has_numbers_and_no_promises():
    reason = recommend_hours([topic(1, "hard", 5, 0.5), topic(2, "easy", 9, 0.1)])["items"][0]["reason"]
    assert reason == (
        "Тема сложная: средний балл 60 из 100, не справились 20% учеников. Рекомендуем добавить 2 часа (5 → 7)."
    )


@pytest.mark.parametrize(
    ("count", "word"),
    [(1, "час"), (2, "часа"), (5, "часов"), (11, "часов"), (21, "час"), (22, "часа")],
)
def test_hours_word(count, word):
    assert hours_word(count) == word
