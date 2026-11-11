"""Поиск классов, у которых провалена или неожиданно хорошо пройдена отдельная тема.

Метод описан в скилле metrics.
"""

import numpy as np
import pandas as pd
from scipy import stats

ROBUST_Z_THRESHOLD = 3.5
# Приводит медианное абсолютное отклонение к масштабу стандартного отклонения.
MAD_SCALE = 0.6745
MIN_TOPICS = 3
MAX_REFITS = 10


def format_points(value: float) -> str:
    return f"{abs(value):.1f}".replace(".", ",")


def expected_scores(cells: pd.DataFrame, excluded: np.ndarray) -> np.ndarray:
    """Ожидаемый балл класса по теме: общий уровень класса плюс сложность темы для его учебника.

    Уровень класса уже включает школу, поэтому отдельно её учитывать не нужно.
    Взвешенный метод наименьших квадратов по средним «класс × тема»; excluded не участвуют в оценке.
    """
    design = pd.concat(
        [
            pd.get_dummies(cells["class_id"], prefix="class"),
            pd.get_dummies(cells["textbook"] + "|" + cells["topic_id"].astype(str), prefix="topic"),
        ],
        axis=1,
    ).to_numpy(float)
    weights = np.sqrt(cells["n"].to_numpy(float)) * ~excluded
    coefficients, *_ = np.linalg.lstsq(design * weights[:, None], cells["score"].to_numpy() * weights, rcond=None)
    return design @ coefficients


def fit_residuals(cells: pd.DataFrame, excluded: np.ndarray) -> None:
    """Добавляет ожидаемый балл, отклонение от него и робастный z; масштаб берётся без исключённых."""
    cells["expected"] = expected_scores(cells, excluded)
    cells["difference"] = cells["avg_score"] - cells["expected"]
    kept = cells["difference"][~excluded]
    mad = float(stats.median_abs_deviation(kept))
    # При MAD = 0 больше половины ячеек совпадают с ожиданием, и масштаба для сравнения нет.
    cells["robust_z"] = MAD_SCALE * (cells["difference"] - kept.median()) / mad if mad > 0 else 0.0


def describe(item: dict) -> str:
    direction = "ниже" if item["difference"] < 0 else "выше"
    advice = (
        "Стоит выяснить, как проходили тему в этом классе."
        if item["difference"] < 0
        else "Стоит изучить опыт учителя."
    )
    return (
        f"{item['class']}, {item['school']}: тема «{item['topic']}» — {format_points(item['avg_score'])} балла, "
        f"на {format_points(item['difference'])} {direction} ожидаемого для этого класса. {advice}"
    )


def class_outliers(results: pd.DataFrame) -> dict:
    """Ищет пары «класс × тема», результат которых не объясняется уровнем класса и учебником."""
    cells = results.groupby(["class_id", "class", "school_id", "school", "textbook", "topic_id", "topic"], as_index=False).agg(
        avg_score=("score", "mean"), n=("score", "size")
    )
    n_classes = int(cells["class_id"].nunique())
    if cells["topic_id"].nunique() < MIN_TOPICS or n_classes < 2:
        return {"n_classes": n_classes, "n_cells": len(cells), "outliers": [],
                "conclusion": "Данных недостаточно, чтобы искать аномальные результаты."}

    cells["score"] = cells["avg_score"]
    # Аномальная ячейка тянет за собой оценку уровня класса и темы, и соседние ячейки
    # кажутся необычными. Поэтому по одной исключаем самую крайнюю и пересчитываем ожидания.
    excluded = np.zeros(len(cells), dtype=bool)
    for _ in range(MAX_REFITS):
        fit_residuals(cells, excluded)
        candidates = cells["robust_z"].abs().where(~excluded, 0)
        if candidates.max() < ROBUST_Z_THRESHOLD:
            break
        excluded[int(np.argmax(candidates.to_numpy()))] = True
    else:
        fit_residuals(cells, excluded)

    outliers = []
    for row in cells.to_dict("records"):
        if abs(row["robust_z"]) < ROBUST_Z_THRESHOLD:
            continue
        item = {
            "class_id": int(row["class_id"]),
            "class": row["class"],
            "school_id": int(row["school_id"]),
            "school": row["school"],
            "textbook": row["textbook"],
            "topic_id": int(row["topic_id"]),
            "topic": row["topic"],
            "avg_score": round(float(row["avg_score"]), 1),
            "expected_score": round(float(row["expected"]), 1),
            "difference": round(float(row["difference"]), 1),
            "robust_z": round(float(row["robust_z"]), 2),
            "direction": "выше ожидаемого" if row["difference"] > 0 else "ниже ожидаемого",
        }
        item["text"] = describe(item)
        outliers.append(item)
    outliers.sort(key=lambda item: -abs(item["robust_z"]))

    conclusion = (
        f"Необычных результатов: {len(outliers)} (проверено {n_classes} классов по всем темам)."
        if outliers
        else f"Среди {n_classes} классов необычных результатов по отдельным темам не найдено."
    )
    return {"n_classes": n_classes, "n_cells": len(cells), "outliers": outliers, "conclusion": conclusion}
