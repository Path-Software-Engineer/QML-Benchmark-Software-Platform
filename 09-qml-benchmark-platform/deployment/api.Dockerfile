FROM python:3.12.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/workspace/services/qml-core/src:/workspace/services/benchmark-api/src

WORKDIR /workspace
COPY requirements.lock ./
RUN pip install --no-cache-dir --requirement requirements.lock
COPY services/qml-core services/qml-core
COPY services/benchmark-api services/benchmark-api
COPY data data

RUN useradd --create-home --uid 10001 app && chown -R app:app /workspace
USER app
EXPOSE 8080
CMD ["uvicorn", "benchmark_api.app:app", "--host", "0.0.0.0", "--port", "8080"]
