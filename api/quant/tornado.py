import numpy as np


def _run_simplified_dcf(ticker: str, data_fetcher,
                        wacc: float = 0.08,
                        terminal_growth: float = 0.025,
                        revenue_growth: float = 0.05,
                        ebitda_margin: float = 0.20,
                        capex_ratio: float = 0.05,
                        tax_rate: float = 0.21) -> float:
    """Run a simplified DCF to calculate per-share value given assumptions."""
    info = data_fetcher.get_info(ticker)
    shares_out = info.get("shares_outstanding", info.get("sharesOutstanding", 0)) or 0
    if shares_out <= 0:
        return 0.0

    total_debt = info.get("totalDebt", 0) or 0
    cash = info.get("totalCash", 0) or 0
    net_debt = total_debt - cash

    # Get last revenue from income statement DataFrame
    last_rev = 100.0
    try:
        is_df = data_fetcher.get_income_stmt(ticker)
        if is_df is not None and not is_df.empty and "Total Revenue" in is_df.index:
            rev_hist = is_df.loc["Total Revenue"].dropna().values
            if len(rev_hist) > 0 and rev_hist[0] > 0:
                last_rev = float(rev_hist[0])
    except Exception:
        pass

    projection_years = 5
    projected_rev = [last_rev * ((1 + revenue_growth) ** i) for i in range(1, projection_years + 1)]
    projected_ebitda = [r * ebitda_margin for r in projected_rev]
    projected_fcf = [e * (1 - tax_rate) - (r * capex_ratio) for e, r in zip(projected_ebitda, projected_rev)]

    wacc = max(0.01, wacc)
    discount_factors = [(1 + wacc) ** i for i in range(1, projection_years + 1)]
    pv_fcf = sum(f / d for f, d in zip(projected_fcf, discount_factors))

    tg = min(wacc - 0.001, terminal_growth)
    tv = projected_fcf[-1] * (1 + tg) / (wacc - tg)
    pv_tv = tv / ((1 + wacc) ** projection_years)

    ev = pv_fcf + pv_tv
    eq = ev - net_debt
    return max(0.0, eq / shares_out)


def calculate_tornado(ticker: str, data_fetcher) -> dict:
    """
    Calculates single-variable sensitivity (tornado chart data) by varying drivers ±1σ.
    """
    info = data_fetcher.get_info(ticker)
    currency = info.get("currency", "USD")
    current_price = info.get("current_price", info.get("currentPrice", info.get("regularMarketPrice", 0.0))) or 0.0

    base_assumptions = {
        "revenue_growth": {"base": 0.05, "std": 0.02},
        "ebitda_margin": {"base": 0.20, "std": 0.02},
        "wacc": {"base": 0.08, "std": 0.01},
        "terminal_growth": {"base": 0.025, "std": 0.005},
        "capex_ratio": {"base": 0.05, "std": 0.01},
        "tax_rate": {"base": 0.21, "std": 0.02},
    }

    base_price = _run_simplified_dcf(
        ticker, data_fetcher,
        wacc=base_assumptions["wacc"]["base"],
        terminal_growth=base_assumptions["terminal_growth"]["base"],
        revenue_growth=base_assumptions["revenue_growth"]["base"],
        ebitda_margin=base_assumptions["ebitda_margin"]["base"],
        capex_ratio=base_assumptions["capex_ratio"]["base"],
        tax_rate=base_assumptions["tax_rate"]["base"],
    )

    results = []
    for driver, params in base_assumptions.items():
        low_val = params["base"] - params["std"]
        high_val = params["base"] + params["std"]

        args_low = {k: v["base"] for k, v in base_assumptions.items()}
        args_high = {k: v["base"] for k, v in base_assumptions.items()}
        args_low[driver] = low_val
        args_high[driver] = high_val

        price_low = _run_simplified_dcf(ticker, data_fetcher, **args_low)
        price_high = _run_simplified_dcf(ticker, data_fetcher, **args_high)

        impact = abs(price_high - price_low)
        results.append({
            "driver_name": driver,
            "base_value": params["base"],
            "low_value": low_val,
            "high_value": high_val,
            "low_price": round(price_low, 2),
            "high_price": round(price_high, 2),
            "impact": round(impact, 2),
        })

    results = sorted(results, key=lambda x: x["impact"], reverse=True)

    return {
        "ticker": ticker,
        "currency": currency,
        "current_price": current_price,
        "base_price": round(base_price, 2),
        "tornado_data": results,
    }


def calculate_scenarios(ticker: str, data_fetcher) -> dict:
    """
    Calculates Bear, Base, and Bull scenarios based on varying all drivers together.
    """
    info = data_fetcher.get_info(ticker)
    currency = info.get("currency", "USD")
    current_price = info.get("current_price", info.get("currentPrice", info.get("regularMarketPrice", 0.0))) or 0.0

    base = {
        "revenue_growth": {"base": 0.05, "std": 0.02},
        "ebitda_margin": {"base": 0.20, "std": 0.02},
        "wacc": {"base": 0.08, "std": 0.01},
        "terminal_growth": {"base": 0.025, "std": 0.005},
        "capex_ratio": {"base": 0.05, "std": 0.01},
        "tax_rate": {"base": 0.21, "std": 0.00},
    }

    def run_scenario(name, std_mult, wacc_adj, tg_adj):
        args = {}
        assumptions = {}
        for k, v in base.items():
            val = v["base"] + (v["std"] * std_mult)
            if k == "wacc":
                val = v["base"] + wacc_adj
            elif k == "terminal_growth":
                val = v["base"] + tg_adj
            args[k] = val
            assumptions[k] = round(val, 4)

        price = _run_simplified_dcf(ticker, data_fetcher, **args)
        return {
            "scenario_name": name,
            "assumptions": assumptions,
            "implied_price": round(price, 2),
        }

    scenarios = [
        run_scenario("Bear", -2, 0.01, -0.005),
        run_scenario("Base", 0, 0.0, 0.0),
        run_scenario("Bull", 2, -0.01, 0.005),
    ]

    return {
        "ticker": ticker,
        "currency": currency,
        "current_price": current_price,
        "scenarios": scenarios,
    }
