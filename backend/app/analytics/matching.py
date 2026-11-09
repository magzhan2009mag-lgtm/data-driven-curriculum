"""Propensity score matching для сравнения учебников. Метод описан в скилле metrics."""

from itertools import combinations

import numpy as np
import pandas as pd
from scipy import stats
from scipy.special import logit
from sklearn.linear_model import LogisticRegression

from app.analytics.textbooks import ALPHA, MIN_STUDENTS, NOT_ENOUGH_DATA, holm_adjust, student_z_scores

CALIPER_SD = 0.2
LOGISTIC_MAX_ITERATIONS = 1000
NOTE = (
    "Подбор выравнивает только входной тест и школу. Различия, которых нет в этих данных, "
    "например опыт учителя, он не учитывает."
)


def standardized_difference(a: pd.Series, b: pd.Series) -> float:
    spread = np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2)
    return 0.0 if spread == 0 else float((a.mean() - b.mean()) / spread)


def propensity_logits(data: pd.DataFrame, a: str) -> np.ndarray:
    """Логит вероятности учиться по учебнику a при данных входном тесте и школе."""
    pretest = data["pretest_score"].astype(float)
    spread = pretest.std()
    features = pd.get_dummies(data["school_id"].astype(str), dtype=float)
    features["pretest"] = (pretest - pretest.mean()) / spread if spread > 0 else 0.0
    model = LogisticRegression(max_iter=LOGISTIC_MAX_ITERATIONS)
    model.fit(features.to_numpy(), (data["textbook"] == a).to_numpy())
    probability = model.predict_proba(features.to_numpy())[:, 1]
    return logit(np.clip(probability, 1e-6, 1 - 1e-6))


def nearest_pairs(treated: pd.DataFrame, control: pd.DataFrame, caliper: float) -> list[tuple[int, int]]:
    """Жадный подбор 1:1 без возвращения: каждому берём ближайшего свободного в пределах caliper."""
    free = control.sort_values("student_id")
    pairs = []
    for row in treated.sort_values("student_id").to_dict("records"):
        if free.empty:
            break
        distances = (free["ps_logit"] - row["ps_logit"]).abs()
        best = distances.idxmin()
        if distances[best] <= caliper:
            pairs.append((row["student_id"], free.at[best, "student_id"]))
            free = free.drop(best)
    return pairs


def match_pair(data: pd.DataFrame, a: str, b: str) -> dict:
    """Принимает таблицу student_id, textbook, z, pretest_score, school_id."""
    pair = data[data["textbook"].isin([a, b])].copy()
    pair["ps_logit"] = propensity_logits(pair, a)
    caliper = CALIPER_SD * float(pair["ps_logit"].std())

    group_a, group_b = pair[pair["textbook"] == a], pair[pair["textbook"] == b]
    treated, control = (group_a, group_b) if len(group_a) <= len(group_b) else (group_b, group_a)
    matched = nearest_pairs(treated, control, caliper)

    by_student = pair.set_index("student_id")
    first, second = [row[0] for row in matched], [row[1] for row in matched]
    if treated is not group_a:
        first, second = second, first
    matched_a, matched_b = by_student.loc[first], by_student.loc[second]

    result = {
        "a": a,
        "b": b,
        "n_a": len(group_a),
        "n_b": len(group_b),
        "n_matched": len(matched),
        "smd_before": round(standardized_difference(group_a["pretest_score"], group_b["pretest_score"]), 3),
        "smd_after": None,
        "mean_difference": None,
        "ci_low": None,
        "ci_high": None,
        "p_value": None,
    }
    if len(matched) < MIN_STUDENTS:
        return result

    differences = matched_a["z"].to_numpy() - matched_b["z"].to_numpy()
    test = stats.ttest_rel(matched_a["z"], matched_b["z"])
    interval = test.confidence_interval(0.95)
    p_value = float(test.pvalue)
    return {
        **result,
        "smd_after": round(standardized_difference(matched_a["pretest_score"], matched_b["pretest_score"]), 3),
        "mean_difference": round(float(differences.mean()), 3),
        "ci_low": round(float(interval.low), 3),
        "ci_high": round(float(interval.high), 3),
        # Если разница всегда нулевая, тест возвращает NaN: различий увидеть нельзя.
        "p_value": 1.0 if np.isnan(p_value) else p_value,
    }


def build_conclusion(subject: str, pairs: list[dict]) -> str:
    sentences = []
    for pair in pairs:
        if not pair["significant"]:
            continue
        higher, lower = (pair["a"], pair["b"]) if pair["mean_difference"] > 0 else (pair["b"], pair["a"])
        size = f"{abs(pair['mean_difference']):.2f}".replace(".", ",")
        sentences.append(f"{higher} выше, чем {lower}, на {size} стандартного отклонения.")
    if sentences:
        return f"{subject}, среди похожих учеников: " + " ".join(sentences)
    if any(pair["p_adjusted"] is not None for pair in pairs):
        return f"{subject}: среди похожих учеников значимой разницы между учебниками не найдено."
    return f"{subject}: {NOT_ENOUGH_DATA}, чтобы сравнить учебники на похожих учениках."


def match_textbooks(results: pd.DataFrame, students: pd.DataFrame, topic_id: int | None = None) -> dict:
    """Сравнивает пары учебников на учениках с похожими входным тестом и школой."""
    scope = results if topic_id is None else results[results["topic_id"] == topic_id]
    topic = None if topic_id is None or scope.empty else scope["topic"].iloc[0]
    data = student_z_scores(scope).merge(students, on="student_id")

    pairs = [match_pair(data, a, b) for a, b in combinations(sorted(data["textbook"].unique()), 2)]
    for pair in pairs:
        pair.update(p_adjusted=None, significant=False)
    tested = [pair for pair in pairs if pair["p_value"] is not None]
    for pair, adjusted in zip(tested, holm_adjust([pair["p_value"] for pair in tested])):
        pair.update(p_value=round(pair["p_value"], 4), p_adjusted=round(adjusted, 4), significant=adjusted < ALPHA)

    subject = f"Тема «{topic}»" if topic else "Все темы"
    return {"topic_id": topic_id, "topic": topic, "pairs": pairs,
            "conclusion": build_conclusion(subject, pairs), "note": NOTE}
