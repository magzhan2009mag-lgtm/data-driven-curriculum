import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import School, SchoolClass, Student, TestResult, Textbook, Topic

RESULT_COLUMNS = [
    "student_id",
    "topic_id",
    "topic",
    "hours_planned",
    "textbook_id",
    "textbook",
    "school_id",
    "school",
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
            TestResult.score,
        )
        .join(Topic, TestResult.topic_id == Topic.id)
        .join(Textbook, TestResult.textbook_id == Textbook.id)
        .join(Student, TestResult.student_id == Student.id)
        .join(SchoolClass, Student.class_id == SchoolClass.id)
        .join(School, SchoolClass.school_id == School.id)
    )
    return pd.DataFrame(session.execute(query).mappings().all(), columns=RESULT_COLUMNS)
