FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY manage.py ./
COPY config ./config
COPY vps_market ./vps_market

RUN pip install --no-cache-dir .

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
