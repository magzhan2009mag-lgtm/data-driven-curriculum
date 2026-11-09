import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.models import Base, School, SchoolClass, TestResult, Textbook, Topic
from scripts.seed import generate, load_summary


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
    assert 11_000 <= count <= 13_000


def test_same_seed_gives_identical_data(session, tmp_path):
    with seeded_session(tmp_path / "again.db") as again:
        assert all_results(session) == all_results(again)


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
        "Учебник A": 7,
        "Учебник B": 7,
        "Учебник C": 6,
    }


def test_fractions_have_the_lowest_average(session):
    by_topic, _ = load_summary(session)
    assert by_topic.loc[by_topic["avg_score"].idxmin(), "topic"] == "Дроби"


def test_textbook_b_has_the_lowest_average(session):
    _, by_textbook = load_summary(session)
    assert by_textbook.loc[by_textbook["avg_score"].idxmin(), "textbook"] == "Учебник B"
