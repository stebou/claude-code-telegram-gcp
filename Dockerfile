# ============================================================================
# Stage 1: Builder - Install dependencies with Poetry
# ============================================================================
FROM python:3.11-bookworm AS builder

# Configure Poetry
ENV POETRY_VERSION=1.7.1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_VIRTUALENVS_CREATE=true \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Install Poetry
RUN pip install --no-cache-dir poetry==${POETRY_VERSION}

WORKDIR /app

# Copy dependency files first (leverage Docker cache)
COPY bot/pyproject.toml bot/poetry.lock ./

# Install dependencies only (no dev deps)
RUN --mount=type=cache,target=$POETRY_CACHE_DIR \
    poetry install --no-root --only main

# ============================================================================
# Stage 2: Runtime - Production image
# ============================================================================
FROM python:3.11-slim-bookworm AS runtime

# Install Node.js for Claude CLI
RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    curl \
    git \
    tmux \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser -m appuser

# Install Claude CLI globally
RUN npm install -g @anthropic-ai/claude-code@latest

WORKDIR /app

# Copy virtualenv from builder
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv

# Copy application code
COPY --chown=appuser:appuser bot/ ./bot/

# Create directories for persistent data
RUN mkdir -p \
    /app/data \
    /home/appuser/.claude \
    /home/appuser/.config \
    /approved-directory \
    && chown -R appuser:appuser \
        /app/data \
        /home/appuser/.claude \
        /home/appuser/.config \
        /approved-directory

# Switch to non-root user
USER appuser

# Add virtualenv to PATH
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    HOME=/home/appuser

# Health check for Telegram bot
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import requests; requests.get('https://api.telegram.org', timeout=5).raise_for_status()" || exit 1

# Run bot
CMD ["python", "-m", "bot.src.main"]
