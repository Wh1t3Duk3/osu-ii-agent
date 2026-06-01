import asyncio

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.enums import ParseMode, ChatAction
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from app.config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_WEBHOOK_URL,
    TELEGRAM_WEBHOOK_PATH,
    TELEGRAM_WEBHOOK_PORT,
)
from app.core import chat_with_session, clear_history
from app.logging_config import logger

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()


def _session_id(message: Message) -> str:
    return f"tg_{message.from_user.id}"


@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    clear_history(_session_id(message))
    await message.answer(
        "👋 Здравствуйте! Я — ИИ-справочник Оренбургского государственного университета.\n\n"
        "Задавайте вопросы об университете: расписание, приёмная кампания, "
        "контакты кафедр и многое другое.\n\n"
        "Команды:\n"
        "/start — начать новый диалог\n"
        "/clear — очистить историю диалога"
    )


@dp.message(Command("clear"))
async def cmd_clear(message: Message) -> None:
    clear_history(_session_id(message))
    await message.answer("🗑️ История диалога очищена.")


@dp.message(F.text)
async def handle_message(message: Message) -> None:
    session_id = _session_id(message)
    user_text = message.text

    logger.info(f"💬 Telegram | user_id={message.from_user.id}: {user_text[:200]}")

    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)

    response = await chat_with_session(session_id, user_text)

    logger.info(f"🤖 Telegram | user_id={message.from_user.id}: {response[:200]}")

    for chunk in _split_message(response):
        await message.answer(chunk, parse_mode=ParseMode.MARKDOWN)


def _split_message(text: str, limit: int = 4000) -> list[str]:
    if len(text) <= limit:
        return [text]

    chunks = []
    while text:
        if len(text) <= limit:
            chunks.append(text)
            break
        split_at = text.rfind("\n", 0, limit)
        if split_at == -1:
            split_at = limit
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")

    return chunks


async def start() -> None:
    # webhook_url = f"{TELEGRAM_WEBHOOK_URL}{TELEGRAM_WEBHOOK_PATH}"
    #
    # await bot.set_webhook(
    #     url=webhook_url,
    #     drop_pending_updates=True,
    # )
    # logger.info(f"🔗 Telegram webhook зарегистрирован: {webhook_url}")

    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=TELEGRAM_WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=TELEGRAM_WEBHOOK_PORT)
    await site.start()

    logger.info(f"🚀 Telegram webhook сервер слушает порт {TELEGRAM_WEBHOOK_PORT}")

    # Держим сервер живым — управление передаётся asyncio.gather в main.py
    await asyncio.Event().wait()
