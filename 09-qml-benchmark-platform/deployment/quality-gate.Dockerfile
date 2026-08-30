FROM python:3.12.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/workspace/services/qml-core/src:/workspace/services/benchmark-api/src:/workspace/apps/dashboard:/workspace

WORKDIR /workspace
COPY requirements.lock ./
RUN pip install --no-cache-dir --requirement requirements.lock
COPY . .
CMD ["sh", "-c", "ruff check . && ruff format --check . && mypy && pytest"]
