"""Сложность тем. Формулы и пороги описаны в скилле metrics."""

import pandas as pd

FAIL_THRESHOLD = 50
HARD_FROM = 0.40
MEDIUM_FROM = 0.25
ANOMALY_Z = 2
BIN_WIDTH = 10
BIN_COUNT = 10


def compute_index(avg_score: float, fail_rate: float) -> float:
    return 0.6 * (1 - avg_score / 100) + 0.4 * fail_rate


def difficulty_level(index: float) -> str:
    if index >= HARD_FROM:
        return "hard"
    if index >= MEDIUM_FROM:
        return "medium"
    return "easy"


def score_distribution(scores: pd.Series) -> list[dict]:
    # Балл 100 попадает в последний интервал, поэтому интервалов 10, а не 11.
    bins = (scores // BIN_WIDTH).clip(upper=BIN_COUNT - 1)
    counts = bins.value_counts()
    result = []
    for number in range(BIN_COUNT):
        low = number * BIN_WIDTH
        high = 100 if number == BIN_COUNT - 1 else low + BIN_WIDTH - 1
        result.append(
            {"range": f"{low}–{high}", "count": int(counts.get(number, 0)), "failing": high < FAIL_THRESHOLD}
        )
    return result


def add_anomaly_flags(items: list[dict]) -> None:
    """Отмечает темы, индекс сложности которых аномально выше, чем у остальных."""
    indexes = pd.Series([item["difficulty_index"] for item in items], dtype=float)
    spread = indexes.std()
    # Одна тема или одинаковые индексы: сравнивать не с чем, std равно NaN или 0.
    z_scores = (indexes - indexes.mean()) / spread if spread > 0 else indexes * 0
    for item, z_score in zip(items, z_scores):
        item["difficulty_z"] = round(float(z_score), 2)
        item["is_anomalous"] = bool(z_score >= ANOMALY_Z)


def topic_difficulty(results: pd.DataFrame) -> list[dict]:
    """Возвращает темы от самой сложной к самой лёгкой."""
    items = []
    for (topic_id, topic, hours), group in results.groupby(["topic_id", "topic", "hours_planned"]):
        avg_score = float(group["score"].mean())
        fail_rate = float((group["score"] < FAIL_THRESHOLD).mean())
        index = compute_index(avg_score, fail_rate)
        by_school = group.groupby(["school_id", "school"])["score"].mean()
        items.append(
            {
                "topic_id": int(topic_id),
                "topic": topic,
                "hours_planned": int(hours),
                "avg_score": round(avg_score, 1),
                "median_score": round(float(group["score"].median()), 1),
                # У единственного результата разброса нет, а std вернул бы NaN.
                "std_score": round(float(group["score"].std()), 1) if len(group) > 1 else 0.0,
                "fail_rate": round(fail_rate, 3),
                "difficulty_index": round(index, 3),
                "level": difficulty_level(index),
                "by_school": [
                    {"school_id": int(school_id), "school": school, "avg_score": round(float(score), 1)}
                    for (school_id, school), score in by_school.items()
                ],
                "score_distribution": score_distribution(group["score"]),
            }
        )
    add_anomaly_flags(items)
    return sorted(items, key=lambda item: (-item["difficulty_index"], item["topic_id"]))
