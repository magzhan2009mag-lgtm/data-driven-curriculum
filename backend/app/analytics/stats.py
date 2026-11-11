"""Объём проанализированных данных для строки «Проанализировано: …» на главной."""

import pandas as pd


def data_stats(results: pd.DataFrame, n_item_responses: int, year_stats: pd.DataFrame) -> dict:
    """results и year_stats уже отфильтрованы по школе, если она выбрана."""
    years = sorted(int(year) for year in year_stats["year"].unique())
    return {
        "n_results": len(results),
        "n_item_responses": n_item_responses,
        "n_students": int(results["student_id"].nunique()),
        "n_classes": int(results["class_id"].nunique()),
        "n_schools": int(results["school_id"].nunique()),
        "n_topics": int(results["topic_id"].nunique()),
        "archive_from": years[0] if years else None,
        "archive_to": years[-1] if years else None,
    }
