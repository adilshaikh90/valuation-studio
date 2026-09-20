"""
Sensitivity - 2D sensitivity tables: WACC vs Terminal Growth, WACC vs Exit Multiple.
Uses real WACC, FCF, and net debt from financial statements.
"""
import numpy as np
import pandas as pd
from typing import Optional


def calculate_sensitivity(
    ticker: str,
    data_fetcher,
    base_wacc: Optional[float] = None,
    base_terminal_growth: float = 0.025,
    base_exit_multiple: Optional[float] = None,
) -> dict:
    """
    Sensitivity matrices for WACC vs Terminal Growth Rate and WACC vs Exit Multiple.
    """
    info          = data_fetcher.get_info(ticker)
    currency      = info.get("currency", "USD")
    currency_sym  = data_fetcher.get_currency_symbol(currency)
    current_price = info.get("current_price") or info.get("currentPrice") or 0.0
    shares_out    = info.get("shares_outstanding") or info.get("sharesOutstanding") or 0

    # ── Real WACC ────────────────────────────────────────────────────────────
    if base_wacc is None:
        try:
            from api.valuation.wacc_builder import calculate_wacc
            wacc_data = calculate_wacc(ticker, data_fetcher)
            base_wacc = wacc_data.get("wacc", 0.09)
        except Exception:
            base_wacc = 0.09
    base_wacc = max(min(float(base_wacc), 0.25), 0.04)

    if base_exit_multiple is None:
        base_exit_multiple = float(info.get("enterpriseToEbitda") or 10.0)

    # ── Net debt from balance sheet ───────────────────────────────────────────
    bs_df = data_fetcher.get_balance_sheet(ticker)

    def _sg(df, names, default=0.0):
        for n in names:
            if n in df.index:
                try:
                    v = df.loc[n].iloc[0]
                    if pd.notna(v):
                        return abs(float(v))
                except Exception:
                    pass
        return default

    cash    = _sg(bs_df, ['Cash And Cash Equivalents', 'CashAndCashEquivalents', 'Cash'])
    lt_debt = _sg(bs_df, ['Long Term Debt', 'LongTermDebt'])
    st_debt = _sg(bs_df, ['Current Debt', 'Short Long Term Debt', 'Current Portion Of Long Term Debt'])
    net_debt = (lt_debt + st_debt) - cash

    # ── Real FCF base ─────────────────────────────────────────────────────────
    last_fcf = 0.0
    try:
        cf_df = data_fetcher.get_cashflow(ticker)
        for row_name in ['Free Cash Flow', 'FreeCashFlow']:
            if row_name in cf_df.index:
                vals = cf_df.loc[row_name].dropna().values
                if len(vals) > 0:
                    last_fcf = float(vals[0])  # most recent
                    break
        if last_fcf <= 0:
            # Compute: Operating CF − CapEx
            ocf = _sg(cf_df, ['Operating Cash Flow', 'Cash From Operations', 'Total Cash From Operating Activities'])
            cap = _sg(cf_df, ['Capital Expenditure', 'CapitalExpenditure', 'Purchase Of Property Plant And Equipment'])
            last_fcf = ocf - cap
    except Exception:
        pass

    if last_fcf <= 0:
        market_cap = info.get("market_cap") or 0
        last_fcf = market_cap * 0.03 if market_cap > 0 else 1e9

    # ── Projection ───────────────────────────────────────────────────────────
    projection_years = 5
    fcf_growth  = 0.05
    projected_fcf = [last_fcf * ((1 + fcf_growth) ** i) for i in range(1, projection_years + 1)]
    last_year_fcf   = projected_fcf[-1]
    last_year_ebitda = last_year_fcf * 1.3

    # ── Step arrays ──────────────────────────────────────────────────────────
    wacc_steps = [base_wacc + i * 0.005 for i in range(-4, 5)]           # 9 values ±2%
    tg_steps   = [base_terminal_growth + i * 0.005 for i in range(-3, 4)] # 7 values ±1.5%
    em_steps   = [max(1.0, base_exit_multiple + i) for i in range(-3, 4)] # 7 values ±3x

    def calculate_price(w, tg=None, em=None):
        if shares_out <= 0:
            return 0.0
        w = max(0.015, w)
        dfs = [(1 + w) ** i for i in range(1, projection_years + 1)]
        pv_fcf = sum(f / d for f, d in zip(projected_fcf, dfs))
        if tg is not None:
            tg = min(w - 0.001, tg)
            tv = last_year_fcf * (1 + tg) / (w - tg)
        else:
            tv = last_year_ebitda * em
        pv_tv = tv / ((1 + w) ** projection_years)
        ev = pv_fcf + pv_tv
        eq = ev - net_debt
        return round(max(0.0, eq / shares_out), 2)

    grid1 = [[calculate_price(w, tg=tg) for tg in tg_steps] for w in wacc_steps]
    grid2 = [[calculate_price(w, em=em) for em in em_steps] for w in wacc_steps]

    return {
        "ticker":         ticker,
        "currency":       currency,
        "currency_symbol": currency_sym,
        "current_price":  current_price,
        "base_value":     calculate_price(base_wacc, tg=base_terminal_growth),
        "wacc_vs_tg": {
            "matrix":     grid1,
            "row_labels": [round(w, 4) for w in wacc_steps],
            "col_labels": [round(tg, 4) for tg in tg_steps],
            "row_axis":   "WACC",
            "col_axis":   "Terminal Growth Rate",
        },
        "wacc_vs_em": {
            "matrix":     grid2,
            "row_labels": [round(w, 4) for w in wacc_steps],
            "col_labels": [round(em, 1) for em in em_steps],
            "row_axis":   "WACC",
            "col_axis":   "Exit Multiple (EV/EBITDA)",
        },
    }
