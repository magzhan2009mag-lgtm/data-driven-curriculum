"""Рекомендации по часам. Правила описаны в скилле metrics."""

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


def redistribute(topics: list[dict]) -> dict[int, int]:
    """Переносит по одному часу с лёгких тем на сложные. Возвращает изменение по каждой теме."""
    deltas = {topic["topic_id"]: 0 for topic in topics}

    def current_hours(topic: dict) -> int:
        return topic["hours_planned"] + deltas[topic["topic_id"]]

    def pressure(topic: dict) -> float:
        return topic["difficulty_index"] / current_hours(topic)

    while True:
        receivers = [
            topic for topic in topics
            if topic["level"] == "hard" and deltas[topic["topic_id"]] < change_limit(topic["hours_planned"])
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


def build_reason(topic: dict, delta: int) -> str:
    current = topic["hours_planned"]
    target = current + delta
    facts = f"средний балл {topic['avg_score']:.0f} из 100, не справились {topic['fail_rate']:.0%} учеников."
    amount = f"{abs(delta)} {hours_word(delta)}"

    if topic["level"] == "hard":
        if delta:
            return f"Тема сложная: {facts} Рекомендуем добавить {amount} ({current} → {target})."
        return f"Тема сложная: {facts} Часы не добавлены: не осталось лёгких тем, с которых можно их перенести."
    if topic["level"] == "easy":
        if delta:
            return f"Тема усваивается хорошо: {facts} Можно передать {amount} более сложным темам ({current} → {target})."
        return f"Тема усваивается хорошо: {facts} Сложным темам больше не нужны часы отсюда, оставляем {current} {hours_word(current)}."
    return f"Тема средней сложности: {facts} Оставляем {current} {hours_word(current)} без изменений."


def recommend_hours(topics: list[dict]) -> dict:
    """Принимает результат topic_difficulty и возвращает рекомендации в том же порядке."""
    deltas = redistribute(topics)
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
                "reason": build_reason(topic, deltas[topic["topic_id"]]),
            }
            for topic in topics
        ],
    }
