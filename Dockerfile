FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt
COPY . .
RUN apt-get update && apt-get install -y curl && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && apt-get install -y nodejs && rm -rf /var/lib/apt/lists/*
RUN npm --prefix frontend ci && npm --prefix frontend run build && python manage.py collectstatic --noinput

EXPOSE 10000
CMD ["gunicorn", "chamapilot.wsgi:application", "--bind", "0.0.0.0:10000"]
