from ddgs import DDGS
from langchain.tools import tool

from app.logging_config import logger

_MAIN_SITE = "www.osu.ru"
_FULL_SITE = "osu.ru"
_MIN_RESULTS = 2  # если меньше — расширяем поиск на весь домен


def _format(r: dict) -> str:
    return f"**{r['title']}**\n{r['body']}\nИсточник: {r['href']}\n"


def _search(query: str, site: str, max_results: int) -> list[str]:
    with DDGS() as ddgs:
        return [
            _format(r)
            for r in ddgs.text(f"{query} site:{site}", max_results=max_results)
        ]


@tool
async def search_on_site(query: str) -> str:
    """Ищет информацию только на официальном сайте Оренбургского государственного университета.

    Используй этот инструмент, когда нужно найти страницы по расписанию, пересдачам,
    правилам обучения, контактам кафедр и любой другой информации об ОГУ.
    """
    logger.info(f"🔧 Tool[search_on_site] query={query!r}")

    try:
        # Сначала ищем только на главном сайте (без филиалов)
        results = _search(query, _MAIN_SITE, max_results=5)
        logger.info(f"🔍 Найдено на {_MAIN_SITE}: {len(results)}")

        # Если результатов мало — расширяем на весь домен, помечаем филиалы
        if len(results) < _MIN_RESULTS:
            logger.info(f"🔍 Мало результатов, расширяю поиск на {_FULL_SITE}")
            extended = _search(query, _FULL_SITE, max_results=5)

            # Отделяем результаты филиалов от уже найденных
            affiliate_results = [
                r for r in extended
                if _MAIN_SITE not in r and r not in results
            ]

            if affiliate_results:
                affiliate_block = (
                    "\n\n⚠️ **Результаты с сайтов филиалов ОГУ** "
                    "(могут не относиться к главному университету):\n\n"
                    + "\n---\n".join(affiliate_results)
                )
                results = results + [affiliate_block]

        if not results:
            return f"По запросу '{query}' ничего не найдено на сайте osu.ru"

        return "\n---\n".join(results)

    except Exception as e:
        logger.error(f"❌ Ошибка поиска: {e}", exc_info=True)
        return f"Ошибка при поиске: {e}"
