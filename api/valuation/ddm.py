"""
DDM — Dividend Discount Model with Gordon Growth, Two-Stage, and H-Model variants.
Uses real dividend history from yfinance.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional


def calculate_ddm(ticker: str, data_fetcher, cost_of_equity: Optional[float] = None) -> Dict[str, Any]:
    """
    Dividend Discount Model — 3 variants.
    Returns {'applicable': False} if company doesn't pay dividends.
    """
    info            = data_fetcher.get_info(ticker)
    currency        = info.get("currency", "USD")
    currency_symbol = data_fetcher.get_currency_symbol(currency)
    current_price   = info.get("current_price") or info.get("currentPrice") or 0.0

    # ── Check dividends ───────────────────────────────────────────────────────
    div_rate = info.get("dividend_yield") or info.get("dividendRate")

    # Also try to fetch dividend history for more accurate data
    div_history = []
    try:
        divs = data_fetcher.get_dividends(ticker)
        div_history = divs.get("dividends", [])
    except Exception:
        pass

    # Use trailing 12m dividend sum as current annual dividend
    d0 = 0.0
    if div_history:
        # Sort by date and take last 4 quarters
        sorted_divs = sorted(div_history, key=lambda x: x["date"])
        last_4 = sorted_divs[-4:] if len(sorted_divs) >= 4 else sorted_divs
        d0 = sum(item["amount"] for item in last_4)

    if d0 == 0 and div_rate:
        # Use trailing annual from info
        if div_rate < 1.0:  # it's a yield fraction
            d0 = current_price * div_rate if current_price else 0
        else:
            d0 = div_rate

    if d0 <= 0:
        return {
            "applicable": False,
            "reason": "Company does not pay dividends or dividend data unavailable.",
            "currency": currency,
            "currency_symbol": currency_symbol,
        }

    # ── Dividend growth rate ───────────────────────────────────────────────────
    cagr_3y = 0.04
    cagr_5y = 0.04
    if len(div_history) >= 8:
        try:
            by_year = {}
            for d in div_history:
                yr = d["date"][:4]
                by_year[yr] = by_year.get(yr, 0) + d["amount"]
            years_sorted = sorted(by_year.keys())
            annual_divs  = [by_year[y] for y in years_sorted if by_year[y] > 0]

            if len(annual_divs) >= 3:
                cagr_3y = (annual_divs[-1] / annual_divs[-3]) ** (1/3) - 1
                cagr_3y = max(min(cagr_3y, 0.30), -0.10)
            if len(annual_divs) >= 5:
                cagr_5y = (annual_divs[-1] / annual_divs[-5]) ** (1/5) - 1
                cagr_5y = max(min(cagr_5y, 0.25), -0.10)
        except Exception:
            pass

    payout_ratio = info.get("payout_ratio") or info.get("payoutRatio") or 0.0
    eps          = info.get("eps") or info.get("trailingEps") or 0.0
    coverage     = eps / d0 if d0 > 0 and eps > 0 else None
    consec_years = len(set(d["date"][:4] for d in div_history)) if div_history else 0

    # ── Cost of Equity ─────────────────────────────────────────────────────────
    if cost_of_equity:
        ke = cost_of_equity
    else:
        try:
            from api.valuation.wacc_builder import calculate_wacc
            wacc_data = calculate_wacc(ticker, data_fetcher)
            ke = wacc_data.get("cost_of_equity", 0.10)
        except Exception:
            ke = 0.10
    ke = max(min(ke, 0.25), 0.04)

    # Use 5yr cagr as growth, stable at 2.5%
    g       = cagr_5y
    g_stable = 0.025

    # ── Gordon Growth Model ─────────────────────────────────────────────────────
    if ke <= g:
        gordon_value = None
        gordon_note  = f"Invalid: growth ({g:.1%}) ≥ cost of equity ({ke:.1%})"
    else:
        d1           = d0 * (1 + g)
        gordon_value = round(d1 / (ke - g), 2)
        gordon_note  = None

    # ── Two-Stage DDM ───────────────────────────────────────────────────────────
    stage1_years = 5
    pv_divs      = 0.0
    current_div  = d0
    for i in range(1, stage1_years + 1):
        current_div *= (1 + g)
        pv_divs     += current_div / ((1 + ke) ** i)

    if ke <= g_stable:
        two_stage_value = None
    else:
        tv_two = (current_div * (1 + g_stable)) / (ke - g_stable)
        two_stage_value = round(pv_divs + tv_two / ((1 + ke) ** stage1_years), 2)

    # ── H-Model ─────────────────────────────────────────────────────────────────
    H = 5.0  # half-life of high-growth period
    if ke <= g_stable:
        h_model_value = None
    else:
        h_model_value = round(
            (d0 * (1 + g_stable)) / (ke - g_stable)
            + (d0 * H * (g - g_stable)) / (ke - g_stable),
            2,
        )

    return {
        "applicable":               True,
        "gordon_growth_value":      gordon_value,
        "gordon_note":              gordon_note,
        "two_stage_value":          two_stage_value,
        "h_model_value":            h_model_value,
        "current_dividend_annual":  round(d0, 4),
        "cost_of_equity":           round(ke, 4),
        "3yr_dividend_cagr":        round(cagr_3y, 4),
        "5yr_dividend_cagr":        round(cagr_5y, 4),
        "payout_ratio":             round(payout_ratio, 4) if payout_ratio else None,
        "coverage_ratio":           round(coverage, 2) if coverage else None,
        "years_of_consecutive_dividends": consec_years,
        "current_price":            current_price,
        "currency":                 currency,
        "currency_symbol":          currency_symbol,
    }
