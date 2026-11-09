"""Регрессия с контролем школы и темы. Метод описан в скилле metrics."""

import pandas as pd
import statsmodels.formula.api as smf

from app.analytics.textbooks import ALPHA, holm_adjust

CLUSTER_NOTE = (
    "Класс не входит в формулу как отдельный фактор: у каждого класса один учебник, и их вклады "
    "нельзя разделить. Поэтому погрешность считается с учётом группировки учеников по классам."
)


def format_points(value: float) -> str:
    return f"{abs(value):.1f}".replace(".", ",")


def build_conclusion(subject: str, reference: str, effects: list[dict]) -> str:
    sentences = []
    for effect in effects:
        if not effect["significant"]:
            continue
        direction = "выше" if effect["coef"] > 0 else "ниже"
        sentences.append(
            f"{effect['textbook']} {direction}, чем {reference}, на {format_points(effect['coef'])} балла "
            "при одинаковых школе и теме."
        )
    if not sentences:
        return f"{subject}: при одинаковых школе и теме значимых отличий от «{reference}» не найдено."
    return f"{subject}: " + " ".join(sentences)


def textbook_regression(results: pd.DataFrame, topic_id: int | None = None) -> dict:
    """Оценивает вклад учебника относительно первого по алфавиту."""
    scope = results if topic_id is None else results[results["topic_id"] == topic_id]
    topic = None if topic_id is None or scope.empty else scope["topic"].iloc[0]
    response = {"topic_id": topic_id, "topic": topic, "reference": None, "effects": [],
                "n_results": len(scope), "n_classes": int(scope["class_id"].nunique()), "note": CLUSTER_NOTE}

    if scope["textbook"].nunique() < 2 or scope["class_id"].nunique() < 2:
        return {**response, "conclusion": "Данных недостаточно, чтобы оценить вклад учебника."}

    formula = "score ~ C(textbook)"
    if scope["school_id"].nunique() > 1:
        formula += " + C(school_id)"
    if scope["topic_id"].nunique() > 1:
        formula += " + C(topic_id)"
    # Классов мало, поэтому интервалы считаем по t-распределению, а не по нормальному.
    model = smf.ols(formula, data=scope).fit(cov_type="cluster", cov_kwds={"groups": scope["class_id"]}, use_t=True)

    names = sorted(scope["textbook"].unique())
    reference, others = names[0], names[1:]
    terms = [f"C(textbook)[T.{name}]" for name in others]
    intervals = model.conf_int()
    adjusted = holm_adjust([float(model.pvalues[term]) for term in terms])

    effects = [
        {
            "textbook": name,
            "coef": round(float(model.params[term]), 2),
            "ci_low": round(float(intervals.loc[term, 0]), 2),
            "ci_high": round(float(intervals.loc[term, 1]), 2),
            "p_value": round(float(model.pvalues[term]), 4),
            "p_adjusted": round(p_adjusted, 4),
            "significant": p_adjusted < ALPHA,
        }
        for name, term, p_adjusted in zip(others, terms, adjusted)
    ]
    subject = f"Тема «{topic}»" if topic else "Все темы"
    return {**response, "reference": reference, "effects": effects,
            "conclusion": build_conclusion(subject, reference, effects)}
