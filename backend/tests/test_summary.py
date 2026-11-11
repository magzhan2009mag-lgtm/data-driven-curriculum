import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.analytics.summary import finding_card, hours_card, weakest_textbook_card
from app.main import app, get_db

KINDS = ["hardest_topic", "weakest_textbook", "hours"]


@pytest.fixture(scope="module")
def client(seeded_engine):
    def override_get_db():
        with Session(seeded_engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def cards(client, query: str = "") -> dict[str, dict]:
    body = client.get(f"/summary{query}").json()
    assert len(body["cards"]) == 4
    return {card["kind"]: card for card in body["cards"]}


def test_summary_without_school(client):
    result = cards(client)
    assert list(result)[:3] == KINDS
    topics = client.get("/topics/difficulty").json()
    hardest = result["hardest_topic"]
    assert (hardest["headline"], hardest["value"], hardest["path"]) == (topics[0]["topic"], topics[0]["avg_score"], "/topics/3")
    assert hardest["value_all"] is None

    compare = client.get("/textbooks/compare").json()
    weakest = min(compare["textbooks"], key=lambda book: book["adjusted_score"])
    assert result["weakest_textbook"]["headline"] == weakest["name"] == "Учебник B"
    assert "разница значимая" in result["weakest_textbook"]["text"]
    assert not result["weakest_textbook"]["all_schools"]

    hours = client.get("/recommendations").json()
    assert result["hours"]["value"] == hours["hours_moved"]
    assert "84 часа" in result["hours"]["text"]

    outlier = result["outlier"]
    assert (outlier["headline"], outlier["path"]) == ("6Д, Школа №4", "/topics/7")


def test_summary_follows_school(client):
    result = cards(client, "?school_id=5")
    topics = client.get("/topics/difficulty?school_id=5").json()
    hardest = result["hardest_topic"]
    assert (hardest["value"], hardest["value_all"]) == (topics[0]["avg_score"], topics[0]["avg_score_all"])

    hours = client.get("/recommendations?school_id=5").json()
    assert (result["hours"]["value"], result["hours"]["value_all"]) == (hours["hours_moved"], hours["hours_moved_all"])

    # В Школе №5 учеников у A и B мало: учебник сравниваем по всем школам и честно об этом пишем.
    weakest = result["weakest_textbook"]
    assert weakest["all_schools"] and weakest["value_all"] is None
    assert weakest["text"].startswith("В Школе №5 учеников мало, поэтому вывод по всем школам")

    # Необычных классов в Школе №5 нет: четвёртая карточка — корень проблемы с баллом школы.
    root = result["root"]
    assert root["headline"] == "Дроби" and root["path"] == "/topics/3"
    fractions = next(item for item in topics if item["topic_id"] == 3)
    assert (root["value"], root["value_all"]) == (fractions["avg_score"], fractions["avg_score_all"])


def test_summary_shows_outlier_of_its_school(client):
    assert cards(client, "?school_id=4")["outlier"]["headline"] == "6Д, Школа №4"


def test_summary_unknown_school(client):
    response = client.get("/summary?school_id=999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Школа не найдена"


def book(name: str, score: float, enough: bool = True) -> dict:
    return {"name": name, "adjusted_score": score, "enough_data": enough}


def test_weakest_textbook_uses_school_when_data_is_enough():
    comparison = {
        "textbooks": [book("Учебник A", 70), book("Учебник B", 60)],
        "comparisons": [{"a": "Учебник A", "b": "Учебник B", "p_adjusted": 0.3, "significant": False, "effect": "малый"}],
    }
    result = weakest_textbook_card(comparison, {"textbooks": [], "comparisons": []}, "Школа №2")
    assert result["headline"] == "Учебник B" and not result["all_schools"]
    assert result["text"] == "В Школе №2 60,0 балла против 70,0 у учебника A: разница не подтверждается."


def test_hours_card_without_changes():
    result = hours_card({"hours_moved": 0, "items": [{"topic_id": 1, "topic": "Т", "delta": 0}], "total_hours": 84})
    assert result["value"] == 0
    assert result["text"].startswith("Менять часы не нужно")


def test_finding_card_without_outliers_and_roots():
    result = finding_card({"outliers": [], "conclusion": "Необычных результатов не найдено."}, {"roots": []}, [])
    assert (result["label"], result["text"], result["value"]) == ("Необычные результаты", "Необычных результатов не найдено.", None)
