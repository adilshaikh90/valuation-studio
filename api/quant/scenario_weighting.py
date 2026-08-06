from api.quant.tornado import calculate_scenarios

def calculate_weighted_scenarios(ticker: str, data_fetcher, custom_scenarios=None) -> dict:
    """
    Calculates probability-weighted scenarios for a ticker.
    """
    base_scenarios_data = calculate_scenarios(ticker, data_fetcher)
    currency = base_scenarios_data["currency"]
    current_price = base_scenarios_data["current_price"]
    
    if custom_scenarios is not None and len(custom_scenarios) > 0:
        scenarios = custom_scenarios
    else:
        # Default probabilities: Bear=25%, Base=50%, Bull=25%
        scenarios = []
        default_probs = {"Bear": 0.25, "Base": 0.50, "Bull": 0.25}
        for sc in base_scenarios_data["scenarios"]:
            name = sc["scenario_name"]
            prob = default_probs.get(name, 0.0)
            scenarios.append({
                "scenario_name": name,
                "probability": prob,
                "assumptions": sc["assumptions"],
                "implied_price": sc["implied_price"]
            })
            
    # Validate sum of probabilities is close to 1.0
    total_prob = sum(s["probability"] for s in scenarios)
    if not (0.99 <= total_prob <= 1.01):
        # Normalize
        for s in scenarios:
            s["probability"] /= total_prob
            
    weighted_value = sum(s["implied_price"] * s["probability"] for s in scenarios)
    upside_pct = (weighted_value / current_price - 1.0) if current_price > 0 else 0.0
    
    return {
        "ticker": ticker,
        "currency": currency,
        "current_price": current_price,
        "scenarios": scenarios,
        "weighted_value": weighted_value,
        "upside_pct": upside_pct
    }
