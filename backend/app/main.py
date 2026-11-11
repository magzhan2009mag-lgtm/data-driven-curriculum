from collections.abc import Iterator

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Response
from sqlalchemy.orm import Session

from app.analytics.clusters import cluster_schools, cluster_topics
from app.analytics.data import load_item_responses, load_results, load_students, load_year_stats
from app.analytics.difficulty import topic_difficulty
from app.analytics.explain import explain_recommendations
from app.analytics.hours_effect import hours_effect
from app.analytics.items import item_quality
from app.analytics.matching import match_textbooks
from app.analytics.outliers import class_outliers
from app.analytics.prerequisites import root_dependents, topic_prerequisites
from app.analytics.recommendations import recommend_by_textbook, recommend_hours, recommend_optimal_hours
from app.analytics.regression import textbook_regression
from app.analytics.schools import (
    SCOPE_NOTE,
    Scope,
    add_all_schools_to_hours,
    add_all_schools_to_textbooks,
    add_all_schools_to_topics,
    add_classes_to_topics,
    few_students,
    list_schools,
    only_school,
    outliers_for_school,
    school_note,
)
from app.analytics.export import content_disposition, csv_filename, hours_csv
from app.analytics.summary import build_summary
from app.analytics.textbooks import MIN_STUDENTS, compare_textbooks
from app.analytics.trends import topic_trends
from app.database import SessionLocal

app = FastAPI(title="Data-Driven Curriculum API")


def get_db() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


def get_scope(school_id: int | None = None, db: Session = Depends(get_db)) -> Scope:
    """Необязательный фильтр по школе, общий для всех эндпоинтов."""
    results = load_results(db)
    if school_id is None:
        return Scope(results, results)
    scoped = only_school(results, school_id)
    if scoped.empty:
        raise HTTPException(status_code=404, detail="Школа не найдена")
    return Scope(results, scoped, school_id, scoped["school"].iloc[0])


def require_topic(results: pd.DataFrame, topic_id: int | None) -> None:
    if topic_id is not None and topic_id not in results["topic_id"].values:
        raise HTTPException(status_code=404, detail="Тема не найдена")


def topic_scope(results: pd.DataFrame, topic_id: int | None) -> pd.DataFrame:
    return results if topic_id is None else results[results["topic_id"] == topic_id]


def all_school_roots(scope: Scope) -> dict[int, list[str]]:
    """Корни проблемы считаются по всем школам: внутри одной школы связи тем не найти."""
    return root_dependents(topic_prerequisites(scope.all_results))


def hours_for(scope: Scope, roots: dict[int, list[str]] | None = None) -> dict:
    roots = all_school_roots(scope) if roots is None else roots
    response = recommend_by_textbook(scope.results, roots, scope.school)
    if scope.filtered:
        add_all_schools_to_hours(response, recommend_hours(topic_difficulty(scope.all_results), roots))
    return response


@app.get("/schools")
def get_schools(db: Session = Depends(get_db)) -> list[dict]:
    return list_schools(load_results(db))


def topics_for(scope: Scope) -> list[dict]:
    topics = topic_difficulty(scope.results)
    if scope.filtered:
        add_all_schools_to_topics(topics, topic_difficulty(scope.all_results))
        add_classes_to_topics(topics, scope.results)
    return topics


def outliers_for(scope: Scope) -> dict:
    response = class_outliers(scope.all_results)
    return outliers_for_school(response, scope.school_id, scope.school) if scope.filtered else response


@app.get("/topics/difficulty")
def get_topics_difficulty(scope: Scope = Depends(get_scope)) -> list[dict]:
    return topics_for(scope)


@app.get("/summary")
def get_summary(scope: Scope = Depends(get_scope)) -> dict:
    """«Главное за минуту»: самая сложная тема, самый слабый учебник, перенос часов, необычный класс или корень."""
    prerequisites = topic_prerequisites(scope.all_results)
    comparison = compare_textbooks(scope.results)
    overall = compare_textbooks(scope.all_results) if scope.filtered else comparison
    return build_summary(
        topics_for(scope),
        comparison,
        overall,
        hours_for(scope, root_dependents(prerequisites)),
        outliers_for(scope),
        prerequisites,
        scope.school,
    )


@app.get("/textbooks/compare")
def get_textbooks_compare(topic_id: int | None = None, scope: Scope = Depends(get_scope)) -> dict:
    require_topic(scope.all_results, topic_id)
    response = compare_textbooks(scope.results, topic_id)
    response["school_note"] = None
    if scope.filtered:
        add_all_schools_to_textbooks(response, compare_textbooks(scope.all_results, topic_id))
        few = {book["name"]: book["n_students"] for book in response["textbooks"] if book["n_students"] < MIN_STUDENTS}
        response["school_note"] = school_note(scope.school, few)
    return response


@app.get("/textbooks/regression")
def get_textbooks_regression(topic_id: int | None = None, scope: Scope = Depends(get_scope)) -> dict:
    require_topic(scope.all_results, topic_id)
    if not scope.filtered:
        return textbook_regression(scope.results, topic_id)
    scoped = topic_scope(scope.results, topic_id)
    few = few_students(scoped)
    response = textbook_regression(scoped[~scoped["textbook"].isin(few)], topic_id)
    return {**response, "school_note": school_note(scope.school, few)}


@app.get("/textbooks/matching")
def get_textbooks_matching(
    topic_id: int | None = None, scope: Scope = Depends(get_scope), db: Session = Depends(get_db)
) -> dict:
    require_topic(scope.all_results, topic_id)
    students = load_students(db)
    if not scope.filtered:
        return match_textbooks(scope.results, students, topic_id)
    response = match_textbooks(scope.results, students[students["school_id"] == scope.school_id], topic_id)
    return {**response, "school_note": school_note(scope.school, few_students(topic_scope(scope.results, topic_id)))}


@app.get("/recommendations")
def get_recommendations(scope: Scope = Depends(get_scope)) -> dict:
    return hours_for(scope)


@app.get("/recommendations/export.csv")
def get_recommendations_csv(scope: Scope = Depends(get_scope)) -> Response:
    """План часов для Excel. Учитывает фильтр по школе."""
    return Response(
        content=hours_csv(hours_for(scope)).encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": content_disposition(csv_filename(scope.school_id))},
    )


@app.get("/recommendations/optimal")
def get_recommendations_optimal(scope: Scope = Depends(get_scope)) -> dict:
    return recommend_optimal_hours(topic_difficulty(scope.results), all_school_roots(scope))


@app.get("/recommendations/explanation")
def get_recommendations_explanation(scope: Scope = Depends(get_scope)) -> dict:
    return explain_recommendations(hours_for(scope))


@app.get("/hours/effect")
def get_hours_effect(scope: Scope = Depends(get_scope)) -> dict:
    return hours_effect(topic_difficulty(scope.results))


@app.get("/clusters")
def get_clusters(scope: Scope = Depends(get_scope)) -> dict:
    schools = cluster_schools(scope.all_results)
    if not scope.filtered:
        return {"topics": cluster_topics(topic_difficulty(scope.results)), "schools": schools}
    # Группы школ осмысленны только среди всех школ: показываем группу выбранной.
    own = [
        {**group, "members": [member for member in group["members"] if member["id"] == scope.school_id]}
        for group in schools
        if any(member["id"] == scope.school_id for member in group["members"])
    ]
    return {"topics": cluster_topics(topic_difficulty(scope.results)), "schools": own, "scope_note": SCOPE_NOTE}


@app.get("/classes/outliers")
def get_class_outliers(scope: Scope = Depends(get_scope)) -> dict:
    return outliers_for(scope)


@app.get("/items/quality")
def get_items_quality(topic_id: int, scope: Scope = Depends(get_scope), db: Session = Depends(get_db)) -> dict:
    responses = load_item_responses(db, topic_id, scope.school_id)
    if responses.empty:
        raise HTTPException(status_code=404, detail="Тема не найдена")
    return item_quality(responses, topic_id)


@app.get("/topics/prerequisites")
def get_topics_prerequisites(scope: Scope = Depends(get_scope)) -> dict:
    response = topic_prerequisites(scope.all_results)
    return {**response, "scope_note": SCOPE_NOTE} if scope.filtered else response


@app.get("/topics/trends")
def get_topics_trends(scope: Scope = Depends(get_scope), db: Session = Depends(get_db)) -> list[dict]:
    year_stats = load_year_stats(db)
    if scope.filtered:
        year_stats = year_stats[year_stats["school_id"] == scope.school_id]
    return topic_trends(scope.results, year_stats)
