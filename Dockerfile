FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY week1 week1
COPY week2 week2
COPY week3 week3
COPY week4 week4
COPY alembic.ini .

EXPOSE 8000
CMD ["uvicorn", "week4.main:app", "--host", "0.0.0.0", "--port", "8000"]
