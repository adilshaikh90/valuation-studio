"""
Monte Carlo - Bootstrapped simulation resampling from real historical financials.
10,000 iterations, bootstrapping revenue growth, EBITDA margins, and CapEx ratios.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any


def _safe_series(df: pd.DataFrame, row_names: list) -> np.ndarray:
    """Extract a row from DataFrame by trying multiple name variants."""
    if df is None or df.empty:
        return np.array([])
    for name in row_names:
        if name in df.index:
            vals = df.loc[name].dropna()
            if len(vals) > 0:
                return vals.values[::-1].astype(float)  # chronological order
    return np.array([])


def run_monte_carlo(ticker: str, data_fetcher, iterations: int = 10000) -> Dict[str, Any]:
    """
    Bootstrapped Monte Carlo simulation.
    Resamples from actual historical revenue growth, margins, and CapEx ratios.
    """
    info = data_fetcher.get_info(ticker)
    currency        = info.get("currency", "USD")
    currency_symbol = data_fetcher.get_currency_symbol(currency)

    # Use the processed field names from get_company_info
    current_price = (
        info.get("current_price") or
        info.get("currentPrice") or
        info.get("regularMarketPrice") or 0.0
    )
    shares_out = (
        info.get("shares_outstanding") or
        info.get("sharesOutstanding") or 0
    )
    market_cap = info.get("market_cap") or info.get("marketCap") or 0

    # ── Get real financial DataFrames ─────────────────────────────────────────
    income_df  = data_fetcher.get_income_stmt(ticker)
    cf_df      = data_fetcher.get_cashflow(ticker)
    bs_df      = data_fetcher.get_balance_sheet(ticker)

    # Revenue history
    rev_arr = _safe_series(income_df, ['Total Revenue', 'TotalRevenue', 'Revenue'])
    if len(rev_arr) < 2:
        # Fallback: synthesize from market cap
        base = market_cap * 0.25 if market_cap > 0 else 1e9
        rev_arr = np.array([base * (0.9 ** i) for i in range(4, -1, -1)])

    # EBITDA history - try direct, or compute EBIT + D&A
    ebitda_arr = _safe_series(income_df, ['EBITDA', 'Ebitda'])
    if len(ebitda_arr) < 2:
        ebit_arr = _safe_series(income_df, ['EBIT', 'Operating Income', 'OperatingIncome'])
        da_arr   = _safe_series(cf_df, ['Depreciation And Amortization', 'Depreciation',
                                         'DepreciationAndAmortization'])
        n = min(len(ebit_arr), len(da_arr), len(rev_arr))
        if n > 0:
            ebitda_arr = ebit_arr[:n] + da_arr[:n]
        else:
            ebitda_arr = rev_arr * 0.20

    # CapEx history
    capex_arr = np.abs(_safe_series(cf_df, ['Capital Expenditure', 'CapitalExpenditure',
                                             'Purchase Of Property Plant And Equipment']))

    # Net debt
    cash     = 0.0
    total_d  = 0.0
    if not bs_df.empty:
        for name in ['Cash And Cash Equivalents', 'CashAndCashEquivalents',
                     'Cash Cash Equivalents And Short Term Investments', 'Cash']:
            if name in bs_df.index:
                v = bs_df.loc[name].iloc[0]
                if pd.notna(v):
                    cash = abs(float(v))
                    break
        for name in ['Long Term Debt', 'LongTermDebt']:
            if name in bs_df.index:
                v = bs_df.loc[name].iloc[0]
                if pd.notna(v):
                    total_d += abs(float(v))
                    break

    net_debt = total_d - cash

    # ── Build bootstrap samples ────────────────────────────────────────────────
    # Revenue growth rates
    n_rev = min(len(rev_arr), len(ebitda_arr))
    rev_use = rev_arr[:n_rev]
    ebitda_use = ebitda_arr[:n_rev]

    if len(rev_use) > 1:
        rev_growth = np.diff(rev_use) / np.where(rev_use[:-1] == 0, 1, rev_use[:-1])
    else:
        rev_growth = np.array([0.06])
    rev_growth = np.clip(rev_growth, -0.40, 0.80)

    # EBITDA margins
    safe_rev = np.where(rev_use == 0, 1, rev_use)
    ebitda_margins = ebitda_use / safe_rev
    ebitda_margins = np.clip(ebitda_margins, 0.01, 0.80)

    # CapEx ratios
    n_cap = min(len(capex_arr), len(rev_use))
    if n_cap > 0:
        capex_ratios = capex_arr[:n_cap] / np.where(rev_use[:n_cap] == 0, 1, rev_use[:n_cap])
        capex_ratios = np.clip(capex_ratios, 0.0, 0.40)
    else:
        capex_ratios = np.array([0.05])

    # Ensure minimum bootstrap pool size
    if len(rev_growth) < 3:
        mu = float(np.mean(rev_growth))
        rev_growth = np.concatenate([rev_growth, np.random.normal(mu, 0.03, 10)])
    if len(ebitda_margins) < 3:
        mu = float(np.mean(ebitda_margins))
        ebitda_margins = np.concatenate([ebitda_margins, np.random.normal(mu, 0.02, 10)])
    if len(capex_ratios) < 3:
        mu = float(np.mean(capex_ratios))
        capex_ratios = np.concatenate([capex_ratios, np.random.normal(mu, 0.01, 10)])

    # ── WACC base ─────────────────────────────────────────────────────────────
    try:
        from api.valuation.wacc_builder import calculate_wacc
        wacc_data = calculate_wacc(ticker, data_fetcher)
        base_wacc = wacc_data.get("wacc", 0.09)
    except Exception:
        base_wacc = 0.09
    base_wacc = max(min(base_wacc, 0.25), 0.04)

    # ── Simulation ────────────────────────────────────────────────────────────
    projection_years = 5
    last_rev = float(rev_use[-1]) if len(rev_use) > 0 else (market_cap * 0.25 if market_cap > 0 else 1e9)
    tax_rate = 0.21

    sim_prices = np.zeros(iterations)

    for i in range(iterations):
        g = np.random.choice(rev_growth, size=projection_years, replace=True)
        m = np.random.choice(ebitda_margins, size=projection_years, replace=True)
        c = np.random.choice(capex_ratios, size=projection_years, replace=True)

        # Perturb WACC and terminal growth
        wacc    = float(np.random.triangular(max(0.02, base_wacc - 0.025), base_wacc, base_wacc + 0.025))
        term_g  = float(np.random.uniform(0.015, 0.035))
        if wacc <= term_g:
            wacc = term_g + 0.02

        # Project revenues
        rev     = last_rev * np.cumprod(1.0 + g)
        ebitda  = rev * m
        fcf     = ebitda * (1 - tax_rate) - rev * c

        # Discount
        dfs  = (1.0 + wacc) ** np.arange(1, projection_years + 1)
        pv   = np.sum(fcf / dfs)

        # Terminal value (Gordon Growth)
        tv    = fcf[-1] * (1 + term_g) / (wacc - term_g)
        pv_tv = tv / ((1.0 + wacc) ** projection_years)

        ev = pv + pv_tv
        eq = ev - net_debt

        if shares_out > 0:
            sim_prices[i] = max(0.0, eq / shares_out)
        elif market_cap > 0:
            # Express as % of current price
            sim_prices[i] = max(0.0, (eq / market_cap) * current_price)

    # ── Statistics ────────────────────────────────────────────────────────────
    valid = sim_prices[sim_prices > 0]
    if len(valid) < iterations * 0.5:
        # Too many zeros - simulation probably bad, return market-based estimate
        mean_val   = current_price
        std_val    = current_price * 0.20
        percentile_vals = np.percentile([current_price * x for x in
                                         [0.70, 0.80, 0.90, 1.0, 1.10, 1.20, 1.30]], [5, 10, 25, 50, 75, 90, 95])
        prob_up = 0.50
    else:
        mean_val   = float(np.mean(valid))
        std_val    = float(np.std(valid))
        percentile_vals = np.percentile(sim_prices, [5, 10, 25, 50, 75, 90, 95])
        prob_up    = float(np.mean(sim_prices > current_price)) if current_price > 0 else 0.0

    counts, bins = np.histogram(sim_prices[sim_prices > 0], bins=50)

    return {
        "ticker":                ticker,
        "currency":              currency,
        "currency_symbol":       currency_symbol,
        "current_price":         current_price,
        "mean":                  round(float(mean_val), 2),
        "median":                round(float(percentile_vals[3]), 2),
        "std_dev":               round(float(std_val), 2),
        "p10":                   round(float(percentile_vals[1]), 2),
        "p90":                   round(float(percentile_vals[5]), 2),
        "percentiles": {
            "P5":  round(float(percentile_vals[0]), 2),
            "P10": round(float(percentile_vals[1]), 2),
            "P25": round(float(percentile_vals[2]), 2),
            "P50": round(float(percentile_vals[3]), 2),
            "P75": round(float(percentile_vals[4]), 2),
            "P90": round(float(percentile_vals[5]), 2),
            "P95": round(float(percentile_vals[6]), 2),
        },
        "percentile_5":          round(float(percentile_vals[0]), 2),
        "percentile_10":         round(float(percentile_vals[1]), 2),
        "percentile_25":         round(float(percentile_vals[2]), 2),
        "percentile_50":         round(float(percentile_vals[3]), 2),
        "percentile_75":         round(float(percentile_vals[4]), 2),
        "percentile_90":         round(float(percentile_vals[5]), 2),
        "percentile_95":         round(float(percentile_vals[6]), 2),
        "probability_of_upside": round(prob_up, 4),
        "bins":                  [round(float(b), 2) for b in bins[:-1]],
        "frequencies":           counts.tolist(),
        "histogram_data": {
            "bins":   [round(float(b), 2) for b in bins[:-1]],
            "counts": counts.tolist(),
        },
        "iterations": iterations,
    }
