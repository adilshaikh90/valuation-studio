"""Test valuation and quant endpoints."""
import requests
import time

BASE = "http://127.0.0.1:8000"

# Login
r = requests.post(f"{BASE}/api/auth/login", json={"email": "admin@test.com", "password": "Test1234!"})
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

endpoints = [
    ("/api/valuation/AAPL/dcf-fcff", "DCF FCFF"),
    ("/api/valuation/AAPL/dcf-fcfe", "DCF FCFE"),
    ("/api/valuation/AAPL/ddm", "DDM"),
    ("/api/valuation/AAPL/apv", "APV"),
    ("/api/valuation/AAPL/comps", "Trading Comps"),
    ("/api/valuation/AAPL/nav", "NAV"),
    ("/api/valuation/AAPL/lbo", "LBO"),
    ("/api/valuation/AAPL/football-field", "Football Field"),
    ("/api/performance/AAPL", "Performance"),
    ("/api/news/AAPL", "News"),
]

for path, name in endpoints:
    try:
        r = requests.get(f"{BASE}{path}", headers=headers, timeout=60)
        status = r.status_code
        if status == 200:
            data = r.json()
            # Show a key value if possible
            if isinstance(data, dict):
                preview = str(data)[:80]
            elif isinstance(data, list):
                preview = f"[{len(data)} items]"
            else:
                preview = str(data)[:80]
            print(f"  OK  {name}: {status} - {preview}")
        else:
            print(f"FAIL  {name}: {status} - {r.text[:100]}")
    except Exception as e:
        print(f"ERR   {name}: {e}")

print("\nDone!")
