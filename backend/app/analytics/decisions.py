"""«Что решить по учебникам»: вывод и совет для каждого учебника. Правила описаны в скилле metrics."""

import pandas as pd

from app.analytics import how as explain
from app.analytics.prerequisites import plural
from app.analytics.textbooks import compare_textbooks

# Совет рассмотреть другой учебник — только при отставании хотя бы со средним эффектом (|d| Коэна ≥ 0,5).
# Малая разница не стоит смены учебника: хватит часов и материалов.
REPLACE_EFFECT = 0.5
# Сколько тем называть в тексте поимённо, остальные — числом.
SHOWN_TOPICS = 3


def points(value: float) -> str:
    return f"{value:.1f}".replace(".", ",")


def letter(textbook: str) -> str:
    return textbook.replace("Учебник ", "")


def letters_or(names: list[str]) -> str:
    short = [letter(name) for name in sorted(names)]
    return short[0] if len(short) == 1 else ", ".join(short[:-1]) + " или " + short[-1]


def quoted(topics: list[str]) -> str:
    items = [f"«{topic}»" for topic in topics]
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " и " + items[-1]


def topic_gaps(results: pd.DataFrame) -> tuple[list[dict], int]:
    """Значимые разницы учебников по каждой теме в одних и тех же школах.

    Это то же сравнение, что на странице «Учебники»: z-баллы внутри «школа × тема», Welch и поправка Холма
    по парам темы. Направление — по знаку d Коэна, разница в баллах — по adjusted_score.
    """
    gaps = []
    topic_ids = sorted(int(topic_id) for topic_id in results["topic_id"].unique())
    for topic_id in topic_ids:
        comparison = compare_textbooks(results, topic_id)
        scores = {book["name"]: book["adjusted_score"] for book in comparison["textbooks"]}
        for pair in comparison["comparisons"]:
            if not pair["significant"]:
                continue
            stronger, weaker = (pair["a"], pair["b"]) if pair["cohens_d"] > 0 else (pair["b"], pair["a"])
            gaps.append(
                {
                    "topic_id": topic_id,
                    "topic": comparison["topic"],
                    "stronger": stronger,
                    "weaker": weaker,
                    "points": round(abs(scores[stronger] - scores[weaker]), 1),
                    "p_adjusted": pair["p_adjusted"],
                    "cohens_d": round(abs(pair["cohens_d"]), 2),
                    "effect": pair["effect"],
                }
            )
    return gaps, len(topic_ids)


def by_topic(gaps: list[dict], other: str) -> dict[str, list[dict]]:
    """Темы с разницами, от самой большой разницы к меньшей; other — поле с другим учебником."""
    grouped: dict[str, list[dict]] = {}
    for gap in sorted(gaps, key=lambda item: -item["points"]):
        grouped.setdefault(gap["topic"], []).append(gap)
    return {topic: sorted(items, key=lambda item: item[other]) for topic, items in grouped.items()}


def letters_and(names: list[str]) -> str:
    short = [letter(name) for name in sorted(names)]
    return short[0] if len(short) == 1 else ", ".join(short[:-1]) + " и " + short[-1]


def in_topics(count: int, n_topics: int) -> str:
    return f"в {count} {plural(count, 'теме', 'темах', 'темах')} из {n_topics}"


def weaker_text(gaps: list[dict], n_topics: int) -> str:
    """«Значимо слабее A и C в 11 темах из 12. Больше всего: «Проценты» — на 11,6 балла ниже A и на 10,8 ниже C; …»."""
    topics = by_topic(gaps, "stronger")
    head = f"Значимо слабее {letters_and(list({gap['stronger'] for gap in gaps}))} {in_topics(len(topics), n_topics)}"
    details = []
    for position, (topic, items) in enumerate(list(topics.items())[:SHOWN_TOPICS]):
        unit = " балла" if position == 0 else ""
        parts = [f"на {points(item['points'])}{unit if index == 0 else ''} ниже {letter(item['stronger'])}"
                 for index, item in enumerate(items)]
        details.append(f"«{topic}» — " + " и ".join(parts))
    if len(topics) <= SHOWN_TOPICS:
        return f"{head}: " + "; ".join(details) + "."
    rest = [gap["points"] for topic in list(topics)[SHOWN_TOPICS:] for gap in topics[topic]]
    others = len(topics) - SHOWN_TOPICS
    return (f"{head}. Больше всего: " + "; ".join(details) + f". В остальных {others} "
            f"{plural(others, 'теме', 'темах', 'темах')} — на {points(min(rest))}–{points(max(rest))} балла.")


def stronger_text(gaps: list[dict], n_topics: int) -> str:
    """«Значимо сильнее A в 2 темах из 12: «Геометрические фигуры» (+3,6 балла) и …; сильнее B в 11 темах из 12 …»."""
    parts = []
    for rival in sorted({gap["weaker"] for gap in gaps}):
        items = sorted((gap for gap in gaps if gap["weaker"] == rival), key=lambda item: -item["points"])
        where = f"{letter(rival)} {in_topics(len(items), n_topics)}"
        if len(items) <= SHOWN_TOPICS:
            topics = [f"«{item['topic']}» (+{points(item['points'])}{' балла' if index == 0 else ''})"
                      for index, item in enumerate(items)]
            parts.append(f"{where}: " + ", ".join(topics))
        else:
            low, high = min(item["points"] for item in items), max(item["points"] for item in items)
            parts.append(f"{where} — на {points(low)}–{points(high)} балла")
    return "Значимо сильнее " + "; сильнее ".join(parts) + "."


def equivalence(name: str, others: list[str], gaps: list[dict], n_topics: int) -> list[dict]:
    """С кем учебник равноценен: нет значимых различий или они меньше чем в половине тем."""
    result = []
    for other in others:
        topics = sorted({gap["topic"] for gap in gaps if {gap["stronger"], gap["weaker"]} == {name, other}})
        if len(topics) * 2 < n_topics:
            result.append({"textbook": other, "except_topics": topics})
    return result


def equivalence_text(items: list[dict]) -> str:
    parts = []
    for item in items:
        where = "В остальных темах равноценен" if item["except_topics"] else "Равноценен"
        parts.append(f"{where} учебнику {letter(item['textbook'])}: выбирайте по цене и удобству.")
    return " ".join(parts)


def decision_how(name: str, results: pd.DataFrame, weaker: list[dict], stronger: list[dict]) -> dict:
    """Сначала темы, где учебник отстаёт (на них держится совет), потом где он сильнее; внутри — от большей разницы."""
    own = results[results["textbook"] == name]
    ordered = sorted(weaker, key=lambda item: -item["points"]) + sorted(stronger, key=lambda item: -item["points"])
    tests = [
        explain.check(f"«{gap['topic']}»: {letter(gap['weaker'])} ниже {letter(gap['stronger'])} на {points(gap['points'])}",
                      gap["p_adjusted"], "d Коэна", gap["cohens_d"], gap["effect"])
        for gap in ordered
    ]
    return explain.how(explain.DECISION, int(own["student_id"].nunique()), len(own), tests)


def textbook_decision(name: str, textbooks: list[str], gaps: list[dict], n_topics: int) -> dict:
    weaker = [gap for gap in gaps if gap["weaker"] == name]
    stronger = [gap for gap in gaps if gap["stronger"] == name]
    equivalent = equivalence(name, [book for book in textbooks if book != name], gaps, n_topics)
    serious = [gap for gap in weaker if gap["cohens_d"] >= REPLACE_EFFECT]

    advice = short_advice = None
    alternatives: list[str] = []
    if serious:
        verdict = "replace"
        alternatives = sorted({gap["stronger"] for gap in serious})
        topics = list(by_topic(serious, "stronger"))
        advice = (f"При следующем выборе учебника рассмотреть {letters_or(alternatives)}; пока он используется — "
                  f"больше часов на {quoted(topics)} и дополнительные материалы.")
        short_advice = (f"Совет: при следующем выборе рассмотреть {letters_or(alternatives)}; пока — больше часов "
                        f"на {quoted(topics[:2])}.")
    elif weaker:
        verdict = "strengthen"
        topics = list(by_topic(weaker, "stronger"))
        advice = (f"Менять учебник не нужно: разница малая. По {plural(len(topics), 'теме', 'темам', 'темам')} "
                  f"{quoted(topics)} — дополнительные материалы и, если нужно, часы.")
        short_advice = advice
    elif stronger:
        verdict = "strong"
    else:
        verdict = "equal"

    parts = []
    if weaker:
        parts.append(weaker_text(weaker, n_topics))
    if stronger:
        parts.append(stronger_text(stronger, n_topics))
    if equivalent:
        parts.append(equivalence_text(equivalent))
    return {
        "textbook": name,
        "verdict": verdict,
        "weaker": weaker,
        "stronger": stronger,
        "equivalent": equivalent,
        "alternatives": alternatives,
        "text": " ".join(parts),
        "advice": advice,
        "short_advice": short_advice,
    }


def textbook_decisions(results: pd.DataFrame, all_schools: bool = False, note: str | None = None) -> dict:
    """Строка-вывод для каждого учебника: где значимо слабее (и что делать), где сильнее, с кем равноценен."""
    gaps, n_topics = topic_gaps(results)
    textbooks = sorted(results["textbook"].unique())
    return {
        "all_schools": all_schools,
        "note": note,
        "n_topics": n_topics,
        "textbooks": [
            {**decision, "how": decision_how(decision["textbook"], results, decision["weaker"], decision["stronger"])}
            for decision in (textbook_decision(name, textbooks, gaps, n_topics) for name in textbooks)
        ],
    }
