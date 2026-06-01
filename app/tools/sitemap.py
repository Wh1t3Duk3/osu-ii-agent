from langchain.tools import tool

from app.logging_config import logger
from app.storage import LocalStorage
from app.config import SITEMAP_FILE

_storage = LocalStorage()


@tool
async def get_sitemap() -> str:
    """Возвращает полный sitemap сайта osu.ru в формате Markdown"""
    logger.info("🔧 Tool[get_sitemap]")
    return await _storage.get_file(file_path=SITEMAP_FILE)
