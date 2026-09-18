"""
APV — Adjusted Present Value.
Uses real financial data: FCF from income/cashflow, tax shields from actual interest expense.
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


def calculate_apv(
    ticker: str,
    data_fetcher,
    unlevered_ke: Optional[float] = None,
    terminal_growth: float = 0.025,
    tax_shield_discount: str = "kd",
) -> Dict[str, Any]:
    """
    Adjusted Present Value = Unlevered Firm Value + PV(Tax Shields).
    """
    info            = data_fetcher.get_info(ticker)
    currency        = info.get("currency", "USD")
    currency_symbol = data_fetcher.get_currency_symbol(currency)
    current_price   = info.get("current_price") or info.get("currentPrice") or 0.0
    shares          = info.get("shares_outstanding") or info.get("sharesOutstanding") or 1.0
    market_cap      = info.get("market_cap") or 0

    # ── WACC components for rates ─────────────────────────────────────────────
    try:
        from api.valuation.wacc_builder import calculate_wacc
        wacc_data = calculate_wacc(ticker, data_fetcher)
        rf        = wacc_data.get("risk_free_rate", 0.04)
        erp       = wacc_data.get("equity_risk_premium", 0.055)
        beta_u    = wacc_data.get("beta_unlevered", 0.8)
        kd        = wacc_data.get("cost_of_debt", 0.05)
        tax_rate  = wacc_data.get("tax_rate", 0.21)
    except Exception:
        rf = 0.04; erp = 0.055; beta_u = 0.8; kd = 0.05; tax_rate = 0.21

    # ── Unlevered cost of equity ──────────────────────────────────────────────
    ke_u = unlevered_ke if unlevered_ke else max(rf + beta_u * erp, 0.05)
    ke_u = max(min(ke_u, 0.25), 0.04)

    # ── FCF from real data (reuse DCF FCFF logic) ─────────────────────────────
    try:
        from api.valuation.dcf_fcff import _extract_historical_fcff, _calculate_growth_rates
        hist_fcf    = _extract_historical_fcff(data_fetcher, ticker, sbc_as_cost=True)
        growth_data = _calculate_growth_rates(hist_fcf)
        base_growth = growth_data["cagr_3y"]
        base_fcf    = hist_fcf[-1] if hist_fcf else market_cap * 0.03
    except Exception:
        base_fcf    = market_cap * 0.03 if market_cap > 0 else 1e9
        base_growth = 0.07

    # ── Project 5-year FCF ────────────────────────────────────────────────────
    projection_years = 5
    projected_fcf = []
    fcf = base_fcf
    for year in range(1, projection_years + 1):
        if year <= 2:
            g = base_growth
        else:
            progress = (year - 2) / max(projection_years - 2, 1)
            g = base_growth + (terminal_growth - base_growth) * progress
        fcf = fcf * (1 + max(g, -0.30))
        projected_fcf.append(fcf)

    # ── Unlevered Firm Value: discount FCFF at Ke_unlevered ──────────────────
    if ke_u <= terminal_growth:
        ke_u = terminal_growth + 0.01

    pv_fcf = [fcf / ((1 + ke_u) ** (i + 1)) for i, fcf in enumerate(projected_fcf)]
    tv_u   = (projected_fcf[-1] * (1 + terminal_growth)) / (ke_u - terminal_growth)
    pv_tv  = tv_u / ((1 + ke_u) ** projection_years)
    unlevered_firm_value = sum(pv_fcf) + pv_tv

    # ── PV of Tax Shields: annual Interest × Tax Rate ─────────────────────────
    income_df = data_fetcher.get_income_stmt(ticker)
    bs_df     = data_fetcher.get_balance_sheet(ticker)
    interest_expense = abs(_safe_get(income_df, ['Interest Expense', 'InterestExpense',
                                                   'Interest Expense Non Operating'], 0))
    if interest_expense == 0:
        # Estimate: cost_of_debt × total debt
        lt_d = abs(_safe_get(bs_df, ['Long Term Debt', 'LongTermDebt'], 0))
        interest_expense = kd * lt_d

    annual_tax_shield = interest_expense * tax_rate
    shield_rate = kd if tax_shield_discount == "kd" else rf
    shield_rate = max(shield_rate, 0.01)

    pv_tax_shield = annual_tax_shield / shield_rate if shield_rate > 0 else 0

    # ── Enterprise & Equity Value ─────────────────────────────────────────────
    enterprise_value = unlevered_firm_value + pv_tax_shield
    try:
        from api.valuation.net_debt_bridge import calculate_net_debt_bridge, ev_to_equity
        bridge = calculate_net_debt_bridge(ticker, data_fetcher)
        equity_value = ev_to_equity(enterprise_value, bridge)
        shares_used  = bridge.get("shares_outstanding", shares)
    except Exception:
        cash  = abs(_safe_get(bs_df, ['Cash And Cash Equivalents'], 0))
        lt_d2 = abs(_safe_get(bs_df, ['Long Term Debt'], 0))
        equity_value = enterprise_value - lt_d2 + cash
        shares_used  = shares

    shares_used = max(shares_used, 1)
    scale = data_fetcher.get_price_scale_to_financials(ticker) if hasattr(data_fetcher, 'get_price_scale_to_financials') else 1.0
    value_per_share = (equity_value / shares_used) * scale
    upside_pct = ((value_per_share / current_price) - 1) * 100 if current_price > 0 else 0

    return {
        "intrinsic_value_per_share": round(value_per_share, 2),
        "enterprise_value":          round(enterprise_value, 0),
        "equity_value":              round(equity_value, 0),
        "unlevered_firm_value":      round(unlevered_firm_value, 0),
        "pv_tax_shield":             round(pv_tax_shield, 0),
        "annual_tax_shield":         round(annual_tax_shield, 0),
        "ke_unlevered":              round(ke_u, 4),
        "beta_unlevered":            round(beta_u, 4),
        "tax_shield_discount_rate":  round(shield_rate, 4),
        "current_price":             current_price,
        "upside_downside_pct":       round(upside_pct, 1),
        "currency":                  currency,
        "currency_symbol":           currency_symbol,
    }
