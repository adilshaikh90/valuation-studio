import numpy as np
from typing import Dict, Any

def calculate_nav(ticker: str, data_fetcher) -> Dict[str, Any]:
    """
    Net Asset Value model.
    """
    info = data_fetcher.get_info(ticker)
    
    total_assets = info.get('totalAssets', 1000)
    total_liabilities = info.get('totalDebt', 500)
    goodwill = 100
    intangibles = 50
    
    nav = total_assets - total_liabilities
    tangible_nav = nav - goodwill - intangibles
    
    shares = info.get('impliedSharesOutstanding', 100)
    nav_per_share = nav / shares if shares else 0
    tangible_nav_per_share = tangible_nav / shares if shares else 0
    
    current_price = info.get('currentPrice', 10)
    
    return {
        'nav': nav,
        'tangible_nav': tangible_nav,
        'nav_per_share': nav_per_share,
        'tangible_nav_per_share': tangible_nav_per_share,
        'price_to_nav': current_price / nav_per_share if nav_per_share else 0,
        'price_to_tangible_nav': current_price / tangible_nav_per_share if tangible_nav_per_share else 0,
        'currency': info.get('currency', 'USD')
    }
