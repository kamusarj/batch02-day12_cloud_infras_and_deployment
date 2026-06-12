# ============================================================
# Production Dockerfile — Single-stage, Railway optimized
# ============================================================
FROM python:3.11-slim

WORKDIR /app

RUN groupadd -r agent && useradd -r -g agent -d /app agent

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY deploy.py .

RUN chown -R agent:agent /app

USER agent

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["python", "deploy.py"]
