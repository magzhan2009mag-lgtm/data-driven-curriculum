from collections.abc import Iterator

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from app.analytics.data import load_results
from app.analytics.difficulty import topic_difficulty
from app.analytics.recommendations import recommend_hours
from app.analytics.textbooks import compare_textbooks
from app.database import SessionLocal

app = FastAPI(title="Data-Driven Curriculum API")


def get_db() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


@app.get("/topics/difficulty")
def get_topics_difficulty(db: Session = Depends(get_db)) -> list[dict]:
    return topic_difficulty(load_results(db))


@app.get("/textbooks/compare")
def get_textbooks_compare(topic_id: int | None = None, db: Session = Depends(get_db)) -> dict:
    results = load_results(db)
    if topic_id is not None and topic_id not in results["topic_id"].values:
        raise HTTPException(status_code=404, detail="Тема не найдена")
    return compare_textbooks(results, topic_id)


@app.get("/recommendations")
def get_recommendations(db: Session = Depends(get_db)) -> dict:
    return recommend_hours(topic_difficulty(load_results(db)))
