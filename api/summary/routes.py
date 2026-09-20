"""
Summary routes - plain English valuation summary for a company.
"""
from fastapi import APIRouter, Depends, HTTPException

from ..auth.utils import get_current_user
from ..company.data_fetcher import CompanyDataFetcher
from ..database.models import User
from ..valuation.football_field import calculate_football_field
from .generator import generate_summary

router = APIRouter(prefix="/api/summary", tags=["summary"])

_data_fetcher = CompanyDataFetcher()


@router.get("/{ticker}")
def get_summary(ticker: str, user: User = Depends(get_current_user)):
    """Generate a plain English summary of all valuation models."""
    try:
        ticker = ticker.upper()

        # Get football field data (runs all valuation models)
        ff_data = calculate_football_field(ticker, _data_fetcher)

        # Generate the narrative summary
        summary = generate_summary(ticker, _data_fetcher, ff_data)
        return summary

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
