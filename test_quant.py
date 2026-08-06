"""Test quant and Excel endpoints."""
import requests

BASE = "http://127.0.0.1:8000"

# Login
r = requests.post(f"{BASE}/api/auth/login", json={"email": "admin@test.com", "password": "Test1234!"})
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

endpoints = [
    ("/api/quant/AAPL/sensitivity", "Sensitivity"),
    ("/api/quant/AAPL/tornado", "Tornado"),
    ("/api/quant/AAPL/scenarios", "Scenarios"),
    ("/api/quant/AAPL/scenario-weighting", "Scenario Weighting"),
    ("/api/quant/AAPL/regression-multiples", "Regression Multiples"),
    ("/api/quant/AAPL/monte-carlo?iterations=1000", "Monte Carlo (1K)"),
]

for path, name in endpoints:
    try:
        r = requests.get(f"{BASE}{path}", headers=headers, timeout=120)
        if r.status_code == 200:
            data = r.json()
            preview = str(data)[:80]
            print(f"  OK  {name}: {r.status_code} - {preview}")
        else:
            print(f"FAIL  {name}: {r.status_code} - {r.text[:150]}")
    except Exception as e:
        print(f"ERR   {name}: {e}")

# Test Excel download
print("\nTesting Excel download...")
try:
    r = requests.get(f"{BASE}/api/excel/AAPL/download", headers=headers, timeout=120)
    if r.status_code == 200:
        content_type = r.headers.get("content-type", "")
        size_kb = len(r.content) / 1024
        print(f"  OK  Excel: {r.status_code} - {size_kb:.1f} KB, type={content_type[:50]}")
    else:
        print(f"FAIL  Excel: {r.status_code} - {r.text[:150]}")
except Exception as e:
    print(f"ERR   Excel: {e}")

# Test Summary
print("\nTesting Summary...")
try:
    r = requests.get(f"{BASE}/api/summary/AAPL", headers=headers, timeout=120)
    if r.status_code == 200:
        data = r.json()
        print(f"  OK  Summary: {r.status_code}")
        print(f"      Text: {data.get('summary_text', '')[:120]}...")
    else:
        print(f"FAIL  Summary: {r.status_code} - {r.text[:150]}")
except Exception as e:
    print(f"ERR   Summary: {e}")

print("\nDone!")
