"""
Core data layer for fetching company information and financials from yfinance.
Equipped with resilient direct Yahoo Finance chart and search fallbacks for cloud environments.
"""
import yfinance as yf
import time
import json
import urllib.request
import datetime
from typing import Dict, Any, List, Optional
import pandas as pd
import requests

class CompanyDataFetcher:
    """
    Fetches and caches company financial data using yfinance and direct Yahoo Finance APIs.
    """
    def __init__(self):
        # 15-minute TTL cache: Dict[ticker, Dict['data': data, 'timestamp': time]]
        self._cache: Dict[str, Any] = {}
        self.CACHE_TTL: int = 15 * 60
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        })

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

    def _get_yf_ticker(self, ticker: str):
        """Get (and cache) the raw yfinance Ticker object with browser session."""
        ticker = ticker.upper().strip()
        cache_key = f"yf_ticker_{ticker}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        try:
            t = yf.Ticker(ticker, session=self.session)
        except Exception:
            t = yf.Ticker(ticker)
        self._set_cache(cache_key, t)
        return t

    def _fetch_direct_yahoo(self, ticker: str) -> Dict[str, Any]:
        """
        Directly queries Yahoo Finance public chart and search APIs with realistic browser headers.
        Bypasses cloud datacenter IP blocks and does not require crumb/cookies.
        """
        ticker = ticker.upper().strip()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'application/json',
        }
        res: Dict[str, Any] = {}

        # 1. Chart API (v8) - highly reliable on cloud IPs
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=5d"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=6) as resp:
                chart_data = json.loads(resp.read().decode('utf-8'))
            results = chart_data.get('chart', {}).get('result', [])
            if results:
                meta = results[0].get('meta', {})
                price = meta.get('regularMarketPrice')
                prev = meta.get('previousClose') or meta.get('chartPreviousClose')
                res['currentPrice'] = price
                res['regularMarketPrice'] = price
                res['previousClose'] = prev
                res['regularMarketPreviousClose'] = prev
                res['fiftyTwoWeekHigh'] = meta.get('fiftyTwoWeekHigh')
                res['fiftyTwoWeekLow'] = meta.get('fiftyTwoWeekLow')
                res['currency'] = meta.get('currency', 'USD')
                res['shortName'] = meta.get('shortName') or meta.get('longName') or ticker
                res['longName'] = meta.get('longName') or res['shortName']
                res['symbol'] = meta.get('symbol', ticker)
        except Exception:
            pass

        # 2. Search API (v1) - gives company name, sector, industry
        try:
            search_url = f"https://query2.finance.yahoo.com/v1/finance/search?q={ticker}"
            req2 = urllib.request.Request(search_url, headers=headers)
            with urllib.request.urlopen(req2, timeout=6) as resp2:
                search_data = json.loads(resp2.read().decode('utf-8'))
            quotes = search_data.get('quotes', [])
            target_q = None
            for q in quotes:
                if q.get('symbol', '').upper() == ticker:
                    target_q = q
                    break
            if not target_q and quotes:
                target_q = quotes[0]
            if target_q:
                if not res.get('shortName') or res['shortName'] == ticker:
                    res['shortName'] = target_q.get('shortname') or target_q.get('longname') or ticker
                if not res.get('longName'):
                    res['longName'] = target_q.get('longname') or res.get('shortName')
                if target_q.get('sector'):
                    res['sector'] = target_q.get('sector')
                if target_q.get('industry'):
                    res['industry'] = target_q.get('industry')
        except Exception:
            pass

        # 3. yfinance fast_info (if available)
        try:
            t = self._get_yf_ticker(ticker)
            fi = getattr(t, 'fast_info', None)
            if fi:
                if not res.get('currentPrice') and getattr(fi, 'last_price', None):
                    res['currentPrice'] = float(fi.last_price)
                    res['regularMarketPrice'] = float(fi.last_price)
                if not res.get('previousClose') and getattr(fi, 'previous_close', None):
                    res['previousClose'] = float(fi.previous_close)
                if getattr(fi, 'market_cap', None):
                    res['marketCap'] = float(fi.market_cap)
                if getattr(fi, 'shares', None):
                    res['sharesOutstanding'] = int(fi.shares)
                if not res.get('currency') and getattr(fi, 'currency', None):
                    res['currency'] = fi.currency
                if not res.get('fiftyTwoWeekHigh') and getattr(fi, 'year_high', None):
                    res['fiftyTwoWeekHigh'] = float(fi.year_high)
                if not res.get('fiftyTwoWeekLow') and getattr(fi, 'year_low', None):
                    res['fiftyTwoWeekLow'] = float(fi.year_low)
        except Exception:
            pass

        return res

    def get_raw_info(self, ticker: str) -> Dict[str, Any]:
        """Fetches and caches raw yf.Ticker(ticker).info dictionary with fallback enrichment."""
        ticker = ticker.upper()
        cache_key = f"raw_info_{ticker}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached
            
        info = {}
        try:
            t = self._get_yf_ticker(ticker)
            info = t.info or {}
        except Exception:
            info = {}

        # If info is empty or missing vital price/name data, enrich from direct Yahoo APIs
        if not info or not info.get('regularMarketPrice') or not info.get('shortName'):
            fallback = self._fetch_direct_yahoo(ticker)
            for k, v in fallback.items():
                if v is not None and not info.get(k):
                    info[k] = v

        if info:
            self._set_cache(cache_key, info)
        return info

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
        """Alias for get_company_info - used by valuation modules."""
        return self.get_company_info(ticker)

    def get_company_info(self, ticker: str) -> Dict[str, Any]:
        """Fetches basic company info with multi-layered fallbacks."""
        ticker = ticker.upper()
        cache_key = f"info_{ticker}"
        cached = self._get_from_cache(cache_key)
        if cached: return cached

        info = self.get_raw_info(ticker)
        
        name = info.get('shortName') or info.get('longName')
        price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('ask') or info.get('bid')

        # If still missing, try direct Yahoo API fallback
        if not name or not price:
            fallback = self._fetch_direct_yahoo(ticker)
            if not name:
                name = fallback.get('shortName') or fallback.get('longName')
            if not price:
                price = fallback.get('currentPrice')
            for k, v in fallback.items():
                if v is not None and not info.get(k):
                    info[k] = v

        if not name and not price:
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

        price = float(price) if price else None
        prev_close = info.get('previousClose') or info.get('regularMarketPreviousClose')
        
        price_change = (price - prev_close) if price and prev_close else None
        price_change_pct = (price_change / prev_close * 100) if price_change and prev_close else None

        data = {
            "name": name or ticker,
            "ticker": ticker,
            "sector": info.get('sector') or 'General',
            "industry": info.get('industry') or 'General',
            "country": info.get('country') or 'Global',
            "market_cap": info.get('marketCap'),
            "currency": curr,
            "currency_symbol": curr_sym,
            "current_price": price,
            "price_change": price_change,
            "price_change_pct": price_change_pct,
            "beta": info.get('beta') or 1.0,
            "shares_outstanding": info.get('sharesOutstanding'),
            "52_week_high": info.get('fiftyTwoWeekHigh'),
            "52_week_low": info.get('fiftyTwoWeekLow'),
            "pe_ratio": info.get('trailingPE') or info.get('forwardPE'),
            "forward_pe": info.get('forwardPE'),
            "dividend_yield": info.get('dividendYield'),
            "eps": info.get('trailingEps'),
            "employees": info.get('fullTimeEmployees'),
            "description": info.get('longBusinessSummary') or f"{name or ticker} operates in the {info.get('sector', 'commercial')} sector.",
            "website": info.get('website') or ''
        }
        self._set_cache(cache_key, data)
        return data

    def get_financials(self, ticker: str) -> Dict[str, Any]:
        """Fetches the 3 main financial statements as JSON-serializable dicts (for API responses)."""
        cache_key = f"financials_{ticker}"
        cached = self._get_from_cache(cache_key)
        if cached: return cached

        try:
            t = self._get_yf_ticker(ticker)
            
            def df_to_list(df: pd.DataFrame) -> List[Dict[str, Any]]:
                if df is None or df.empty: return []
                df = df.fillna(0)
                df_t = df.T.reset_index()
                df_t = df_t.rename(columns={'index': 'date'})
                df_t['date'] = df_t['date'].astype(str)
                return df_t.to_dict('records')

            data = {
                "income_statement": df_to_list(getattr(t, 'income_stmt', None)),
                "balance_sheet": df_to_list(getattr(t, 'balance_sheet', None)),
                "cash_flow": df_to_list(getattr(t, 'cash_flow', None))
            }
            self._set_cache(cache_key, data)
            return data
        except Exception as e:
            return {"error": str(e)}

    # ------------------------------------------------------------------
    # Raw DataFrame accessors - used by valuation & quant modules
    # ------------------------------------------------------------------
    def get_income_stmt(self, ticker: str) -> pd.DataFrame:
        """Returns the income statement as a raw pandas DataFrame (columns = years, rows = line items)."""
        cache_key = f"income_stmt_df_{ticker}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached
        try:
            t = self._get_yf_ticker(ticker)
            df = getattr(t, 'income_stmt', None)
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
            df = getattr(t, 'balance_sheet', None)
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
            df = getattr(t, 'cash_flow', None)
            if df is None:
                df = pd.DataFrame()
            self._set_cache(cache_key, df)
            return df
        except Exception:
            return pd.DataFrame()

    def get_stock_history(self, ticker: str, period: str = '5y') -> Dict[str, Any]:
        """Fetches historical stock price data with direct chart fallback."""
        ticker = ticker.upper()
        cache_key = f"history_{ticker}_{period}"
        cached = self._get_from_cache(cache_key)
        if cached: return cached

        try:
            t = self._get_yf_ticker(ticker)
            hist = t.history(period=period)
            if hist is not None and not hist.empty:
                data = {
                    "dates": hist.index.strftime('%Y-%m-%d').tolist(),
                    "prices": hist['Close'].tolist(),
                    "volumes": hist['Volume'].tolist()
                }
                self._set_cache(cache_key, data)
                return data
        except Exception:
            pass

        # Fallback to direct Yahoo chart API if t.history fails on cloud IP
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
            }
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range={period}&interval=1d"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=8) as r:
                d = json.loads(r.read().decode('utf-8'))
            res = d['chart']['result'][0]
            timestamps = res.get('timestamp', [])
            indicators = res.get('indicators', {}).get('quote', [{}])[0]
            closes = indicators.get('close', [])
            volumes = indicators.get('volume', [])
            dates = [datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc).strftime('%Y-%m-%d') for ts in timestamps]
            clean_prices = [p if p is not None else 0.0 for p in closes]
            clean_vols = [v if v is not None else 0 for v in volumes]
            if dates and clean_prices:
                data = {"dates": dates, "prices": clean_prices, "volumes": clean_vols}
                self._set_cache(cache_key, data)
                return data
        except Exception as e:
            return {"error": str(e)}

        return {"error": f"No history found for {ticker}"}

    def get_dividends(self, ticker: str) -> Dict[str, Any]:
        """Fetches historical dividend payments."""
        cache_key = f"dividends_{ticker}"
        cached = self._get_from_cache(cache_key)
        if cached: return cached

        try:
            t = self._get_yf_ticker(ticker)
            divs = t.dividends
            if divs is None or divs.empty:
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
            t = self._get_yf_ticker(ticker)
            news = t.news
            self._set_cache(cache_key, news or [])
            return news or []
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
