from datetime import datetime

from app.agent import agent
from app.logging_config import logger

# История диалога: {session_id: [(role, text), ...]}
# Используется ботами — Gradio управляет историей самостоятельно
_histories: dict[str, list[tuple[str, str]]] = {}

MAX_HISTORY = 20  # максимум сообщений на сессию


def get_history(session_id: str) -> list[tuple[str, str]]:
    return _histories.get(session_id, [])


def clear_history(session_id: str) -> None:
    _histories.pop(session_id, None)


async def invoke_agent(
    text: str,
    history: list[tuple[str, str]],
) -> str:
    """
    Вызывает агента с текстом и историей.
    Возвращает текстовый ответ.
    """
    messages = list(history) + [("user", text)]

    start = datetime.now()
    try:
        result = await agent.ainvoke({"messages": messages})
        response: str = result["messages"][-1].content
    except Exception as e:
        logger.error(f"❌ Ошибка агента: {e}", exc_info=True)
        response = f"Произошла ошибка при обработке запроса: {e}"

    duration = (datetime.now() - start).total_seconds()
    logger.info(f"✅ Агент ответил за {duration:.2f}с")

    return response


async def chat_with_session(session_id: str, text: str) -> str:
    """
    Вызывает агента с автоматическим управлением историей по session_id.
    Используется Telegram-ботом.
    """
    history = get_history(session_id)
    response = await invoke_agent(text, history)

    # Обновляем историю
    history = history + [("user", text), ("assistant", response)]
    # Обрезаем если стала слишком длинной
    if len(history) > MAX_HISTORY:
        history = history[-MAX_HISTORY:]
    _histories[session_id] = history

    return response
