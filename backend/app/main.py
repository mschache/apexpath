"""FastAPI application entry point for the Cycling Trainer API."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import create_tables
from app.routers import auth, activities, metrics, plans, workouts

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup: Create database tables
    create_tables()
    yield
    # Shutdown: Cleanup if needed


app = FastAPI(
    title="Cycling Trainer API",
    description="Backend API for the Cycling Trainer App - Strava integration, training plans, and fitness tracking",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS - allow multiple origins for development and production
cors_origins = [
    settings.FRONTEND_URL,
    "http://localhost:5173",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",  # Allow all Vercel preview deployments
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(activities.router, prefix="/api/activities", tags=["Activities"])
app.include_router(metrics.router, prefix="/api/metrics", tags=["Fitness Metrics"])
app.include_router(plans.router, prefix="/api/plans", tags=["Training Plans"])
app.include_router(workouts.router, prefix="/api/workouts", tags=["Workouts"])


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - API information."""
    return {
        "name": "Cycling Trainer API",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/health", tags=["Health"])
@app.get("/api/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
