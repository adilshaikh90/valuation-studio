"""
Quant routes - Monte Carlo, Sensitivity, Tornado, Scenarios, Regression.
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from pydantic import BaseModel

from ..auth.utils import get_current_user
from ..company.data_fetcher import CompanyDataFetcher
from ..database.models import User

from .monte_carlo import run_monte_carlo
from .sensitivity import calculate_sensitivity
from .tornado import calculate_tornado, calculate_scenarios
from .scenario_weighting import calculate_weighted_scenarios
from .regression_multiples import calculate_regression_multiples

router = APIRouter(prefix="/api/quant", tags=["quant"])

_data_fetcher = CompanyDataFetcher()


@router.get("/{ticker}/monte-carlo")
def api_monte_carlo(
    ticker: str,
    iterations: int = 10000,
    user: User = Depends(get_current_user),
):
    try:
        return run_monte_carlo(ticker.upper(), _data_fetcher, iterations=iterations)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ticker}/sensitivity")
def api_sensitivity(ticker: str, user: User = Depends(get_current_user)):
    try:
        return calculate_sensitivity(ticker.upper(), _data_fetcher)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ticker}/tornado")
def api_tornado(ticker: str, user: User = Depends(get_current_user)):
    try:
        return calculate_tornado(ticker.upper(), _data_fetcher)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ticker}/scenarios")
def api_scenarios(ticker: str, user: User = Depends(get_current_user)):
    try:
        return calculate_scenarios(ticker.upper(), _data_fetcher)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CustomScenario(BaseModel):
    scenario_name: str
    probability: float
    assumptions: dict
    implied_price: float


@router.get("/{ticker}/scenario-weighting")
def api_scenario_weighting_get(ticker: str, user: User = Depends(get_current_user)):
    try:
        return calculate_weighted_scenarios(ticker.upper(), _data_fetcher)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{ticker}/scenario-weighting")
def api_scenario_weighting_post(
    ticker: str,
    custom_scenarios: Optional[List[CustomScenario]] = None,
    user: User = Depends(get_current_user),
):
    try:
        scens = [s.dict() for s in custom_scenarios] if custom_scenarios else None
        return calculate_weighted_scenarios(ticker.upper(), _data_fetcher, custom_scenarios=scens)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ticker}/regression-multiples")
def api_regression_multiples(ticker: str, user: User = Depends(get_current_user)):
    try:
        return calculate_regression_multiples(ticker.upper(), _data_fetcher)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
