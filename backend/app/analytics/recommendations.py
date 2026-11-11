"""Рекомендации по часам. Правила описаны в скилле metrics."""

import math

import pandas as pd
from scipy.optimize import linprog

from app.analytics.difficulty import HARD_FROM, topic_difficulty
from app.analytics.prerequisites import ROOT_LEVELS, dependents_phrase, plural, root_dependents, topic_prerequisites
from app.analytics.textbooks import MIN_STUDENTS, adjust_for_school

# Корень проблемы: тема → названия тем, которые от неё зависят.
Roots = dict[int, list[str]]

MIN_HOURS = 1


def change_limit(hours: int) -> int:
    return max(2, round(0.3 * hours))


def hours_word(count: int) -> str:
    last_two = abs(count) % 100
    last = last_two % 10
    if last == 1 and last_two != 11:
        return "час"
    if last in (2, 3, 4) and last_two not in (12, 13, 14):
        return "часа"
    return "часов"


def format_ratio(value: float) -> str:
    return f"{value:.1f}".replace(".", ",")


def difficulty_ratio(topic: dict) -> float:
    """Во сколько раз тема сложнее границы сложной темы."""
    return topic["difficulty_index"] / HARD_FROM


def target_hours(topic: dict) -> int:
    """Часы пропорционально сложности: тема в 1,4 раза сложнее границы получает в 1,4 раза больше часов."""
    hours = topic["hours_planned"]
    # Округление «как в школе»: round() в Python округляет 6,5 до 6.
    return max(hours + 1, math.floor(hours * difficulty_ratio(topic) + 0.5))


def hard_need(topic: dict) -> int:
    """Сколько часов сложной теме нужно добавить, с учётом лимита изменения."""
    if topic["level"] != "hard":
        return 0
    return min(target_hours(topic) - topic["hours_planned"], change_limit(topic["hours_planned"]))


def root_dependents_of(topic: dict, roots: Roots | None) -> list[str]:
    """Темы, которые зависят от этой, если она корень проблемы в этом плане (сложная или средняя)."""
    if not roots or topic["level"] not in ROOT_LEVELS:
        return []
    return roots.get(topic["topic_id"], [])


def topic_need(topic: dict, roots: Roots | None = None) -> int:
    """Сколько часов добавить теме: сложной по её сложности, корню проблемы ещё час, в пределах лимита."""
    need = hard_need(topic)
    if root_dependents_of(topic, roots):
        need = min(need + 1, change_limit(topic["hours_planned"]))
    return need


def redistribute(topics: list[dict], roots: Roots | None = None) -> dict[int, int]:
    """Переносит по одному часу с лёгких тем на сложные и корни. Возвращает изменение по каждой теме."""
    deltas = {topic["topic_id"]: 0 for topic in topics}

    def current_hours(topic: dict) -> int:
        return topic["hours_planned"] + deltas[topic["topic_id"]]

    def pressure(topic: dict) -> float:
        return topic["difficulty_index"] / current_hours(topic)

    while True:
        # Получают только темы с нуждой: у донора изменение отрицательное, но часы ему не возвращаются.
        receivers = [
            topic for topic in topics
            if topic_need(topic, roots) > 0 and deltas[topic["topic_id"]] < topic_need(topic, roots)
        ]
        donors = [
            topic for topic in topics
            if topic["level"] == "easy"
            and -deltas[topic["topic_id"]] < change_limit(topic["hours_planned"])
            and current_hours(topic) > MIN_HOURS
        ]
        if not receivers or not donors:
            return deltas

        receiver = min(receivers, key=lambda topic: (-pressure(topic), topic["topic_id"]))
        donor = min(donors, key=lambda topic: (pressure(topic), topic["topic_id"]))
        deltas[receiver["topic_id"]] += 1
        deltas[donor["topic_id"]] -= 1


def optimize(topics: list[dict], roots: Roots | None = None) -> dict[int, int]:
    """Находит перенос часов с максимальной суммой difficulty_index × изменение часов."""
    if not topics:
        return {}

    bounds = []
    for topic in topics:
        limit = change_limit(topic["hours_planned"])
        need = topic_need(topic, roots)
        if need:
            bounds.append((0, need))
        elif topic["level"] == "easy":
            bounds.append((-min(limit, topic["hours_planned"] - MIN_HOURS), 0))
        else:
            bounds.append((0, 0))

    solution = linprog(
        c=[-topic["difficulty_index"] for topic in topics],
        A_eq=[[1] * len(topics)],
        b_eq=[0],
        bounds=bounds,
        method="highs-ds",
    )
    # Границы целые, а ограничение одно с единичными коэффициентами: вершина решения всегда целая.
    return {topic["topic_id"]: round(delta) for topic, delta in zip(topics, solution.x)}


def hard_reason(topic: dict, delta: int, facts: str, dependents: list[str]) -> str:
    current = topic["hours_planned"]
    root = f" От неё {dependents_phrase(dependents)}, поэтому ей нужен ещё час." if dependents else ""
    if not delta:
        return f"Тема сложная: {facts}{root} Часы не добавлены: не осталось лёгких тем, с которых можно их перенести."

    ratio = difficulty_ratio(topic)
    target = target_hours(topic)
    if ratio < 1.05:
        basis = "Тема на границе сложной, поэтому добавляем минимум."
    else:
        basis = (
            f"Она в {format_ratio(ratio)} раза сложнее границы сложной темы, поэтому ей нужно около "
            f"{target} {hours_word(target)} вместо {current}."
        )
    text = (
        f"Тема сложная: {facts} {basis}{root} "
        f"Рекомендуем добавить {delta} {hours_word(delta)} ({current} → {current + delta})."
    )
    if delta < target - current + (1 if dependents else 0):
        if delta == change_limit(current):
            text += " Больше не добавляем, чтобы не менять программу резко."
        else:
            text += " Больше перенести не с чего."
    return text


def build_reason(topic: dict, delta: int, roots: Roots | None = None) -> str:
    current = topic["hours_planned"]
    target = current + delta
    facts = f"средний балл {topic['avg_score']:.0f} из 100, не справились {topic['fail_rate']:.0%} результатов."
    amount = f"{abs(delta)} {hours_word(delta)}"
    dependents = root_dependents_of(topic, roots)

    if topic["level"] == "hard":
        return hard_reason(topic, delta, facts, dependents)
    if dependents:
        root = f"Тема средней сложности: {facts} От неё {dependents_phrase(dependents)}"
        if delta:
            return f"{root}, поэтому рекомендуем добавить {amount} ({current} → {target})."
        return f"{root}, но часы перенести не с чего. Оставляем {current} {hours_word(current)}."
    if topic["level"] == "easy":
        if delta:
            return f"Тема усваивается хорошо: {facts} Можно передать {amount} более сложным темам ({current} → {target})."
        return f"Тема усваивается хорошо: {facts} Сложным темам больше не нужны часы отсюда, оставляем {current} {hours_word(current)}."
    return f"Тема средней сложности: {facts} Оставляем {current} {hours_word(current)} без изменений."


def recommend_hours(topics: list[dict], roots: Roots | None = None) -> dict:
    """Принимает результат topic_difficulty и возвращает рекомендации в том же порядке."""
    return build_response(topics, redistribute(topics, roots), roots)


def recommend_optimal_hours(topics: list[dict], roots: Roots | None = None) -> dict:
    """То же, что recommend_hours, но перенос часов находит линейное программирование."""
    return {**build_response(topics, optimize(topics, roots), roots), "method": "linprog"}


def build_response(topics: list[dict], deltas: dict[int, int], roots: Roots | None = None) -> dict:
    return {
        "total_hours": sum(topic["hours_planned"] for topic in topics),
        "hours_moved": sum(delta for delta in deltas.values() if delta > 0),
        "items": [
            {
                "topic_id": topic["topic_id"],
                "topic": topic["topic"],
                "level": topic["level"],
                "hours_current": topic["hours_planned"],
                "hours_recommended": topic["hours_planned"] + deltas[topic["topic_id"]],
                "delta": deltas[topic["topic_id"]],
                "reason": build_reason(topic, deltas[topic["topic_id"]], roots),
            }
            for topic in topics
        ],
    }


def plan_text(textbook: str, added: list[dict]) -> str:
    if not added:
        return f"{textbook}: менять часы не нужно."
    topics = ", ".join(f"«{item['topic']}» +{item['delta']}" for item in added)
    return f"{textbook}: добавить часы на {topics}."


def not_enough_text(textbook: str, count: int, school: str) -> str:
    students = plural(count, "ученик", "ученика", "учеников")
    return (
        f"{textbook}: в {school.replace('Школа', 'Школе', 1)} всего {count} {students}, "
        "этого мало для отдельного плана. Смотрите план по всем школам."
    )


def recommend_by_textbook(results: pd.DataFrame, roots: Roots | None = None, school: str | None = None) -> dict:
    """Общий план плюс отдельный план для классов каждого учебника.

    Общий план считается по сырым баллам. Планы учебников считаются по баллам с поправкой на школу,
    как если бы все учебники проходили в одинаковых школах: иначе учебник, который чаще выбирают
    сильные школы, выглядел бы лучше, чем есть. У каждого учебника свой перенос часов,
    и сумма часов в каждом плане не меняется. Корни проблемы общие для всех планов: без roots
    они считаются по тем же результатам. В одной школе (school) учебник, у которого меньше
    MIN_STUDENTS учеников, отдельного плана не получает: по 1–2 классам вывод был бы случайным.
    """
    if roots is None:
        roots = root_dependents(topic_prerequisites(results))
    response = recommend_hours(topic_difficulty(results), roots)
    breakdown = {item["topic_id"]: [] for item in response["items"]}
    plans = []
    students = results.groupby("textbook")["student_id"].nunique()
    for textbook, group in adjust_for_school(results).groupby("textbook"):
        if school is not None and students[textbook] < MIN_STUDENTS:
            reason = not_enough_text(textbook, int(students[textbook]), school)
            for rows in breakdown.values():
                rows.append({"textbook": textbook, "level": None, "avg_score": None, "fail_rate": None,
                             "difficulty_index": None, "hours_recommended": None, "delta": None, "reason": reason})
            plans.append({"textbook": textbook, "hours_moved": 0, "added": [], "text": reason, "enough_data": False})
            continue
        topics = topic_difficulty(group)
        deltas = redistribute(topics, roots)
        added = []
        for topic in topics:
            delta = deltas[topic["topic_id"]]
            breakdown[topic["topic_id"]].append(
                {
                    "textbook": textbook,
                    "level": topic["level"],
                    "avg_score": topic["avg_score"],
                    "fail_rate": topic["fail_rate"],
                    "difficulty_index": topic["difficulty_index"],
                    "hours_recommended": topic["hours_planned"] + delta,
                    "delta": delta,
                    "reason": f"{textbook}. {build_reason(topic, delta, roots)}",
                }
            )
            if delta > 0:
                added.append({"topic_id": topic["topic_id"], "topic": topic["topic"], "delta": delta})
        added.sort(key=lambda item: (-item["delta"], item["topic_id"]))
        plans.append(
            {
                "textbook": textbook,
                "hours_moved": sum(item["delta"] for item in added),
                "added": added,
                "text": plan_text(textbook, added),
                "enough_data": True,
            }
        )

    for item in response["items"]:
        item["by_textbook"] = breakdown[item["topic_id"]]
    return {**response, "textbook_plans": plans}
