"""
National Market Benchmark Engine.
Automatically maps international companies to their sovereign/national primary market index
(e.g., FTSE 100 for London/UK, DAX 40 for Frankfurt, CAC 40 for Paris, S&P 500 for US, etc.).
Calculates local CAPM beta, alpha, correlation, and relative performance metrics.
"""
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

NATIONAL_BENCHMARKS: Dict[str, Dict[str, str]] = {
    "UK": {
        "symbol": "^FTSE",
        "name": "FTSE 100",
        "full_name": "FTSE 100 Index (London)",
        "market": "London Stock Exchange (LSE)",
        "currency": "GBP",
        "country": "United Kingdom",
    },
    "DE": {
        "symbol": "^GDAXI",
        "name": "DAX 40",
        "full_name": "DAX 40 Index (Frankfurt)",
        "market": "Frankfurt / XETRA",
        "currency": "EUR",
        "country": "Germany",
    },
    "FR": {
        "symbol": "^FCHI",
        "name": "CAC 40",
        "full_name": "CAC 40 Index (Paris)",
        "market": "Euronext Paris",
        "currency": "EUR",
        "country": "France",
    },
    "NL": {
        "symbol": "^AEX",
        "name": "AEX Index",
        "full_name": "AEX Index (Amsterdam)",
        "market": "Euronext Amsterdam",
        "currency": "EUR",
        "country": "Netherlands",
    },
    "CH": {
        "symbol": "^SSMI",
        "name": "SMI",
        "full_name": "Swiss Market Index (Zurich)",
        "market": "SIX Swiss Exchange",
        "currency": "CHF",
        "country": "Switzerland",
    },
    "IT": {
        "symbol": "FTSEMIB.MI",
        "name": "FTSE MIB",
        "full_name": "FTSE MIB Index (Milan)",
        "market": "Borsa Italiana",
        "currency": "EUR",
        "country": "Italy",
    },
    "ES": {
        "symbol": "^IBEX",
        "name": "IBEX 35",
        "full_name": "IBEX 35 (Madrid)",
        "market": "Bolsa de Madrid",
        "currency": "EUR",
        "country": "Spain",
    },
    "SE": {
        "symbol": "^OMX",
        "name": "OMX Stockholm 30",
        "full_name": "OMX Stockholm 30",
        "market": "Nasdaq Stockholm",
        "currency": "SEK",
        "country": "Sweden",
    },
    "CA": {
        "symbol": "^GSPTSE",
        "name": "S&P/TSX Composite",
        "full_name": "S&P/TSX Composite (Toronto)",
        "market": "Toronto Stock Exchange",
        "currency": "CAD",
        "country": "Canada",
    },
    "AU": {
        "symbol": "^AXJO",
        "name": "S&P/ASX 200",
        "full_name": "S&P/ASX 200 (Sydney)",
        "market": "Australian Securities Exchange",
        "currency": "AUD",
        "country": "Australia",
    },
    "JP": {
        "symbol": "^N225",
        "name": "Nikkei 225",
        "full_name": "Nikkei 225 (Tokyo)",
        "market": "Tokyo Stock Exchange",
        "currency": "JPY",
        "country": "Japan",
    },
    "HK": {
        "symbol": "^HSI",
        "name": "Hang Seng Index",
        "full_name": "Hang Seng Index (Hong Kong)",
        "market": "Hong Kong Exchanges",
        "currency": "HKD",
        "country": "Hong Kong",
    },
    "IN": {
        "symbol": "^NSEI",
        "name": "NIFTY 50",
        "full_name": "NIFTY 50 (India)",
        "market": "National Stock Exchange of India",
        "currency": "INR",
        "country": "India",
    },
    "BR": {
        "symbol": "^BVSP",
        "name": "IBOVESPA",
        "full_name": "IBOVESPA Index (São Paulo)",
        "market": "B3",
        "currency": "BRL",
        "country": "Brazil",
    },
    "KR": {
        "symbol": "^KS11",
        "name": "KOSPI",
        "full_name": "KOSPI (Seoul)",
        "market": "Korea Exchange",
        "currency": "KRW",
        "country": "South Korea",
    },
    "US": {
        "symbol": "^GSPC",
        "name": "S&P 500",
        "full_name": "S&P 500 Index (New York)",
        "market": "U.S. Equity Market (NYSE/NASDAQ)",
        "currency": "USD",
        "country": "United States",
    },
}


def get_benchmark_for_ticker(ticker: str, info: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    """
    Identifies and returns the official primary national benchmark index for a company.
    """
    sym = ticker.upper().strip()
    
    # 1. Direct exchange suffix identification
    if sym.endswith('.L'):
        return NATIONAL_BENCHMARKS["UK"]
    if sym.endswith(('.DE', '.F')):
        return NATIONAL_BENCHMARKS["DE"]
    if sym.endswith('.PA'):
        return NATIONAL_BENCHMARKS["FR"]
    if sym.endswith('.AS'):
        return NATIONAL_BENCHMARKS["NL"]
    if sym.endswith(('.SW', '.VX')):
        return NATIONAL_BENCHMARKS["CH"]
    if sym.endswith('.MI'):
        return NATIONAL_BENCHMARKS["IT"]
    if sym.endswith('.MC'):
        return NATIONAL_BENCHMARKS["ES"]
    if sym.endswith('.ST'):
        return NATIONAL_BENCHMARKS["SE"]
    if sym.endswith(('.TO', '.V')):
        return NATIONAL_BENCHMARKS["CA"]
    if sym.endswith('.AX'):
        return NATIONAL_BENCHMARKS["AU"]
    if sym.endswith('.T'):
        return NATIONAL_BENCHMARKS["JP"]
    if sym.endswith('.HK'):
        return NATIONAL_BENCHMARKS["HK"]
    if sym.endswith(('.NS', '.BO')):
        return NATIONAL_BENCHMARKS["IN"]
    if sym.endswith('.SA'):
        return NATIONAL_BENCHMARKS["BR"]
    if sym.endswith(('.KS', '.KQ')):
        return NATIONAL_BENCHMARKS["KR"]

    # 2. Country inspection from info metadata
    if info:
        country = str(info.get('country') or '').lower()
        if any(c in country for c in ['united kingdom', 'uk', 'britain', 'england', 'scotland', 'wales']):
            return NATIONAL_BENCHMARKS["UK"]
        if 'germany' in country:
            return NATIONAL_BENCHMARKS["DE"]
        if 'france' in country:
            return NATIONAL_BENCHMARKS["FR"]
        if 'netherlands' in country:
            return NATIONAL_BENCHMARKS["NL"]
        if 'switzerland' in country:
            return NATIONAL_BENCHMARKS["CH"]
        if 'italy' in country:
            return NATIONAL_BENCHMARKS["IT"]
        if 'spain' in country:
            return NATIONAL_BENCHMARKS["ES"]
        if 'sweden' in country:
            return NATIONAL_BENCHMARKS["SE"]
        if 'canada' in country:
            return NATIONAL_BENCHMARKS["CA"]
        if 'australia' in country:
            return NATIONAL_BENCHMARKS["AU"]
        if 'japan' in country:
            return NATIONAL_BENCHMARKS["JP"]
        if 'india' in country:
            return NATIONAL_BENCHMARKS["IN"]
        if 'brazil' in country:
            return NATIONAL_BENCHMARKS["BR"]
        if 'south korea' in country or 'korea' in country:
            return NATIONAL_BENCHMARKS["KR"]

    # Default to US S&P 500
    return NATIONAL_BENCHMARKS["US"]


def calculate_relative_metrics(
    stock_series: pd.Series,
    bench_series: pd.Series,
    risk_free_rate: float = 0.04
) -> Dict[str, Any]:
    """
    Calculates institutional CAPM and relative risk metrics vs the local benchmark.
    """
    if stock_series.empty or bench_series.empty:
        return {}

    # Align on common trading dates
    combined = pd.DataFrame({'stock': stock_series, 'bench': bench_series}).dropna()
    if len(combined) < 20:
        return {}

    stock_rets = combined['stock'].pct_change().dropna()
    bench_rets = combined['bench'].pct_change().dropna()

    common_idx = stock_rets.index.intersection(bench_rets.index)
    if len(common_idx) < 20:
        return {}

    s_ret = stock_rets.loc[common_idx]
    b_ret = bench_rets.loc[common_idx]

    cov = np.cov(s_ret, b_ret)[0, 1]
    var_bench = np.var(b_ret, ddof=1)
    beta = float(cov / var_bench) if var_bench > 0 else 1.0

    corr = float(s_ret.corr(b_ret))

    # Annualized returns
    years = len(s_ret) / 252.0
    stock_total_return = (combined['stock'].iloc[-1] / combined['stock'].iloc[0]) - 1.0
    bench_total_return = (combined['bench'].iloc[-1] / combined['bench'].iloc[0]) - 1.0

    stock_cagr = (combined['stock'].iloc[-1] / combined['stock'].iloc[0]) ** (1.0 / years) - 1.0 if years > 0 else 0.0
    bench_cagr = (combined['bench'].iloc[-1] / combined['bench'].iloc[0]) ** (1.0 / years) - 1.0 if years > 0 else 0.0

    # Jensen's Alpha (annualized)
    expected_stock_return = risk_free_rate + beta * (bench_cagr - risk_free_rate)
    alpha = float(stock_cagr - expected_stock_return)

    # Tracking error
    diff_rets = s_ret - b_ret
    tracking_error = float(diff_rets.std() * np.sqrt(252))

    return {
        "beta_vs_benchmark": round(beta, 2),
        "alpha_vs_benchmark": round(alpha, 4),
        "correlation": round(corr, 2),
        "tracking_error": round(tracking_error, 4),
        "stock_cagr": round(float(stock_cagr), 4),
        "benchmark_cagr": round(float(bench_cagr), 4),
        "benchmark_total_return": round(float(bench_total_return), 4),
    }
