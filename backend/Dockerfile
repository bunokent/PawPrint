FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends libpq5 libpango-1.0-0 libpangoft2-1.0-0 && rm -rf /var/lib/apt/lists/*

# Copy uv binary directly from the official image (bypasses pip and timeouts)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml ./
RUN uv pip install --system --no-cache .[dev]

COPY . .
EXPOSE 8000
