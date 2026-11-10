import numpy as np
import pandas as pd
import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session

from app.models import (
    Base,
    Item,
    ItemResponse,
    School,
    SchoolClass,
    Student,
    Test,
    TestResult,
    Textbook,
    Topic,
    TopicYearStat,
)
from scripts.seed import ARCHIVE_YEARS, ITEMS_PER_TEST, generate, is_outdated, load_summary


def seeded_session(path) -> Session:
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    Base.metadata.create_all(engine)
    session = Session(engine)
    generate(session)
    return session


@pytest.fixture(scope="module")
def session(tmp_path_factory):
    with seeded_session(tmp_path_factory.mktemp("seed") / "test.db") as db:
        yield db


def all_results(db: Session) -> list[tuple]:
    query = select(
        TestResult.test_id,
        TestResult.student_id,
        TestResult.topic_id,
        TestResult.textbook_id,
        TestResult.score,
    ).order_by(TestResult.test_id, TestResult.student_id)
    return [tuple(row) for row in db.execute(query)]


def test_result_count_is_in_expected_range(session):
    count = session.scalar(select(func.count()).select_from(TestResult))
    assert 12_000 <= count <= 14_000


def extra_data(db: Session) -> list[list[tuple]]:
    queries = [
        select(Student.id, Student.pretest_score).order_by(Student.id),
        select(ItemResponse.item_id, ItemResponse.student_id, ItemResponse.correct).order_by(ItemResponse.id),
        select(TopicYearStat.topic_id, TopicYearStat.school_id, TopicYearStat.year, TopicYearStat.avg_score)
        .order_by(TopicYearStat.id),
    ]
    return [[tuple(row) for row in db.execute(query)] for query in queries]


def test_same_seed_gives_identical_data(session, tmp_path):
    with seeded_session(tmp_path / "again.db") as again:
        assert all_results(session) == all_results(again)
        assert extra_data(session) == extra_data(again)


def test_every_test_has_all_items(session):
    tests = session.scalar(select(func.count()).select_from(Test))
    assert session.scalar(select(func.count()).select_from(Item)) == tests * ITEMS_PER_TEST


def test_every_result_has_item_responses(session):
    results = session.scalar(select(func.count()).select_from(TestResult))
    assert session.scalar(select(func.count()).select_from(ItemResponse)) == results * ITEMS_PER_TEST


def test_item_answers_agree_with_score(session):
    answers = pd.DataFrame(
        session.execute(
            select(Item.test_id, ItemResponse.student_id, ItemResponse.correct)
            .join(Item, ItemResponse.item_id == Item.id)
        ).mappings().all()
    )
    correct = answers.groupby(["test_id", "student_id"])["correct"].mean().rename("correct").reset_index()
    scores = pd.DataFrame(session.execute(select(TestResult.test_id, TestResult.student_id, TestResult.score)).mappings().all())
    merged = correct.merge(scores, on=["test_id", "student_id"])
    assert np.corrcoef(merged["correct"], merged["score"])[0, 1] > 0.6
    assert merged["correct"].mean() * 100 == pytest.approx(merged["score"].mean(), abs=5)


def test_pretest_is_within_bounds_and_predicts_scores(session):
    frame = pd.DataFrame(
        session.execute(
            select(Student.id, Student.pretest_score, func.avg(TestResult.score).label("average"))
            .join(TestResult, TestResult.student_id == Student.id)
            .group_by(Student.id)
        ).mappings().all()
    )
    assert frame["pretest_score"].between(0, 100).all()
    assert np.corrcoef(frame["pretest_score"], frame["average"])[0, 1] > 0.7


def test_archive_covers_every_school_topic_and_year(session):
    expected = 5 * 12 * len(ARCHIVE_YEARS)
    assert session.scalar(select(func.count()).select_from(TopicYearStat)) == expected


def test_old_schema_is_outdated(tmp_path):
    engine = create_engine(f"sqlite:///{(tmp_path / 'old.db').as_posix()}")
    Base.metadata.create_all(engine)
    assert is_outdated(engine) is False
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE students DROP COLUMN pretest_score"))
    assert is_outdated(engine) is True


def test_empty_database_is_outdated(tmp_path):
    assert is_outdated(create_engine(f"sqlite:///{(tmp_path / 'empty.db').as_posix()}")) is True


def test_scores_are_within_bounds(session):
    low, high = session.execute(select(func.min(TestResult.score), func.max(TestResult.score))).one()
    assert 0 <= low and high <= 100


def test_total_hours(session):
    assert session.scalar(select(func.sum(Topic.hours_planned))) == 84


def test_every_school_uses_all_textbooks(session):
    textbook_count = session.scalar(select(func.count()).select_from(Textbook))
    for school in session.scalars(select(School)):
        used = {school_class.textbook_id for school_class in school.classes}
        assert len(used) == textbook_count


def test_class_textbook_distribution(session):
    query = (
        select(Textbook.name, func.count(SchoolClass.id))
        .join(SchoolClass, SchoolClass.textbook_id == Textbook.id)
        .group_by(Textbook.name)
    )
    assert dict(session.execute(query).all()) == {
        "Учебник A": 6,
        "Учебник B": 6,
        "Учебник C": 10,
    }


def test_fractions_have_the_lowest_average(session):
    by_topic, _ = load_summary(session)
    assert by_topic.loc[by_topic["avg_score"].idxmin(), "topic"] == "Дроби"


def test_textbook_b_has_the_lowest_average(session):
    _, by_textbook = load_summary(session)
    assert by_textbook.loc[by_textbook["avg_score"].idxmin(), "textbook"] == "Учебник B"


def test_strong_schools_choose_textbook_c(session):
    from app.analytics.data import load_results
    from app.analytics.regression import textbook_regression

    results = load_results(session)
    raw = results.groupby("textbook")["score"].mean()
    # Без учёта школы C заметно выше A, но почти вся разница объясняется школами.
    assert raw["Учебник C"] - raw["Учебник A"] > 3
    effect = next(item for item in textbook_regression(results)["effects"] if item["textbook"] == "Учебник C")
    assert abs(effect["coef"]) < 1.5
    assert effect["significant"] is False


def test_anomalous_class_fails_one_topic(session):
    from app.analytics.data import load_results
    from scripts.seed import ANOMALY

    school_no, class_name, topic = ANOMALY
    results = load_results(session)
    in_school = results[results["school"] == f"Школа №{school_no}"]
    by_class = in_school[in_school["topic"] == topic].groupby("class")["score"].mean()
    assert by_class[class_name] < by_class.drop(class_name).min() - 5
