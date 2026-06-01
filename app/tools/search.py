from ddgs import DDGS
from langchain.tools import tool

from app.logging_config import logger


@tool
async def search_on_site(query: str) -> str:
    """Ищет информацию только на официальном сайте Оренбургского государственного университета.

    Используй этот инструмент, когда нужно найти страницы по расписанию, пересдачам,
    правилам обучения, контактам кафедр и любой другой информации об ОГУ.
    """
    logger.info(f"🔧 Tool[search_on_site] query={query!r}")

    full_query = f"{query} site:osu.ru"

    try:
        with DDGS() as ddgs:
            results = [
                f"**{r['title']}**\n{r['body']}\nИсточник: {r['href']}\n"
                for r in ddgs.text(full_query, max_results=5)
            ]

        if not results:
            return f"По запросу '{query}' ничего не найдено на сайте osu.ru"

        return "\n---\n".join(results)

    except Exception as e:
        logger.error(f"❌ Ошибка поиска: {e}", exc_info=True)
        return f"Ошибка при поиске: {e}"
