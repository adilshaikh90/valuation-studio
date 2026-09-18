import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional

# Default peer mapping by sector/industry if none dynamically detected
DEFAULT_SECTOR_PEERS = {
    'Technology': ['MSFT', 'GOOGL', 'META', 'NVDA', 'ORCL', 'CSCO'],
    'Consumer Electronics': ['MSFT', 'GOOGL', 'DELL', 'HPQ', 'SONY'],
    'Financial Services': ['JPM', 'BAC', 'WFC', 'MS', 'GS', 'C'],
    'Healthcare': ['JNJ', 'UNH', 'PFE', 'ABT', 'MRK', 'LLY'],
    'Consumer Cyclical': ['AMZN', 'TSLA', 'HD', 'MCD', 'NKE', 'SBUX'],
    'Communication Services': ['GOOGL', 'META', 'DIS', 'NFLX', 'CMCSA', 'TMUS'],
    'Industrial': ['CAT', 'BA', 'HON', 'GE', 'UNP', 'LMT'],
    'Energy': ['XOM', 'CVX', 'COP', 'SLB', 'EOG', 'OXY'],
}

def calculate_trading_comps(ticker: str, data_fetcher, custom_peers: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Institutional Comparable Company Analysis (Trading Comps).
    Fetches real market multiples, margins, and growth metrics for peer companies.
    """
    ticker = ticker.upper()
    info = data_fetcher.get_info(ticker)
    
    # 1. Determine Peer Universe
    peers = []
    if custom_peers and len(custom_peers) > 0:
        peers = [p.strip().upper() for p in custom_peers if p.strip().upper() != ticker]
    
    if not peers:
        # Try data fetcher get_peers
        try:
            fetched_peers = data_fetcher.get_peers(ticker)
            if fetched_peers:
                peers = [p for p in fetched_peers if p != ticker]
        except Exception:
            peers = []
            
    if not peers:
        # Fallback to sector/industry peers
        sector = info.get('sector', 'Technology')
        peers = DEFAULT_SECTOR_PEERS.get(sector, ['MSFT', 'GOOGL', 'META', 'NVDA'])
        peers = [p for p in peers if p != ticker][:6]

    # Target company metrics
    target_price = float(info.get('current_price', 0) or info.get('currentPrice', 0) or 0)
    target_shares = float(info.get('shares_outstanding', 0) or info.get('sharesOutstanding', 1) or 1)
    target_market_cap = float(info.get('market_cap', 0) or info.get('marketCap', 0) or (target_price * target_shares))
    
    # Real balance sheet & income statement items for target
    target_ebitda = 0.0
    target_net_income = 0.0
    target_revenue = 0.0
    target_ebit = 0.0
    target_book_value = 0.0
    target_net_debt = 0.0

    try:
        inc_df = data_fetcher.get_income_stmt(ticker)
        if inc_df is not None and not inc_df.empty:
            for row_name in ['EBITDA', 'Normalized EBITDA']:
                if row_name in inc_df.index:
                    vals = inc_df.loc[row_name].dropna().values
                    if len(vals) > 0 and vals[0]: target_ebitda = float(vals[0])
                    break
            for row_name in ['Operating Income', 'EBIT']:
                if row_name in inc_df.index:
                    vals = inc_df.loc[row_name].dropna().values
                    if len(vals) > 0 and vals[0]: target_ebit = float(vals[0])
                    break
            for row_name in ['Total Revenue', 'Operating Revenue']:
                if row_name in inc_df.index:
                    vals = inc_df.loc[row_name].dropna().values
                    if len(vals) > 0 and vals[0]: target_revenue = float(vals[0])
                    break
            for row_name in ['Net Income', 'Net Income Common Stockholders']:
                if row_name in inc_df.index:
                    vals = inc_df.loc[row_name].dropna().values
                    if len(vals) > 0 and vals[0]: target_net_income = float(vals[0])
                    break

        bs_df = data_fetcher.get_balance_sheet(ticker)
        if bs_df is not None and not bs_df.empty:
            cash = 0.0
            debt = 0.0
            equity = 0.0
            for row_name in ['Cash And Cash Equivalents', 'Cash Cash Equivalents And Short Term Investments']:
                if row_name in bs_df.index:
                    vals = bs_df.loc[row_name].dropna().values
                    if len(vals) > 0 and vals[0]: cash = float(vals[0])
                    break
            for row_name in ['Total Debt', 'Long Term Debt And Capital Lease Obligation']:
                if row_name in bs_df.index:
                    vals = bs_df.loc[row_name].dropna().values
                    if len(vals) > 0 and vals[0]: debt = float(vals[0])
                    break
            for row_name in ['Common Stock Equity', 'Stockholders Equity']:
                if row_name in bs_df.index:
                    vals = bs_df.loc[row_name].dropna().values
                    if len(vals) > 0 and vals[0]: equity = float(vals[0])
                    break
            target_net_debt = debt - cash
            target_book_value = equity
    except Exception:
        pass

    # Fallbacks from raw info dict
    raw_target = data_fetcher.get_raw_info(ticker) if hasattr(data_fetcher, 'get_raw_info') else {}
    if target_ebitda <= 0:
        target_ebitda = float(raw_target.get('ebitda', 0) or 0)
    if target_net_income <= 0:
        target_net_income = float(raw_target.get('netIncomeToCommon', 0) or (target_price / float(raw_target.get('trailingPE', 25) or 25) * target_shares))
    if target_revenue <= 0:
        target_revenue = float(raw_target.get('totalRevenue', 0) or 0)
    if target_ebit <= 0:
        target_ebit = target_ebitda * 0.85 if target_ebitda > 0 else 0

    target_ev = target_market_cap + target_net_debt

    target_ev_ebitda = float(raw_target.get('enterpriseToEbitda', 0) or 0)
    if target_ev_ebitda <= 0 and target_ebitda > 0:
        target_ev_ebitda = target_ev / target_ebitda

    target_pe = float(info.get('pe_ratio', 0) or raw_target.get('trailingPE', 0) or 0)
    target_pb = float(raw_target.get('priceToBook', 0) or (target_market_cap / target_book_value if target_book_value > 0 else 0))
    target_ev_rev = float(raw_target.get('enterpriseToRevenue', 0) or (target_ev / target_revenue if target_revenue > 0 else 0))
    target_rev_growth = float(raw_target.get('revenueGrowth', 0) or 0)
    target_ebitda_margin = float(raw_target.get('ebitdaMargins', 0) or (target_ebitda / target_revenue if target_revenue > 0 else 0))

    target_metrics = {
        'ticker': ticker,
        'company_name': info.get('name', ticker),
        'market_cap': target_market_cap,
        'ev': target_ev,
        'ev_ebitda': round(target_ev_ebitda, 2) if target_ev_ebitda > 0 else None,
        'ev_ebit': round(target_ev / target_ebit, 2) if target_ebit > 0 else None,
        'p_e': round(target_pe, 2) if target_pe > 0 else None,
        'p_b': round(target_pb, 2) if target_pb > 0 else None,
        'ev_revenue': round(target_ev_rev, 2) if target_ev_rev > 0 else None,
        'rev_growth': round(target_rev_growth, 3),
        'ebitda_margin': round(target_ebitda_margin, 3),
        'ebitda': target_ebitda,
        'net_income': target_net_income,
        'revenue': target_revenue,
        'book_value': target_book_value,
        'net_debt': target_net_debt,
        'shares': target_shares
    }

    # 2. Extract metrics for each peer
    peer_data = []
    ev_ebitda_list = []
    ev_ebit_list = []
    pe_list = []
    pb_list = []
    ev_rev_list = []
    rev_growth_list = []
    ebitda_margin_list = []

    for p_sym in peers:
        try:
            p_info = data_fetcher.get_info(p_sym)
            p_raw = data_fetcher.get_raw_info(p_sym) if hasattr(data_fetcher, 'get_raw_info') else {}

            p_price = float(p_info.get('current_price', 0) or p_raw.get('currentPrice', 0) or 0)
            p_shares = float(p_info.get('shares_outstanding', 0) or p_raw.get('sharesOutstanding', 1) or 1)
            p_mcap = float(p_info.get('market_cap', 0) or p_raw.get('marketCap', 0) or (p_price * p_shares))
            
            p_pe = float(p_info.get('pe_ratio', 0) or p_raw.get('trailingPE', 0) or p_raw.get('forwardPE', 0) or 0)
            p_ev_ebitda = float(p_raw.get('enterpriseToEbitda', 0) or 0)
            p_ev_rev = float(p_raw.get('enterpriseToRevenue', 0) or 0)
            p_pb = float(p_raw.get('priceToBook', 0) or 0)
            p_rev_growth = float(p_raw.get('revenueGrowth', 0) or 0)
            p_ebitda_margin = float(p_raw.get('ebitdaMargins', 0) or 0)
            
            # Estimations if direct ratios missing
            if p_ev_ebitda <= 0 and p_pe > 0:
                p_ev_ebitda = round(p_pe * 0.75, 2)
            p_ev_ebit = round(p_ev_ebitda * 1.15, 2) if p_ev_ebitda > 0 else None

            p_dict = {
                'ticker': p_sym,
                'company_name': p_info.get('name') or p_raw.get('shortName', p_sym),
                'market_cap': p_mcap,
                'ev_ebitda': round(p_ev_ebitda, 2) if p_ev_ebitda > 0 else None,
                'ev_ebit': p_ev_ebit,
                'p_e': round(p_pe, 2) if p_pe > 0 else None,
                'p_b': round(p_pb, 2) if p_pb > 0 else None,
                'ev_rev': round(p_ev_rev, 2) if p_ev_rev > 0 else None,
                'ev_revenue': round(p_ev_rev, 2) if p_ev_rev > 0 else None,
                'rev_growth': round(p_rev_growth, 3),
                'ebitda_margin': round(p_ebitda_margin, 3)
            }


            peer_data.append(p_dict)

            if p_dict['ev_ebitda']: ev_ebitda_list.append(p_dict['ev_ebitda'])
            if p_dict['ev_ebit']: ev_ebit_list.append(p_dict['ev_ebit'])
            if p_dict['p_e']: pe_list.append(p_dict['p_e'])
            if p_dict['p_b']: pb_list.append(p_dict['p_b'])
            if p_dict['ev_rev']: ev_rev_list.append(p_dict['ev_rev'])
            if p_dict['rev_growth']: rev_growth_list.append(p_dict['rev_growth'])
            if p_dict['ebitda_margin']: ebitda_margin_list.append(p_dict['ebitda_margin'])
        except Exception:
            continue

    def _calc_stats(arr):
        if not arr:
            return {'mean': None, 'median': None, 'p25': None, 'p75': None}
        return {
            'mean': round(float(np.mean(arr)), 2),
            'median': round(float(np.median(arr)), 2),
            'p25': round(float(np.percentile(arr, 25)), 2),
            'p75': round(float(np.percentile(arr, 75)), 2)
        }

    peer_stats = {
        'ev_ebitda': _calc_stats(ev_ebitda_list),
        'ev_ebit': _calc_stats(ev_ebit_list),
        'p_e': _calc_stats(pe_list),
        'p_b': _calc_stats(pb_list),
        'ev_revenue': _calc_stats(ev_rev_list),
        'rev_growth': _calc_stats(rev_growth_list),
        'ebitda_margin': _calc_stats(ebitda_margin_list)
    }

    # 3. Calculate implied equity value per share
    implied_values = {}

    scale = data_fetcher.get_price_scale_to_financials(ticker) if hasattr(data_fetcher, 'get_price_scale_to_financials') else 1.0

    # EV / EBITDA
    if peer_stats['ev_ebitda']['median'] and target_metrics['ebitda'] > 0:
        imp_ev = peer_stats['ev_ebitda']['median'] * target_metrics['ebitda']
        imp_eq = max(0, imp_ev - target_metrics['net_debt'])
        implied_values['ev_ebitda'] = round((imp_eq / target_shares) * scale, 2)

    # EV / EBIT
    if peer_stats['ev_ebit']['median'] and target_metrics['ev_ebit'] and target_ebit > 0:
        imp_ev = peer_stats['ev_ebit']['median'] * target_ebit
        imp_eq = max(0, imp_ev - target_metrics['net_debt'])
        implied_values['ev_ebit'] = round((imp_eq / target_shares) * scale, 2)

    # P / E
    if peer_stats['p_e']['median'] and target_metrics['net_income'] > 0:
        imp_eq = peer_stats['p_e']['median'] * target_metrics['net_income']
        implied_values['p_e'] = round((imp_eq / target_shares) * scale, 2)

    # P / B
    if peer_stats['p_b']['median'] and target_metrics['book_value'] > 0:
        imp_eq = peer_stats['p_b']['median'] * target_metrics['book_value']
        implied_values['p_b'] = round((imp_eq / target_shares) * scale, 2)

    # EV / Revenue
    if peer_stats['ev_revenue']['median'] and target_metrics['revenue'] > 0:
        imp_ev = peer_stats['ev_revenue']['median'] * target_metrics['revenue']
        imp_eq = max(0, imp_ev - target_metrics['net_debt'])
        implied_values['ev_revenue'] = round((imp_eq / target_shares) * scale, 2)

    # Regression multiple analysis (Growth vs EV/EBITDA or P/E)
    regression_results = {}
    if len(peer_data) >= 3:
        valid_points = [
            {'growth': p['rev_growth'], 'multiple': p['ev_ebitda']}
            for p in peer_data if p['rev_growth'] is not None and p['ev_ebitda'] is not None
        ]
        if len(valid_points) >= 3:
            regression_results['ev_ebitda'] = {
                'peers_data': valid_points,
                'target': {
                    'growth': target_metrics['rev_growth'],
                    'multiple': target_metrics['ev_ebitda']
                }
            }

    return {
        'target_metrics': target_metrics,
        'peer_data': peer_data,
        'peer_stats': peer_stats,
        'implied_values': implied_values,
        'regression_results': regression_results,
        'premium_discount': {},
        'currency': info.get('currency', 'USD')
    }
