"""
Valuation routes - exposes DCF, DDM, APV, Comps, NAV, LBO, and Football Field endpoints.
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List

from ..auth.utils import get_current_user
from ..company.data_fetcher import CompanyDataFetcher
from ..database.models import User

from .dcf_fcff import calculate_dcf_fcff
from .dcf_fcfe import calculate_dcf_fcfe
from .ddm import calculate_ddm
from .apv import calculate_apv
from .trading_comps import calculate_trading_comps
from .nav import calculate_nav
from .lbo import calculate_lbo
from .football_field import calculate_football_field

router = APIRouter(prefix="/api/valuation", tags=["valuation"])

# Shared data fetcher instance (cached in-memory with 15-min TTL)
_data_fetcher = CompanyDataFetcher()


@router.get("/{ticker}/dcf-fcff")
def dcf_fcff_endpoint(
    ticker: str,
    wacc_override: Optional[float] = None,
    terminal_growth: float = 0.025,
    projection_years: int = 5,
    mid_year_convention: bool = True,
    sbc_as_cost: bool = True,
    exit_multiple: Optional[float] = None,
    user: User = Depends(get_current_user),
):
    try:
        return calculate_dcf_fcff(
            ticker.upper(), _data_fetcher,
            wacc_override=wacc_override,
            terminal_growth=terminal_growth,
            projection_years=projection_years,
            mid_year_convention=mid_year_convention,
            sbc_as_cost=sbc_as_cost,
            exit_multiple=exit_multiple,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ticker}/dcf-fcfe")
def dcf_fcfe_endpoint(
    ticker: str,
    cost_of_equity: Optional[float] = None,
    terminal_growth: float = 0.025,
    user: User = Depends(get_current_user),
):
    try:
        return calculate_dcf_fcfe(
            ticker.upper(), _data_fetcher,
            cost_of_equity_override=cost_of_equity,
            terminal_growth=terminal_growth,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ticker}/ddm")
def ddm_endpoint(ticker: str, user: User = Depends(get_current_user)):
    try:
        return calculate_ddm(ticker.upper(), _data_fetcher)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ticker}/apv")
def apv_endpoint(ticker: str, user: User = Depends(get_current_user)):
    try:
        return calculate_apv(ticker.upper(), _data_fetcher)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ticker}/comps")
def comps_endpoint(
    ticker: str,
    custom_peers: Optional[List[str]] = Query(None),
    user: User = Depends(get_current_user),
):
    try:
        return calculate_trading_comps(ticker.upper(), _data_fetcher, custom_peers=custom_peers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ticker}/nav")
def nav_endpoint(ticker: str, user: User = Depends(get_current_user)):
    try:
        return calculate_nav(ticker.upper(), _data_fetcher)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ticker}/lbo")
def lbo_endpoint(
    ticker: str,
    entry_multiple: Optional[float] = None,
    exit_multiple: Optional[float] = None,
    leverage: float = 5.0,
    hold_period: int = 5,
    target_irr: float = 0.20,
    user: User = Depends(get_current_user),
):
    try:
        return calculate_lbo(
            ticker.upper(), _data_fetcher,
            entry_multiple=entry_multiple,
            exit_multiple=exit_multiple,
            leverage=leverage,
            hold_period=hold_period,
            target_irr=target_irr,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ticker}/football-field")
def football_field_endpoint(
    ticker: str,
    user: User = Depends(get_current_user),
):
    try:
        return calculate_football_field(ticker.upper(), _data_fetcher)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
