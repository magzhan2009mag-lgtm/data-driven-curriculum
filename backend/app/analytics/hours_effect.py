"""Связь плановых часов и результата по темам. Метод описан в скилле metrics."""

import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

MIN_TOPICS = 3
CAVEAT = (
    "Это связь между разными темами, а не эффект дополнительного часа: темы различаются сложностью, "
    "и часы им назначены заранее. Наклон нельзя считать приростом балла от одного часа."
)


def hours_effect(topics: list[dict]) -> dict:
    """Принимает результат topic_difficulty."""
    frame = pd.DataFrame(topics, columns=["hours_planned", "avg_score"]).astype(float)
    response = {"n_topics": len(frame), "spearman_rho": None, "spearman_p": None,
                "slope": None, "ci_low": None, "ci_high": None, "p_value": None, "caveat": CAVEAT}

    if len(frame) < MIN_TOPICS or frame["hours_planned"].nunique() < 2 or frame["avg_score"].nunique() < 2:
        return {**response, "interpretation": "Данных недостаточно, чтобы оценить связь часов и результата."}

    spearman = stats.spearmanr(frame["hours_planned"], frame["avg_score"])
    model = smf.ols("avg_score ~ hours_planned", data=frame).fit()
    low, high = model.conf_int().loc["hours_planned"]
    rho = float(spearman.statistic)

    direction = "выше" if rho > 0 else "ниже"
    rho_text = f"{rho:.2f}".replace(".", ",")
    return {
        **response,
        "spearman_rho": round(rho, 3),
        "spearman_p": round(float(spearman.pvalue), 4),
        "slope": round(float(model.params["hours_planned"]), 2),
        "ci_low": round(float(low), 2),
        "ci_high": round(float(high), 2),
        "p_value": round(float(model.pvalues["hours_planned"]), 4),
        "interpretation": f"В темах с большим числом часов средний балл {direction} (ρ = {rho_text}).",
    }
