"""Проверка методов: находят ли они ровно то, что заложено в синтетические данные, и ничего лишнего.

Генерирует данные с seed 1–8 с закономерностями и те же seed без них, прогоняет методы и печатает
таблицу в Markdown (её результат — в README). Запуск из папки backend:

    python -m scripts.validate
"""

import sys
import tempfile
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.analytics.data import load_item_responses, load_results, load_year_stats
from app.analytics.decisions import REPLACE_EFFECT, textbook_decisions
from app.analytics.items import item_quality
from app.analytics.outliers import class_outliers
from app.analytics.prerequisites import topic_prerequisites
from app.analytics.textbooks import compare_textbooks
from app.analytics.trends import topic_trends
from app.models import Base
from scripts.seed import ANOMALY, BAD_ITEMS, PREREQUISITES, STRONG_C_TOPICS, WEAK_B_TOPICS, YEARLY_TREND, generate

SEEDS = range(1, 9)
NO_PATTERNS = {"prerequisites": {}, "textbook_effects": False, "anomaly": False, "bad_items": False, "trends": False}

# B отстаёт на 8+ баллов в «Дробях» и «Процентах» (−8 против 0 у A и +1 у C) и в геометрии (−3 против +5 у C).
PLANTED = {
    "replace": {("Учебник B", topic) for topic in WEAK_B_TOPICS | STRONG_C_TOPICS},
    "a_vs_c": set(STRONG_C_TOPICS),
    "links": {(base, target) for target, bases in PREREQUISITES.items() for base, _ in bases},
    "outliers": {(f"Школа №{ANOMALY[0]}", ANOMALY[1], ANOMALY[2])},
    "bad_items": set(BAD_ITEMS),
    "trends": {(topic, "ухудшается" if slope < 0 else "улучшается") for topic, slope in YEARLY_TREND.items()},
}
COLUMNS = {
    "replace": "Совет заменить учебник",
    "a_vs_c": "Разница A и C",
    "links": "Связи тем",
    "outliers": "Необычный класс",
    "bad_items": "Плохие задания",
    "trends": "Тренды",
}


def findings(session: Session) -> dict[str, set]:
    """Что нашли методы: те же функции, что отдают API."""
    results = load_results(session)
    decisions = textbook_decisions(results)["textbooks"]
    replace = {
        (item["textbook"], gap["topic"])
        for item in decisions
        if item["verdict"] == "replace"
        for gap in item["weaker"]
        if gap["cohens_d"] >= REPLACE_EFFECT
    }
    a_vs_c = {
        gap["topic"]
        for item in decisions
        for gap in item["weaker"]
        if {gap["weaker"], gap["stronger"]} == {"Учебник A", "Учебник C"}
    }
    links = {(link["from_topic"], link["to_topic"]) for link in topic_prerequisites(results)["links"]}
    outliers = {(item["school"], item["class"], item["topic"]) for item in class_outliers(results)["outliers"]}
    bad_items = set()
    for topic_id in sorted(int(topic_id) for topic_id in results["topic_id"].unique()):
        quality = item_quality(load_item_responses(session, topic_id), topic_id)
        bad_items |= {(quality["topic"], item["test_number"], item["item_number"]) for item in quality["items"] if item["is_bad"]}
    trends = {
        (item["topic"], item["direction"])
        for item in topic_trends(results, load_year_stats(session))
        if item["direction"] != "без заметных изменений"
    }
    trap = compare_textbooks(results)["confounding_note"] is not None
    return {"replace": replace, "a_vs_c": a_vs_c, "links": links, "outliers": outliers, "bad_items": bad_items,
            "trends": trends, "trap": trap}


def run(seed: int, patterns: bool, folder: Path) -> dict:
    engine = create_engine(f"sqlite:///{(folder / f'seed{seed}_{int(patterns)}.db').as_posix()}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        generate(session, seed=seed, **({} if patterns else NO_PATTERNS))
        result = findings(session)
    engine.dispose()
    return result


def cell(found: set, expected: set) -> str:
    """«✓ 3 из 3», «2 из 3», «лишних: 1»; на данных без закономерностей ожидается пусто."""
    extra = len(found - expected)
    if not expected:
        return "✓ ничего" if not found else f"лишних: {extra}"
    hit = len(found & expected)
    text = f"{hit} из {len(expected)}"
    if extra:
        text += f", лишних: {extra}"
    return f"✓ {text}" if hit == len(expected) and not extra else text


def table(rows: list[tuple[int, dict]], patterns: bool) -> list[str]:
    head = ["seed", *COLUMNS.values(), "Ловушка «C лучше»"]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for seed, found in rows:
        expected = PLANTED if patterns else {key: set() for key in PLANTED}
        cells = [cell(found[key], expected[key]) for key in COLUMNS]
        lines.append(f"| {seed} | " + " | ".join(cells) + f" | {'распознана' if found['trap'] else 'нет'} |")
    return lines


def totals(rows: list[tuple[int, dict]], patterns: bool) -> str:
    expected = PLANTED if patterns else {key: set() for key in PLANTED}
    hits = sum(len(found[key] & expected[key]) for _, found in rows for key in COLUMNS)
    planted = sum(len(expected[key]) for _ in rows for key in COLUMNS)
    extra = sum(len(found[key] - expected[key]) for _, found in rows for key in COLUMNS)
    return f"Найдено заложенного: {hits} из {planted}; лишних находок: {extra}."


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        for patterns in (True, False):
            rows = []
            for seed in SEEDS:
                rows.append((seed, run(seed, patterns, folder)))
                print(f"seed {seed} {'с закономерностями' if patterns else 'без'}: готово", file=sys.stderr)
            print(f"\n### {'С заложенными закономерностями' if patterns else 'Без закономерностей'}\n")
            print("\n".join(table(rows, patterns)))
            print(f"\n{totals(rows, patterns)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
