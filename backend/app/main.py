"""
SUPERNATURAL Education Platform
Main FastAPI Application Entry Point
"""

from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from app.database import engine, Base
from app.api.routes import auth, mentors, students, sessions, quizzes, webhooks
from app.config import settings

# ─── Resolve paths relative to project root ───────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # SUPERNATURAL/
FRONTEND_DIR = BASE_DIR / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB tables on startup."""
    Base.metadata.create_all(bind=engine)
    print("✅ SUPERNATURAL Platform started successfully!")
    yield
    print("🛑 SUPERNATURAL Platform shutting down...")


app = FastAPI(
    title="SUPERNATURAL Education Platform",
    description="Fully Autonomous AI-Powered Education Platform",
    version="1.0.0",
    lifespan=lifespan,
)

# ─── CORS Middleware ──────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Static Files & Templates ─────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(FRONTEND_DIR / "templates"))

# ─── Register Routers ─────────────────────────────────────────────────────────
app.include_router(auth.router,      prefix="/api/auth",       tags=["Authentication"])
app.include_router(mentors.router,   prefix="/api/mentors",    tags=["Mentors"])
app.include_router(students.router,  prefix="/api/students",   tags=["Students"])
app.include_router(sessions.router,  prefix="/api/sessions",   tags=["Sessions"])
app.include_router(quizzes.router,   prefix="/api/quizzes",    tags=["Quizzes"])
app.include_router(webhooks.router,  prefix="/api/webhooks",   tags=["N8N Webhooks"])


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/register/student")
async def student_register(request: Request):
    return templates.TemplateResponse("student_onboarding.html", {"request": request})


@app.get("/register/mentor")
async def mentor_register(request: Request):
    return templates.TemplateResponse("mentor_onboarding.html", {"request": request})


@app.get("/dashboard")
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/health")
async def health_check():
    """Health check endpoint for Render."""
    return {
        "status": "healthy",
        "platform": "SUPERNATURAL",
        "environment": settings.APP_ENV,
    }


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
