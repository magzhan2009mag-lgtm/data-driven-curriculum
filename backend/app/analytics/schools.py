"""Фильтр по школе. Что пересчитывается по школе, а что нет, описано в скилле metrics."""

from dataclasses import dataclass

import pandas as pd

from app.analytics.textbooks import MIN_STUDENTS

SCOPE_NOTE = "Считается по всем школам: внутри одной школы для этого метода мало данных."


@dataclass
class Scope:
    """Данные запроса: все результаты и результаты выбранной школы (или те же все, если школа не выбрана)."""

    all_results: pd.DataFrame
    results: pd.DataFrame
    school_id: int | None = None
    school: str | None = None

    @property
    def filtered(self) -> bool:
        return self.school_id is not None


def list_schools(results: pd.DataFrame) -> list[dict]:
    """Школы для выпадающего списка: число классов и учеников."""
    grouped = results.groupby(["school_id", "school"], as_index=False).agg(
        n_classes=("class_id", "nunique"), n_students=("student_id", "nunique")
    )
    return [
        {
            "school_id": int(row["school_id"]),
            "school": row["school"],
            "n_classes": int(row["n_classes"]),
            "n_students": int(row["n_students"]),
        }
        for row in grouped.sort_values("school_id").to_dict("records")
    ]


def only_school(results: pd.DataFrame, school_id: int) -> pd.DataFrame:
    return results[results["school_id"] == school_id]


def textbook_students(results: pd.DataFrame) -> dict[str, int]:
    return {name: int(count) for name, count in results.groupby("textbook")["student_id"].nunique().items()}


def few_students(results: pd.DataFrame) -> dict[str, int]:
    """Учебники, у которых меньше MIN_STUDENTS учеников: по ним вывод не делаем."""
    return {name: count for name, count in sorted(textbook_students(results).items()) if count < MIN_STUDENTS}


def in_school(school: str) -> str:
    """«Школа №5» → «В Школе №5» (в начале предложения)."""
    return "В " + school.replace("Школа", "Школе", 1)


def letters(names: list[str]) -> str:
    short = [name.replace("Учебник ", "") for name in names]
    return short[0] if len(short) == 1 else ", ".join(short[:-1]) + " и " + short[-1]


def school_note(school: str, few: dict[str, int], what: str = "сравнения") -> str | None:
    """Понятный текст, почему в одной школе вывод по учебникам не делаем."""
    if not few:
        return None
    word = "учебника" if len(few) == 1 else "учебников"
    counts = " и ".join(str(count) for count in few.values())
    return (
        f"{in_school(school)} у {word} {letters(list(few))} меньше {MIN_STUDENTS} учеников ({counts}): "
        f"данных одной школы мало для {what}. Смотрите сравнение по всем школам."
    )


def add_all_schools_to_topics(topics: list[dict], all_topics: list[dict]) -> None:
    """Добавляет к темам школы значения по всем школам, чтобы показывать их рядом."""
    by_id = {item["topic_id"]: item for item in all_topics}
    for item in topics:
        overall = by_id[item["topic_id"]]
        item["avg_score_all"] = overall["avg_score"]
        item["fail_rate_all"] = overall["fail_rate"]
        item["difficulty_index_all"] = overall["difficulty_index"]


def add_classes_to_topics(topics: list[dict], results: pd.DataFrame) -> None:
    """Средний балл каждого класса школы по каждой теме с учебником класса."""
    cells = results.groupby(["topic_id", "class_id", "class", "textbook"], as_index=False)["score"].mean()
    for item in topics:
        rows = cells[cells["topic_id"] == item["topic_id"]].sort_values("class")
        item["by_class"] = [
            {
                "class_id": int(row["class_id"]),
                "class": row["class"],
                "textbook": row["textbook"],
                "avg_score": round(float(row["score"]), 1),
            }
            for row in rows.to_dict("records")
        ]


def add_all_schools_to_hours(response: dict, overall: dict) -> None:
    """К плану часов школы добавляет план по всем школам для сравнения."""
    by_id = {item["topic_id"]: item for item in overall["items"]}
    for item in response["items"]:
        item["delta_all"] = by_id[item["topic_id"]]["delta"]
        item["hours_recommended_all"] = by_id[item["topic_id"]]["hours_recommended"]
    response["hours_moved_all"] = overall["hours_moved"]


def add_all_schools_to_textbooks(response: dict, overall: dict) -> None:
    by_name = {book["name"]: book for book in overall["textbooks"]}
    for book in response["textbooks"]:
        book["adjusted_score_all"] = by_name[book["name"]]["adjusted_score"] if book["name"] in by_name else None


def outliers_for_school(response: dict, school_id: int, school: str) -> dict:
    """Выбросы ищутся по всем школам, а показываются только для выбранной."""
    outliers = [item for item in response["outliers"] if item["school_id"] == school_id]
    conclusion = (
        f"{in_school(school)} необычных результатов: {len(outliers)}."
        if outliers
        else f"{in_school(school)} необычных результатов по отдельным темам не найдено."
    )
    return {**response, "outliers": outliers, "conclusion": conclusion, "scope_note": SCOPE_NOTE}


def roots_in_school(roots: dict[int, list[str]], topics: list[dict]) -> dict[int, list[str]]:
    """Корни, которые дают час в плане школы.

    Связи тем ищутся по всем школам, но час сверх потребности корень получает, только если хотя бы одна
    зависимая от него тема сложная именно в этой школе: иначе лечить нечего.
    """
    hard = {topic["topic"] for topic in topics if topic["level"] == "hard"}
    return {root: dependents for root, dependents in roots.items() if any(name in hard for name in dependents)}
