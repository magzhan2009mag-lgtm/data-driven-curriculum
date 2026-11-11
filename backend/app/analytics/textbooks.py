"""Сравнение учебников. Метод описан в скилле metrics."""

from itertools import combinations

import numpy as np
import pandas as pd
from scipy import stats

ALPHA = 0.05
MIN_STUDENTS = 30
BOOTSTRAP_REPEATS = 2000
BOOTSTRAP_SEED = 42
NOT_ENOUGH_DATA = "мало данных"
# Если сырая разница и разница внутри школ расходятся хотя бы на столько баллов, предупреждаем о смешении.
CONFOUNDING_GAP = 2.0
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


def bootstrap_ci(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    """95% доверительный интервал для разницы средних a − b."""
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    means_a = rng.choice(a, size=(BOOTSTRAP_REPEATS, len(a))).mean(axis=1)
    means_b = rng.choice(b, size=(BOOTSTRAP_REPEATS, len(b))).mean(axis=1)
    low, high = np.percentile(means_a - means_b, [2.5, 97.5])
    return float(low), float(high)


def mann_whitney_p(a: np.ndarray, b: np.ndarray) -> float:
    p_value = float(stats.mannwhitneyu(a, b, alternative="two-sided").pvalue)
    # Если все значения равны, тест возвращает NaN: различий увидеть нельзя.
    return 1.0 if np.isnan(p_value) else p_value


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


def format_points(value: float) -> str:
    return f"{abs(value):.1f}".replace(".", ",")


def school_deviation(results: pd.DataFrame) -> pd.Series:
    """Отклонение балла от среднего по его школе и теме."""
    return results["score"] - results.groupby(["school_id", "topic_id"])["score"].transform("mean")


def adjusted_scores(results: pd.DataFrame) -> dict[str, float]:
    """Средний балл учебника, если бы все учебники проходили в одинаковых школах.

    Общее среднее плюс среднее отклонение результата от среднего по его школе и теме.
    """
    return (results["score"].mean() + school_deviation(results).groupby(results["textbook"]).mean()).to_dict()


def adjust_for_school(results: pd.DataFrame) -> pd.DataFrame:
    """Баллы, как если бы все учебники проходили в одинаковых школах.

    Балл − среднее школы по теме + среднее темы по всем школам. Средний балл учебника по теме
    из этих баллов совпадает с adjusted_score в сравнении учебников по этой теме.
    """
    topic_mean = results.groupby("topic_id")["score"].transform("mean")
    return results.assign(score=school_deviation(results) + topic_mean)


def confounding_note(textbooks: list[dict], comparisons: list[dict]) -> str | None:
    """Объясняет, когда сырые средние вводят в заблуждение из-за разного состава школ."""
    raw = {book["name"]: book["avg_score"] for book in textbooks}
    adjusted = {book["name"]: book["adjusted_score"] for book in textbooks}
    candidates = []
    for pair in comparisons:
        if pair["p_adjusted"] is None:
            continue
        raw_diff = raw[pair["a"]] - raw[pair["b"]]
        adjusted_diff = adjusted[pair["a"]] - adjusted[pair["b"]]
        if abs(raw_diff) >= CONFOUNDING_GAP and abs(raw_diff - adjusted_diff) >= CONFOUNDING_GAP:
            candidates.append((pair, raw_diff, adjusted_diff))
    if not candidates:
        return None

    # Важнее всего пары, где сырая разница есть, а при честном сравнении не подтверждается.
    pair, raw_diff, adjusted_diff = max(
        candidates, key=lambda item: (not item[0]["significant"], abs(item[1] - item[2]))
    )
    higher, lower = (pair["a"], pair["b"]) if raw_diff > 0 else (pair["b"], pair["a"])
    if not pair["significant"]:
        within = f"разница {format_points(adjusted_diff)} балла и статистически не подтверждается"
    elif (adjusted_diff > 0) == (raw_diff > 0):
        within = f"{higher} выше на {format_points(adjusted_diff)} балла"
    else:
        within = f"{lower} выше на {format_points(adjusted_diff)} балла"
    return (
        f"Без учёта школ {higher} выглядит сильнее, чем {lower}, на {format_points(raw_diff)} балла. "
        "Но учебники распределены по школам неравномерно, а уровень школ сильно различается. "
        f"Если сравнивать классы одной и той же школы, {within}."
    )


def format_p(p_value: float) -> str:
    # Неразрывные пробелы: при переносе строки «p < 0,001» не должно разрываться.
    if p_value < 0.001:
        return "p < 0,001"
    return f"p = {p_value:.3f}".replace(".", ",")


def build_conclusion(subject: str, textbooks: list[dict], comparisons: list[dict]) -> str:
    if not textbooks:
        return "Нет результатов для сравнения учебников."

    averages = {book["name"]: book["adjusted_score"] for book in textbooks}
    sentences = []
    significant = [pair for pair in comparisons if pair["significant"]]
    for pair in sorted(significant, key=lambda item: -abs(item["cohens_d"])):
        higher, lower = (pair["a"], pair["b"]) if pair["cohens_d"] > 0 else (pair["b"], pair["a"])
        difference = f"{abs(averages[higher] - averages[lower]):.1f}".replace(".", ",")
        sentences.append(
            f"{higher} выше, чем {lower}, на {difference} балла в одних и тех же школах "
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
    adjusted = adjusted_scores(scope) if not scope.empty else {}

    textbooks = [
        {
            "textbook_id": int(textbook_id),
            "name": name,
            "n_students": len(z_by_book[name]),
            "avg_score": round(float(group["score"].mean()), 1),
            "adjusted_score": round(float(adjusted[name]), 1),
            "mean_z": round(float(z_by_book[name].mean()), 3),
            "enough_data": len(z_by_book[name]) >= MIN_STUDENTS,
        }
        for (textbook_id, name), group in scope.groupby(["textbook_id", "textbook"])
    ]

    comparisons = []
    for a, b in combinations(sorted(z_by_book), 2):
        enough = len(z_by_book[a]) >= MIN_STUDENTS and len(z_by_book[b]) >= MIN_STUDENTS
        pair = {"a": a, "b": b, "p_value": None, "p_adjusted": None, "cohens_d": None,
                "effect": NOT_ENOUGH_DATA, "significant": False,
                "mann_whitney_p": None, "mann_whitney_p_adjusted": None, "ci_low": None, "ci_high": None}
        if enough:
            p_value = float(stats.ttest_ind(z_by_book[a], z_by_book[b], equal_var=False).pvalue)
            # Без разброса в обеих группах тест возвращает NaN: различий увидеть нельзя.
            pair["p_value"] = 1.0 if np.isnan(p_value) else p_value
            pair["cohens_d"] = cohens_d(z_by_book[a], z_by_book[b])
            pair["effect"] = effect_label(pair["cohens_d"])
            pair["mann_whitney_p"] = mann_whitney_p(z_by_book[a], z_by_book[b])
            pair["ci_low"], pair["ci_high"] = bootstrap_ci(z_by_book[a], z_by_book[b])
        comparisons.append(pair)

    tested = [pair for pair in comparisons if pair["p_value"] is not None]
    for pair, adjusted in zip(tested, holm_adjust([pair["p_value"] for pair in tested])):
        pair["p_adjusted"] = adjusted
        pair["significant"] = adjusted < ALPHA
    for pair, adjusted in zip(tested, holm_adjust([pair["mann_whitney_p"] for pair in tested])):
        pair["mann_whitney_p_adjusted"] = adjusted

    subject = f"Тема «{topic}»" if topic else "Все темы"
    conclusion = build_conclusion(subject, textbooks, comparisons)
    note = confounding_note(textbooks, comparisons)

    for pair in tested:
        pair["p_value"] = round(pair["p_value"], 4)
        pair["p_adjusted"] = round(pair["p_adjusted"], 4)
        pair["cohens_d"] = round(pair["cohens_d"], 2)
        pair["mann_whitney_p"] = round(pair["mann_whitney_p"], 4)
        pair["mann_whitney_p_adjusted"] = round(pair["mann_whitney_p_adjusted"], 4)
        pair["ci_low"] = round(pair["ci_low"], 3)
        pair["ci_high"] = round(pair["ci_high"], 3)

    return {
        "topic_id": topic_id,
        "topic": topic,
        "textbooks": textbooks,
        "comparisons": comparisons,
        "conclusion": conclusion,
        "confounding_note": note,
        "limitation": LIMITATION,
    }
