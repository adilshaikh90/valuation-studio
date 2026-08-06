"""
Football Field — aggregates all valuation models for a side-by-side comparison chart.
Uses P10/P90 from sensitivity tables for DCF ranges, P25/P75 for comps.
"""
from typing import Dict, Any, List, Optional
import statistics


def _range_from_sensitivity(result: dict, key: str = "sensitivity_table") -> tuple:
    """Extract P10/P90 range from a sensitivity matrix."""
    try:
        table = result.get(key, {})
        matrix = table.get("matrix", [])
        all_vals = [v for row in matrix for v in row if v is not None and v > 0]
        if len(all_vals) >= 3:
            all_vals_sorted = sorted(all_vals)
            n = len(all_vals_sorted)
            p10 = all_vals_sorted[int(n * 0.10)]
            p90 = all_vals_sorted[int(n * 0.90)]
            return (p10, p90)
    except Exception:
        pass
    return None, None


def calculate_football_field(
    ticker: str,
    data_fetcher,
    custom_peers: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Run all valuation models and aggregate results.
    Returns a list of {method, low, high, mid, description} for the chart.
    """
    from api.valuation.dcf_fcff import calculate_dcf_fcff
    from api.valuation.dcf_fcfe import calculate_dcf_fcfe
    from api.valuation.ddm import calculate_ddm
    from api.valuation.apv import calculate_apv
    from api.valuation.trading_comps import calculate_trading_comps
    from api.valuation.nav import calculate_nav
    from api.valuation.lbo import calculate_lbo

    info          = data_fetcher.get_info(ticker)
    current_price = info.get("current_price") or info.get("currentPrice") or 0.0
    currency      = info.get("currency", "USD")
    currency_sym  = data_fetcher.get_currency_symbol(currency)

    results = []

    # ── DCF FCFF ─────────────────────────────────────────────────────────────
    try:
        fcff = calculate_dcf_fcff(ticker, data_fetcher)
        mid  = fcff.get("intrinsic_value_per_share", 0)
        # Use sensitivity table for P10/P90 range
        low, high = _range_from_sensitivity(fcff)
        if low is None or low <= 0:
            low  = mid * 0.85
            high = mid * 1.15
        if mid <= 0:
            mid = (low + high) / 2
        results.append({
            "method":      "DCF (FCFF)",
            "low":         round(low, 2),
            "high":        round(high, 2),
            "mid":         round(mid, 2),
            "description": "P10-P90 sensitivity range",
        })
    except Exception as e:
        pass

    # ── DCF FCFE ─────────────────────────────────────────────────────────────
    try:
        fcfe = calculate_dcf_fcfe(ticker, data_fetcher)
        mid  = fcfe.get("intrinsic_value_per_share", 0)
        if mid > 0:
            results.append({
                "method":      "DCF (FCFE)",
                "low":         round(mid * 0.85, 2),
                "high":        round(mid * 1.15, 2),
                "mid":         round(mid, 2),
                "description": "Levered free cash flow",
            })
    except Exception:
        pass

    # ── DDM ───────────────────────────────────────────────────────────────────
    try:
        ddm = calculate_ddm(ticker, data_fetcher)
        if ddm.get("applicable"):
            vals = [v for v in [
                ddm.get("gordon_growth_value"),
                ddm.get("two_stage_value"),
                ddm.get("h_model_value"),
            ] if v is not None and v > 0]
            if vals:
                low  = round(min(vals), 2)
                high = round(max(vals), 2)
                mid  = round(statistics.mean(vals), 2)
                results.append({
                    "method":      "DDM",
                    "low":         low,
                    "high":        high,
                    "mid":         mid,
                    "description": "Gordon / Two-Stage / H-Model",
                })
    except Exception:
        pass

    # ── APV ───────────────────────────────────────────────────────────────────
    try:
        apv = calculate_apv(ticker, data_fetcher)
        mid = apv.get("intrinsic_value_per_share", 0)
        if mid > 0:
            results.append({
                "method":      "APV",
                "low":         round(mid * 0.88, 2),
                "high":        round(mid * 1.12, 2),
                "mid":         round(mid, 2),
                "description": "Adjusted Present Value",
            })
    except Exception:
        pass

    # ── Trading Comps ─────────────────────────────────────────────────────────
    try:
        comps = calculate_trading_comps(ticker, data_fetcher, custom_peers)
        implied = comps.get("implied_values", {})
        comp_vals = [v for v in implied.values() if v is not None and isinstance(v, (int, float)) and v > 0]
        if comp_vals:
            low  = round(min(comp_vals), 2)
            high = round(max(comp_vals), 2)
            mid  = round(statistics.median(comp_vals), 2)
            results.append({
                "method":      "Trading Comps",
                "low":         low,
                "high":        high,
                "mid":         mid,
                "description": "P25–P75 implied from peer multiples",
            })
    except Exception:
        pass

    # ── NAV ───────────────────────────────────────────────────────────────────
    try:
        nav = calculate_nav(ticker, data_fetcher)
        nav_ps      = nav.get("nav_per_share", 0)
        tangible_ps = nav.get("tangible_nav_per_share", 0)
        if nav_ps > 0:
            low  = round(min(nav_ps, tangible_ps) if tangible_ps > 0 else nav_ps * 0.9, 2)
            high = round(nav_ps, 2)
            mid  = round((low + high) / 2, 2)
            results.append({
                "method":      "NAV",
                "low":         low,
                "high":        high,
                "mid":         mid,
                "description": "Book value per share",
            })
    except Exception:
        pass

    # ── LBO Floor ─────────────────────────────────────────────────────────────
    try:
        lbo = calculate_lbo(ticker, data_fetcher)
        floor = lbo.get("lbo_floor_price", 0)
        if floor > 0:
            results.append({
                "method":      "LBO Floor",
                "low":         round(floor * 0.90, 2),
                "high":        round(floor * 1.10, 2),
                "mid":         round(floor, 2),
                "description": "Max entry for 20% IRR",
            })
    except Exception:
        pass

    return {
        "ticker":        ticker,
        "current_price": current_price,
        "currency":      currency,
        "currency_symbol": currency_sym,
        "methods":       results,
    }
