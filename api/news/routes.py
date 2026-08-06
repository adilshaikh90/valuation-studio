"""
News routes — recent news for a given ticker via yfinance.
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any

from ..auth.utils import get_current_user
from ..company.data_fetcher import CompanyDataFetcher
from ..database.models import User

router = APIRouter(prefix="/api/news", tags=["news"])

_data_fetcher = CompanyDataFetcher()


@router.get("/{ticker}")
def get_news(ticker: str, user: User = Depends(get_current_user)) -> List[Dict[str, Any]]:
    try:
        news_items = _data_fetcher.get_news(ticker.upper())

        if not news_items or (len(news_items) == 1 and "error" in news_items[0]):
            return []

        # Normalize yfinance news format into a consistent structure
        normalized = []
        for item in news_items:
            if isinstance(item, dict):
                normalized.append({
                    "title": item.get("title", item.get("headline", "")),
                    "publisher": item.get("publisher", item.get("source", "Unknown")),
                    "link": item.get("link", item.get("url", "#")),
                    "published_date": item.get("providerPublishTime", item.get("published_date", "")),
                    "thumbnail_url": (
                        item.get("thumbnail", {}).get("resolutions", [{}])[0].get("url", "")
                        if isinstance(item.get("thumbnail"), dict)
                        else item.get("thumbnail_url", "")
                    ),
                    "type": item.get("type", "Article"),
                })

        # Sort by recency (newest first)
        normalized.sort(key=lambda x: str(x.get("published_date", "")), reverse=True)
        return normalized

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
