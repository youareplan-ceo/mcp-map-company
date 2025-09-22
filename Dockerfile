# FastAPI/uvicorn 컨테이너 (러닝용)
FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt . || true
RUN pip install --no-cache-dir -r requirements.txt || true
COPY . .
EXPOSE 8099
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8099"]
