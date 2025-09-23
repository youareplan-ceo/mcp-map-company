import os
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel

# Data models
class Cash(BaseModel):
    krw: float = 0.0
    usd: float = 0.0

class Holding(BaseModel):
    symbol: str
    shares: float
    avg_cost: float
    current_price: Optional[float] = None

class Portfolio(BaseModel):
    userId: str
    holdings: List[Holding] = []
    cash: Cash = Cash()

class PortfolioUpdate(BaseModel):
    userId: str
    holdings: Optional[List[Holding]] = None
    cash: Optional[Cash] = None

# Configuration
DATA_FILE = Path(__file__).parent.parent / "data" / "portfolio.json"
API_KEY_HEADER = "x-stockpilot-key"

router = APIRouter(prefix="/api/v1")

# File operations
def read_portfolio_db() -> Dict[str, Any]:
    """Read portfolio database from JSON file"""
    try:
        if not DATA_FILE.exists():
            return {}

        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            return json.loads(content) if content.strip() else {}
    except Exception:
        return {}

def write_portfolio_db(data: Dict[str, Any]) -> None:
    """Write portfolio database to JSON file"""
    # Ensure data directory exists
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        f.write(json.dumps(data, indent=2, ensure_ascii=False))

# Authentication
async def verify_api_key(x_stockpilot_key: Optional[str] = Header(None)):
    """Verify API key from header"""
    required_key = os.getenv("STOCKPILOT_API_KEY")

    # If no API key is set in environment, allow all requests (development mode)
    if not required_key:
        return True

    # If API key is set, it must match the header
    if x_stockpilot_key != required_key:
        raise HTTPException(status_code=401, detail="Unauthorized")

    return True

# API Endpoints
@router.get("/portfolio", response_model=Portfolio)
async def get_portfolio(
    userId: str,
    authenticated: bool = Depends(verify_api_key)
):
    """Get user portfolio"""
    if not userId.strip():
        raise HTTPException(status_code=400, detail="Missing userId")

    db = read_portfolio_db()
    user_data = db.get(userId, {})

    # Return default portfolio if user not found
    if not user_data:
        return Portfolio(
            userId=userId,
            holdings=[],
            cash=Cash(krw=0, usd=0)
        )

    return Portfolio(**user_data)

@router.put("/portfolio")
async def update_portfolio(
    portfolio_update: PortfolioUpdate,
    authenticated: bool = Depends(verify_api_key)
):
    """Update user portfolio"""
    if not portfolio_update.userId.strip():
        raise HTTPException(status_code=400, detail="Missing userId")

    db = read_portfolio_db()

    # Get existing user data or create new
    user_data = db.get(portfolio_update.userId, {
        "userId": portfolio_update.userId,
        "holdings": [],
        "cash": {"krw": 0, "usd": 0}
    })

    # Update holdings if provided
    if portfolio_update.holdings is not None:
        user_data["holdings"] = [holding.dict() for holding in portfolio_update.holdings]

    # Update cash if provided
    if portfolio_update.cash is not None:
        user_data["cash"] = portfolio_update.cash.dict()

    # Save updated data
    db[portfolio_update.userId] = user_data
    write_portfolio_db(db)

    return {"ok": True}

# Health check for portfolio service
@router.get("/portfolio/health")
async def portfolio_health():
    """Portfolio service health check"""
    return {
        "status": "ok",
        "service": "portfolio",
        "data_file": str(DATA_FILE),
        "file_exists": DATA_FILE.exists()
    }