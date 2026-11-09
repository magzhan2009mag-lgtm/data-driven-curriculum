from collections.abc import Iterator

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from app.analytics.data import load_results
from app.analytics.difficulty import topic_difficulty
from app.analytics.hours_effect import hours_effect
from app.analytics.recommendations import recommend_hours, recommend_optimal_hours
from app.analytics.regression import textbook_regression
from app.analytics.textbooks import compare_textbooks
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


@app.get("/hours/effect")
def get_hours_effect(db: Session = Depends(get_db)) -> dict:
    return hours_effect(topic_difficulty(load_results(db)))
