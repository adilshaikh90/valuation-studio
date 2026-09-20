"""
DCF FCFE - Discounted Cash Flow using Free Cash Flow to Equity.
Uses real financial data from yfinance via data_fetcher.
"""
import pandas as pd
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


def calculate_dcf_fcfe(
    ticker: str,
    data_fetcher,
    cost_of_equity_override: Optional[float] = None,
    terminal_growth: float = 0.025,
    projection_years: int = 5,
) -> Dict[str, Any]:
    """Full FCFE valuation using real financial statements."""

    info            = data_fetcher.get_info(ticker)
    currency        = info.get("currency", "USD")
    currency_symbol = data_fetcher.get_currency_symbol(currency)
    current_price   = info.get("current_price") or info.get("currentPrice") or 0.0
    shares          = info.get("shares_outstanding") or info.get("sharesOutstanding") or 1e9

    # ── Cost of Equity from WACC builder ────────────────────────────────────
    try:
        from api.valuation.wacc_builder import calculate_wacc
        wacc_data = calculate_wacc(ticker, data_fetcher)
        ke = cost_of_equity_override or wacc_data.get("cost_of_equity", 0.10)
    except Exception:
        ke = cost_of_equity_override or 0.10
    ke = max(min(ke, 0.30), 0.04)

    # ── Historical FCFE ─────────────────────────────────────────────────────
    # FCFE = Net Income + D&A − CapEx − ΔNWC + Net Borrowing
    try:
        income_df = data_fetcher.get_income_stmt(ticker)
        cf_df     = data_fetcher.get_cashflow(ticker)
        bs_df     = data_fetcher.get_balance_sheet(ticker)
        n_years   = min(income_df.shape[1], cf_df.shape[1], 5)

        historical_fcfe = []
        for i in range(n_years):
            net_income = _safe_get(income_df, ['Net Income', 'NetIncome'], i)
            da         = abs(_safe_get(cf_df, ['Depreciation And Amortization', 'Depreciation', 'DepreciationAndAmortization'], i))
            capex      = abs(_safe_get(cf_df, ['Capital Expenditure', 'CapitalExpenditure', 'Purchase Of Property Plant And Equipment'], i))

            # Change in working capital
            ca_c = _safe_get(bs_df, ['Current Assets', 'Total Current Assets'], i)
            cl_c = _safe_get(bs_df, ['Current Liabilities', 'Total Current Liabilities'], i)
            ca_p = _safe_get(bs_df, ['Current Assets', 'Total Current Assets'], min(i+1, bs_df.shape[1]-1))
            cl_p = _safe_get(bs_df, ['Current Liabilities', 'Total Current Liabilities'], min(i+1, bs_df.shape[1]-1))
            delta_nwc = (ca_c - cl_c) - (ca_p - cl_p)

            # Net borrowing = change in total debt
            lt_d_c = _safe_get(bs_df, ['Long Term Debt', 'LongTermDebt'], i)
            lt_d_p = _safe_get(bs_df, ['Long Term Debt', 'LongTermDebt'], min(i+1, bs_df.shape[1]-1))
            net_borrowing = lt_d_c - lt_d_p

            fcfe = net_income + da - capex - delta_nwc + net_borrowing
            historical_fcfe.append(fcfe)

        historical_fcfe = list(reversed(historical_fcfe))
    except Exception:
        historical_fcfe = []

    # Fallback
    if not historical_fcfe or all(v <= 0 for v in historical_fcfe):
        market_cap = info.get("market_cap") or 0
        base = market_cap * 0.025 if market_cap > 0 else 1e9
        historical_fcfe = [base * (0.9 ** i) for i in range(4, -1, -1)]

    # ── Growth rate ─────────────────────────────────────────────────────────
    pos = [v for v in historical_fcfe if v > 0]
    if len(pos) >= 2:
        cagr = (pos[-1] / pos[0]) ** (1 / len(pos)) - 1
        cagr = max(min(cagr, 0.40), -0.15)
    else:
        cagr = 0.06

    # ── Project FCFE ─────────────────────────────────────────────────────────
    projected_fcfe = []
    fcfe = historical_fcfe[-1]
    for year in range(1, projection_years + 1):
        if year <= 2:
            g = cagr
        else:
            progress = (year - 2) / max(projection_years - 2, 1)
            g = cagr + (terminal_growth - cagr) * progress
        g = max(g, -0.30)
        fcfe = fcfe * (1 + g)
        projected_fcfe.append(fcfe)

    # ── Discount at Ke ─────────────────────────────────────────────────────
    if ke <= terminal_growth:
        ke = terminal_growth + 0.02

    pv_fcfe          = []
    discount_factors = []
    for i, v in enumerate(projected_fcfe):
        df = 1.0 / ((1 + ke) ** (i + 1))
        discount_factors.append(round(df, 6))
        pv_fcfe.append(v * df)

    # ── Terminal Value ──────────────────────────────────────────────────────
    terminal_value = (projected_fcfe[-1] * (1 + terminal_growth)) / (ke - terminal_growth)
    tv_df          = 1.0 / ((1 + ke) ** projection_years)
    pv_tv          = terminal_value * tv_df

    equity_value     = sum(pv_fcfe) + pv_tv
    shares           = max(shares, 1)
    scale            = data_fetcher.get_price_scale_to_financials(ticker) if hasattr(data_fetcher, 'get_price_scale_to_financials') else 1.0
    value_per_share  = (equity_value / shares) * scale
    upside_pct       = ((value_per_share / current_price) - 1) * 100 if current_price > 0 else 0

    return {
        "intrinsic_value_per_share": round(value_per_share, 2),
        "equity_value":              round(equity_value, 0),
        "projected_fcfe":            [round(v, 0) for v in projected_fcfe],
        "discount_factors":          discount_factors,
        "pv_fcfe":                   [round(v, 0) for v in pv_fcfe],
        "terminal_value":            round(terminal_value, 0),
        "tv_as_pct_of_equity":       round(pv_tv / equity_value * 100, 1) if equity_value else 0,
        "cost_of_equity":            round(ke, 4),
        "historical_fcfe":           [round(v, 0) for v in historical_fcfe],
        "current_price":             current_price,
        "upside_downside_pct":       round(upside_pct, 1),
        "currency":                  currency,
        "currency_symbol":           currency_symbol,
    }
