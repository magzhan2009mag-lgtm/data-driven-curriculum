"""«Главное за минуту»: четыре вывода для верха главной. Правила описаны в скилле metrics."""

from app.analytics.prerequisites import dependents_phrase, plural
from app.analytics.schools import in_school

LEVEL_WORDS = {"hard": "сложная", "medium": "средней сложности", "easy": "лёгкая"}


def score(value: float) -> str:
    return f"{value:.1f}".replace(".", ",")


def percent(share: float) -> str:
    return f"{round(share * 100)}%"


def letter(textbook: str) -> str:
    return textbook.replace("Учебник ", "")


def card(kind: str, label: str, text: str, path: str, *, headline: str | None = None, value: float | None = None,
         unit: str | None = None, value_all: float | None = None, all_schools: bool = False,
         advice: str | None = None) -> dict:
    """Карточка-вывод. unit: score (балл из 100) или hours (часы); value_all — то же по всем школам."""
    return {"kind": kind, "label": label, "headline": headline, "value": value, "unit": unit,
            "value_all": value_all, "text": text, "path": path, "all_schools": all_schools, "advice": advice}


def hardest_topic_card(topics: list[dict]) -> dict:
    """Темы приходят от самой сложной: первая и есть самая сложная."""
    topic = topics[0]
    fail_all = topic.get("fail_rate_all")
    compare = f" (по всем школам {percent(fail_all)})" if fail_all is not None else ""
    text = (f"Тема {LEVEL_WORDS[topic['level']]}: не справились {percent(topic['fail_rate'])} "
            f"результатов{compare}.")
    return card("hardest_topic", "Самая сложная тема", text, f"/topics/{topic['topic_id']}",
                headline=topic["topic"], value=topic["avg_score"], unit="score", value_all=topic.get("avg_score_all"))


def pair_verdict(pair: dict | None) -> str:
    if pair is None or pair["p_adjusted"] is None:
        return "данных для вывода мало"
    if pair["significant"]:
        return f"разница значимая, эффект {pair['effect']}"
    return "разница не подтверждается"


def weakest_textbook_card(comparison: dict, overall: dict, school: str | None, decisions: dict | None = None) -> dict:
    """Самый слабый учебник по баллу «в одинаковых школах».

    В одной школе, где у какого-то учебника мало учеников, сравнение берётся по всем школам
    (all_schools) — иначе вывода не было бы вовсе.
    """
    use_overall = school is not None and any(not book["enough_data"] for book in comparison["textbooks"])
    source = overall if use_overall else comparison
    books = sorted(source["textbooks"], key=lambda book: (book["adjusted_score"], book["name"]))
    if len(books) < 2:
        return card("weakest_textbook", "Самый слабый учебник", "Сравнивать не с чем: учебник один.", "/textbooks")
    weakest, best = books[0], books[-1]
    pair = next(
        (item for item in source["comparisons"] if {item["a"], item["b"]} == {weakest["name"], best["name"]}), None
    )
    where = "В одинаковых школах" if school is None or use_overall else in_school(school)
    text = (f"{where} {score(weakest['adjusted_score'])} балла против {score(best['adjusted_score'])} "
            f"у учебника {letter(best['name'])}: {pair_verdict(pair)}.")
    if use_overall:
        text = f"{in_school(school)} учеников мало, поэтому вывод по всем школам. {text}"
    decision = next((item for item in (decisions or {}).get("textbooks", []) if item["textbook"] == weakest["name"]), None)
    return card("weakest_textbook", "Самый слабый учебник", text, "/textbooks", headline=weakest["name"],
                value=weakest["adjusted_score"], unit="score",
                value_all=None if use_overall else weakest.get("adjusted_score_all"), all_schools=use_overall,
                advice=decision["short_advice"] if decision else None)


def hours_card(hours: dict) -> dict:
    moved = hours["hours_moved"]
    added = sorted((item for item in hours["items"] if item["delta"] > 0), key=lambda item: (-item["delta"], item["topic_id"]))
    if moved == 0:
        text = "Менять часы не нужно: сложным темам хватает часов."
    else:
        topics = ", ".join(f"«{item['topic']}» +{item['delta']}" for item in added)
        total = hours["total_hours"]
        text = f"С лёгких тем на сложные: {topics}. Всего в программе {total} {plural(total, 'час', 'часа', 'часов')}, как и было."
    return card("hours", "Сколько часов перенести", text, "/recommendations", value=moved, unit="hours",
                value_all=hours.get("hours_moved_all"))


def finding_card(outliers: dict, prerequisites: dict, topics: list[dict], school: str | None = None,
                 active_roots: set[int] | None = None) -> dict:
    """Необычный класс, если он есть в выбранном срезе; иначе корень проблемы.

    active_roots — корни, которые дают час в плане школы; у остальных пишем, почему часа нет.
    """
    if outliers["outliers"]:
        item = outliers["outliers"][0]
        text = (f"Тема «{item['topic']}»: {score(item['avg_score'])} балла при ожидаемых "
                f"{score(item['expected_score'])}. Стоит выяснить, как её проходили в этом классе.")
        return card("outlier", "Необычный класс", text, f"/topics/{item['topic_id']}",
                    headline=f"{item['class']}, {item['school']}", value=item["avg_score"], unit="score")
    if prerequisites["roots"]:
        root = prerequisites["roots"][0]
        topic = next(item for item in topics if item["topic_id"] == root["topic_id"])
        names = [dependent["topic"] for dependent in root["dependents"]]
        text = f"От неё {dependents_phrase(names)}: пробелы в ней переходят дальше по программе."
        if school is not None and active_roots is not None and root["topic_id"] not in active_roots:
            text += f" {in_school(school)} зависимые темы не сложные, поэтому лишний час ей не нужен."
        return card("root", "Корень проблемы", text, f"/topics/{root['topic_id']}", headline=root["topic"],
                    value=topic["avg_score"], unit="score", value_all=topic.get("avg_score_all"))
    return card("outlier", "Необычные результаты", outliers["conclusion"], "/")


def build_summary(topics: list[dict], comparison: dict, overall: dict, hours: dict, outliers: dict,
                  prerequisites: dict, school: str | None, active_roots: set[int] | None = None,
                  decisions: dict | None = None) -> dict:
    return {
        "cards": [
            hardest_topic_card(topics),
            weakest_textbook_card(comparison, overall, school, decisions),
            hours_card(hours),
            finding_card(outliers, prerequisites, topics, school, active_roots),
        ]
    }
