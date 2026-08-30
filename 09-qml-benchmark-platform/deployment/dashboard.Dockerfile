FROM python:3.12.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/workspace/apps/dashboard

WORKDIR /workspace
COPY requirements.lock ./
RUN pip install --no-cache-dir --requirement requirements.lock
COPY apps/dashboard apps/dashboard

RUN useradd --create-home --uid 10001 app && chown -R app:app /workspace
USER app
EXPOSE 8050
CMD ["python", "-m", "qml_dashboard.app"]
