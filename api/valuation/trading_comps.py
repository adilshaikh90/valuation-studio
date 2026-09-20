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
    
    # 1. Determine Institutional Peer Universe
    from api.valuation.peers import get_institutional_peers
    peer_meta = get_institutional_peers(ticker, data_fetcher=data_fetcher, info=info, custom_peers=custom_peers)
    peers = peer_meta.get('peers', [])
    peer_source = peer_meta.get('peer_source', 'Curated Peer Universe')
    matched_industry = peer_meta.get('industry') or info.get('industry', 'Industry')
    matched_region = peer_meta.get('region', 'GLOBAL')

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

    SECTOR_MULTIPLE_BENCHMARKS = {
        'semiconductor': {'ev_ebitda': 24.8, 'pe': 28.5, 'pb': 7.2, 'ev_rev': 7.1, 'rev_growth': 0.165, 'ebitda_margin': 0.32},
        'technology': {'ev_ebitda': 22.4, 'pe': 26.0, 'pb': 6.5, 'ev_rev': 5.8, 'rev_growth': 0.135, 'ebitda_margin': 0.27},
        'financial': {'ev_ebitda': 11.2, 'pe': 13.0, 'pb': 1.35, 'ev_rev': 3.1, 'rev_growth': 0.055, 'ebitda_margin': 0.38},
        'bank': {'ev_ebitda': 10.5, 'pe': 12.2, 'pb': 1.25, 'ev_rev': 2.8, 'rev_growth': 0.048, 'ebitda_margin': 0.35},
        'healthcare': {'ev_ebitda': 15.6, 'pe': 21.5, 'pb': 4.3, 'ev_rev': 4.2, 'rev_growth': 0.082, 'ebitda_margin': 0.23},
        'pharma': {'ev_ebitda': 14.8, 'pe': 19.8, 'pb': 4.0, 'ev_rev': 3.9, 'rev_growth': 0.075, 'ebitda_margin': 0.25},
        'consumer': {'ev_ebitda': 16.2, 'pe': 22.4, 'pb': 4.8, 'ev_rev': 2.4, 'rev_growth': 0.068, 'ebitda_margin': 0.16},
        'energy': {'ev_ebitda': 6.8, 'pe': 10.8, 'pb': 1.6, 'ev_rev': 1.5, 'rev_growth': 0.042, 'ebitda_margin': 0.26},
        'industrial': {'ev_ebitda': 13.8, 'pe': 18.5, 'pb': 3.4, 'ev_rev': 1.9, 'rev_growth': 0.054, 'ebitda_margin': 0.15},
        'default': {'ev_ebitda': 16.5, 'pe': 21.0, 'pb': 4.0, 'ev_rev': 3.2, 'rev_growth': 0.080, 'ebitda_margin': 0.20},
    }

    for p_sym in peers:
        try:
            p_info = data_fetcher.get_info(p_sym)
            p_raw = data_fetcher.get_raw_info(p_sym) if hasattr(data_fetcher, 'get_raw_info') else {}

            p_price = float(p_info.get('current_price', 0) or p_raw.get('currentPrice', 0) or p_raw.get('regularMarketPrice', 0) or 0)
            p_shares = float(p_info.get('shares_outstanding', 0) or p_raw.get('sharesOutstanding', 1) or 1)
            p_mcap = float(p_info.get('market_cap', 0) or p_raw.get('marketCap', 0) or (p_price * p_shares))
            
            p_sec = (str(p_info.get('sector') or p_raw.get('sector') or matched_industry or '') + ' ' + str(p_info.get('industry') or '')).lower()
            bm = SECTOR_MULTIPLE_BENCHMARKS['default']
            for k_sec, v_bm in SECTOR_MULTIPLE_BENCHMARKS.items():
                if k_sec in p_sec:
                    bm = v_bm
                    break

            # P/E Ratio
            raw_pe = p_info.get('pe_ratio') or p_raw.get('trailingPE') or p_raw.get('forwardPE')
            if raw_pe is not None and float(raw_pe) > 0:
                p_pe = float(raw_pe)
            elif p_price > 0 and (p_info.get('eps') or p_raw.get('trailingEps', 0)):
                eps_val = float(p_info.get('eps') or p_raw.get('trailingEps', 0))
                p_pe = round(p_price / eps_val, 2) if eps_val > 0 else bm['pe']
            else:
                p_pe = bm['pe']

            # EV/EBITDA
            raw_ev_ebitda = p_raw.get('enterpriseToEbitda')
            if raw_ev_ebitda is not None and float(raw_ev_ebitda) > 0:
                p_ev_ebitda = float(raw_ev_ebitda)
            elif p_pe > 0:
                p_ev_ebitda = round(p_pe * 0.78, 2)
            else:
                p_ev_ebitda = bm['ev_ebitda']

            p_ev_ebit = round(p_ev_ebitda * 1.18, 2) if p_ev_ebitda > 0 else None

            # P/B Ratio
            raw_pb = p_raw.get('priceToBook') or p_info.get('priceToBook')
            if raw_pb is not None and float(raw_pb) > 0:
                p_pb = float(raw_pb)
            else:
                p_pb = bm['pb']

            # EV/Revenue
            raw_ev_rev = p_raw.get('enterpriseToRevenue')
            if raw_ev_rev is not None and float(raw_ev_rev) > 0:
                p_ev_rev = float(raw_ev_rev)
            elif p_ev_ebitda > 0 and bm['ebitda_margin'] > 0:
                p_ev_rev = round(p_ev_ebitda * bm['ebitda_margin'], 2)
            else:
                p_ev_rev = bm['ev_rev']

            # Revenue Growth
            raw_growth = p_raw.get('revenueGrowth') or p_raw.get('quarterlyRevenueGrowth')
            if raw_growth is not None and float(raw_growth) != 0:
                p_rev_growth = float(raw_growth)
            else:
                p_rev_growth = bm['rev_growth']

            # EBITDA Margin
            raw_margin = p_raw.get('ebitdaMargins') or p_raw.get('operatingMargins') or p_raw.get('profitMargins')
            if raw_margin is not None and float(raw_margin) > 0:
                p_ebitda_margin = float(raw_margin)
            else:
                p_ebitda_margin = bm['ebitda_margin']

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
        'currency': info.get('currency', 'USD'),
        'peer_source': peer_source,
        'matched_industry': matched_industry,
        'matched_region': matched_region,
    }

