"""
Performance routes - 5-year price history, stats, benchmark comparison.
"""
from fastapi import APIRouter, Depends, HTTPException
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from ..auth.utils import get_current_user
from ..database.models import User

router = APIRouter(prefix="/api/performance", tags=["performance"])


def _calculate_stats(series: pd.Series, risk_free_rate: float = 0.04) -> dict:
    """Calculate key performance statistics from a price series."""
    if series.empty or len(series) < 2:
        return {}

    start_price = float(series.iloc[0])
    end_price = float(series.iloc[-1])
    total_return = (end_price / start_price) - 1.0

    years = len(series) / 252.0
    cagr = (end_price / start_price) ** (1 / years) - 1.0 if years > 0 else 0.0

    daily_returns = series.pct_change().dropna()
    volatility = float(daily_returns.std() * np.sqrt(252))

    sharpe_ratio = (cagr - risk_free_rate) / volatility if volatility > 0 else 0.0

    roll_max = series.cummax()
    drawdown = series / roll_max - 1.0
    max_drawdown = float(drawdown.min())

    return {
        "total_return": round(float(total_return), 4),
        "annualized_return": round(float(cagr), 4),
        "max_drawdown": round(max_drawdown, 4),
        "volatility": round(volatility, 4),
        "sharpe_ratio": round(float(sharpe_ratio), 4),
    }


@router.get("/{ticker}")
def get_performance(ticker: str, user: User = Depends(get_current_user)):
    try:
        from ..company.data_fetcher import CompanyDataFetcher
        from .benchmark import get_benchmark_for_ticker, calculate_relative_metrics

        fetcher = CompanyDataFetcher()
        company_info = fetcher.get_company_info(ticker.upper())

        # Resolve sovereign/national primary market benchmark
        benchmark_meta = get_benchmark_for_ticker(ticker.upper(), company_info)
        bench_symbol = benchmark_meta["symbol"]

        end_date = datetime.today()
        start_date = end_date - timedelta(days=5 * 365)

        # Fetch ticker data
        df = yf.download(ticker.upper(), start=start_date, end=end_date, progress=False)
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No price data found for {ticker}")

        # Handle multi-level columns from yf.download
        if isinstance(df.columns, pd.MultiIndex):
            close_col = df["Close"]
            if isinstance(close_col, pd.DataFrame):
                close_col = close_col.iloc[:, 0]
        else:
            close_col = df["Close"] if "Close" in df.columns else df.iloc[:, 0]

        close_series = close_col.dropna()

        # Fetch local benchmark data (e.g. ^FTSE for UK, ^GDAXI for DE, ^GSPC for US)
        bench_df = yf.download(bench_symbol, start=start_date, end=end_date, progress=False)
        if not bench_df.empty:
            if isinstance(bench_df.columns, pd.MultiIndex):
                bench_close = bench_df["Close"]
                if isinstance(bench_close, pd.DataFrame):
                    bench_close = bench_close.iloc[:, 0]
            else:
                bench_close = bench_df["Close"] if "Close" in bench_df.columns else bench_df.iloc[:, 0]
            bench_series = bench_close.dropna()
        else:
            bench_series = pd.Series(dtype=float)

        ticker_stats = _calculate_stats(close_series)
        bench_stats = _calculate_stats(bench_series)

        # Compute institutional relative risk and CAPM metrics vs local benchmark
        rel_metrics = calculate_relative_metrics(close_series, bench_series)

        # Monthly returns for heatmap
        monthly = close_series.resample("ME").last()
        monthly_returns_series = monthly.pct_change().dropna()
        monthly_returns = []
        for date, ret in monthly_returns_series.items():
            monthly_returns.append({
                "month": date.month,
                "year": date.year,
                "return_pct": round(float(ret), 4),
            })

        # 52-week high/low
        one_year_ago = end_date - timedelta(days=365)
        last_year_data = close_series.loc[close_series.index >= pd.Timestamp(one_year_ago)]
        high_52 = float(last_year_data.max()) if not last_year_data.empty else float(close_series.max())
        low_52 = float(last_year_data.min()) if not last_year_data.empty else float(close_series.min())

        return {
            "ticker": ticker.upper(),
            "benchmark": benchmark_meta,
            "relative_metrics": rel_metrics,
            "dates": [d.strftime("%Y-%m-%d") for d in close_series.index],
            "prices": [round(float(p), 2) for p in close_series.values],
            "benchmark_dates": [d.strftime("%Y-%m-%d") for d in bench_series.index] if not bench_series.empty else [],
            "benchmark_prices": [round(float(p), 2) for p in bench_series.values] if not bench_series.empty else [],
            "stats": ticker_stats,
            "benchmark_stats": bench_stats,
            "52_week_high": round(high_52, 2),
            "52_week_low": round(low_52, 2),
            "monthly_returns": monthly_returns,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

