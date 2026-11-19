FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY bot.py config.py creative_modes.py openai_client.py claude_client.py memory.py web_app.py ./
COPY static ./static

EXPOSE 8000
CMD ["uvicorn", "web_app:app", "--host", "0.0.0.0", "--port", "8000"]
