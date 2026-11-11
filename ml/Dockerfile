# Backend AI chạy được ở mọi nơi nhận Docker (Railway, Fly, Hugging Face Spaces, Cloud Run...).
#   docker build -t ai-api . && docker run -p 8000:8000 -e SYSTEM=... -e ANTHROPIC_API_KEY=... ai-api
FROM python:3.12-slim
ENV PYTHONUTF8=1 PYTHONIOENCODING=utf-8 PYTHONDONTWRITEBYTECODE=1 PORT=8000
WORKDIR /app
COPY requirements-llm.txt .
RUN pip install --no-cache-dir -r requirements-llm.txt
COPY mlkit/__init__.py mlkit/result.py mlkit/
COPY serve/ serve/
COPY examples/ examples/
COPY mypkg/ mypkg/
COPY data/hanoi_rules_87_2025.json data/hanoi_rules_87_2025.json
EXPOSE 8000
CMD ["sh", "-c", "uvicorn serve.app_llm:app --host 0.0.0.0 --port ${PORT}"]
