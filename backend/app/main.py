from collections.abc import Iterator

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from app.analytics.clusters import cluster_schools, cluster_topics
from app.analytics.data import load_item_responses, load_results, load_students, load_year_stats
from app.analytics.difficulty import topic_difficulty
from app.analytics.explain import explain_recommendations
from app.analytics.hours_effect import hours_effect
from app.analytics.items import item_quality
from app.analytics.matching import match_textbooks
from app.analytics.outliers import class_outliers
from app.analytics.recommendations import recommend_hours, recommend_optimal_hours
from app.analytics.regression import textbook_regression
from app.analytics.textbooks import compare_textbooks
from app.analytics.trends import topic_trends
from app.database import SessionLocal

app = FastAPI(title="Data-Driven Curriculum API")


def get_db() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


def require_topic(results: pd.DataFrame, topic_id: int | None) -> None:
    if topic_id is not None and topic_id not in results["topic_id"].values:
        raise HTTPException(status_code=404, detail="Тема не найдена")


@app.get("/topics/difficulty")
def get_topics_difficulty(db: Session = Depends(get_db)) -> list[dict]:
    return topic_difficulty(load_results(db))


@app.get("/textbooks/compare")
def get_textbooks_compare(topic_id: int | None = None, db: Session = Depends(get_db)) -> dict:
    results = load_results(db)
    require_topic(results, topic_id)
    return compare_textbooks(results, topic_id)


@app.get("/textbooks/regression")
def get_textbooks_regression(topic_id: int | None = None, db: Session = Depends(get_db)) -> dict:
    results = load_results(db)
    require_topic(results, topic_id)
    return textbook_regression(results, topic_id)


@app.get("/recommendations")
def get_recommendations(db: Session = Depends(get_db)) -> dict:
    return recommend_hours(topic_difficulty(load_results(db)))


@app.get("/recommendations/optimal")
def get_recommendations_optimal(db: Session = Depends(get_db)) -> dict:
    return recommend_optimal_hours(topic_difficulty(load_results(db)))


@app.get("/recommendations/explanation")
def get_recommendations_explanation(db: Session = Depends(get_db)) -> dict:
    return explain_recommendations(recommend_hours(topic_difficulty(load_results(db))))


@app.get("/hours/effect")
def get_hours_effect(db: Session = Depends(get_db)) -> dict:
    return hours_effect(topic_difficulty(load_results(db)))


@app.get("/clusters")
def get_clusters(db: Session = Depends(get_db)) -> dict:
    results = load_results(db)
    return {"topics": cluster_topics(topic_difficulty(results)), "schools": cluster_schools(results)}


@app.get("/classes/outliers")
def get_class_outliers(db: Session = Depends(get_db)) -> dict:
    return class_outliers(load_results(db))


@app.get("/items/quality")
def get_items_quality(topic_id: int, db: Session = Depends(get_db)) -> dict:
    responses = load_item_responses(db, topic_id)
    if responses.empty:
        raise HTTPException(status_code=404, detail="Тема не найдена")
    return item_quality(responses, topic_id)


@app.get("/topics/trends")
def get_topics_trends(db: Session = Depends(get_db)) -> list[dict]:
    return topic_trends(load_results(db), load_year_stats(db))


@app.get("/textbooks/matching")
def get_textbooks_matching(topic_id: int | None = None, db: Session = Depends(get_db)) -> dict:
    results = load_results(db)
    require_topic(results, topic_id)
    return match_textbooks(results, load_students(db), topic_id)
