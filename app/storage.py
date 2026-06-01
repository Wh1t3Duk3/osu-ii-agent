from pathlib import Path
from typing import Optional, Union

import aiofiles
import chardet

from app.logging_config import logger
from app.config import STORAGE_PATH


class LocalStorage:
    """Асинхронный класс для работы с локальным хранилищем файлов"""

    def __init__(self, base_path: str = STORAGE_PATH):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 Инициализировано хранилище: {self.base_path.absolute()}")

    async def detect_encoding(self, content: bytes) -> str:
        if not content:
            return "utf-8"

        result = chardet.detect(content)
        encoding = result.get("encoding", "utf-8")
        confidence = result.get("confidence", 0)

        logger.debug(f"🔍 Определена кодировка: {encoding} (уверенность: {confidence:.2%})")

        if encoding and "utf" not in encoding.lower():
            try:
                content.decode("utf-8")
                return "utf-8"
            except Exception:
                pass

        return encoding or "utf-8"

    async def get_file(
        self,
        file_path: str,
        encoding: str = None,
        auto_detect: bool = True,
    ) -> Optional[Union[str, bytes]]:
        full_path = self.base_path / file_path

        if not full_path.exists():
            logger.warning(f"⚠️ Файл не найден: {full_path}")
            return None

        if not full_path.is_file():
            logger.warning(f"⚠️ Путь не является файлом: {full_path}")
            return None

        try:
            async with aiofiles.open(full_path, "rb") as f:
                content = await f.read()

            if encoding is None and not auto_detect:
                logger.info(f"✅ Прочитан бинарный файл: {file_path} ({len(content)} байт)")
                return content

            if encoding is None and auto_detect:
                encoding = await self.detect_encoding(content)

            if encoding:
                try:
                    decoded = content.decode(encoding)
                    logger.info(f"✅ Прочитан файл: {file_path} ({encoding}, {len(decoded)} символов)")
                    return decoded
                except UnicodeDecodeError:
                    logger.error(f"❌ Ошибка декодирования: {file_path} ({encoding})")
                    for fallback in ["utf-8", "cp1251", "koi8-r", "iso-8859-5"]:
                        if fallback == encoding:
                            continue
                        try:
                            return content.decode(fallback)
                        except Exception:
                            continue
                    logger.warning("⚠️ Не удалось декодировать файл, возвращаем байты")
                    return content

            return content

        except Exception as e:
            logger.error(f"❌ Ошибка при чтении файла {file_path}: {e}", exc_info=True)
            return None
