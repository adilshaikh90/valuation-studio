"""
Admin routes — user management and analytics dashboard (admin-only).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from ..auth.utils import require_admin
from ..database.db import get_db
from ..database.models import User, SearchLog

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users")
def get_users(
    page: int = 1,
    limit: int = 50,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all users with pagination."""
    offset = (page - 1) * limit
    total = db.query(func.count(User.id)).scalar()
    users = db.query(User).order_by(User.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "role": u.role,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "last_login": u.last_login.isoformat() if u.last_login else None,
            }
            for u in users
        ],
        "total": total,
        "page": page,
        "limit": limit,
    }


@router.patch("/users/{user_id}")
def toggle_user_active(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Toggle a user's active status."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = not user.is_active
    db.commit()
    return {
        "message": f"User {user.email} is now {'active' if user.is_active else 'inactive'}",
        "is_active": user.is_active,
    }


@router.patch("/users/{user_id}/role")
def update_user_role(
    user_id: int,
    payload: dict,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Change a user's role between 'user' and 'admin'."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_role = payload.get("role", "user")
    if new_role not in ["user", "admin"]:
        raise HTTPException(status_code=400, detail="Invalid role specified")

    user.role = new_role
    db.commit()
    return {
        "message": f"User {user.email} role updated to {user.role}",
        "role": user.role,
    }


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Delete a user account."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own admin account")

    db.delete(user)
    db.commit()
    return {"message": f"User {user.email} successfully deleted"}


@router.get("/logs")
def get_search_logs(
    limit: int = 50,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get recent search audit logs."""
    logs = (
        db.query(SearchLog, User.email)
        .outerjoin(User, SearchLog.user_id == User.id)
        .order_by(SearchLog.timestamp.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": log.SearchLog.id,
            "ticker": log.SearchLog.ticker,
            "company": log.SearchLog.company,
            "country": log.SearchLog.country,
            "currency": log.SearchLog.currency,
            "timestamp": log.SearchLog.timestamp.isoformat() if log.SearchLog.timestamp else None,
            "user_email": log.email or "Anonymous",
        }
        for log in logs
    ]


@router.get("/analytics")
def get_analytics(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Dashboard analytics: searches, top tickers, user growth."""
    total_users = db.query(func.count(User.id)).scalar()
    total_searches = db.query(func.count(SearchLog.id)).scalar()

    # Searches by day — last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    searches_by_day_raw = (
        db.query(
            func.date(SearchLog.timestamp).label("date"),
            func.count(SearchLog.id).label("count"),
        )
        .filter(SearchLog.timestamp >= thirty_days_ago)
        .group_by(func.date(SearchLog.timestamp))
        .order_by(func.date(SearchLog.timestamp))
        .all()
    )
    searches_by_day = [{"date": str(r.date), "count": r.count} for r in searches_by_day_raw]

    # Top tickers
    top_tickers_raw = (
        db.query(
            SearchLog.ticker,
            SearchLog.company,
            func.count(SearchLog.id).label("count"),
        )
        .group_by(SearchLog.ticker, SearchLog.company)
        .order_by(func.count(SearchLog.id).desc())
        .limit(20)
        .all()
    )
    top_tickers = [
        {"ticker": r.ticker, "company": r.company or r.ticker, "count": r.count}
        for r in top_tickers_raw
    ]

    # Top users
    top_users_raw = (
        db.query(
            User.email,
            func.count(SearchLog.id).label("search_count"),
        )
        .join(SearchLog, SearchLog.user_id == User.id)
        .group_by(User.email)
        .order_by(func.count(SearchLog.id).desc())
        .limit(10)
        .all()
    )
    top_users = [{"email": r.email, "search_count": r.search_count} for r in top_users_raw]

    # Searches by country
    searches_by_country_raw = (
        db.query(
            SearchLog.country,
            func.count(SearchLog.id).label("count"),
        )
        .filter(SearchLog.country.isnot(None))
        .group_by(SearchLog.country)
        .order_by(func.count(SearchLog.id).desc())
        .all()
    )
    searches_by_country = [{"country": r.country, "count": r.count} for r in searches_by_country_raw]

    # New users by day — last 30 days
    new_users_raw = (
        db.query(
            func.date(User.created_at).label("date"),
            func.count(User.id).label("count"),
        )
        .filter(User.created_at >= thirty_days_ago)
        .group_by(func.date(User.created_at))
        .order_by(func.date(User.created_at))
        .all()
    )
    new_users_by_day = [{"date": str(r.date), "count": r.count} for r in new_users_raw]

    return {
        "total_users": total_users,
        "total_searches": total_searches,
        "searches_by_day": searches_by_day,
        "top_tickers": top_tickers,
        "top_users": top_users,
        "searches_by_country": searches_by_country,
        "new_users_by_day": new_users_by_day,
    }
