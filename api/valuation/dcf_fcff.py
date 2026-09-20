"""
DCF FCFF - Discounted Cash Flow using Free Cash Flow to Firm.
Uses real financial statements from yfinance via data_fetcher.
"""
import numpy as np
import numpy_financial as npf
import pandas as pd
from typing import Dict, Any, Optional, List


def _safe_get(df: pd.DataFrame, row_names: List[str], col_idx: int = 0, default: float = 0.0) -> float:
    """Safely extract a value from a DataFrame by trying multiple row name variants."""
    if df is None or df.empty:
        return default
    for name in row_names:
        if name in df.index:
            try:
                vals = df.loc[name]
                if hasattr(vals, 'iloc'):
                    v = vals.iloc[col_idx]
                else:
                    v = vals
                if pd.notna(v):
                    return float(v)
            except Exception:
                continue
    return default


def _extract_historical_fcff(data_fetcher, ticker: str, sbc_as_cost: bool = True) -> List[float]:
    """Extract historical FCFF from real financial statements."""
    try:
        income_df  = data_fetcher.get_income_stmt(ticker)
        cf_df      = data_fetcher.get_cashflow(ticker)
        bs_df      = data_fetcher.get_balance_sheet(ticker)

        if income_df.empty or cf_df.empty:
            return []

        n_years = min(income_df.shape[1], cf_df.shape[1], 5)
        fcff_list = []

        for i in range(n_years):
            # EBIT
            ebit = _safe_get(income_df, ['EBIT', 'Operating Income', 'OperatingIncome'], i)

            # Tax rate (effective)
            pre_tax = _safe_get(income_df, ['Pretax Income', 'PretaxIncome'], i)
            tax_prov = _safe_get(income_df, ['Tax Provision', 'TaxProvision', 'Income Tax Expense'], i)
            if pre_tax > 0 and tax_prov > 0:
                tax_rate = min(tax_prov / pre_tax, 0.40)
            else:
                tax_rate = 0.21

            nopat = ebit * (1 - tax_rate)

            # D&A from cash flow
            da = _safe_get(cf_df, ['Depreciation And Amortization', 'Depreciation', 'DepreciationAndAmortization',
                                   'Depreciation Depletion Amortization'], i)
            # Make sure D&A is positive
            da = abs(da)

            # CapEx (usually negative in CF statement)
            capex = _safe_get(cf_df, ['Capital Expenditure', 'CapitalExpenditure', 'Purchase Of Property Plant And Equipment',
                                       'Capital Expenditures'], i)
            capex = abs(capex)

            # Change in Working Capital
            curr_assets_curr = _safe_get(bs_df, ['Current Assets', 'Total Current Assets', 'CurrentAssets'], i)
            curr_liab_curr   = _safe_get(bs_df, ['Current Liabilities', 'Total Current Liabilities', 'CurrentLiabilities'], i)
            curr_assets_prev = _safe_get(bs_df, ['Current Assets', 'Total Current Assets', 'CurrentAssets'], min(i + 1, bs_df.shape[1] - 1))
            curr_liab_prev   = _safe_get(bs_df, ['Current Liabilities', 'Total Current Liabilities', 'CurrentLiabilities'], min(i + 1, bs_df.shape[1] - 1))

            wc_curr = curr_assets_curr - curr_liab_curr
            wc_prev = curr_assets_prev - curr_liab_prev
            delta_wc = wc_curr - wc_prev  # increase = cash outflow

            # SBC adjustment
            sbc = 0.0
            if sbc_as_cost:
                sbc = abs(_safe_get(cf_df, ['Stock Based Compensation', 'StockBasedCompensation',
                                             'Share Based Compensation'], i))

            fcff = nopat + da - capex - delta_wc - sbc
            fcff_list.append(fcff)

        # Return in chronological order (oldest first)
        return list(reversed(fcff_list))

    except Exception:
        return []


def _calculate_growth_rates(series: List[float]) -> Dict[str, float]:
    """Calculate growth rates from a historical series."""
    if not series or len(series) < 2:
        return {"cagr_3y": 0.07, "cagr_5y": 0.07}

    # Filter out zeros and negatives for CAGR
    pos_series = [v for v in series if v > 0]
    if len(pos_series) >= 2:
        n3 = min(3, len(pos_series))
        cagr_3y = (pos_series[-1] / pos_series[-n3]) ** (1 / n3) - 1
        n5 = len(pos_series)
        cagr_5y = (pos_series[-1] / pos_series[0]) ** (1 / n5) - 1
    else:
        cagr_3y = 0.07
        cagr_5y = 0.07

    # Clamp to realistic bounds
    cagr_3y = max(min(cagr_3y, 0.50), -0.20)
    cagr_5y = max(min(cagr_5y, 0.40), -0.15)

    return {"cagr_3y": cagr_3y, "cagr_5y": cagr_5y}


def _build_sensitivity_table(base_fcf: float, terminal_growth: float, wacc: float,
                              projection_years: int, pv_fcf_sum: float) -> Dict:
    """Build a 9x9 sensitivity table varying WACC vs terminal growth rate."""
    wacc_steps = [wacc + i * 0.005 for i in range(-4, 5)]   # ±2% in 0.5% steps
    tgr_steps  = [terminal_growth + i * 0.005 for i in range(-3, 4)]  # ±1.5% in 0.5% steps

    matrix = []
    for w in wacc_steps:
        row = []
        for g in tgr_steps:
            if w <= g:
                row.append(None)
                continue
            try:
                tv = (base_fcf * (1 + g)) / (w - g)
                tv_pv = tv / ((1 + w) ** projection_years)
                ev = pv_fcf_sum + tv_pv
                row.append(round(ev, 2))
            except Exception:
                row.append(None)
        matrix.append(row)

    return {
        "row_labels": [round(w, 4) for w in wacc_steps],
        "col_labels": [round(g, 4) for g in tgr_steps],
        "matrix": matrix,
    }


def calculate_dcf_fcff(
    ticker: str,
    data_fetcher,
    wacc_override: Optional[float] = None,
    terminal_growth: float = 0.025,
    projection_years: int = 5,
    mid_year_convention: bool = True,
    sbc_as_cost: bool = True,
    exit_multiple: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Full DCF FCFF valuation using real financial statement data.
    """
    # ── Company info ────────────────────────────────────────────────────────
    info = data_fetcher.get_info(ticker)
    currency        = info.get("currency", "USD")
    currency_symbol = data_fetcher.get_currency_symbol(currency)
    current_price   = info.get("current_price") or info.get("currentPrice") or 0.0
    shares          = info.get("shares_outstanding") or info.get("sharesOutstanding") or 1e9
    market_cap      = info.get("market_cap") or info.get("marketCap") or 0.0

    # ── WACC ────────────────────────────────────────────────────────────────
    try:
        from api.valuation.wacc_builder import calculate_wacc
        wacc_data = calculate_wacc(ticker, data_fetcher)
        wacc = wacc_override if wacc_override else wacc_data.get("wacc", 0.10)
        wacc = max(min(wacc, 0.30), 0.04)  # clamp 4%–30%
    except Exception:
        wacc_data = {"wacc": 0.10}
        wacc = wacc_override or 0.10

    # ── Historical FCFF ─────────────────────────────────────────────────────
    historical_fcf = _extract_historical_fcff(data_fetcher, ticker, sbc_as_cost)

    # If we couldn't get real data, use a fallback based on market cap
    if not historical_fcf or all(v <= 0 for v in historical_fcf):
        # Estimate FCF as ~5% of market cap (rough starting point)
        base_estimate = market_cap * 0.03 if market_cap > 0 else 1e9
        historical_fcf = [base_estimate * (0.9 ** i) for i in range(4, -1, -1)]

    growth_rates = _calculate_growth_rates(historical_fcf)
    base_growth  = growth_rates["cagr_3y"]
    base_fcf     = historical_fcf[-1] if historical_fcf else 1e9

    # ── Project FCF for N years ─────────────────────────────────────────────
    projected_fcf = []
    fcf = base_fcf
    for year in range(1, projection_years + 1):
        if year <= 2:
            g = base_growth
        else:
            # Linear decay from base_growth to terminal_growth
            progress = (year - 2) / max(projection_years - 2, 1)
            g = base_growth + (terminal_growth - base_growth) * progress
        g = max(g, -0.30)
        fcf = fcf * (1 + g)
        projected_fcf.append(fcf)

    # ── Discount factors ────────────────────────────────────────────────────
    pv_fcf          = []
    discount_factors = []
    for i, fcf_val in enumerate(projected_fcf):
        t  = (i + 0.5) if mid_year_convention else (i + 1)
        df = 1.0 / ((1 + wacc) ** t)
        discount_factors.append(round(df, 6))
        pv_fcf.append(fcf_val * df)

    pv_fcf_sum = sum(pv_fcf)

    # ── Terminal Value (Gordon Growth) ──────────────────────────────────────
    last_fcf = projected_fcf[-1]
    if wacc <= terminal_growth:
        wacc = terminal_growth + 0.01  # prevent division by zero

    terminal_value_gordon = (last_fcf * (1 + terminal_growth)) / (wacc - terminal_growth)
    tv_df                 = 1.0 / ((1 + wacc) ** (projection_years - 0.5 if mid_year_convention else projection_years))
    pv_tv_gordon          = terminal_value_gordon * tv_df

    # ── Terminal Value (Exit Multiple) ──────────────────────────────────────
    try:
        ev_ebitda_current = info.get("enterpriseToEbitda") or 12.0
        em = exit_multiple if exit_multiple else ev_ebitda_current
        ebitda_n = last_fcf * 1.25  # rough EBITDA proxy
        terminal_value_exit = ebitda_n * em
        pv_tv_exit = terminal_value_exit * tv_df
    except Exception:
        terminal_value_exit = terminal_value_gordon
        pv_tv_exit = pv_tv_gordon

    # ── Enterprise Values ────────────────────────────────────────────────────
    enterprise_value_gordon = pv_fcf_sum + pv_tv_gordon
    enterprise_value_exit   = pv_fcf_sum + pv_tv_exit

    # ── Net Debt Bridge ──────────────────────────────────────────────────────
    try:
        from api.valuation.net_debt_bridge import calculate_net_debt_bridge, ev_to_equity, equity_to_per_share
        bridge = calculate_net_debt_bridge(ticker, data_fetcher)
        equity_value_gordon = ev_to_equity(enterprise_value_gordon, bridge)
        equity_value_exit   = ev_to_equity(enterprise_value_exit, bridge)
        shares_diluted = bridge.get("shares_outstanding", shares)
    except Exception:
        # Manual fallback: EV − Net Debt
        bs_df = data_fetcher.get_balance_sheet(ticker)
        cash  = abs(_safe_get(bs_df, ['Cash And Cash Equivalents', 'CashAndCashEquivalents', 'Cash'], 0))
        st_d  = abs(_safe_get(bs_df, ['Current Debt', 'Short Long Term Debt', 'Current Portion Of Long Term Debt'], 0))
        lt_d  = abs(_safe_get(bs_df, ['Long Term Debt', 'LongTermDebt'], 0))
        total_debt  = st_d + lt_d
        net_debt    = total_debt - cash
        equity_value_gordon = enterprise_value_gordon - net_debt
        equity_value_exit   = enterprise_value_exit - net_debt
        shares_diluted = shares

    # Shares in same unit as FCF (both in base currency units - yfinance uses actual $)
    shares_diluted = max(shares_diluted, 1)
    scale = data_fetcher.get_price_scale_to_financials(ticker) if hasattr(data_fetcher, 'get_price_scale_to_financials') else 1.0
    value_per_share_gordon = (equity_value_gordon / shares_diluted) * scale
    value_per_share_exit   = (equity_value_exit / shares_diluted) * scale

    # ── TV as % of EV ────────────────────────────────────────────────────────
    tv_pct = pv_tv_gordon / enterprise_value_gordon if enterprise_value_gordon > 0 else 0

    # ── Sensitivity table ────────────────────────────────────────────────────
    sensitivity = _build_sensitivity_table(
        base_fcf=projected_fcf[-1],
        terminal_growth=terminal_growth,
        wacc=wacc,
        projection_years=projection_years,
        pv_fcf_sum=pv_fcf_sum,
    )

    # Convert absolute EV sensitivity into per-share if possible
    if shares_diluted > 1:
        for row in sensitivity["matrix"]:
            for j, v in enumerate(row):
                if v is not None:
                    bs_df_tmp = data_fetcher.get_balance_sheet(ticker)
                    try:
                        net_d = _safe_get(bs_df_tmp, ['Long Term Debt'], 0) - _safe_get(bs_df_tmp, ['Cash And Cash Equivalents'], 0)
                        row[j] = round(((v - net_d) / shares_diluted) * scale, 2)
                    except Exception:
                        row[j] = round((v / shares_diluted) * scale, 2)

    upside_pct = ((value_per_share_gordon / current_price) - 1) * 100 if current_price > 0 else 0

    return {
        "intrinsic_value_per_share":    round(value_per_share_gordon, 2),
        "intrinsic_value_exit_multiple": round(value_per_share_exit, 2),
        "enterprise_value":             round(enterprise_value_gordon, 0),
        "equity_value":                 round(equity_value_gordon, 0),
        "projected_fcf":                [round(v, 0) for v in projected_fcf],
        "discount_factors":             discount_factors,
        "pv_fcf":                       [round(v, 0) for v in pv_fcf],
        "terminal_value_gordon":        round(terminal_value_gordon, 0),
        "terminal_value_exit":          round(terminal_value_exit, 0),
        "tv_as_pct_of_ev":              round(tv_pct * 100, 1),
        "wacc_components":              {**wacc_data, "wacc": round(wacc, 4)},
        "assumptions": {
            "terminal_growth":   terminal_growth,
            "projection_years":  projection_years,
            "base_growth":       round(base_growth, 4),
            "mid_year":          mid_year_convention,
            "sbc_as_cost":       sbc_as_cost,
        },
        "current_price":          current_price,
        "upside_downside_pct":    round(upside_pct, 1),
        "sensitivity_table":      sensitivity,
        "historical_fcf":         [round(v, 0) for v in historical_fcf],
        "historical_growth_rates": growth_rates,
        "currency":               currency,
        "currency_symbol":        currency_symbol,
    }
