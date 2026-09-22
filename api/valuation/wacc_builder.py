"""
WACC Calculation module.
"""
import yfinance as yf
from typing import Dict, Any

def calculate_wacc(ticker: str, data_fetcher, peers: list = None, use_peer_beta: bool = False) -> Dict[str, Any]:
    """
    Calculates the Weighted Average Cost of Capital (WACC).
    """
    info = data_fetcher.get_company_info(ticker)
    if "error" in info:
        return info
        
    financials = data_fetcher.get_financials(ticker)
    
    # 1. Risk-Free Rate
    try:
        tnx = yf.Ticker("^TNX")
        risk_free_rate = tnx.info.get('regularMarketPrice', 4.0) / 100.0
    except:
        risk_free_rate = 0.04 # Fallback
        
    # 2. Beta
    beta_raw = info.get('beta')
    if beta_raw is None or beta_raw == 1.0:
        if hasattr(data_fetcher, 'calculate_beta'):
            b_calc = data_fetcher.calculate_beta(ticker, country=info.get('country'))
            if b_calc is not None:
                beta_raw = b_calc
        if beta_raw is None:
            beta_raw = 1.0 # Fallback
        
    # 3. Market Values
    market_cap = info.get('market_cap', 0)
    
    total_debt = 0.0
    interest_expense = 0.0
    pre_tax_income = 0.0
    tax_provision = 0.0
    
    bs = financials.get('balance_sheet', [])
    if bs and len(bs) > 0:
        latest_bs = bs[0]
        st_debt = latest_bs.get('Current Debt', latest_bs.get('Short Long Term Debt', 0.0))
        lt_debt = latest_bs.get('Long Term Debt', 0.0)
        total_debt = st_debt + lt_debt
        
    ist = financials.get('income_statement', [])
    if ist and len(ist) > 0:
        latest_is = ist[0]
        interest_expense = latest_is.get('Interest Expense', 0.0)
        pre_tax_income = latest_is.get('Pretax Income', 0.0)
        tax_provision = latest_is.get('Tax Provision', 0.0)
        
    # 4. Tax Rate
    is_uk = ticker.upper().endswith('.L') or 'united kingdom' in str(info.get('country', '')).lower()
    default_tax = 0.25 if is_uk else 0.21
    if pre_tax_income > 0 and tax_provision > 0:
        tax_rate = tax_provision / pre_tax_income
    else:
        tax_rate = default_tax

        
    # 5. Cost of Debt
    if total_debt > 0 and interest_expense > 0:
        cost_of_debt = interest_expense / total_debt
    else:
        cost_of_debt = risk_free_rate + 0.02 # Estimate for non-debt companies
        
    # 6. Cost of Equity (CAPM)
    equity_risk_premium = 0.055 # Default
    
    debt_to_equity = total_debt / market_cap if market_cap > 0 else 0.0
    
    # Hamada Equation: un-levered beta
    beta_unlevered = beta_raw / (1 + (1 - tax_rate) * debt_to_equity)
    beta_used = beta_raw
    
    if use_peer_beta and peers:
        # Future enhancement: average unlevered beta of peers and re-lever
        pass
        
    cost_of_equity = risk_free_rate + beta_used * equity_risk_premium
    
    # 7. WACC
    total_capital = market_cap + total_debt
    if total_capital > 0:
        weight_equity = market_cap / total_capital
        weight_debt = total_debt / total_capital
    else:
        weight_equity = 1.0
        weight_debt = 0.0
        
    wacc = (weight_equity * cost_of_equity) + (weight_debt * cost_of_debt * (1 - tax_rate))
    
    return {
        "risk_free_rate": risk_free_rate,
        "beta_raw": beta_raw,
        "beta_unlevered": beta_unlevered,
        "beta_used": beta_used,
        "equity_risk_premium": equity_risk_premium,
        "cost_of_equity": cost_of_equity,
        "cost_of_debt": cost_of_debt,
        "tax_rate": tax_rate,
        "weight_equity": weight_equity,
        "weight_debt": weight_debt,
        "wacc": wacc,
        "total_debt": total_debt,
        "market_cap": market_cap
    }
