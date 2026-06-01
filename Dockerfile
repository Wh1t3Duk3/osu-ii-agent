FROM python:3.10-slim

# Системные зависимости для playwright, pymupdf, trafilatura
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxcb1 \
    libxkbcommon0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Копируем зависимости и устанавливаем
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Устанавливаем браузер для Playwright
RUN uv run playwright install chromium

# Копируем исходный код
COPY app/ ./app/
COPY storage/ ./storage/

EXPOSE 7860 8080

CMD ["uv", "run", "python", "-m", "app.main"]
