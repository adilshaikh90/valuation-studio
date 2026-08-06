"""
Company API routes.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
from ..database.db import get_db
from ..database.models import User, SearchLog
from ..auth.utils import get_current_user
from .data_fetcher import CompanyDataFetcher

router = APIRouter(prefix="/api/company", tags=["company"])
fetcher = CompanyDataFetcher()

def log_search(ticker: str, info: dict, user_id: int, db: Session) -> None:
    """Helper to log user searches to the database."""
    try:
        log = SearchLog(
            user_id=user_id,
            ticker=ticker,
            company=info.get('name', ''),
            country=info.get('country', ''),
            currency=info.get('currency', '')
        )
        db.add(log)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Failed to log search: {e}")

@router.get("/search")
def search_company(q: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Searches for a company and logs the activity."""
    ticker = q.upper().strip()
    info = fetcher.get_company_info(ticker)
    
    if "error" in info:
        raise HTTPException(status_code=404, detail=info["error"])
        
    log_search(ticker, info, current_user.id, db)
    return {"message": "Company found", "ticker": ticker, "name": info.get("name")}

@router.get("/{ticker}")
def get_company(ticker: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Gets full company information."""
    info = fetcher.get_company_info(ticker)
    if "error" in info:
        raise HTTPException(status_code=404, detail=info["error"])
    return info

@router.get("/{ticker}/financials")
def get_company_financials(ticker: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Gets the 3 financial statements for a company."""
    financials = fetcher.get_financials(ticker)
    if "error" in financials:
        raise HTTPException(status_code=404, detail=financials["error"])
    return financials
