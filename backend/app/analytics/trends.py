"""Изменение результатов по годам. Метод описан в скилле metrics."""

import pandas as pd
import statsmodels.formula.api as smf

from app.analytics.regression import format_points
from app.analytics.textbooks import ALPHA, holm_adjust

MIN_YEARS = 3
IMPROVING = "улучшается"
WORSENING = "ухудшается"
STABLE = "без заметных изменений"


def describe(topic: str, direction: str, slope: float) -> str:
    if direction == STABLE:
        return f"Тема «{topic}»: результаты по годам заметно не меняются."
    return f"Тема «{topic}» {direction}: примерно на {format_points(slope)} балла в год."


def topic_trends(results: pd.DataFrame, year_stats: pd.DataFrame) -> list[dict]:
    """Возвращает темы от самого сильного ухудшения к самому сильному улучшению."""
    if year_stats.empty:
        return []

    current_year = int(year_stats["year"].max()) + 1
    current = results.groupby(["school_id", "topic_id"], as_index=False)["score"].mean()
    current = current.rename(columns={"score": "avg_score"}).assign(year=current_year)
    frame = pd.concat([year_stats, current], ignore_index=True)
    if frame["year"].nunique() < MIN_YEARS:
        return []

    names = results.drop_duplicates("topic_id").set_index("topic_id")["topic"]
    fitted = []
    for topic_id, group in frame.groupby("topic_id"):
        formula = "avg_score ~ year + C(school_id)" if group["school_id"].nunique() > 1 else "avg_score ~ year"
        fitted.append((int(topic_id), group, smf.ols(formula, data=group).fit()))

    adjusted = holm_adjust([float(model.pvalues["year"]) for _, _, model in fitted])
    items = []
    for (topic_id, group, model), p_adjusted in zip(fitted, adjusted):
        slope = float(model.params["year"])
        low, high = model.conf_int().loc["year"]
        direction = STABLE if p_adjusted >= ALPHA else IMPROVING if slope > 0 else WORSENING
        by_year = group.groupby("year")["avg_score"].mean()
        items.append(
            {
                "topic_id": topic_id,
                "topic": names[topic_id],
                "slope_per_year": round(slope, 2),
                "ci_low": round(float(low), 2),
                "ci_high": round(float(high), 2),
                "p_value": round(float(model.pvalues["year"]), 4),
                "p_adjusted": round(p_adjusted, 4),
                "direction": direction,
                "text": describe(names[topic_id], direction, slope),
                "by_year": [{"year": int(year), "avg_score": round(float(score), 1)} for year, score in by_year.items()],
            }
        )
    return sorted(items, key=lambda item: (item["slope_per_year"], item["topic_id"]))
