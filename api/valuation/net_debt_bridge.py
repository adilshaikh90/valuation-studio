"""
Net Debt Bridge - converts Enterprise Value to Equity Value.
Uses real balance sheet data from yfinance via data_fetcher DataFrames.
"""
import pandas as pd
from typing import Dict, Any, List


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


def calculate_net_debt_bridge(ticker: str, data_fetcher) -> Dict[str, Any]:
    """
    Builds the Net Debt Bridge: EV → Equity Value.
    Uses actual balance sheet DataFrame for accuracy.
    """
    info   = data_fetcher.get_info(ticker)
    bs_df  = data_fetcher.get_balance_sheet(ticker)
    shares = info.get("shares_outstanding") or info.get("sharesOutstanding") or 1.0

    # Debt components
    st_debt  = abs(_safe_get(bs_df, ['Current Debt', 'Short Long Term Debt', 'Current Portion Of Long Term Debt',
                                      'Current Debt And Capital Lease Obligation'], 0))
    lt_debt  = abs(_safe_get(bs_df, ['Long Term Debt', 'LongTermDebt', 'Long Term Debt And Capital Lease Obligation'], 0))
    total_debt = st_debt + lt_debt

    # Cash and equivalents
    cash = abs(_safe_get(bs_df, ['Cash And Cash Equivalents', 'CashAndCashEquivalents',
                                  'Cash Cash Equivalents And Short Term Investments', 'Cash'], 0))

    # Other adjustments
    minority_interest  = abs(_safe_get(bs_df, ['Minority Interest', 'NoncontrollingInterestInSubsidiaries'], 0))
    preferred_equity   = abs(_safe_get(bs_df, ['Preferred Stock', 'PreferredStock', 'Preferred Stock Equity'], 0))
    equity_investments = abs(_safe_get(bs_df, ['Investments And Advances', 'Long Term Investments',
                                                'Equity Investments'], 0))

    net_debt = total_debt - cash
    equity_value_adjustment = -total_debt + cash - minority_interest - preferred_equity + equity_investments

    return {
        "total_debt":              round(total_debt, 0),
        "cash":                    round(cash, 0),
        "minority_interest":       round(minority_interest, 0),
        "preferred_equity":        round(preferred_equity, 0),
        "equity_investments":      round(equity_investments, 0),
        "net_debt":                round(net_debt, 0),
        "equity_value_adjustment": round(equity_value_adjustment, 0),
        "shares_outstanding":      shares,
    }


def ev_to_equity(enterprise_value: float, bridge_data: Dict[str, Any]) -> float:
    """EV → Equity Value using bridge adjustments."""
    return enterprise_value + bridge_data.get("equity_value_adjustment", 0.0)


def equity_to_per_share(equity_value: float, shares_outstanding: float) -> float:
    """Equity Value → per-share value."""
    return equity_value / shares_outstanding if shares_outstanding > 0 else 0.0


def get_diluted_shares(ticker: str, data_fetcher) -> float:
    """Diluted share count from company info."""
    info = data_fetcher.get_info(ticker)
    return float(info.get("shares_outstanding") or info.get("sharesOutstanding") or 1.0)
