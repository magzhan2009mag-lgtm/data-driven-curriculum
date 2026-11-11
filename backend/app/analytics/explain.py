"""LLM-пояснения рекомендаций. Правила описаны в скилле metrics."""

import json
import logging

import anthropic
from pydantic import BaseModel

logger = logging.getLogger(__name__)

MODEL = "claude-opus-5-5"
MAX_TOKENS = 16000
TIMEOUT_SECONDS = 60.0
MAX_RETRIES = 1
SOURCE_LLM = "llm"
SOURCE_TEMPLATE = "template"

SYSTEM_PROMPT = """Ты помогаешь методисту понять рекомендации по распределению учебных часов.
Для каждой темы напиши на русском языке одно-два простых предложения: почему рекомендовано именно такое изменение часов.
Методист не статистик, поэтому обходись без терминов вроде p-value и индекса.
Используй только числа из исходных данных и не добавляй новых фактов.
Часы перераспределяются между темами, поэтому не обещай рост баллов и не называй ожидаемый результат.
Баллы в by_textbook пересчитаны так, будто все учебники проходят в одинаковых школах.
Если в by_textbook видно, что по одному учебнику тема даётся заметно хуже, назови этот учебник
и сколько часов советуется его классам.
Верни пояснение для каждой темы с её topic_id."""

_cache: dict[str, dict[int, str]] = {}


class TopicExplanation(BaseModel):
    topic_id: int
    explanation: str


class Explanations(BaseModel):
    items: list[TopicExplanation]


def build_facts(items: list[dict]) -> list[dict]:
    """Оставляет только агрегаты по темам: данные учеников в запрос не попадают."""
    fields = ("topic_id", "topic", "level", "hours_current", "hours_recommended", "delta", "reason")
    textbook_fields = ("textbook", "level", "avg_score", "fail_rate", "delta")
    facts = []
    for item in items:
        fact = {field: item[field] for field in fields}
        if "by_textbook" in item:
            # Учебник без отдельного плана (мало данных в одной школе) в запрос не идёт: чисел у него нет.
            fact["by_textbook"] = [
                {field: row[field] for field in textbook_fields} for row in item["by_textbook"] if row["delta"] is not None
            ]
        facts.append(fact)
    return facts


def request_explanations(facts: list[dict]) -> dict[int, str] | None:
    """Возвращает пояснения по темам или None, если получить их не удалось."""
    try:
        client = anthropic.Anthropic(timeout=TIMEOUT_SECONDS, max_retries=MAX_RETRIES)
        response = client.beta.messages.parse(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": "low"},
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": json.dumps(facts, ensure_ascii=False)}],
            output_format=Explanations,
        )
    except anthropic.AuthenticationError:
        logger.warning("Claude API: нет действующего ключа, используем шаблонные пояснения")
        return None
    except anthropic.RateLimitError:
        logger.warning("Claude API: превышен лимит запросов, используем шаблонные пояснения")
        return None
    except anthropic.APIStatusError as error:
        logger.warning("Claude API: ошибка %s, используем шаблонные пояснения", error.status_code)
        return None
    except anthropic.APIConnectionError:
        logger.warning("Claude API: нет соединения, используем шаблонные пояснения")
        return None
    except (anthropic.AnthropicError, TypeError) as error:
        # SDK сообщает об отсутствии любых учётных данных через TypeError ещё до запроса.
        logger.warning("Claude API недоступен (%s), используем шаблонные пояснения", type(error).__name__)
        return None

    if response.stop_reason != "end_turn" or response.parsed_output is None:
        logger.warning("Claude API: ответ не завершён (%s), используем шаблонные пояснения", response.stop_reason)
        return None

    explanations = {item.topic_id: item.explanation.strip() for item in response.parsed_output.items}
    expected = {fact["topic_id"] for fact in facts}
    if set(explanations) != expected or not all(explanations.values()):
        logger.warning("Claude API: пояснения не совпали со списком тем, используем шаблонные пояснения")
        return None
    return explanations


def explain_recommendations(recommendations: dict) -> dict:
    """Добавляет к рекомендациям пояснения. Без ответа Claude показывает шаблонный текст."""
    items = recommendations["items"]
    facts = build_facts(items)
    key = json.dumps(facts, ensure_ascii=False, sort_keys=True)

    explanations = _cache.get(key)
    if explanations is None:
        explanations = request_explanations(facts)
        # Неудачи не кэшируем: после восстановления сети запрос должен пройти.
        if explanations is not None:
            _cache[key] = explanations

    if explanations is None:
        return {
            "total_hours": recommendations["total_hours"],
            "source": SOURCE_TEMPLATE,
            "items": [{**item, "explanation": item["reason"]} for item in items],
        }
    return {
        "total_hours": recommendations["total_hours"],
        "source": SOURCE_LLM,
        "items": [{**item, "explanation": explanations[item["topic_id"]]} for item in items],
    }
