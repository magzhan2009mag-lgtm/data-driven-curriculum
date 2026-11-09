"""Поиск классов с аномальными результатами. Метод описан в скилле metrics."""

import pandas as pd
from scipy import stats

ROBUST_Z_THRESHOLD = 3.5
# Приводит медианное абсолютное отклонение к масштабу стандартного отклонения.
MAD_SCALE = 0.6745


def class_outliers(results: pd.DataFrame) -> dict:
    """Сравнивает классы по среднему z-баллу: темы разной сложности дают равный вклад."""
    groups = results.groupby("topic_id")["score"]
    z_scores = ((results["score"] - groups.transform("mean")) / groups.transform("std")).fillna(0)
    classes = (
        results.assign(z=z_scores)
        .groupby(["class_id", "class", "school"], as_index=False)["z"]
        .mean()
    )

    median = classes["z"].median()
    mad = float(stats.median_abs_deviation(classes["z"]))
    # При MAD = 0 больше половины классов совпадают, и масштаба для сравнения нет.
    classes["robust_z"] = MAD_SCALE * (classes["z"] - median) / mad if mad > 0 else 0.0

    outliers = [
        {
            "class_id": int(row["class_id"]),
            "class": row["class"],
            "school": row["school"],
            "mean_z": round(float(row["z"]), 3),
            "robust_z": round(float(row["robust_z"]), 2),
            "direction": "выше остальных" if row["robust_z"] > 0 else "ниже остальных",
        }
        for row in classes.to_dict("records")
        if abs(row["robust_z"]) >= ROBUST_Z_THRESHOLD
    ]
    outliers.sort(key=lambda item: -abs(item["robust_z"]))

    conclusion = (
        f"Классов с аномальными результатами: {len(outliers)} из {len(classes)}."
        if outliers
        else f"Среди {len(classes)} классов аномальных результатов не найдено."
    )
    return {"n_classes": len(classes), "outliers": outliers, "conclusion": conclusion}
