from fastapi import FastAPI

app = FastAPI(title="MCP API", version="0.1.0")

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "MCP API", "version": "0.1.0"}

@app.get("/portfolio")
def get_portfolio():
    # TODO: 추후 DuckDB 연동 및 사용자 데이터 반영
    return {"portfolio": [], "note": "stub"}

@app.get("/recommend")
def get_recommendations():
    # TODO: 추천 알고리즘 연결
    return {"recommendations": [], "note": "stub"}
