"""
Core data layer for fetching company information and financials from yfinance.
"""
import yfinance as yf
import time
from typing import Dict, Any, List, Optional
import pandas as pd

class CompanyDataFetcher:
    """
    Fetches and caches company financial data using yfinance.
    """
    def __init__(self):
        # 15-minute TTL cache: Dict[ticker, Dict['data': data, 'timestamp': time]]
        self._cache: Dict[str, Any] = {}
        self.CACHE_TTL: int = 15 * 60
        
        self.CURRENCY_SYMBOLS: Dict[str, str] = {
            "USD":"$", "EUR":"€", "GBP":"£", "INR":"₹", "JPY":"¥", "CNY":"¥", 
            "KRW":"₩", "BRL":"R$", "CAD":"C$", "AUD":"A$", "CHF":"CHF", "HKD":"HK$", 
            "SGD":"S$", "SEK":"kr", "NOK":"kr", "DKK":"kr", "PLN":"zł", "CZK":"Kč", 
            "THB":"฿", "MYR":"RM", "IDR":"Rp", "PHP":"₱", "TWD":"NT$", "ZAR":"R", 
            "MXN":"Mex$", "RUB":"₽", "TRY":"₺", "ARS":"AR$", "CLP":"CL$", "COP":"CO$", 
            "PEN":"S/", "ILS":"₪", "SAR":"﷼", "AED":"د.إ", "QAR":"QR", "KWD":"KD", 
            "BHD":"BD", "OMR":"OMR", "EGP":"E£", "NGN":"₦", "KES":"KSh", "GHS":"GH₵", 
            "PKR":"Rs", "BDT":"৳", "LKR":"Rs", "VND":"₫", "NZD":"NZ$"
        }

    def _get_from_cache(self, key: str) -> Optional[Any]:
        """Retrieves an item from cache if it has not expired."""
        if key in self._cache:
            item = self._cache[key]
            if time.time() - item['timestamp'] < self.CACHE_TTL:
                return item['data']
        return None

    def _set_cache(self, key: str, data: Any) -> None:
        """Sets an item in the cache."""
        self._cache[key] = {
            'data': data,
            'timestamp': time.time()
        }

    def get_raw_info(self, ticker: str) -> Dict[str, Any]:
        """Fetches and caches raw yf.Ticker(ticker).info dictionary."""
        ticker = ticker.upper()
        cache_key = f"raw_info_{ticker}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached
        try:
            t = yf.Ticker(ticker)
            info = t.info or {}
            self._set_cache(cache_key, info)
            return info
        except Exception:
            return {}


    def get_currency_symbol(self, iso_code: str) -> str:
        """Returns the currency symbol for a given ISO currency code."""
        if not iso_code: return "$"
        code = iso_code.strip()
        if code in ['GBp', 'GBX', 'GBx', 'gbp', 'gbx']:
            return "GBX "
        if code.upper() == 'GBP':
            return "£"
        return self.CURRENCY_SYMBOLS.get(code.upper(), code.upper())

    def format_currency(self, value: float, iso_code: str) -> str:
        """Formats a currency value based on its ISO code conventions."""
        if pd.isna(value) or value is None:
            return "N/A"
        if iso_code in ['GBp', 'GBX', 'GBx', 'gbp', 'gbx']:
            return f"GBX {value:,.2f}"
        sym = self.get_currency_symbol(iso_code)
        if iso_code.upper() == 'INR':
            # Indian numbering system formatting
            try:
                s, *d = str(value).partition(".")
                r = ",".join([s[x-2:x] for x in range(-3, -len(s), -2)][::-1] + [s[-3:]])
                return f"{sym}{r}{d[0]}{d[1][:2]}"
            except:
                pass
        return f"{sym}{value:,.2f}"

    def get_price_scale_to_financials(self, ticker: str) -> float:
        """
        Returns multiplier to convert per-share values from financialCurrency into quoted market currency.
        For LSE stocks where financials are in GBP and market price is quoted in GBX (pence), returns 100.0.
        """
        info = self.get_raw_info(ticker)
        quote_curr = info.get('currency', '')
        fin_curr = info.get('financialCurrency', '')
        if quote_curr in ['GBp', 'GBX', 'GBx', 'gbp', 'gbx'] and fin_curr.upper() == 'GBP':
            return 100.0
        return 1.0

    def get_info(self, ticker: str) -> Dict[str, Any]:
        """Alias for get_company_info — used by valuation modules."""
        return self.get_company_info(ticker)

    def get_company_info(self, ticker: str) -> Dict[str, Any]:
        """Fetches basic company info."""
        cache_key = f"info_{ticker}"
        cached = self._get_from_cache(cache_key)
        if cached: return cached

        try:
            t = yf.Ticker(ticker)
            info = t.info
            
            if not info or 'shortName' not in info:
                return {"error": f"No data found for {ticker}"}
                
            raw_curr = info.get('currency', 'USD')
            if str(raw_curr).strip() in ['GBp', 'GBX', 'GBx', 'gbp', 'gbx']:
                curr = 'GBX'
                curr_sym = 'GBX '
            elif str(raw_curr).strip().upper() == 'GBP':
                curr = 'GBP'
                curr_sym = '£'
            else:
                curr = raw_curr
                curr_sym = self.get_currency_symbol(curr)

            price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('ask') or info.get('bid')
            # Last resort: use fast_info which is more reliable
            if not price:
                try:
                    price = t.fast_info.last_price
                except Exception:
                    pass
            price = float(price) if price else None
            prev_close = info.get('previousClose') or info.get('regularMarketPreviousClose')
            
            price_change = price - prev_close if price and prev_close else None
            price_change_pct = (price_change / prev_close * 100) if price_change and prev_close else None

            data = {
                "name": info.get('shortName', info.get('longName')),
                "ticker": ticker.upper(),
                "sector": info.get('sector'),
                "industry": info.get('industry'),
                "country": info.get('country'),
                "market_cap": info.get('marketCap'),
                "currency": curr,
                "currency_symbol": curr_sym,
                "current_price": price,
                "price_change": price_change,
                "price_change_pct": price_change_pct,
                "beta": info.get('beta'),
                "shares_outstanding": info.get('sharesOutstanding'),
                "52_week_high": info.get('fiftyTwoWeekHigh'),
                "52_week_low": info.get('fiftyTwoWeekLow'),
                "pe_ratio": info.get('trailingPE'),
                "forward_pe": info.get('forwardPE'),
                "dividend_yield": info.get('dividendYield'),
                "eps": info.get('trailingEps'),
                "employees": info.get('fullTimeEmployees'),
                "description": info.get('longBusinessSummary'),
                "website": info.get('website')
            }
            self._set_cache(cache_key, data)
            return data
        except Exception as e:
            return {"error": str(e)}

    def get_financials(self, ticker: str) -> Dict[str, Any]:
        """Fetches the 3 main financial statements as JSON-serializable dicts (for API responses)."""
        cache_key = f"financials_{ticker}"
        cached = self._get_from_cache(cache_key)
        if cached: return cached

        try:
            t = yf.Ticker(ticker)
            
            def df_to_list(df: pd.DataFrame) -> List[Dict[str, Any]]:
                if df is None or df.empty: return []
                df = df.fillna(0)
                df_t = df.T.reset_index()
                df_t = df_t.rename(columns={'index': 'date'})
                df_t['date'] = df_t['date'].astype(str)
                return df_t.to_dict('records')

            data = {
                "income_statement": df_to_list(t.income_stmt),
                "balance_sheet": df_to_list(t.balance_sheet),
                "cash_flow": df_to_list(t.cash_flow)
            }
            self._set_cache(cache_key, data)
            return data
        except Exception as e:
            return {"error": str(e)}

    # ------------------------------------------------------------------
    # Raw DataFrame accessors — used by valuation & quant modules
    # ------------------------------------------------------------------
    def _get_yf_ticker(self, ticker: str):
        """Get (and cache) the raw yfinance Ticker object."""
        cache_key = f"yf_ticker_{ticker}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        t = yf.Ticker(ticker)
        self._set_cache(cache_key, t)
        return t

    def get_income_stmt(self, ticker: str) -> pd.DataFrame:
        """Returns the income statement as a raw pandas DataFrame (columns = years, rows = line items)."""
        cache_key = f"income_stmt_df_{ticker}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached
        try:
            t = self._get_yf_ticker(ticker)
            df = t.income_stmt
            if df is None:
                df = pd.DataFrame()
            self._set_cache(cache_key, df)
            return df
        except Exception:
            return pd.DataFrame()

    def get_balance_sheet(self, ticker: str) -> pd.DataFrame:
        """Returns the balance sheet as a raw pandas DataFrame."""
        cache_key = f"balance_sheet_df_{ticker}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached
        try:
            t = self._get_yf_ticker(ticker)
            df = t.balance_sheet
            if df is None:
                df = pd.DataFrame()
            self._set_cache(cache_key, df)
            return df
        except Exception:
            return pd.DataFrame()

    def get_cashflow(self, ticker: str) -> pd.DataFrame:
        """Returns the cash flow statement as a raw pandas DataFrame."""
        cache_key = f"cashflow_df_{ticker}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached
        try:
            t = self._get_yf_ticker(ticker)
            df = t.cash_flow
            if df is None:
                df = pd.DataFrame()
            self._set_cache(cache_key, df)
            return df
        except Exception:
            return pd.DataFrame()

    def get_stock_history(self, ticker: str, period: str = '5y') -> Dict[str, Any]:
        """Fetches historical stock price data."""
        cache_key = f"history_{ticker}_{period}"
        cached = self._get_from_cache(cache_key)
        if cached: return cached

        try:
            t = yf.Ticker(ticker)
            hist = t.history(period=period)
            if hist.empty:
                return {"error": "No history found"}
            
            data = {
                "dates": hist.index.strftime('%Y-%m-%d').tolist(),
                "prices": hist['Close'].tolist(),
                "volumes": hist['Volume'].tolist()
            }
            self._set_cache(cache_key, data)
            return data
        except Exception as e:
            return {"error": str(e)}

    def get_dividends(self, ticker: str) -> Dict[str, Any]:
        """Fetches historical dividend payments."""
        cache_key = f"dividends_{ticker}"
        cached = self._get_from_cache(cache_key)
        if cached: return cached

        try:
            t = yf.Ticker(ticker)
            divs = t.dividends
            if divs.empty:
                return {"dividends": []}
            
            data = {
                "dividends": [{"date": k.strftime('%Y-%m-%d'), "amount": v} for k, v in divs.items()]
            }
            self._set_cache(cache_key, data)
            return data
        except Exception as e:
            return {"error": str(e)}

    def get_news(self, ticker: str) -> List[Dict[str, Any]]:
        """Fetches recent news items."""
        cache_key = f"news_{ticker}"
        cached = self._get_from_cache(cache_key)
        if cached: return cached

        try:
            t = yf.Ticker(ticker)
            news = t.news
            self._set_cache(cache_key, news)
            return news
        except Exception as e:
            return [{"error": str(e)}]

    def get_peers(self, ticker: str) -> List[str]:
        """Fetches an institutional, business-model and geography aligned list of peer tickers."""
        cache_key = f"peers_{ticker.upper()}"
        cached = self._get_from_cache(cache_key)
        if cached: return cached

        try:
            from api.valuation.peers import get_institutional_peers
            info = self.get_company_info(ticker)
            res = get_institutional_peers(ticker, data_fetcher=self, info=info)
            peers = res.get('peers', [])
            self._set_cache(cache_key, peers)
            return peers
        except Exception:
            return []

