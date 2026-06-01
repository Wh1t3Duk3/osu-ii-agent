import asyncio

from app.cache import init_cache
from app.logging_config import logger


async def main() -> None:
    await init_cache()

    from app.bots.telegram import start as tg_start
    from app.ui import build_ui
    from app.config import GRADIO_HOST, GRADIO_PORT, GRADIO_ROOT_PATH

    ui = build_ui()

    logger.info("🚀 Запуск ИИ-справочника ОГУ")

    await asyncio.gather(
        tg_start(),
        asyncio.to_thread(
            ui.launch,
            server_name=GRADIO_HOST,
            server_port=GRADIO_PORT,
            root_path=GRADIO_ROOT_PATH,
            share=False,
            prevent_thread_lock=True,
        ),
    )


if __name__ == "__main__":
    asyncio.run(main())
