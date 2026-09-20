# Valuation Studio

**Institutional-grade financial valuation. For everyone.**

DCF, DDM, APV, LBO, NAV, Trading Comps, Monte Carlo, Regression Multiples - enter any public ticker and get a complete IB-level analysis in seconds. Download a full Excel financial model with live formulas.

---

## Features

| Category | What's Included |
|----------|----------------|
| **Valuation Models** | DCF (FCFF), DCF (FCFE), DDM (3 variants), APV, Trading Comps, NAV, LBO |
| **Quant Lab** | Bootstrapped Monte Carlo (10K sims), Sensitivity Tables, Tornado/Scenario Analysis, Probability-Weighted Scenarios, Regression-Implied Multiples |
| **Outputs** | Football Field Chart, Plain English Summary, 14-sheet Excel Model with live formulas |
| **Coverage** | Any public company, any exchange, 50+ currencies auto-detected |
| **Platform** | User auth, admin dashboard with analytics, search history |

## Tech Stack

- **Backend:** Python, FastAPI, SQLAlchemy, SQLite
- **Data:** yfinance (free, no API key required)
- **Excel:** openpyxl (real formulas, not static values)
- **Frontend:** Vanilla HTML/CSS/JS, Chart.js
- **Deployment:** Railway (free tier with GitHub Education)

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/valuation-studio.git
cd valuation-studio
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux
pip install -r requirements.txt
```

### 2. Run locally

```bash
python -m uvicorn api.index:app --reload
```

Open **http://localhost:8000** in your browser.

### 3. Create an admin account

Sign up normally, then run this one-time command to promote yourself:

```bash
python -c "
from api.database.db import engine, SessionLocal
from api.database.models import User
db = SessionLocal()
user = db.query(User).filter(User.email == 'YOUR_EMAIL').first()
if user:
    user.role = 'admin'
    db.commit()
    print(f'{user.email} is now admin')
"
```

## Deploy to Render (100% Free)

### Method A: Blueprint (Automatic)
1. Push this repository to your GitHub.
2. Go to [dashboard.render.com](https://dashboard.render.com) → Click **New +** → **Blueprint**.
3. Select your repository. Render will auto-detect [`render.yaml`](file:///c:/Users/adils/Downloads/valuation-studio/render.yaml) and configure the service.
4. Click **Apply**.

### Method B: Manual Web Service
1. Go to [dashboard.render.com](https://dashboard.render.com) → Click **New +** → **Web Service**.
2. Connect your GitHub repository.
3. Configure the following settings:
   - **Root Directory:** *(Leave blank)*
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type:** `Free`
4. In **Environment Variables**, add:
   - `PYTHON_VERSION` = `3.11.9`
   - `SECRET_KEY` = `any-random-secret-string`
5. Click **Create Web Service**.

## Deploy to Railway

1. Push to GitHub
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Select your repo
4. Set environment variable: `SECRET_KEY=your-random-secret-key`
5. Railway auto-detects the `Procfile` and deploys

**Cost:** Free with GitHub Education ($5/month credit).


## Project Structure

```
valuation-studio/
├── api/
│   ├── index.py              # FastAPI app entry point
│   ├── auth/                 # JWT auth (signup, login)
│   ├── company/              # yfinance data fetcher + currency
│   ├── valuation/            # DCF, DDM, APV, Comps, NAV, LBO, Football Field
│   ├── quant/                # Monte Carlo, Sensitivity, Tornado, Regression
│   ├── performance/          # 5-year stock performance + S&P benchmark
│   ├── news/                 # Company news
│   ├── excel/                # 14-sheet Excel model generator
│   ├── summary/              # Plain English summary
│   ├── admin/                # User management + analytics
│   └── database/             # SQLAlchemy models + SQLite
├── public/
│   ├── css/                  # Design system + component styles
│   ├── js/                   # API client, app logic, Chart.js helpers
│   └── *.html                # 13 frontend pages
├── requirements.txt
├── Procfile                  # Railway deployment
├── railway.json              # Railway config
└── README.md
```

## Disclaimer

This application is for **educational and research purposes only**. It does not constitute investment advice. The valuations generated are based on publicly available data and standardized financial models. Past performance does not guarantee future results.

---

Built with ❤️ by Valuation Studio
