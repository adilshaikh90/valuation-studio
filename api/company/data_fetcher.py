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
import numpy as np
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
            ttl = item.get('ttl', self.CACHE_TTL)
            if time.time() - item['timestamp'] < ttl:
                return item['data']
        return None

    def _set_cache(self, key: str, data: Any, ttl: Optional[int] = None) -> None:
        """Sets an item in the cache with optional custom TTL."""
        self._cache[key] = {
            'data': data,
            'timestamp': time.time(),
            'ttl': ttl or self.CACHE_TTL
        }

    def _get_yf_ticker(self, ticker: str):
        """Get (and cache) the raw yfinance Ticker object."""
        ticker = ticker.upper().strip()
        cache_key = f"yf_ticker_{ticker}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        t = yf.Ticker(ticker)
        self._set_cache(cache_key, t)
        return t

    def detect_country(self, ticker: str, info: Optional[Dict[str, Any]] = None) -> str:
        """Determines company country of listing from metadata, exchange, or ticker suffix."""
        if info:
            c = info.get('country')
            if c and str(c).strip() not in ['Global', 'General', '–', '-', '']:
                return str(c).strip()

        tk = ticker.upper().strip()
        if tk.endswith('.L'): return 'United Kingdom'
        if tk.endswith('.DE'): return 'Germany'
        if tk.endswith('.PA'): return 'France'
        if tk.endswith('.AS'): return 'Netherlands'
        if tk.endswith('.MI'): return 'Italy'
        if tk.endswith('.MC'): return 'Spain'
        if tk.endswith('.SW') or tk.endswith('.VX'): return 'Switzerland'
        if tk.endswith('.ST'): return 'Sweden'
        if tk.endswith('.TO'): return 'Canada'
        if tk.endswith('.AX'): return 'Australia'
        if tk.endswith('.T'): return 'Japan'
        if tk.endswith('.HK'): return 'Hong Kong'
        if tk.endswith('.NS') or tk.endswith('.BO'): return 'India'
        if tk.endswith('.SA'): return 'Brazil'
        if tk.endswith('.KS') or tk.endswith('.KQ'): return 'South Korea'

        if info:
            exch = str(info.get('exchange', '') or info.get('exchDisp', '')).upper()
            if any(e in exch for e in ['NASDAQ', 'NYSE', 'AMEX', 'BATS', 'OTC', 'NMS', 'NGS', 'NCM']):
                return 'United States'
            if 'LONDON' in exch or 'LSE' in exch:
                return 'United Kingdom'

        if '.' not in tk:
            return 'United States'
        return 'United States'

    def calculate_beta(self, ticker: str, country: Optional[str] = None) -> float:
        """
        Calculates 5-year monthly covariance beta against the sovereign national benchmark.
        Falls back to 2-year weekly if monthly series is sparse.
        """
        ticker = ticker.upper().strip()
        cache_key = f"beta_{ticker}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        if not country or str(country).strip() in ['Global', 'General', '–', '-', '']:
            country = self.detect_country(ticker)

        c_low = str(country).lower()
        if any(c in c_low for c in ['united kingdom', 'uk', 'britain', 'england']) or ticker.endswith('.L'):
            bench_sym = "^FTSE"
        elif 'germany' in c_low or ticker.endswith('.DE'):
            bench_sym = "^GDAXI"
        elif 'france' in c_low or ticker.endswith('.PA'):
            bench_sym = "^FCHI"
        elif 'netherlands' in c_low or ticker.endswith('.AS'):
            bench_sym = "^AEX"
        elif 'switzerland' in c_low or ticker.endswith('.SW') or ticker.endswith('.VX'):
            bench_sym = "^SSMI"
        elif 'japan' in c_low or ticker.endswith('.T'):
            bench_sym = "^N225"
        elif 'india' in c_low or ticker.endswith('.NS') or ticker.endswith('.BO'):
            bench_sym = "^NSEI"
        elif 'canada' in c_low or ticker.endswith('.TO'):
            bench_sym = "^GSPTSE"
        elif 'australia' in c_low or ticker.endswith('.AX'):
            bench_sym = "^AXJO"
        else:
            bench_sym = "^GSPC"

        try:
            stock_t = self._get_yf_ticker(ticker)
            bench_t = self._get_yf_ticker(bench_sym)

            s_hist = stock_t.history(period="5y", interval="1mo")["Close"].dropna()
            b_hist = bench_t.history(period="5y", interval="1mo")["Close"].dropna()

            if len(s_hist) < 15 or len(b_hist) < 15:
                s_hist = stock_t.history(period="2y", interval="1wk")["Close"].dropna()
                b_hist = bench_t.history(period="2y", interval="1wk")["Close"].dropna()

            if not s_hist.empty and not b_hist.empty:
                s_hist.index = s_hist.index.tz_localize(None) if s_hist.index.tz is not None else s_hist.index
                b_hist.index = b_hist.index.tz_localize(None) if b_hist.index.tz is not None else b_hist.index
                combined = pd.DataFrame({'stock': s_hist, 'bench': b_hist}).dropna()
                if len(combined) >= 10:
                    s_rets = combined['stock'].pct_change().dropna()
                    b_rets = combined['bench'].pct_change().dropna()
                    cov = np.cov(s_rets, b_rets)[0, 1]
                    var_b = np.var(b_rets, ddof=1)
                    if var_b > 0 and not np.isnan(cov):
                        b_calc = round(float(cov / var_b), 3)
                        self._set_cache(cache_key, b_calc)
                        return b_calc
        except Exception:
            pass

        return 1.0

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
                res['exchangeName'] = meta.get('exchangeName')
        except Exception:
            pass

        # 2. Search API (v1) - gives company name, sector, industry, country
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
                if target_q.get('exchDisp'):
                    res['exchDisp'] = target_q.get('exchDisp')
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

        # Country detection
        res['country'] = self.detect_country(ticker, res)
        return res

    def get_raw_info(self, ticker: str) -> Dict[str, Any]:
        """Fetches and caches raw yf.Ticker(ticker).info dictionary with fallback enrichment."""
        ticker = ticker.upper().strip()
        cache_key = f"raw_info_{ticker}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        info = {}
        for attempt in range(2):
            try:
                t = yf.Ticker(ticker)
                info = t.info or {}
                if info and info.get('regularMarketPrice') and (info.get('shortName') or info.get('longName')):
                    break
            except Exception:
                time.sleep(0.3)

        # If info is empty or missing vital price/name data, enrich from direct Yahoo APIs
        if not info or not info.get('regularMarketPrice') or not info.get('shortName'):
            fallback = self._fetch_direct_yahoo(ticker)
            for k, v in fallback.items():
                if v is not None and not info.get(k):
                    info[k] = v

        if info:
            is_rich = bool(info.get('regularMarketPrice') and (info.get('beta') or info.get('trailingPE') or info.get('trailingEps')))
            ttl = self.CACHE_TTL if is_rich else 30
            self._set_cache(cache_key, info, ttl=ttl)
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

        # 1. Resolve Country
        country = info.get('country')
        if not country or str(country).strip() in ['Global', 'General', '–', '-', '']:
            country = self.detect_country(ticker, info)

        # 2. Resolve Beta (Institutional 5Y Monthly Beta)
        raw_beta = info.get('beta')
        if raw_beta is not None and not pd.isna(raw_beta):
            try:
                b_val = float(raw_beta)
                if abs(b_val) > 0.001 and abs(b_val - 1.0) > 0.0001:
                    beta = round(b_val, 3)
                else:
                    calc = self.calculate_beta(ticker, country=country)
                    beta = calc if calc is not None else round(b_val, 3)
            except (ValueError, TypeError):
                beta = self.calculate_beta(ticker, country=country)
        else:
            beta = self.calculate_beta(ticker, country=country)

        # 3. Resolve EPS
        eps = info.get('trailingEps') or info.get('epsTrailingTwelveMonths')
        if eps is None or pd.isna(eps):
            eps = info.get('forwardEps')
        if eps is None or pd.isna(eps):
            try:
                inc_df = self.get_income_stmt(ticker)
                if inc_df is not None and not inc_df.empty:
                    for row in ['Diluted EPS', 'Basic EPS', 'DilutedEPS', 'BasicEPS']:
                        if row in inc_df.index:
                            v = inc_df.loc[row].dropna()
                            if len(v) > 0 and pd.notna(v.iloc[0]):
                                eps = round(float(v.iloc[0]), 2)
                                break
                    if eps is None:
                        for ni_row in ['Diluted NI Availto Com Stockholders', 'Net Income Common Stockholders', 'Net Income']:
                            if ni_row in inc_df.index:
                                ni_v = inc_df.loc[ni_row].dropna()
                                shares = info.get('sharesOutstanding') or info.get('shares')
                                if len(ni_v) > 0 and pd.notna(ni_v.iloc[0]) and shares and float(shares) > 0:
                                    eps = round(float(ni_v.iloc[0]) / float(shares), 2)
                                    break
            except Exception:
                pass
        else:
            eps = round(float(eps), 2)

        # 4. Resolve P/E Ratio
        pe_ratio = info.get('trailingPE')
        if (pe_ratio is None or pd.isna(pe_ratio)) and price and eps and eps > 0:
            pe_ratio = round(price / eps, 2)
        elif pe_ratio is not None and not pd.isna(pe_ratio):
            pe_ratio = round(float(pe_ratio), 2)

        # 5. Resolve Forward P/E
        forward_pe = info.get('forwardPE')
        if (forward_pe is None or pd.isna(forward_pe)) and info.get('forwardEps') and price:
            try:
                f_eps = float(info['forwardEps'])
                if f_eps > 0:
                    forward_pe = round(price / f_eps, 2)
            except Exception:
                pass
        if forward_pe is None and pe_ratio is not None:
            forward_pe = pe_ratio
        elif forward_pe is not None and not pd.isna(forward_pe):
            forward_pe = round(float(forward_pe), 2)

        # 6. Resolve Dividend Yield
        div_yield = info.get('dividendYield') or info.get('trailingAnnualDividendYield')
        if div_yield is None or pd.isna(div_yield):
            try:
                t = self._get_yf_ticker(ticker)
                divs = getattr(t, 'dividends', None)
                if divs is not None and not divs.empty:
                    now = pd.Timestamp.now()
                    one_yr_ago = now - pd.Timedelta(days=365)
                    divs.index = divs.index.tz_localize(None) if divs.index.tz is not None else divs.index
                    last_year_divs = divs[divs.index >= one_yr_ago]
                    tot = float(last_year_divs.sum())
                    if tot > 0 and price and price > 0:
                        div_yield = round((tot / price) * 100, 2)
                    else:
                        div_yield = 0.0
                else:
                    div_yield = 0.0
            except Exception:
                div_yield = None
        else:
            try:
                div_val = float(div_yield)
                if 0 < div_val < 0.15:
                    div_yield = round(div_val * 100, 2)
                else:
                    div_yield = round(div_val, 2)
            except Exception:
                div_yield = None

        # 7. Resolve Employees
        employees = info.get('fullTimeEmployees') or info.get('employees')
        if employees is not None and not pd.isna(employees):
            try:
                employees = int(employees)
            except Exception:
                employees = None

        # 8. Resolve Description
        desc = info.get('longBusinessSummary')
        sector = info.get('sector') or 'General'
        industry = info.get('industry') or 'General'
        mcap = info.get('marketCap')
        if not desc or len(str(desc).strip()) < 30:
            mcap_str = f"market capitalization of {curr_sym}{mcap:,.0f}" if mcap else "active market capitalization"
            desc = (
                f"{name} ({ticker}) operates in the {sector} sector ({industry} industry) "
                f"and is listed in {country}. The company currently has a {mcap_str} "
                f"under ticker symbol {ticker}."
            )

        data = {
            "name": name or ticker,
            "ticker": ticker,
            "sector": sector,
            "industry": industry,
            "country": country,
            "market_cap": mcap,
            "currency": curr,
            "currency_symbol": curr_sym,
            "current_price": price,
            "price_change": price_change,
            "price_change_pct": price_change_pct,
            "beta": beta,
            "shares_outstanding": info.get('sharesOutstanding'),
            "52_week_high": info.get('fiftyTwoWeekHigh'),
            "52_week_low": info.get('fiftyTwoWeekLow'),
            "pe_ratio": pe_ratio,
            "forward_pe": forward_pe,
            "dividend_yield": div_yield,
            "eps": eps,
            "employees": employees,
            "description": desc,
            "website": info.get('website') or ''
        }
        is_rich = bool(price and beta and (pe_ratio or eps))
        ttl = self.CACHE_TTL if is_rich else 30
        self._set_cache(cache_key, data, ttl=ttl)
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
