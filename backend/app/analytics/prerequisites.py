"""Связи между темами и корни проблемы. Метод описан в скилле metrics."""

from itertools import combinations

import numpy as np
import pandas as pd
from scipy import stats

from app.analytics import how as explain
from app.analytics.difficulty import topic_difficulty
from app.analytics.textbooks import ALPHA, holm_adjust

MIN_STD_COEF = 0.15
MIN_STUDENTS = 50
MIN_TOPICS = 3
# Насколько хуже ранняя тема в тексте связи: «на 10 баллов хуже».
POINTS_STEP = 10
# Дисперсия остатка темы не опускается ниже этой доли её полной дисперсии.
MIN_UNIQUE_SHARE = 0.01
ROOT_LEVELS = ("hard", "medium")
NOTE = (
    "Связь значит, что у учеников одного уровня пробелы в ранней теме идут вместе с провалом поздней. "
    "Это повод проверить, как проходят тему-основу, но не доказательство причины."
)


def plural(count: int, one: str, few: str, many: str) -> str:
    last_two = abs(count) % 100
    last = last_two % 10
    if last == 1 and last_two != 11:
        return one
    if last in (2, 3, 4) and last_two not in (12, 13, 14):
        return few
    return many


def format_points(value: float) -> str:
    rounded = round(abs(value), 1)
    if rounded == int(rounded):
        count = int(rounded)
        return f"{count} {plural(count, 'балл', 'балла', 'баллов')}"
    return f"{rounded:.1f}".replace(".", ",") + " балла"


def quoted(names: list[str]) -> str:
    items = [f"«{name}»" for name in names]
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " и " + items[-1]


def dependents_phrase(names: list[str]) -> str:
    """«зависит тема «Проценты»» или «зависят темы «Десятичные дроби» и «Проценты»»."""
    if len(names) == 1:
        return f"зависит тема {quoted(names)}"
    return f"зависят темы {quoted(names)}"


def student_topic_scores(results: pd.DataFrame) -> pd.DataFrame:
    """Средний балл ученика по каждой теме. Остаются ученики, у которых есть все темы."""
    return results.groupby(["student_id", "topic_id"])["score"].mean().unstack().dropna()


def common_loadings(cov: np.ndarray) -> np.ndarray:
    """Вклад общего уровня ученика в каждую тему по модели с одним общим фактором.

    Квадрат вклада темы t — медиана S_tj·S_tk / S_jk по всем парам других тем. Медиана нужна,
    чтобы одна-две прямые связи между темами не попали в общий уровень.
    """
    size = len(cov)
    loadings = np.zeros(size)
    for topic in range(size):
        others = [index for index in range(size) if index != topic]
        ratios = [cov[topic, j] * cov[topic, k] / cov[j, k] for j, k in combinations(others, 2) if cov[j, k] > 0]
        loadings[topic] = np.sqrt(max(float(np.median(ratios)), 0.0)) if ratios else 0.0
    return loadings


def unique_cov(cov: np.ndarray) -> np.ndarray:
    """Ковариация остатков тем: то, что не объясняется общим уровнем ученика."""
    loadings = common_loadings(cov)
    unique = cov - np.outer(loadings, loadings)
    np.fill_diagonal(unique, np.maximum(np.diag(unique), MIN_UNIQUE_SHARE * np.diag(cov)))
    return unique


def earlier_topic_effects(unique: np.ndarray, n_students: int) -> list[dict]:
    """Для каждой темы — регрессия её остатка на остатки всех тем, которые идут раньше по программе."""
    effects = []
    for target in range(1, len(unique)):
        earlier = list(range(target))
        inverse = np.linalg.pinv(unique[np.ix_(earlier, earlier)])
        coefs = inverse @ unique[earlier, target]
        residual = max(float(unique[target, target] - unique[earlier, target] @ coefs), 1e-9)
        errors = np.sqrt(np.diag(inverse) * residual / n_students)
        for position, base in enumerate(earlier):
            coef = float(coefs[position])
            effects.append(
                {
                    "base": base,
                    "target": target,
                    "coef": coef,
                    "std_coef": coef * float(np.sqrt(unique[base, base] / unique[target, target])),
                    "p_value": float(2 * stats.norm.sf(abs(coef / errors[position]))),
                }
            )
    return effects


def link_text(base: str, target: str, points: float) -> str:
    return (
        f"Ученики, которые написали «{base}» на {POINTS_STEP} баллов хуже, чем ученики их уровня, "
        f"пишут «{target}» в среднем на {format_points(points)} хуже."
    )


def root_text(topic: str, level: str, dependents: list[dict]) -> str:
    """«Тема «Проценты» сложная, но корень — тема «Дроби»: пробелы в ней переходят в …»."""
    hard = [item["topic"] for item in dependents if item["level"] == "hard"]
    problem = f"Тема {quoted(hard)} сложная" if len(hard) == 1 else f"Темы {quoted(hard)} сложные"
    text = (
        f"{problem}, но корень — тема «{topic}»: пробелы в ней переходят в "
        f"{quoted([item['topic'] for item in dependents])}."
    )
    if level == "hard":
        return f"{text} Сама тема «{topic}» тоже сложная."
    return f"{text} Сама она средней сложности, и по её баллам проблему легко не заметить."


def find_roots(links: list[dict], levels: dict[int, str]) -> list[dict]:
    """Корень — сложная или средняя тема, от которой зависит хотя бы одна сложная тема."""
    roots = []
    for base_id in sorted({link["from_topic_id"] for link in links}):
        outgoing = [link for link in links if link["from_topic_id"] == base_id]
        dependents = [
            {"topic_id": link["to_topic_id"], "topic": link["to_topic"], "level": levels[link["to_topic_id"]]}
            for link in outgoing
        ]
        if levels[base_id] not in ROOT_LEVELS or not any(item["level"] == "hard" for item in dependents):
            continue
        topic = outgoing[0]["from_topic"]
        roots.append(
            {
                "topic_id": base_id,
                "topic": topic,
                "level": levels[base_id],
                "dependents": dependents,
                "text": root_text(topic, levels[base_id], dependents),
            }
        )
    return roots


def build_conclusion(links: list[dict], roots: list[dict]) -> str:
    if not links:
        return "Связей между темами не найдено: провал одной темы не тянет за собой следующие."
    found = f"Найдено связей между темами: {len(links)}."
    if not roots:
        return f"{found} Ни одна из них не ведёт к сложной теме."
    return f"{found} {'Корень' if len(roots) == 1 else 'Корни'} проблемы: {quoted([root['topic'] for root in roots])}."


def topic_prerequisites(results: pd.DataFrame) -> dict:
    """Находит темы, слабое освоение которых тянет за собой провал следующих тем."""
    difficulty = topic_difficulty(results)
    levels = {item["topic_id"]: item["level"] for item in difficulty}
    topics = [
        {"topic_id": item["topic_id"], "topic": item["topic"], "level": item["level"]}
        for item in sorted(difficulty, key=lambda item: item["topic_id"])
    ]
    scores = student_topic_scores(results)
    response = {"topics": topics, "links": [], "roots": [], "n_students": len(scores), "note": NOTE}

    if scores.shape[1] < MIN_TOPICS or len(scores) < MIN_STUDENTS:
        return {**response, "conclusion": "Мало данных, чтобы искать связи между темами."}

    topic_ids = [int(topic_id) for topic_id in scores.columns]
    names = {item["topic_id"]: item["topic"] for item in topics}
    effects = earlier_topic_effects(unique_cov(np.cov(scores.to_numpy(dtype=float), rowvar=False)), len(scores))

    links = []
    for effect, p_adjusted in zip(effects, holm_adjust([effect["p_value"] for effect in effects])):
        if p_adjusted >= ALPHA or effect["std_coef"] < MIN_STD_COEF:
            continue
        base, target = topic_ids[effect["base"]], topic_ids[effect["target"]]
        points = POINTS_STEP * effect["coef"]
        links.append(
            {
                "from_topic_id": base,
                "from_topic": names[base],
                "to_topic_id": target,
                "to_topic": names[target],
                "coef": round(effect["coef"], 3),
                "std_coef": round(effect["std_coef"], 3),
                "p_value": round(effect["p_value"], 6),
                "p_adjusted": round(p_adjusted, 6),
                "points": round(points, 1),
                "text": link_text(names[base], names[target], points),
            }
        )
    links.sort(key=lambda link: (link["from_topic_id"], link["to_topic_id"]))
    roots = find_roots(links, levels)
    n_results = int(results["student_id"].isin(scores.index).sum())
    for root in roots:
        root["how"] = explain.how(
            explain.ROOT,
            len(scores),
            n_results,
            [
                explain.check(f"«{link['from_topic']}» → «{link['to_topic']}»", link["p_adjusted"],
                              "стандартизованный коэффициент", link["std_coef"],
                              f"{format_points(link['points'])} на каждые 10")
                for link in links
                if link["from_topic_id"] == root["topic_id"]
            ],
        )
    return {**response, "links": links, "roots": roots, "conclusion": build_conclusion(links, roots)}


def root_dependents(prerequisites: dict) -> dict[int, list[str]]:
    """Корни для рекомендаций по часам: тема → названия всех тем, которые от неё зависят."""
    return {root["topic_id"]: [item["topic"] for item in root["dependents"]] for root in prerequisites["roots"]}
