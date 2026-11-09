"""Генерация синтетических данных. Параметры описаны в скилле seed-data."""

import argparse
import sys

import numpy as np
import pandas as pd
from sqlalchemy import func, insert, select
from sqlalchemy.orm import Session

from app.database import SessionLocal, engine
from app.models import (
    Base,
    School,
    SchoolClass,
    Student,
    Subject,
    Test,
    TestResult,
    Textbook,
    Topic,
)

SEED = 42
SCHOOL_COUNT = 5
TESTS_PER_TOPIC = 2
MIN_CLASS_SIZE = 23
MAX_CLASS_SIZE = 27
SKIP_RATE = 0.03

SCHOOL_SD = 3
CLASS_SD = 2
STUDENT_SD = 10
NOISE_SD = 8

TEXTBOOKS = ("A", "B", "C")
# Четвёртый класс каждой школы; первые три всегда A, B, C.
EXTRA_CLASS_TEXTBOOKS = ("A", "B", "C", "A", "B")
CLASS_LETTERS = ("А", "Б", "В", "Г")

# (название, базовый балл, плановые часы)
TOPICS = (
    ("Натуральные числа", 80, 9),
    ("Делимость чисел", 72, 8),
    ("Дроби", 54, 5),
    ("Десятичные дроби", 62, 6),
    ("Проценты", 56, 5),
    ("Отношения и пропорции", 60, 6),
    ("Отрицательные числа", 64, 7),
    ("Уравнения", 55, 6),
    ("Координатная плоскость", 78, 8),
    ("Геометрические фигуры", 76, 8),
    ("Площадь и объём", 68, 7),
    ("Статистика и диаграммы", 82, 9),
)

WEAK_B_TOPICS = {"Дроби", "Проценты"}
STRONG_C_TOPICS = {"Геометрические фигуры", "Площадь и объём"}


def textbook_effect(textbook: str, topic: str) -> int:
    if textbook == "B":
        return -8 if topic in WEAK_B_TOPICS else -3
    if textbook == "C":
        return 5 if topic in STRONG_C_TOPICS else 1
    return 0


def generate(session: Session, seed: int = SEED) -> None:
    """Заполняет пустую БД. Один и тот же seed всегда даёт одни и те же данные."""
    rng = np.random.default_rng(seed)

    subject = Subject(name="Математика")
    textbooks = {key: Textbook(name=f"Учебник {key}", subject=subject) for key in TEXTBOOKS}
    topics = [Topic(name=name, hours_planned=hours, subject=subject) for name, _, hours in TOPICS]
    tests = [Test(topic=topic, number=n + 1) for topic in topics for n in range(TESTS_PER_TOPIC)]
    session.add_all([subject, *textbooks.values(), *topics, *tests])
    session.flush()

    bases = {name: base for name, base, _ in TOPICS}
    rows = []
    student_no = 0

    for school_index in range(SCHOOL_COUNT):
        school = School(name=f"Школа №{school_index + 1}")
        session.add(school)
        school_effect = rng.normal(0, SCHOOL_SD)

        class_textbooks = [*TEXTBOOKS, EXTRA_CLASS_TEXTBOOKS[school_index]]
        for letter, textbook_key in zip(CLASS_LETTERS, class_textbooks):
            textbook = textbooks[textbook_key]
            school_class = SchoolClass(name=f"6{letter}", school=school, textbook=textbook)
            session.add(school_class)
            class_effect = rng.normal(0, CLASS_SD)

            for _ in range(int(rng.integers(MIN_CLASS_SIZE, MAX_CLASS_SIZE + 1))):
                student_no += 1
                student = Student(name=f"Ученик {student_no:03d}", school_class=school_class)
                session.add(student)
                session.flush()
                student_effect = rng.normal(0, STUDENT_SD)

                for test in tests:
                    topic_name = test.topic.name
                    noise = rng.normal(0, NOISE_SD)
                    if rng.random() < SKIP_RATE:
                        continue
                    raw = (
                        bases[topic_name]
                        + school_effect
                        + class_effect
                        + student_effect
                        + textbook_effect(textbook_key, topic_name)
                        + noise
                    )
                    rows.append(
                        {
                            "test_id": test.id,
                            "student_id": student.id,
                            "topic_id": test.topic_id,
                            "textbook_id": textbook.id,
                            "score": int(np.clip(round(raw), 0, 100)),
                        }
                    )

    session.execute(insert(TestResult), rows)
    session.commit()


def load_summary(session: Session) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Возвращает сводку по темам и средний балл по учебникам."""
    query = (
        select(
            Topic.id.label("topic_id"),
            Topic.name.label("topic"),
            Topic.hours_planned.label("hours"),
            Textbook.name.label("textbook"),
            TestResult.score,
        )
        .join(TestResult, TestResult.topic_id == Topic.id)
        .join(Textbook, Textbook.id == TestResult.textbook_id)
    )
    data = pd.DataFrame(session.execute(query).mappings().all())

    by_topic = (
        data.assign(failed=data["score"] < 50)
        .groupby(["topic_id", "topic", "hours"], sort=True)
        .agg(avg_score=("score", "mean"), fail_rate=("failed", "mean"))
        .reset_index()
    )
    by_textbook = data.groupby("textbook")["score"].mean().reset_index(name="avg_score")
    return by_topic, by_textbook


def print_summary(session: Session) -> None:
    by_topic, by_textbook = load_summary(session)
    counts = {
        "школ": session.scalar(select(func.count()).select_from(School)),
        "классов": session.scalar(select(func.count()).select_from(SchoolClass)),
        "учеников": session.scalar(select(func.count()).select_from(Student)),
        "результатов": session.scalar(select(func.count()).select_from(TestResult)),
    }
    print(", ".join(f"{name}: {value}" for name, value in counts.items()))
    print()
    print(f"{'Тема':<26}{'Часы':>6}{'Ср. балл':>10}{'Не сдали':>10}")
    for row in by_topic.itertuples():
        print(f"{row.topic:<26}{row.hours:>6}{row.avg_score:>10.1f}{row.fail_rate:>10.1%}")
    print(f"{'Всего часов':<26}{by_topic['hours'].sum():>6}")
    print()
    print(f"{'Учебник':<26}{'Ср. балл':>10}")
    for row in by_textbook.itertuples():
        print(f"{row.textbook:<26}{row.avg_score:>10.1f}")


def main() -> int:
    # Названия тем кириллицей не должны ломать вывод в консоли Windows.
    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Генерация синтетических данных")
    parser.add_argument("--reset", action="store_true", help="удалить данные и создать заново")
    args = parser.parse_args()

    if args.reset:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    with SessionLocal() as session:
        if session.scalar(select(func.count()).select_from(School)):
            print("В базе уже есть данные. Чтобы создать их заново, добавьте --reset.")
            return 1
        generate(session)
        print_summary(session)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
