"""
LBO - Leveraged Buyout model with real financial data.
Uses actual EBITDA from income statement, real cost of debt from WACC builder.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List


def _safe_get(df: pd.DataFrame, row_names: List[str], col_idx: int = 0, default: float = 0.0) -> float:
    if df is None or df.empty:
        return default
    for name in row_names:
        if name in df.index:
            try:
                vals = df.loc[name]
                v = vals.iloc[col_idx] if hasattr(vals, 'iloc') else vals
                if pd.notna(v):
                    return float(v)
            except Exception:
                continue
    return default


def calculate_lbo(
    ticker: str,
    data_fetcher,
    entry_multiple: Optional[float] = None,
    exit_multiple: Optional[float] = None,
    leverage: float = 5.0,
    hold_period: int = 5,
    target_irr: float = 0.20,
) -> Dict[str, Any]:
    """
    Full LBO model using real EBITDA, cost of debt, and cash flow data.
    """
    info            = data_fetcher.get_info(ticker)
    currency        = info.get("currency", "USD")
    currency_symbol = data_fetcher.get_currency_symbol(currency)
    current_price   = info.get("current_price") or info.get("currentPrice") or 0.0
    shares          = info.get("shares_outstanding") or info.get("sharesOutstanding") or 1.0
    market_cap      = info.get("market_cap") or 0

    # ── Real EBITDA from income statement ────────────────────────────────────
    income_df = data_fetcher.get_income_stmt(ticker)
    cf_df     = data_fetcher.get_cashflow(ticker)

    ebit = _safe_get(income_df, ['EBIT', 'Operating Income', 'OperatingIncome'], 0)
    da   = abs(_safe_get(cf_df, ['Depreciation And Amortization', 'Depreciation',
                                  'DepreciationAndAmortization'], 0))
    ebitda = ebit + da

    # Fallback: use market cap estimate if EBITDA unavailable
    if ebitda <= 0:
        ebitda = market_cap * 0.12 if market_cap > 0 else 1e9

    # ── Entry EV ─────────────────────────────────────────────────────────────
    current_ev_ebitda = info.get("enterpriseToEbitda") or 10.0
    em_entry  = entry_multiple if entry_multiple else current_ev_ebitda
    em_exit   = exit_multiple  if exit_multiple  else em_entry
    entry_ev  = ebitda * em_entry

    # ── Debt structure ────────────────────────────────────────────────────────
    try:
        from api.valuation.wacc_builder import calculate_wacc
        wacc_data = calculate_wacc(ticker, data_fetcher)
        kd        = wacc_data.get("cost_of_debt", 0.06)
        tax_rate  = wacc_data.get("tax_rate", 0.21)
    except Exception:
        kd = 0.06; tax_rate = 0.21

    max_debt  = min(leverage * ebitda, 0.70 * entry_ev)
    debt      = max_debt
    entry_equity = entry_ev - debt

    if entry_equity <= 0:
        # Reduce leverage so equity is at least 20% of EV
        debt = entry_ev * 0.70
        entry_equity = entry_ev * 0.30

    # ── Annual cash flow for debt paydown ────────────────────────────────────
    # FCF ≈ EBITDA − CapEx − Tax − Interest
    capex = abs(_safe_get(cf_df, ['Capital Expenditure', 'CapitalExpenditure',
                                   'Purchase Of Property Plant And Equipment'], 0))
    if capex == 0:
        capex = ebitda * 0.10  # estimate 10% of EBITDA

    # ── 5-year debt schedule ──────────────────────────────────────────────────
    debt_schedule = []
    remaining_debt = debt
    ebitda_projected = ebitda

    for year in range(1, hold_period + 1):
        ebitda_projected *= 1.04  # modest EBITDA growth
        interest_pmt = remaining_debt * kd
        ebt  = ebitda_projected - da - interest_pmt
        taxes = max(ebt * tax_rate, 0)
        net_income = ebt - taxes
        fcf  = net_income + da - capex  # simplified free cash flow

        paydown = max(min(fcf, remaining_debt), 0)
        beg_debt  = remaining_debt
        remaining_debt = max(0, remaining_debt - paydown)

        debt_schedule.append({
            "year":     year,
            "beg_debt": round(beg_debt, 0),
            "interest": round(interest_pmt, 0),
            "fcf":      round(fcf, 0),
            "paydown":  round(paydown, 0),
            "end_debt": round(remaining_debt, 0),
        })

    # ── Exit metrics ─────────────────────────────────────────────────────────
    exit_ebitda  = ebitda_projected
    exit_ev      = exit_ebitda * em_exit
    exit_equity  = exit_ev - remaining_debt

    moic = exit_equity / entry_equity if entry_equity > 0 else 0
    irr  = (moic ** (1 / hold_period)) - 1 if moic > 0 else 0

    # ── LBO Floor Price (max entry for target IRR) ───────────────────────────
    target_moic       = (1 + target_irr) ** hold_period
    max_entry_equity  = exit_equity / target_moic if target_moic > 0 else 0
    max_entry_ev      = max_entry_equity + debt
    scale             = data_fetcher.get_price_scale_to_financials(ticker) if hasattr(data_fetcher, 'get_price_scale_to_financials') else 1.0
    floor_per_share   = (max_entry_equity / max(shares, 1)) * scale

    current_price_per_share_check = market_cap / max(shares, 1) if market_cap > 0 else current_price

    return {
        "entry_ev":        round(entry_ev, 0),
        "entry_multiple":  round(em_entry, 1),
        "debt":            round(debt, 0),
        "entry_equity":    round(entry_equity, 0),
        "exit_ev":         round(exit_ev, 0),
        "exit_multiple":   round(em_exit, 1),
        "exit_equity":     round(exit_equity, 0),
        "remaining_debt":  round(remaining_debt, 0),
        "moic":            round(moic, 2),
        "irr":             round(irr, 4),
        "lbo_floor_price": round(floor_per_share, 2),
        "ebitda":          round(ebitda, 0),
        "cost_of_debt":    round(kd, 4),
        "hold_period":     hold_period,
        "debt_schedule":   debt_schedule,
        "current_price":   current_price,
        "currency":        currency,
        "currency_symbol": currency_symbol,
    }
