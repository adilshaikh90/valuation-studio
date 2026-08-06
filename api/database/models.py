"""
SQLAlchemy models for the Valuation Studio application.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from .db import Base

class User(Base):
    """
    User model for authentication and profiles.
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, default="user")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = Column(DateTime, nullable=True)
    
    search_logs = relationship("SearchLog", back_populates="user")
    custom_peers = relationship("CustomPeer", back_populates="user")


class SearchLog(Base):
    """
    Search log model to track user queries.
    """
    __tablename__ = "search_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    ticker = Column(String, index=True)
    company = Column(String)
    country = Column(String)
    currency = Column(String)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", back_populates="search_logs")


class CustomPeer(Base):
    """
    Model to store custom peer relationships defined by users.
    """
    __tablename__ = "custom_peers"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    target_ticker = Column(String, index=True)
    peer_ticker = Column(String)
    added_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", back_populates="custom_peers")
