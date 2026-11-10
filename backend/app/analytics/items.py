"""Качество заданий: дискриминативность и модель Раша. Метод описан в скилле metrics."""

import numpy as np
import pandas as pd
from scipy import stats
from scipy.special import expit

MIN_POINT_BISERIAL = 0.2
# Почти все или почти никто отвечают верно: корреляция низкая из-за потолка, а не из-за формулировки.
TOO_EASY_FROM = 0.9
TOO_HARD_BELOW = 0.1
NOT_DISCRIMINATING = "не различает сильных и слабых"
TOO_EASY = "слишком лёгкое"
TOO_HARD = "слишком трудное"
RASCH_MAX_ITERATIONS = 200
RASCH_TOLERANCE = 1e-4
RASCH_MAX_STEP = 1.0


def point_biserial(responses: pd.DataFrame) -> dict[int, float | None]:
    """Корреляция ответа на задание с суммой остальных заданий того же теста."""
    totals = responses.groupby(["test_id", "student_id"])["correct"].transform("sum")
    frame = responses.assign(rest=totals - responses["correct"].astype(int))

    correlations = {}
    for item_id, group in frame.groupby("item_id"):
        if group["correct"].nunique() < 2 or group["rest"].nunique() < 2:
            correlations[int(item_id)] = None
        else:
            correlations[int(item_id)] = float(stats.pointbiserialr(group["correct"], group["rest"]).statistic)
    return correlations


def drop_extreme(matrix: pd.DataFrame) -> pd.DataFrame:
    """Убирает учеников и задания без ошибок или без верных ответов: их оценка уходит в бесконечность."""
    while not matrix.empty:
        students = matrix.sum(axis=1).between(1, matrix.notna().sum(axis=1) - 1)
        items = matrix.sum(axis=0).between(1, matrix.notna().sum(axis=0) - 1)
        if students.all() and items.all():
            break
        matrix = matrix.loc[students, items]
    return matrix


def rasch_difficulties(matrix: pd.DataFrame) -> pd.Series:
    """Совместное максимальное правдоподобие. Строки — ученики, столбцы — задания, значения 0, 1 или NaN."""
    fitted = drop_extreme(matrix)
    if fitted.empty:
        return pd.Series(np.nan, index=matrix.columns, dtype=float)

    answers = np.nan_to_num(fitted.to_numpy(dtype=float))
    observed = fitted.notna().to_numpy()
    abilities = np.zeros(answers.shape[0])
    difficulties = np.zeros(answers.shape[1])

    for _ in range(RASCH_MAX_ITERATIONS):
        previous = difficulties.copy()

        probability = expit(abilities[:, None] - difficulties)
        residual = (answers - probability) * observed
        information = probability * (1 - probability) * observed
        abilities += np.clip(residual.sum(axis=1) / information.sum(axis=1), -RASCH_MAX_STEP, RASCH_MAX_STEP)

        probability = expit(abilities[:, None] - difficulties)
        residual = (answers - probability) * observed
        information = probability * (1 - probability) * observed
        difficulties -= np.clip(residual.sum(axis=0) / information.sum(axis=0), -RASCH_MAX_STEP, RASCH_MAX_STEP)
        difficulties -= difficulties.mean()

        if np.abs(difficulties - previous).max() < RASCH_TOLERANCE:
            break

    # Известная поправка Райта: совместное правдоподобие завышает разброс сложностей.
    item_count = answers.shape[1]
    corrected = difficulties * (item_count - 1) / item_count
    return pd.Series(corrected, index=fitted.columns, dtype=float).reindex(matrix.columns)


def item_issue(p_correct: float, correlation: float | None) -> str | None:
    if p_correct >= TOO_EASY_FROM:
        return TOO_EASY
    if p_correct < TOO_HARD_BELOW:
        return TOO_HARD
    if correlation is not None and correlation < MIN_POINT_BISERIAL:
        return NOT_DISCRIMINATING
    return None


def item_quality(responses: pd.DataFrame, topic_id: int) -> dict:
    """Оценивает задания темы."""
    correlations = point_biserial(responses)
    matrix = responses.assign(correct=responses["correct"].astype(float)).pivot_table(
        index="student_id", columns="item_id", values="correct"
    )
    difficulties = rasch_difficulties(matrix)
    catalog = responses.groupby(["item_id", "test_number", "item_number"], as_index=False)["correct"].mean()

    items = []
    for row in catalog.sort_values(["test_number", "item_number"]).to_dict("records"):
        item_id = int(row["item_id"])
        correlation = correlations[item_id]
        difficulty = difficulties.get(item_id, np.nan)
        issue = item_issue(float(row["correct"]), correlation)
        items.append(
            {
                "item_id": item_id,
                "test_number": int(row["test_number"]),
                "item_number": int(row["item_number"]),
                "p_correct": round(float(row["correct"]), 3),
                "point_biserial": None if correlation is None else round(correlation, 3),
                "rasch_difficulty": None if np.isnan(difficulty) else round(float(difficulty), 2),
                "issue": issue,
                "is_bad": issue == NOT_DISCRIMINATING,
            }
        )

    topic = responses["topic"].iloc[0]
    bad = [f"тест {item['test_number']}, задание {item['item_number']}" for item in items if item["is_bad"]]
    conclusion = (
        f"Тема «{topic}»: заданий, которые плохо различают сильных и слабых учеников, {len(bad)} из {len(items)} "
        f"({'; '.join(bad)}). Их стоит пересмотреть."
        if bad
        else f"Тема «{topic}»: все задания различают сильных и слабых учеников."
    )
    extreme = [item for item in items if item["issue"] in (TOO_EASY, TOO_HARD)]
    if extreme:
        listed = "; ".join(f"тест {item['test_number']}, задание {item['item_number']}" for item in extreme)
        conclusion += f" Почти все отвечают одинаково на задания: {listed}. Они мало говорят о подготовке."
    return {"topic_id": topic_id, "topic": topic, "items": items, "n_bad": len(bad), "conclusion": conclusion}
