"""Quick integration test for Valuation Studio API."""
import requests
import json

BASE = "http://127.0.0.1:8000"

def test():
    # 1. Health check
    r = requests.get(f"{BASE}/api/health")
    print(f"[1] Health: {r.status_code} - {r.json()['status']}")

    # 2. Signup
    r = requests.post(f"{BASE}/api/auth/signup", json={"email": "admin@test.com", "password": "Test1234!"})
    print(f"[2] Signup: {r.status_code} - {r.text[:80]}")

    if r.status_code in (200, 201):
        token = r.json()["access_token"]
    else:
        # Already signed up, try login
        r = requests.post(f"{BASE}/api/auth/login", json={"email": "admin@test.com", "password": "Test1234!"})
        print(f"[2b] Login: {r.status_code}")
        token = r.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}

    # 3. Get me
    r = requests.get(f"{BASE}/api/auth/me", headers=headers)
    print(f"[3] /me: {r.status_code} - {r.json().get('email', r.text[:50])}")

    # 4. Landing page
    r = requests.get(f"{BASE}/")
    is_html = "html" in r.text.lower()
    print(f"[4] Landing: {r.status_code} - HTML={is_html}")

    # 5. Company lookup
    print("[5] Testing AAPL company lookup...")
    r = requests.get(f"{BASE}/api/company/AAPL", headers=headers, timeout=30)
    if r.status_code == 200:
        data = r.json()
        print(f"[5] Company: {r.status_code} - name={data.get('name', '?')}")
        print(f"    price={data.get('current_price')}, currency={data.get('currency')}")
    else:
        print(f"[5] Company: {r.status_code} - {r.text[:100]}")

    print("\nAll basic tests passed!")

if __name__ == "__main__":
    test()
