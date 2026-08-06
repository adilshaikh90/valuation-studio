import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional

def calculate_trading_comps(ticker: str, data_fetcher, custom_peers: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Calculate Trading Comps.
    """
    info = data_fetcher.get_info(ticker)
    
    peers = custom_peers if custom_peers else ['AAPL', 'MSFT', 'GOOGL']
    
    target_metrics = {
        'ev_ebitda': info.get('enterpriseToEbitda', 15),
        'p_e': info.get('trailingPE', 20),
        'ebitda': 1000,
        'net_income': 500
    }
    
    peer_data = []
    ev_ebitda_list = []
    pe_list = []
    
    for peer in peers:
        peer_info = data_fetcher.get_info(peer)
        ev_ebitda = peer_info.get('enterpriseToEbitda', 15)
        pe = peer_info.get('trailingPE', 20)
        ev_ebitda_list.append(ev_ebitda)
        pe_list.append(pe)
        peer_data.append({'ticker': peer, 'ev_ebitda': ev_ebitda, 'p_e': pe})
        
    peer_stats = {
        'ev_ebitda': {
            'mean': np.mean(ev_ebitda_list),
            'median': np.median(ev_ebitda_list),
            'p25': np.percentile(ev_ebitda_list, 25),
            'p75': np.percentile(ev_ebitda_list, 75)
        },
        'p_e': {
            'mean': np.mean(pe_list),
            'median': np.median(pe_list),
            'p25': np.percentile(pe_list, 25),
            'p75': np.percentile(pe_list, 75)
        }
    }
    
    implied_ev = peer_stats['ev_ebitda']['median'] * target_metrics['ebitda']
    net_debt = 500
    implied_equity = implied_ev - net_debt
    shares = info.get('impliedSharesOutstanding', 100)
    
    implied_price_ev_ebitda = implied_equity / shares if shares else 0
    implied_price_pe = peer_stats['p_e']['median'] * target_metrics['net_income'] / shares if shares else 0
    
    return {
        'target_metrics': target_metrics,
        'peer_data': peer_data,
        'peer_stats': peer_stats,
        'implied_values': {
            'ev_ebitda': implied_price_ev_ebitda,
            'p_e': implied_price_pe
        },
        'premium_discount': {},
        'currency': info.get('currency', 'USD')
    }
