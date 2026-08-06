"""
Valuation Studio — Main FastAPI Application Entry Point.
Registers all route modules, sets up middleware, database, and static file serving.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import uvicorn

from .database.db import engine, Base
from .auth import routes as auth_routes
from .company import routes as company_routes
from .valuation import routes as valuation_routes
from .quant import routes as quant_routes
from .performance import routes as performance_routes
from .news import routes as news_routes
from .admin import routes as admin_routes
from .excel import routes as excel_routes
from .summary import routes as summary_routes

# ---------------------------------------------------------------------------
# App Setup
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Valuation Studio API",
    description="Institutional-grade financial valuation platform",
    version="1.0.0",
)

# CORS — allow all origins for development; tighten in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Database startup
# ---------------------------------------------------------------------------
@app.on_event("startup")
def on_startup():
    """Create all database tables on application startup."""
    Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------------------------
# Register all API routers
# ---------------------------------------------------------------------------
app.include_router(auth_routes.router)
app.include_router(company_routes.router)
app.include_router(valuation_routes.router)
app.include_router(quant_routes.router)
app.include_router(performance_routes.router)
app.include_router(news_routes.router)
app.include_router(admin_routes.router)
app.include_router(excel_routes.router)
app.include_router(summary_routes.router)

# ---------------------------------------------------------------------------
# Static files — serve the frontend
# ---------------------------------------------------------------------------
PUBLIC_DIR = Path(__file__).resolve().parent.parent / "public"

# Mount static asset directories
if (PUBLIC_DIR / "css").exists():
    app.mount("/css", StaticFiles(directory=str(PUBLIC_DIR / "css")), name="css")
if (PUBLIC_DIR / "js").exists():
    app.mount("/js", StaticFiles(directory=str(PUBLIC_DIR / "js")), name="js")
if (PUBLIC_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(PUBLIC_DIR / "assets")), name="assets")

# ---------------------------------------------------------------------------
# HTML page routes — serve frontend pages
# ---------------------------------------------------------------------------
HTML_PAGES = [
    "index", "login", "signup", "dashboard", "football-field",
    "valuation", "comps", "lbo-nav", "quant", "performance",
    "news", "download", "admin",
]

@app.get("/", include_in_schema=False)
async def serve_landing():
    """Serve the landing page."""
    index_file = PUBLIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "Valuation Studio API", "status": "running", "version": "1.0.0"}

# Generate routes for all HTML pages
for _page in HTML_PAGES:
    if _page == "index":
        continue  # Already handled above

    def _make_handler(page_name: str):
        async def handler():
            html_file = PUBLIC_DIR / f"{page_name}.html"
            if html_file.exists():
                return FileResponse(str(html_file))
            return {"error": f"Page {page_name} not found"}
        handler.__name__ = f"serve_{page_name.replace('-', '_')}"
        return handler

    app.get(f"/{_page}.html", include_in_schema=False)(_make_handler(_page))
    app.get(f"/{_page}", include_in_schema=False)(_make_handler(_page))

# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health_check():
    """Health check endpoint for Railway / monitoring."""
    return {"status": "healthy", "app": "Valuation Studio", "version": "1.0.0"}

# ---------------------------------------------------------------------------
# Run with: python -m uvicorn api.index:app --reload
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run("api.index:app", host="0.0.0.0", port=8000, reload=True)
