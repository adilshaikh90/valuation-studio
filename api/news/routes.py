"""
News routes — recent news for a given ticker via yfinance.
Handles the new yfinance news structure (nested under 'content').
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from datetime import datetime

from ..auth.utils import get_current_user
from ..company.data_fetcher import CompanyDataFetcher
from ..database.models import User

router = APIRouter(prefix="/api/news", tags=["news"])
_data_fetcher = CompanyDataFetcher()


def _parse_news_item(item: dict) -> dict | None:
    """Parse a single yfinance news item — handles both old and new API structure."""
    if not isinstance(item, dict):
        return None

    # NEW yfinance structure: item = {"id": ..., "content": {...}}
    content = item.get("content", {})
    if content:
        title = content.get("title", "")
        summary = content.get("summary", content.get("description", ""))
        # Strip HTML from summary
        import re
        summary = re.sub(r'<[^>]+>', '', summary or "")

        publisher = (content.get("provider") or {}).get("displayName", "Yahoo Finance")
        link = (
            (content.get("canonicalUrl") or {}).get("url")
            or (content.get("clickThroughUrl") or {}).get("url")
            or "#"
        )
        pub_date = content.get("pubDate", "")
        thumb = ""
        thumb_data = content.get("thumbnail") or {}
        resolutions = thumb_data.get("resolutions", [])
        # Pick 170x128 thumbnail if available
        for r in resolutions:
            if r.get("tag") == "170x128":
                thumb = r.get("url", "")
                break
        if not thumb and resolutions:
            thumb = resolutions[0].get("url", "")

        content_type = content.get("contentType", "STORY")

    # OLD yfinance structure: flat dict
    else:
        title = item.get("title", "")
        summary = item.get("summary", "")
        publisher = item.get("publisher", item.get("source", "Unknown"))
        link = item.get("link", item.get("url", "#"))
        pub_date = item.get("providerPublishTime", item.get("published_date", ""))
        content_type = item.get("type", "STORY")
        thumb_data = item.get("thumbnail") or {}
        resolutions = (thumb_data.get("resolutions", []) if isinstance(thumb_data, dict) else [])
        thumb = resolutions[0].get("url", "") if resolutions else ""

    if not title:
        return None

    # Format date nicely
    formatted_date = ""
    try:
        if isinstance(pub_date, (int, float)):
            formatted_date = datetime.fromtimestamp(pub_date).strftime("%b %d, %Y %H:%M")
        elif isinstance(pub_date, str) and pub_date:
            dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
            formatted_date = dt.strftime("%b %d, %Y %H:%M")
    except Exception:
        formatted_date = str(pub_date)[:10] if pub_date else ""

    return {
        "title": title,
        "summary": summary[:280] + "..." if len(summary) > 280 else summary,
        "publisher": publisher,
        "link": link,
        "published_date": formatted_date,
        "raw_date": str(pub_date),
        "thumbnail_url": thumb,
        "type": content_type,
    }


@router.get("/{ticker}")
def get_news(ticker: str, user: User = Depends(get_current_user)) -> List[Dict[str, Any]]:
    try:
        news_items = _data_fetcher.get_news(ticker.upper())

        if not news_items:
            return []

        result = []
        for item in news_items:
            parsed = _parse_news_item(item)
            if parsed:
                result.append(parsed)

        # Sort newest first by raw_date
        result.sort(key=lambda x: str(x.get("raw_date", "")), reverse=True)
        return result[:20]  # Return max 20 articles

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
