# Архитектура ИИ-справочника ОГУ

## Обзор

ИИ-агент на базе LLM, который отвечает на вопросы об Оренбургском государственном университете,
извлекая актуальную информацию с официального сайта [osu.ru](https://osu.ru).

Агент доступен через два интерфейса одновременно:
- **Telegram-бот** (webhook, aiogram 3.x)
- **Web-интерфейс** (Gradio)

---

## Структура проекта

```
osu-agent/
├── app/
│   ├── main.py            # Точка входа. Запускает Gradio и Telegram параллельно.
│   ├── config.py          # Все настройки из переменных окружения (.env)
│   ├── logging_config.py  # Настройка логгера (RotatingFileHandler)
│   ├── core.py            # Общая логика вызова агента и управление историей диалога
│   ├── agent.py           # LLM, system prompt, создание LangChain агента
│   ├── storage.py         # LocalStorage — чтение файлов с автоопределением кодировки
│   ├── cache.py           # SQLite-кеш скрапнутых страниц (aiosqlite, TTL 24ч)
│   ├── ui.py              # Gradio ChatInterface
│   ├── tools/
│   │   ├── __init__.py    # Экспортирует all_tools
│   │   ├── sitemap.py     # Tool: get_sitemap — читает sitemap из файла
│   │   ├── search.py      # Tool: search_on_site — поиск через DuckDuckGo site:osu.ru
│   │   └── scraper.py     # Tool: scrape_page — скрапинг HTML/PDF/DOCX с кешем
│   └── bots/
│       └── telegram.py    # Telegram-бот (aiogram webhook + aiohttp)
│
├── storage/
│   ├── docs/
│   │   └── sitemap.md     # Предзагруженный sitemap osu.ru (обновляется вручную)
│   └── db/
│       └── page_cache.db  # SQLite база кеша (не в git)
│
├── docs/
│   └── architecture.md    # Этот файл
│
├── Dockerfile
├── docker-compose.yaml
├── nginx.conf.example     # Пример конфига nginx для поддомена
├── pyproject.toml
├── uv.lock
├── .env                   # Секреты (не в git)
└── .env.example           # Шаблон переменных окружения
```

---

## Архитектурная схема

```
Пользователь (Telegram)
        │
        ▼
  Telegram API
        │  HTTPS POST
        ▼
   nginx (443 ssl)
   osu.awesome-corp.ru
        │
        ├─ /webhook/telegram ──► aiohttp сервер :8080
        │                              │
        │                         aiogram dp
        │                              │
        └─ /          ──────────► Gradio UI :7860
                                       │
                              (оба вызывают)
                                       │
                                       ▼
                                   core.py
                              invoke_agent()
                                       │
                                       ▼
                              LangChain Agent
                           (qwen via OpenRouter)
                                       │
                          ┌────────────┼────────────┐
                          ▼            ▼             ▼
                     get_sitemap  search_on_site  scrape_page
                          │            │              │
                     storage/      DuckDuckGo     httpx + trafilatura
                     docs/         site:osu.ru    (или Playwright)
                     sitemap.md                   (или PDF/DOCX парсер)
                                                       │
                                                  SQLite cache
                                                  storage/db/
                                                  page_cache.db
```

---

## Модули

### `app/main.py`
Точка входа. Инициализирует SQLite-кеш и запускает два сервиса параллельно через `asyncio.gather`:
- Telegram webhook-сервер
- Gradio UI (в отдельном потоке через `asyncio.to_thread`)

### `app/config.py`
Все константы приложения. Загружает переменные из `.env` через `python-dotenv`.

| Переменная | Описание |
|---|---|
| `OPENROUTER_API_KEY` | Ключ API OpenRouter |
| `TELEGRAM_BOT_API_KEY` | Токен Telegram-бота |
| `TELEGRAM_WEBHOOK_URL` | Публичный HTTPS-домен (без слеша) |
| `TELEGRAM_WEBHOOK_PATH` | Путь webhook: `/webhook/telegram` |
| `TELEGRAM_WEBHOOK_PORT` | Порт aiohttp сервера: `8080` |
| `GRADIO_HOST` | Хост Gradio: `0.0.0.0` |
| `GRADIO_PORT` | Порт Gradio: `7860` |
| `GRADIO_ROOT_PATH` | Префикс пути (пусто при поддомене) |
| `LLM_MODEL` | Модель LLM: `qwen/qwen3.5-flash-02-23` |

### `app/core.py`
Единая точка вызова агента для всех интерфейсов.

- `invoke_agent(text, history)` — вызывает LangChain агента, возвращает строку ответа
- `chat_with_session(session_id, text)` — обёртка с автоматическим управлением историей диалога по `session_id`. Хранит историю в памяти (dict), ограничивает до 20 сообщений.

### `app/agent.py`
Инициализация LLM и агента:
- **LLM**: `qwen/qwen3.5-flash-02-23` через OpenRouter API (совместим с OpenAI SDK)
- **Фреймворк**: LangChain `create_agent` + LangGraph под капотом
- **System prompt**: правила поведения агента — актуальность данных (2025-2026), форматирование для мессенджеров, запрет на выдумывание информации, лимит 5 вызовов инструментов

### `app/tools/`

#### `get_sitemap`
Читает предзагруженный `storage/docs/sitemap.md` через `LocalStorage`.
Используется агентом для навигации по структуре сайта без лишних запросов.

#### `search_on_site`
Поиск по сайту osu.ru через DuckDuckGo (`ddgs`).
Формирует запрос вида `{query} site:osu.ru`, возвращает до 5 результатов.

#### `scrape_page`
Основной инструмент извлечения содержимого страниц. Поддерживает три типа документов:

| Тип | Определение | Обработка |
|---|---|---|
| HTML | по умолчанию | `httpx` + `trafilatura` → Playwright (fallback) |
| PDF | `.pdf` в URL или `Content-Type: application/pdf` | `httpx` (binary) + `PyMuPDF (fitz)` |
| DOCX | `.docx`/`.doc` в URL или `Content-Type` | `httpx` (binary) + `python-docx` |

Все результаты кешируются в SQLite (TTL 24 часа). Повторный запрос того же URL возвращается мгновенно.

### `app/cache.py`
SQLite-кеш на `aiosqlite`.

| Функция | Описание |
|---|---|
| `init_cache()` | Создаёт таблицу `pages` если не существует |
| `get_cached(url)` | Возвращает кешированный контент или `None` если устарел |
| `set_cached(url, content)` | Сохраняет контент, ключ — SHA256 от URL |

TTL: 24 часа (`86400` сек). Путь к БД: `storage/db/page_cache.db`.

### `app/storage.py`
Асинхронное чтение локальных файлов с автоопределением кодировки (`chardet`).
Поддерживает fallback кодировки: UTF-8 → CP1251 → KOI8-R → ISO-8859-5.

### `app/logging_config.py`
Настраивает единый logger `OSU_Agent`:
- **Консоль**: уровень DEBUG
- **Файл** `osu_agent.log`: `RotatingFileHandler`, макс. 10 МБ × 3 файла

### `app/ui.py`
Gradio `ChatInterface`. Парсит историю диалога из формата Gradio в `list[tuple[str, str]]`
и передаёт в `core.invoke_agent()`.

### `app/bots/telegram.py`
Telegram-бот на aiogram 3.x в режиме webhook.

**Команды бота:**
- `/start` — приветствие + сброс истории
- `/clear` — очистить историю диалога

**Особенности:**
- Сообщения длиннее 4000 символов автоматически разбиваются на части
- Отправка с `ParseMode.MARKDOWN`; при ошибке парсинга (`TelegramBadRequest`) — fallback на plain text
- Webhook-сервер: `aiohttp` + `SimpleRequestHandler` от aiogram

---

## Деплой

### Локально (разработка)
```bash
# Поднять ngrok тоннель
ngrok http 8080

# Указать в .env
TELEGRAM_WEBHOOK_URL=https://xxxx.ngrok-free.app

# Запустить
python -m app.main
```

### VPS (продакшен)

**Стек:** Docker + nginx (локально на VPS) + Let's Encrypt (wildcard SSL)

```
Интернет
    │ HTTPS
    ▼
nginx (osu.awesome-corp.ru)
    ├── /webhook/telegram → Docker :8080
    └── /                → Docker :7860
```

```bash
# На VPS
cp .env.example .env && nano .env
docker compose up -d --build
```

nginx конфиг: см. `nginx.conf.example`

---

## Зависимости

| Пакет | Версия | Назначение |
|---|---|---|
| `langchain` + `langgraph` | 1.3+ | Агентный фреймворк |
| `langchain-openai` | 1.2+ | Провайдер OpenRouter/OpenAI |
| `aiogram` | 3.x | Telegram Bot API |
| `aiohttp` | — | HTTP-сервер для webhook |
| `gradio` | 6.x | Web UI |
| `httpx` | 0.28+ | Async HTTP клиент |
| `trafilatura` | — | Извлечение текста из HTML |
| `playwright` | 1.60+ | Headless браузер (fallback для JS-страниц) |
| `pymupdf` (fitz) | — | Парсинг PDF |
| `python-docx` | — | Парсинг DOCX |
| `aiosqlite` | — | Async SQLite (кеш страниц) |
| `ddgs` | 9.x | DuckDuckGo Search |
| `aiofiles` | 25.x | Async чтение файлов |
| `chardet` | 7.x | Автоопределение кодировки |
| `python-dotenv` | — | Загрузка `.env` |
