import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
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

RESULT_COLUMNS = [
    "student_id",
    "topic_id",
    "topic",
    "hours_planned",
    "textbook_id",
    "textbook",
    "school_id",
    "school",
    "class_id",
    "class",
    "score",
]


def load_results(session: Session) -> pd.DataFrame:
    """Возвращает по строке на результат теста со школой, темой и учебником."""
    query = (
        select(
            TestResult.student_id,
            TestResult.topic_id,
            Topic.name.label("topic"),
            Topic.hours_planned,
            TestResult.textbook_id,
            Textbook.name.label("textbook"),
            School.id.label("school_id"),
            School.name.label("school"),
            SchoolClass.id.label("class_id"),
            SchoolClass.name.label("class"),
            TestResult.score,
        )
        .join(Topic, TestResult.topic_id == Topic.id)
        .join(Textbook, TestResult.textbook_id == Textbook.id)
        .join(Student, TestResult.student_id == Student.id)
        .join(SchoolClass, Student.class_id == SchoolClass.id)
        .join(School, SchoolClass.school_id == School.id)
    )
    return pd.DataFrame(session.execute(query).mappings().all(), columns=RESULT_COLUMNS)


def load_item_responses(session: Session, topic_id: int) -> pd.DataFrame:
    """Возвращает по строке на ответ ученика на задание одной темы."""
    columns = ["topic", "test_id", "test_number", "item_id", "item_number", "student_id", "correct"]
    query = (
        select(
            Topic.name.label("topic"),
            Test.id.label("test_id"),
            Test.number.label("test_number"),
            Item.id.label("item_id"),
            Item.number.label("item_number"),
            ItemResponse.student_id,
            ItemResponse.correct,
        )
        .join(Item, ItemResponse.item_id == Item.id)
        .join(Test, Item.test_id == Test.id)
        .join(Topic, Test.topic_id == Topic.id)
        .where(Topic.id == topic_id)
    )
    return pd.DataFrame(session.execute(query).mappings().all(), columns=columns)


def load_students(session: Session) -> pd.DataFrame:
    """Возвращает входной тест и школу каждого ученика."""
    query = (
        select(Student.id.label("student_id"), Student.pretest_score, SchoolClass.school_id)
        .join(SchoolClass, Student.class_id == SchoolClass.id)
    )
    return pd.DataFrame(session.execute(query).mappings().all(), columns=["student_id", "pretest_score", "school_id"])


def load_year_stats(session: Session) -> pd.DataFrame:
    """Возвращает архивные средние по школе, теме и году."""
    query = select(TopicYearStat.topic_id, TopicYearStat.school_id, TopicYearStat.year, TopicYearStat.avg_score)
    return pd.DataFrame(session.execute(query).mappings().all(), columns=["topic_id", "school_id", "year", "avg_score"])
