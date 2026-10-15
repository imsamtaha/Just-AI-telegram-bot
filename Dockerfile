FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY bot.py config.py openai_client.py web_app.py ./
COPY static ./static
RUN addgroup --system app && adduser --system --ingroup app app

EXPOSE 8000
USER app
CMD ["uvicorn", "web_app:app", "--host", "0.0.0.0", "--port", "8000"]
