"""Генерация синтетических данных. Параметры описаны в скилле seed-data."""

import argparse
import sys

import numpy as np
import pandas as pd
from scipy.special import expit, logit
from sqlalchemy import Engine, func, insert, inspect, select
from sqlalchemy.orm import Session

from app.database import SessionLocal, engine
from app.models import (
    Base,
    Item,
    ItemResponse,
    School,
    SchoolClass,
    Student,
    Subject,
    Test,
    TestResult,
    Textbook,
    Topic,
    TopicYearStat,
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

# Новые данные используют свои генераторы, чтобы не сдвигать последовательность основных баллов.
ITEM_DIFFICULTY_SEED_OFFSET = 1
ITEM_RESPONSE_SEED_OFFSET = 2
PRETEST_SEED_OFFSET = 3
ARCHIVE_SEED_OFFSET = 4

ITEMS_PER_TEST = 8
ITEM_DIFFICULTY_SD = 0.8
# Баллы разбросаны узко, и без усиления даже хорошие задания плохо различали бы учеников.
ITEM_DISCRIMINATION = 2.0
# (тема, номер теста, номер задания): ответ на них не зависит от подготовки ученика.
BAD_ITEMS = {("Дроби", 1, 3), ("Уравнения", 2, 5)}
BAD_ITEM_PROBABILITY = 0.5

PRETEST_BASE = 65
PRETEST_NOISE_SD = 6

ARCHIVE_YEARS = (2022, 2023, 2024, 2025)
CURRENT_YEAR = 2026
ARCHIVE_NOISE_SD = 1.0
MIN_ARCHIVE_STUDENTS = 90
MAX_ARCHIVE_STUDENTS = 110
# Изменение среднего балла за год; у остальных тем тренда нет.
YEARLY_TREND = {"Дроби": -1.5, "Геометрические фигуры": 1.2}


def textbook_effect(textbook: str, topic: str) -> int:
    if textbook == "B":
        return -8 if topic in WEAK_B_TOPICS else -3
    if textbook == "C":
        return 5 if topic in STRONG_C_TOPICS else 1
    return 0


def item_difficulties(seed: int = SEED) -> np.ndarray:
    """Заложенные сложности заданий: строка — тест, столбец — задание, среднее по тесту 0."""
    rng = np.random.default_rng(seed + ITEM_DIFFICULTY_SEED_OFFSET)
    values = rng.normal(0, ITEM_DIFFICULTY_SD, (len(TOPICS) * TESTS_PER_TOPIC, ITEMS_PER_TEST))
    return values - values.mean(axis=1, keepdims=True)


def add_items(session: Session, tests: list[Test], rows: list[dict], seed: int) -> None:
    """Создаёт задания и ответы так, чтобы доля верных ответов соответствовала баллу за тест."""
    rng = np.random.default_rng(seed + ITEM_RESPONSE_SEED_OFFSET)
    items = [[Item(test_id=test.id, number=n + 1) for n in range(ITEMS_PER_TEST)] for test in tests]
    session.add_all([item for test_items in items for item in test_items])
    session.flush()

    item_ids = np.array([[item.id for item in test_items] for test_items in items])
    is_bad = np.array(
        [[(test.topic.name, test.number, n + 1) in BAD_ITEMS for n in range(ITEMS_PER_TEST)] for test in tests]
    )
    test_position = {test.id: position for position, test in enumerate(tests)}

    results = pd.DataFrame(rows)
    positions = results["test_id"].map(test_position).to_numpy()
    # Крайние баллы ограничены: logit от 0 и 1 бесконечен.
    ability = logit(results["score"].clip(3, 97).to_numpy() / 100)
    # Усиливаем отличия внутри теста, сохраняя его средний уровень.
    test_mean = pd.Series(ability).groupby(positions).transform("mean").to_numpy()
    ability = test_mean + ITEM_DISCRIMINATION * (ability - test_mean)
    probability = expit(ability[:, None] - item_difficulties(seed)[positions])
    probability[is_bad[positions]] = BAD_ITEM_PROBABILITY
    correct = rng.random(probability.shape) < probability

    student_ids = np.repeat(results["student_id"].to_numpy(), ITEMS_PER_TEST)
    responses = [
        {"item_id": item_id, "student_id": student_id, "correct": is_correct}
        for item_id, student_id, is_correct in zip(
            item_ids[positions].ravel().tolist(), student_ids.tolist(), correct.ravel().tolist()
        )
    ]
    session.execute(insert(ItemResponse), responses)


def add_archive(session: Session, topics: list[Topic], rows: list[dict], student_school: dict[int, int], seed: int) -> None:
    """Создаёт средние прошлых лет от текущего среднего школы по теме."""
    rng = np.random.default_rng(seed + ARCHIVE_SEED_OFFSET)
    names = {topic.id: topic.name for topic in topics}
    results = pd.DataFrame(rows)
    results["school_id"] = results["student_id"].map(student_school)

    archive = []
    for (school_id, topic_id), current in results.groupby(["school_id", "topic_id"])["score"].mean().items():
        trend = YEARLY_TREND.get(names[topic_id], 0)
        for year in ARCHIVE_YEARS:
            value = current - trend * (CURRENT_YEAR - year) + rng.normal(0, ARCHIVE_NOISE_SD)
            archive.append(
                {
                    "topic_id": int(topic_id),
                    "school_id": int(school_id),
                    "year": year,
                    "avg_score": round(float(np.clip(value, 0, 100)), 1),
                    "n_students": int(rng.integers(MIN_ARCHIVE_STUDENTS, MAX_ARCHIVE_STUDENTS + 1)),
                }
            )
    session.execute(insert(TopicYearStat), archive)


def generate(session: Session, seed: int = SEED) -> None:
    """Заполняет пустую БД. Один и тот же seed всегда даёт одни и те же данные."""
    rng = np.random.default_rng(seed)
    pretest_rng = np.random.default_rng(seed + PRETEST_SEED_OFFSET)

    subject = Subject(name="Математика")
    textbooks = {key: Textbook(name=f"Учебник {key}", subject=subject) for key in TEXTBOOKS}
    topics = [Topic(name=name, hours_planned=hours, subject=subject) for name, _, hours in TOPICS]
    tests = [Test(topic=topic, number=n + 1) for topic in topics for n in range(TESTS_PER_TOPIC)]
    session.add_all([subject, *textbooks.values(), *topics, *tests])
    session.flush()

    bases = {name: base for name, base, _ in TOPICS}
    rows = []
    student_school = {}
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
                student_effect = rng.normal(0, STUDENT_SD)
                pretest = PRETEST_BASE + school_effect + student_effect + pretest_rng.normal(0, PRETEST_NOISE_SD)
                student = Student(
                    name=f"Ученик {student_no:03d}",
                    school_class=school_class,
                    pretest_score=int(np.clip(round(pretest), 0, 100)),
                )
                session.add(student)
                session.flush()
                student_school[student.id] = school.id

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
    add_items(session, tests, rows, seed)
    add_archive(session, topics, rows, student_school, seed)
    session.commit()


def is_outdated(target: Engine) -> bool:
    """Проверяет, что в БД есть все таблицы и столбцы текущих моделей."""
    inspector = inspect(target)
    for table in Base.metadata.sorted_tables:
        if not inspector.has_table(table.name):
            return True
        existing = {column["name"] for column in inspector.get_columns(table.name)}
        if set(table.columns.keys()) - existing:
            return True
    return False


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
    parser.add_argument("--if-outdated", action="store_true", help="пересоздать БД, только если её схема устарела")
    args = parser.parse_args()

    if args.if_outdated and not is_outdated(engine):
        print("Демонстрационные данные актуальны.")
        return 0

    if args.reset or args.if_outdated:
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
