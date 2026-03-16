FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# El token del bot se pasa vía variable de entorno TELEGRAM_BOT_TOKEN
CMD ["python", "bot.py"]

