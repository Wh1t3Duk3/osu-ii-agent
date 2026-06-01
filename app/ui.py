import gradio as gr

from app.core import invoke_agent
from app.logging_config import logger
from app.config import GRADIO_HOST, GRADIO_PORT, GRADIO_ROOT_PATH


def _parse_history(history) -> list[tuple[str, str]]:
    messages = []
    if not history:
        return messages

    for item in history:
        if isinstance(item, (list, tuple)) and len(item) == 2:
            user_msg, assistant_msg = item
            if user_msg:
                messages.append(("user", str(user_msg)))
            if assistant_msg:
                messages.append(("assistant", str(assistant_msg)))
        elif isinstance(item, dict) and "role" in item and "content" in item:
            role = item["role"]
            if role in ("user", "assistant"):
                messages.append((role, item["content"]))

    return messages


async def chat(message: str, history) -> str:
    logger.info(f"💬 Gradio | пользователь: {message[:200]}")
    history_tuples = _parse_history(history)
    response = await invoke_agent(message, history_tuples)
    logger.info(f"🤖 Gradio | агент: {response[:200]}")
    return response


def build_ui() -> gr.ChatInterface:
    return gr.ChatInterface(
        fn=chat,
        title="ИИ-Справочник ОГУ",
        description="Задавайте вопросы по университету. Агент ищет информацию в реальном времени.",
        examples=[
            "Какие есть факультеты в ОГУ?",
            "Как найти расписание занятий?",
            "Когда начинается приёмная кампания?",
            "Где находится главный корпус?",
        ],
    )
