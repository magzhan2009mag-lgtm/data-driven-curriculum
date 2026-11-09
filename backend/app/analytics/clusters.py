"""Группировка похожих тем и школ. Метод описан в скилле metrics."""

import pandas as pd
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.preprocessing import StandardScaler

RANDOM_STATE = 42
TOPIC_FEATURES = ["avg_score", "fail_rate", "std_score"]
TOPIC_GROUP_NAMES = ("Слабые результаты", "Средние результаты", "Сильные результаты")
SCHOOL_GROUP_NAMES = ("Результаты ниже", "Результаты выше")


def cluster_topics(topics: list[dict]) -> list[dict]:
    """K-means тем. Принимает результат topic_difficulty."""
    if len(topics) < len(TOPIC_GROUP_NAMES):
        return []

    frame = pd.DataFrame(topics)
    features = StandardScaler().fit_transform(frame[TOPIC_FEATURES])
    model = KMeans(n_clusters=len(TOPIC_GROUP_NAMES), random_state=RANDOM_STATE, n_init=10)
    frame["cluster"] = model.fit_predict(features)
    return summarize(frame, "topic_id", "topic", TOPIC_GROUP_NAMES, "avg_score")


def cluster_schools(results: pd.DataFrame) -> list[dict]:
    """Иерархическая кластеризация школ по профилю средних баллов за темы."""
    profile = results.pivot_table(index=["school_id", "school"], columns="topic_id", values="score", aggfunc="mean")
    if len(profile) < len(SCHOOL_GROUP_NAMES):
        return []

    model = AgglomerativeClustering(n_clusters=len(SCHOOL_GROUP_NAMES), linkage="ward")
    frame = profile.index.to_frame(index=False)
    frame["avg_score"] = profile.mean(axis=1).to_numpy()
    frame["cluster"] = model.fit_predict(profile.to_numpy())
    return summarize(frame, "school_id", "school", SCHOOL_GROUP_NAMES, "avg_score")


def summarize(frame: pd.DataFrame, id_column: str, name_column: str, names: tuple[str, ...], score: str) -> list[dict]:
    """Именует группы по среднему баллу: номера кластеров сами по себе ничего не значат."""
    order = frame.groupby("cluster")[score].mean().sort_values().index
    return [
        {
            "group": name,
            "avg_score": round(float(frame.loc[frame["cluster"] == cluster, score].mean()), 1),
            "members": [
                {"id": int(row[id_column]), "name": row[name_column]}
                for _, row in frame[frame["cluster"] == cluster].iterrows()
            ],
        }
        for name, cluster in zip(names, order)
    ]
