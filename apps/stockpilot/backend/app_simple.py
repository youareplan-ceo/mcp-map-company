from fastapi import FastAPI
import uvicorn
from datetime import datetime

app = FastAPI(title="StockPilot AI")

@app.get("/")
def root():
    return {"message": "StockPilot AI is running!", "time": datetime.now()}

@app.get("/api/v1/health")
def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    print("🚀 서버 시작: http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
