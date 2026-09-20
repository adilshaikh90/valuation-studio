"""
Valuation Studio - Root application entry point for Render, Railway, and local deployment.
Delegates to api.index:app so that both `main:app` and `api.index:app` work out of the box.
"""
import os
import uvicorn
from api.index import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
