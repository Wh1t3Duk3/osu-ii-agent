import io
from urllib.parse import urlparse

import fitz  # pymupdf
import httpx
import trafilatura
from docx import Document
from langchain.tools import tool
from playwright.async_api import async_playwright

from app.cache import get_cached, set_cached
from app.logging_config import logger

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

_PDF_EXTENSIONS = {".pdf"}
_DOCX_EXTENSIONS = {".docx", ".doc"}


def _detect_type(url: str, content_type: str) -> str:
    """Определяет тип документа по Content-Type и расширению URL."""
    ct = content_type.lower()
    if "pdf" in ct:
        return "pdf"
    if "word" in ct or "officedocument" in ct:
        return "docx"

    ext = urlparse(url).path.lower()
    if any(ext.endswith(e) for e in _PDF_EXTENSIONS):
        return "pdf"
    if any(ext.endswith(e) for e in _DOCX_EXTENSIONS):
        return "docx"

    return "html"


def _extract_pdf(data: bytes) -> str:
    doc = fitz.open(stream=data, filetype="pdf")
    pages = []
    for i, page in enumerate(doc, start=1):
        text = page.get_text().strip()
        if text:
            pages.append(f"**Страница {i}**\n{text}")
    doc.close()
    return "\n\n".join(pages) if pages else ""


def _extract_docx(data: bytes) -> str:
    doc = Document(io.BytesIO(data))
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


async def _fetch_binary(url: str) -> tuple[bytes, str]:
    """Скачивает файл и возвращает (bytes, content_type)."""
    async with httpx.AsyncClient(timeout=30.0, headers=_HEADERS, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.content, response.headers.get("content-type", "")


async def _fetch_html(url: str) -> str | None:
    """Быстрый fetch через httpx + trafilatura для HTML-страниц."""
    try:
        async with httpx.AsyncClient(timeout=20.0, headers=_HEADERS, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            html = response.text

        return trafilatura.extract(
            html,
            output_format="markdown",
            include_links=True,
            include_tables=True,
            url=url,
        )
    except Exception as e:
        logger.warning(f"⚠️ httpx/trafilatura не справился с {url}: {e}")
        return None


async def _fetch_with_playwright(url: str) -> str | None:
    """Fallback через headless браузер для JS-heavy страниц."""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=30000, wait_until="networkidle")
            html = await page.content()
            await browser.close()

        return trafilatura.extract(
            html,
            output_format="markdown",
            include_links=True,
            include_tables=True,
            url=url,
        )
    except Exception as e:
        logger.warning(f"⚠️ Playwright не справился с {url}: {e}")
        return None


async def fetch_page(url: str) -> str:
    cached = await get_cached(url)
    if cached:
        return cached

    logger.info(f"🌐 Скрапинг: {url}")

    # Определяем тип по расширению URL до запроса (быстрый путь)
    ext = urlparse(url).path.lower()
    pre_detected = None
    if any(ext.endswith(e) for e in _PDF_EXTENSIONS):
        pre_detected = "pdf"
    elif any(ext.endswith(e) for e in _DOCX_EXTENSIONS):
        pre_detected = "docx"

    content: str | None = None

    if pre_detected in ("pdf", "docx"):
        try:
            data, content_type = await _fetch_binary(url)
            doc_type = pre_detected or _detect_type(url, content_type)

            if doc_type == "pdf":
                logger.info(f"📄 Извлекаю текст из PDF: {url}")
                content = _extract_pdf(data)
            elif doc_type == "docx":
                logger.info(f"📝 Извлекаю текст из DOCX: {url}")
                content = _extract_docx(data)
        except Exception as e:
            logger.warning(f"⚠️ Ошибка при извлечении документа {url}: {e}")
    else:
        # HTML-путь: сначала быстрый, потом Playwright
        content = await _fetch_html(url)

        if not content:
            # Проверяем — может сервер отдал PDF несмотря на URL
            try:
                data, content_type = await _fetch_binary(url)
                doc_type = _detect_type(url, content_type)
                if doc_type == "pdf":
                    logger.info(f"📄 Content-Type=pdf, извлекаю: {url}")
                    content = _extract_pdf(data)
                elif doc_type == "docx":
                    content = _extract_docx(data)
            except Exception:
                pass

        if not content:
            logger.info(f"🎭 Переключаюсь на Playwright: {url}")
            content = await _fetch_with_playwright(url)

    if not content:
        return "Не удалось извлечь содержимое страницы."

    await set_cached(url, content)
    return content


@tool
async def scrape_page(url: str) -> str:
    """Открывает страницу или документ (HTML, PDF, DOCX) с сайта osu.ru и извлекает текст.

    Аргументы:
    - url: полный адрес страницы или файла (например https://www.osu.ru/doc/12345
      или https://elib.osu.ru/bitstream/.../document.pdf)

    Используй этот инструмент после search_on_site, когда нашёл нужную ссылку и хочешь
    получить полный чистый текст страницы или документа.
    """
    logger.info(f"🔧 Tool[scrape_page] url={url!r}")
    return await fetch_page(url)
