from dotenv import load_dotenv
import os

load_dotenv()

OPENROUTER_API_KEY: str = os.environ["OPENROUTER_API_KEY"]
OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

TELEGRAM_BOT_TOKEN: str = os.environ["TELEGRAM_BOT_API_KEY"]
TELEGRAM_WEBHOOK_URL: str = os.environ["TELEGRAM_WEBHOOK_URL"]
TELEGRAM_WEBHOOK_PATH: str = "/webhook/telegram"
TELEGRAM_WEBHOOK_PORT: int = 8080

LLM_MODEL: str = "qwen/qwen3.5-flash-02-23"
LLM_TEMPERATURE: float = 0.2
LLM_MAX_TOKENS: int = 4096

STORAGE_PATH: str = "./storage"
SITEMAP_FILE: str = "docs/sitemap.md"
DB_PATH: str = "./storage/db"

LOG_FILE: str = "osu_agent.log"
LOG_MAX_BYTES: int = 10 * 1024 * 1024  # 10 MB
LOG_BACKUP_COUNT: int = 3

GRADIO_HOST: str = "0.0.0.0"
GRADIO_PORT: int = 7860
GRADIO_ROOT_PATH: str = os.getenv("GRADIO_ROOT_PATH", "/agent")
