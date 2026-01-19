"""Database configuration and session management."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.models.base import Base

settings = get_settings()

# Create SQLAlchemy engine
# For SQLite, we need check_same_thread=False for FastAPI
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False,
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all database tables."""
    # Import all models to ensure they are registered with Base
    from app.models import (  # noqa: F401
        User,
        Activity,
        FitnessMetric,
        TrainingPlan,
        PlannedWorkout,
        FitnessSignature,
        TrainingLoadRecord,
    )
    Base.metadata.create_all(bind=engine)
