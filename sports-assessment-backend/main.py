"""
main.py
-------
FastAPI application entry point for the AI Sports Talent Assessment backend.

Startup:
  - Creates SQLite database tables via SQLAlchemy.
  - Registers all API routers.
  - Configures CORS for the React frontend (default: http://localhost:5173).
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from database import engine, Base, apply_safe_schema_updates
from routers import upload, process, results, athletes, auth, coach

# ─── Lifespan: DB init ────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables on startup (idempotent)
    Base.metadata.create_all(bind=engine)
    apply_safe_schema_updates()
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("models", exist_ok=True)
    yield
    # Cleanup (if needed) on shutdown


# ─── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="AI Sports Talent Assessment API",
    description=(
        "Backend AI pipeline for SAI Annexure A sports fitness tests.\n\n"
        "Tests supported: T3 (Sit & Reach), T4 (Vertical Jump), T5 (Standing Broad Jump), "
        "T8 (4×10m Shuttle Run), T9 (Sit-Ups).\n\n"
        "Each test uses MediaPipe Pose Estimation with rule-based analyzers."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ─── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://127.0.0.1:5173",
        "http://localhost:3000",   # Create React App fallback
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────
app.include_router(upload.router)
app.include_router(process.router)
app.include_router(results.router)
app.include_router(athletes.router)
app.include_router(auth.router)
app.include_router(coach.router)


# ─── Health check ─────────────────────────────────────────────────────────────
@app.get("/", tags=["health"])
def health_check():
    return {
        "status": "running",
        "service": "AI Sports Talent Assessment API",
        "version": "1.0.0",
        "tests_supported": ["T3", "T4", "T5", "T8", "T9"],
    }


@app.get("/api/health", tags=["health"])
def api_health():
    return {"status": "ok"}
