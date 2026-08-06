"""
Generates a plain English summary of valuation results.
"""


def generate_summary(ticker: str, data_fetcher, football_field_data: dict, monte_carlo_data: dict = None) -> dict:
    """
    Generates a jargon-free summary text of the valuation results.
    Uses get_info() (alias for get_company_info) which returns a dict.
    """
    info = data_fetcher.get_info(ticker)
    company_name = info.get("name", info.get("shortName", ticker))
    currency = info.get("currency", "USD")
    current_price = info.get("current_price", info.get("currentPrice", 0.0)) or 0.0

    strengths = []
    risks = []

    # Analyze financial health from info dict
    total_debt = info.get("totalDebt", 0) or 0
    total_equity = info.get("totalStockholderEquity", 1) or 1
    de_ratio = total_debt / total_equity if total_equity != 0 else 0

    if de_ratio > 1.5:
        risks.append("Elevated debt levels increase financial risk.")
    elif de_ratio < 0.5 and de_ratio >= 0:
        strengths.append("The company maintains a conservative balance sheet with low leverage.")

    dividend_yield = info.get("dividend_yield", info.get("dividendYield", 0)) or 0
    if dividend_yield > 0.02:
        strengths.append("The company has a track record of consistent dividend payments.")

    market_cap = info.get("market_cap", 0) or 0
    if market_cap > 100_000_000_000:
        strengths.append("As a large-cap company, it typically offers greater stability and liquidity.")

    beta = info.get("beta", 1.0) or 1.0
    if beta > 1.5:
        risks.append("Higher-than-average stock volatility may lead to larger price swings.")
    elif beta < 0.8:
        strengths.append("Lower volatility compared to the broader market suggests more stable returns.")

    # Analyze cash flows via DataFrame accessor
    try:
        cf_df = data_fetcher.get_cashflow(ticker)
        if cf_df is not None and not cf_df.empty and "Free Cash Flow" in cf_df.index:
            fcf = cf_df.loc["Free Cash Flow"].dropna().values
            if len(fcf) >= 2 and fcf[0] > fcf[1] and fcf[0] > 0:
                strengths.append("The company generates strong and growing free cash flows.")
            elif len(fcf) >= 1 and fcf[0] > 0:
                strengths.append("The company generates positive free cash flows.")
    except Exception:
        pass

    # Generate intro
    summary_text = f"{company_name} ({ticker}) currently trades at {current_price:,.2f} {currency}.\n\n"

    methods = football_field_data.get("methods", [])
    all_mins = []
    all_maxs = []

    # methods is a LIST of dicts: [{method, low, high, mid, description}, ...]
    for item in methods:
        if not isinstance(item, dict):
            continue
        method = item.get("method", "Unknown")
        min_val = item.get("low", 0) or 0
        max_val = item.get("high", 0) or 0
        mid_val = item.get("mid", (min_val + max_val) / 2) or 0
        all_mins.append(min_val)
        all_maxs.append(max_val)

        if method == "DDM" and dividend_yield == 0:
            summary_text += f"Dividend-based valuation is not applicable as {company_name} does not currently pay dividends.\n"
            continue

        if mid_val == 0:
            continue

        diff_pct = ((mid_val - current_price) / current_price) * 100 if current_price > 0 else 0

        if diff_pct > 10:
            summary_text += f"The {method} suggests the stock may be worth approximately {mid_val:,.2f}, indicating it could be undervalued by ~{abs(diff_pct):.0f}% based on historical assumptions.\n"
        elif diff_pct < -10:
            summary_text += f"The {method} suggests the stock may be worth approximately {mid_val:,.2f}, indicating it could be overvalued by ~{abs(diff_pct):.0f}% based on historical assumptions.\n"
        else:
            summary_text += f"The {method} suggests the stock may be worth approximately {mid_val:,.2f}, indicating it is fairly valued.\n"

    if all_mins and all_maxs:
        overall_min = min(m for m in all_mins if m > 0) if any(m > 0 for m in all_mins) else 0
        overall_max = max(all_maxs)
        overall_mid = (overall_min + overall_max) / 2
        summary_text += f"\nAcross all models, the implied value ranges from {overall_min:,.2f} to {overall_max:,.2f}, with a midpoint of {overall_mid:,.2f}.\n"

    if monte_carlo_data:
        prob = monte_carlo_data.get("probability_of_upside", 0) * 100
        summary_text += f"Based on 10,000 simulations, there is a {prob:.1f}% probability the stock is currently undervalued.\n"

    disclaimer = (
        "This analysis is generated automatically for educational and research purposes only. "
        "It does not constitute investment advice. Past performance does not guarantee future results."
    )

    return {
        "summary_text": summary_text,
        "key_metrics": {
            "current_price": current_price,
            "currency": currency,
            "dividend_yield": dividend_yield,
            "debt_to_equity": round(de_ratio, 2),
        },
        "strengths": strengths,
        "risks": risks,
        "disclaimer": disclaimer,
    }
