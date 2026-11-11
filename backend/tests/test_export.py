import csv
import io
from urllib.parse import unquote

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app, get_db

HEADER = ["Тема", "Часов по плану", "Рекомендовано всем классам", "Учебник A", "Учебник B", "Учебник C", "Причина"]


@pytest.fixture(scope="module")
def client(seeded_engine):
    def override_get_db():
        with Session(seeded_engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def read_rows(response) -> list[list[str]]:
    return list(csv.reader(io.StringIO(response.content.decode("utf-8-sig")), delimiter=";"))


def test_csv_opens_in_russian_excel(client):
    response = client.get("/recommendations/export.csv")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert response.content.startswith(b"\xef\xbb\xbf")
    disposition = response.headers["content-disposition"]
    assert disposition.startswith('attachment; filename="hours.csv"')
    assert unquote(disposition.split("UTF-8''")[1]) == "часы-по-темам.csv"
    assert b"\r\n" in response.content


def test_csv_matches_recommendations(client):
    rows = read_rows(client.get("/recommendations/export.csv"))
    assert rows[0] == HEADER
    assert len(rows) == 13
    plan = {item["topic"]: item for item in client.get("/recommendations").json()["items"]}
    assert [row[0] for row in rows[1:]] == sorted(plan, key=lambda name: plan[name]["topic_id"])
    for topic, hours, overall, a, b, c, reason in rows[1:]:
        item = plan[topic]
        assert (int(hours), int(overall), reason) == (item["hours_current"], item["hours_recommended"], item["reason"])
        assert [int(a), int(b), int(c)] == [row["hours_recommended"] for row in item["by_textbook"]]
    assert sum(int(row[2]) for row in rows[1:]) == 84


def test_csv_follows_school(client):
    response = client.get("/recommendations/export.csv?school_id=5")
    assert unquote(response.headers["content-disposition"].split("UTF-8''")[1]) == "часы-по-темам-школа-5.csv"
    rows = read_rows(response)
    plan = {item["topic"]: item for item in client.get("/recommendations?school_id=5").json()["items"]}
    for row in rows[1:]:
        assert int(row[2]) == plan[row[0]]["hours_recommended"]
        # В Школе №5 у учебников A и B мало учеников: отдельного плана нет.
        assert row[3:5] == ["мало данных", "мало данных"]
        assert row[5].isdigit()


def test_csv_unknown_school(client):
    response = client.get("/recommendations/export.csv?school_id=999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Школа не найдена"
