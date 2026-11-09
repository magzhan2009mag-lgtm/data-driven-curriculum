from types import SimpleNamespace
from unittest.mock import MagicMock

import anthropic
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.analytics import explain
from app.main import app, get_db


def recommendations() -> dict:
    return {
        "total_hours": 14,
        "hours_moved": 2,
        "items": [
            {"topic_id": 1, "topic": "Дроби", "level": "hard", "hours_current": 5, "hours_recommended": 7,
             "delta": 2, "reason": "Шаблон 1"},
            {"topic_id": 2, "topic": "Числа", "level": "easy", "hours_current": 9, "hours_recommended": 7,
             "delta": -2, "reason": "Шаблон 2"},
        ],
    }


def model_answer(*pairs: tuple[int, str], stop_reason: str = "end_turn") -> SimpleNamespace:
    items = [explain.TopicExplanation(topic_id=topic_id, explanation=text) for topic_id, text in pairs]
    return SimpleNamespace(stop_reason=stop_reason, parsed_output=explain.Explanations(items=items))


@pytest.fixture(autouse=True)
def fake_claude(monkeypatch) -> MagicMock:
    """Тесты никогда не обращаются к настоящему API."""
    explain._cache.clear()
    client = MagicMock()
    client.beta.messages.parse.return_value = model_answer((1, " Текст 1 "), (2, "Текст 2"))
    monkeypatch.setattr(explain.anthropic, "Anthropic", MagicMock(return_value=client))
    return client.beta.messages.parse


def test_llm_text_is_used(fake_claude):
    result = explain.explain_recommendations(recommendations())
    assert result["source"] == explain.SOURCE_LLM
    assert [item["explanation"] for item in result["items"]] == ["Текст 1", "Текст 2"]
    assert result["items"][0]["delta"] == 2


def test_request_uses_expected_model_and_only_aggregates(fake_claude):
    explain.explain_recommendations(recommendations())
    arguments = fake_claude.call_args.kwargs
    assert arguments["model"] == "claude-opus-5-5"
    assert arguments["output_format"] is explain.Explanations
    assert "не обещай рост баллов" in arguments["system"]
    assert set(explain.build_facts(recommendations()["items"])[0]) == {
        "topic_id", "topic", "level", "hours_current", "hours_recommended", "delta", "reason",
    }


def test_answer_is_cached(fake_claude):
    explain.explain_recommendations(recommendations())
    explain.explain_recommendations(recommendations())
    assert fake_claude.call_count == 1


def status_error(error_type: type, status: int) -> Exception:
    return error_type("ошибка", response=MagicMock(status_code=status, headers={}), body=None)


@pytest.mark.parametrize(
    "error",
    [
        status_error(anthropic.AuthenticationError, 401),
        status_error(anthropic.RateLimitError, 429),
        status_error(anthropic.InternalServerError, 500),
        anthropic.APIConnectionError(request=MagicMock()),
        TypeError("Could not resolve authentication method"),
    ],
)
def test_api_failure_falls_back_to_template(fake_claude, error):
    fake_claude.side_effect = error
    result = explain.explain_recommendations(recommendations())
    assert result["source"] == explain.SOURCE_TEMPLATE
    assert [item["explanation"] for item in result["items"]] == ["Шаблон 1", "Шаблон 2"]


def test_failure_is_not_cached(fake_claude):
    fake_claude.side_effect = anthropic.APIConnectionError(request=MagicMock())
    explain.explain_recommendations(recommendations())
    fake_claude.side_effect = None
    assert explain.explain_recommendations(recommendations())["source"] == explain.SOURCE_LLM


@pytest.mark.parametrize(
    "answer",
    [
        model_answer((1, "Текст 1")),
        model_answer((1, "Текст 1"), (2, "Текст 2"), (3, "Лишняя тема")),
        model_answer((1, "Текст 1"), (2, "   ")),
        model_answer((1, "Текст 1"), (2, "Текст 2"), stop_reason="refusal"),
        SimpleNamespace(stop_reason="end_turn", parsed_output=None),
    ],
)
def test_unusable_answer_falls_back_to_template(fake_claude, answer):
    fake_claude.return_value = answer
    assert explain.explain_recommendations(recommendations())["source"] == explain.SOURCE_TEMPLATE


def test_endpoint_answers(seeded_engine, fake_claude):
    fake_claude.side_effect = anthropic.APIConnectionError(request=MagicMock())

    def override_get_db():
        with Session(seeded_engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        body = TestClient(app).get("/recommendations/explanation").json()
    finally:
        app.dependency_overrides.clear()
    assert body["source"] == explain.SOURCE_TEMPLATE
    assert body["total_hours"] == 84
    assert all(item["explanation"] == item["reason"] for item in body["items"])
