import numpy as np

def calculate_regression_multiples(ticker: str, data_fetcher, custom_peers=None) -> dict:
    """
    Calculates regression-implied multiples (EV/EBITDA, EV/EBIT, P/E)
    based on peer fundamentals using multivariate OLS.
    """
    info = data_fetcher.get_info(ticker)
    currency = info.get("currency", "USD")
    current_price = info.get("currentPrice", info.get("regularMarketPrice", 0.0))
    shares_out = info.get("sharesOutstanding", 0)
    net_debt = info.get("totalDebt", 0) - info.get("totalCash", 0)
    
    # Mocking peer universe (in real app, use data_fetcher.get_peers())
    peers = custom_peers if custom_peers else ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "INTC", "AMD", "CSCO"]
    if ticker in peers:
        peers.remove(ticker)
        
    peer_data_used = []
    
    # Generate mock fundamental data for peers to simulate OLS 
    # Real implementation would call data_fetcher for each peer
    np.random.seed(42) 
    for p in peers:
        peer_data_used.append({
            "ticker": p,
            "ev_ebitda": np.random.uniform(8, 25),
            "ev_ebit": np.random.uniform(10, 30),
            "pe": np.random.uniform(15, 40),
            "growth": np.random.uniform(0.02, 0.25),
            "margin": np.random.uniform(0.10, 0.40),
            "roic": np.random.uniform(0.05, 0.25),
            "log_mc": np.random.uniform(23, 28)
        })
        
    # Target company fundamentals (mocked)
    target_data = {
        "growth": 0.10,
        "margin": 0.20,
        "roic": 0.15,
        "log_mc": 25.0
    }
    
    metrics = ["ev_ebitda", "ev_ebit", "pe"]
    results = {}
    scatter_data = {}
    
    for metric in metrics:
        y = np.array([p[metric] for p in peer_data_used])
        x1 = np.array([p["growth"] for p in peer_data_used])
        x2 = np.array([p["margin"] for p in peer_data_used])
        x3 = np.array([p["roic"] for p in peer_data_used])
        x4 = np.array([p["log_mc"] for p in peer_data_used])
        
        # OLS regression: Y = b0 + b1*x1 + b2*x2 + b3*x3 + b4*x4
        X = np.column_stack([np.ones(len(peers)), x1, x2, x3, x4])
        
        try:
            coeffs, residuals_ss, rank, s = np.linalg.lstsq(X, y, rcond=None)
            
            # R-squared
            ss_tot = np.sum((y - np.mean(y))**2)
            ss_res = residuals_ss[0] if len(residuals_ss) > 0 else np.sum((y - X.dot(coeffs))**2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            
            # Predict
            pred = coeffs[0] + coeffs[1]*target_data["growth"] + coeffs[2]*target_data["margin"] + coeffs[3]*target_data["roic"] + coeffs[4]*target_data["log_mc"]
            actual = 15.0 # Mock actual
            residual = actual - pred
            
            # Implied price
            if metric.startswith("ev"):
                # implied EV = pred * EBITDA or EBIT
                ebitda = 1000.0 # Mock metric value
                implied_ev = pred * ebitda
                implied_price = max(0, (implied_ev - net_debt) / max(1, shares_out))
            else:
                # P/E
                eps = 5.0 # Mock EPS
                implied_price = pred * eps
                
            results[metric] = {
                "metric": metric,
                "r_squared": float(r_squared),
                "coefficients": coeffs.tolist(),
                "predicted_multiple": float(pred),
                "actual_multiple": actual,
                "residual": float(residual),
                "implied_price": implied_price,
                "flag": "Weak explanatory power" if r_squared < 0.1 else "OK"
            }
            
            # Scatter data
            sc_data = []
            pred_peers = X.dot(coeffs)
            for i, p in enumerate(peers):
                sc_data.append({
                    "ticker": p,
                    "actual_multiple": float(y[i]),
                    "predicted_multiple": float(pred_peers[i])
                })
            scatter_data[metric] = sc_data
            
        except np.linalg.LinAlgError:
            results[metric] = {"error": "Regression failed"}

    return {
        "ticker": ticker,
        "currency": currency,
        "regression_results": results,
        "scatter_data": scatter_data,
        "peer_data_used": peer_data_used
    }
