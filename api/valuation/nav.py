import numpy as np
from typing import Dict, Any

def calculate_nav(ticker: str, data_fetcher) -> Dict[str, Any]:
    """
    Net Asset Value model.
    """
    info = data_fetcher.get_info(ticker)
    
    bs_df = data_fetcher.get_balance_sheet(ticker)
    from api.valuation.dcf_fcff import _safe_get
    
    total_assets = _safe_get(bs_df, ['Total Assets', 'TotalAssets'], default=info.get('totalAssets', 1000))
    total_liabilities = _safe_get(bs_df, ['Total Liabilities Net Minority Interest', 'TotalLiabilitiesNetMinorityInterest', 'Total Debt'], default=info.get('totalDebt', 500))
    goodwill = _safe_get(bs_df, ['Goodwill', 'Goodwill And Other Intangible Assets'], default=0)
    intangibles = _safe_get(bs_df, ['Other Intangible Assets', 'Intangible Assets'], default=0)
    
    nav = total_assets - total_liabilities
    tangible_nav = nav - goodwill - intangibles
    
    shares = info.get('shares_outstanding') or info.get('sharesOutstanding') or 1
    scale = data_fetcher.get_price_scale_to_financials(ticker) if hasattr(data_fetcher, 'get_price_scale_to_financials') else 1.0
    
    nav_per_share = round((nav / shares * scale), 2) if shares else 0
    tangible_nav_per_share = round((tangible_nav / shares * scale), 2) if shares else 0
    
    current_price = info.get('current_price') or info.get('currentPrice', 10)
    
    return {
        'nav': nav,
        'tangible_nav': tangible_nav,
        'nav_per_share': nav_per_share,
        'tangible_nav_per_share': tangible_nav_per_share,
        'price_to_nav': round(current_price / nav_per_share, 2) if nav_per_share else 0,
        'price_to_tangible_nav': round(current_price / tangible_nav_per_share, 2) if tangible_nav_per_share else 0,
        'currency': info.get('currency', 'USD')
    }
