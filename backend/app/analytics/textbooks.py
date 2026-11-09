"""Сравнение учебников. Метод описан в скилле metrics."""

from itertools import combinations

import numpy as np
import pandas as pd
from scipy import stats

ALPHA = 0.05
MIN_STUDENTS = 30
NOT_ENOUGH_DATA = "мало данных"
LIMITATION = (
    "Тест не учитывает, что ученики сгруппированы по классам, поэтому значимость может быть "
    "немного завышена. Опирайтесь и на p-value, и на размер эффекта."
)


def holm_adjust(p_values: list[float]) -> list[float]:
    """Поправка Холма на множественные сравнения."""
    count = len(p_values)
    adjusted = [0.0] * count
    running_max = 0.0
    for rank, index in enumerate(sorted(range(count), key=p_values.__getitem__)):
        running_max = max(running_max, (count - rank) * p_values[index])
        adjusted[index] = min(running_max, 1.0)
    return adjusted


def cohens_d(a: np.ndarray, b: np.ndarray) -> float:
    pooled_variance = ((len(a) - 1) * a.var(ddof=1) + (len(b) - 1) * b.var(ddof=1)) / (len(a) + len(b) - 2)
    if pooled_variance == 0:
        return 0.0
    return float((a.mean() - b.mean()) / np.sqrt(pooled_variance))


def effect_label(d: float) -> str:
    size = abs(d)
    if size < 0.2:
        return "пренебрежимо мал"
    if size < 0.5:
        return "малый"
    if size < 0.8:
        return "средний"
    return "большой"


def student_z_scores(results: pd.DataFrame) -> pd.DataFrame:
    """Средняя z-оценка ученика: два теста одного ученика не считаются независимыми."""
    groups = results.groupby(["school_id", "topic_id"])["score"]
    # Если все баллы в группе равны, std = 0 и отклонения от среднего нет.
    z_scores = ((results["score"] - groups.transform("mean")) / groups.transform("std").replace(0, np.nan)).fillna(0)
    return (
        results.assign(z=z_scores)
        .groupby(["student_id", "textbook"], as_index=False)["z"]
        .mean()
    )


def format_p(p_value: float) -> str:
    # Неразрывные пробелы: при переносе строки «p < 0,001» не должно разрываться.
    if p_value < 0.001:
        return "p < 0,001"
    return f"p = {p_value:.3f}".replace(".", ",")


def build_conclusion(subject: str, textbooks: list[dict], comparisons: list[dict]) -> str:
    if not textbooks:
        return "Нет результатов для сравнения учебников."

    averages = {book["name"]: book["avg_score"] for book in textbooks}
    sentences = []
    significant = [pair for pair in comparisons if pair["significant"]]
    for pair in sorted(significant, key=lambda item: -abs(item["cohens_d"])):
        higher, lower = (pair["a"], pair["b"]) if pair["cohens_d"] > 0 else (pair["b"], pair["a"])
        difference = f"{abs(averages[higher] - averages[lower]):.1f}".replace(".", ",")
        sentences.append(
            f"{higher} выше, чем {lower}, на {difference} балла "
            f"(размер эффекта: {pair['effect']}, {format_p(pair['p_adjusted'])})."
        )

    if sentences:
        conclusion = f"{subject}: " + " ".join(sentences)
    elif any(pair["p_adjusted"] is not None for pair in comparisons):
        conclusion = f"{subject}: статистически значимой разницы между учебниками не найдено."
    else:
        conclusion = f"{subject}: данных недостаточно, чтобы сравнить учебники."

    for book in textbooks:
        if book["n_students"] < MIN_STUDENTS:
            conclusion += f" {book['name']}: мало данных ({book['n_students']} уч.), вывод не делаем."
    return conclusion


def compare_textbooks(results: pd.DataFrame, topic_id: int | None = None) -> dict:
    """Сравнивает учебники по одной теме или, без topic_id, по всем темам."""
    scope = results if topic_id is None else results[results["topic_id"] == topic_id]
    topic = None if topic_id is None or scope.empty else scope["topic"].iloc[0]

    students = student_z_scores(scope) if not scope.empty else pd.DataFrame(columns=["student_id", "textbook", "z"])
    z_by_book = {name: group["z"].to_numpy() for name, group in students.groupby("textbook")}

    textbooks = [
        {
            "textbook_id": int(textbook_id),
            "name": name,
            "n_students": len(z_by_book[name]),
            "avg_score": round(float(group["score"].mean()), 1),
            "mean_z": round(float(z_by_book[name].mean()), 3),
        }
        for (textbook_id, name), group in scope.groupby(["textbook_id", "textbook"])
    ]

    comparisons = []
    for a, b in combinations(sorted(z_by_book), 2):
        enough = len(z_by_book[a]) >= MIN_STUDENTS and len(z_by_book[b]) >= MIN_STUDENTS
        pair = {"a": a, "b": b, "p_value": None, "p_adjusted": None, "cohens_d": None,
                "effect": NOT_ENOUGH_DATA, "significant": False}
        if enough:
            p_value = float(stats.ttest_ind(z_by_book[a], z_by_book[b], equal_var=False).pvalue)
            # Без разброса в обеих группах тест возвращает NaN: различий увидеть нельзя.
            pair["p_value"] = 1.0 if np.isnan(p_value) else p_value
            pair["cohens_d"] = cohens_d(z_by_book[a], z_by_book[b])
            pair["effect"] = effect_label(pair["cohens_d"])
        comparisons.append(pair)

    tested = [pair for pair in comparisons if pair["p_value"] is not None]
    for pair, adjusted in zip(tested, holm_adjust([pair["p_value"] for pair in tested])):
        pair["p_adjusted"] = adjusted
        pair["significant"] = adjusted < ALPHA

    subject = f"Тема «{topic}»" if topic else "Все темы"
    conclusion = build_conclusion(subject, textbooks, comparisons)

    for pair in tested:
        pair["p_value"] = round(pair["p_value"], 4)
        pair["p_adjusted"] = round(pair["p_adjusted"], 4)
        pair["cohens_d"] = round(pair["cohens_d"], 2)

    return {
        "topic_id": topic_id,
        "topic": topic,
        "textbooks": textbooks,
        "comparisons": comparisons,
        "conclusion": conclusion,
        "limitation": LIMITATION,
    }
