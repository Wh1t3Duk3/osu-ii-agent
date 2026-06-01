import hashlib
import time

import aiosqlite

from app.logging_config import logger
from app.config import DB_PATH

_DB_PATH = f"{DB_PATH}/page_cache.db"
_TTL = 86400  # 24 часа


async def init_cache() -> None:
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS pages (
                url_hash  TEXT PRIMARY KEY,
                url       TEXT NOT NULL,
                content   TEXT NOT NULL,
                cached_at REAL NOT NULL
            )
        """)
        await db.commit()
    logger.info("🗄️ Кеш страниц инициализирован")


def _key(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()


async def get_cached(url: str) -> str | None:
    async with aiosqlite.connect(_DB_PATH) as db:
        async with db.execute(
            "SELECT content, cached_at FROM pages WHERE url_hash = ?", (_key(url),)
        ) as cursor:
            row = await cursor.fetchone()

    if row is None:
        return None

    content, cached_at = row
    age = time.time() - cached_at

    if age > _TTL:
        logger.debug(f"⏰ Кеш устарел ({age/3600:.1f}ч): {url}")
        return None

    logger.info(f"✅ Кеш попадание ({age/3600:.1f}ч): {url}")
    return content


async def set_cached(url: str, content: str) -> None:
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO pages VALUES (?, ?, ?, ?)",
            (_key(url), url, content, time.time()),
        )
        await db.commit()
    logger.debug(f"💾 Сохранено в кеш: {url}")
