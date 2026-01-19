"""User model for storing Strava-authenticated users."""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Integer, String, DateTime, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.activity import Activity
    from app.models.training_plan import TrainingPlan
    from app.models.fitness_metric import FitnessMetric
    from app.models.fitness_signature import FitnessSignature
    from app.models.training_load import TrainingLoadRecord


class User(Base):
    """User model for storing Strava-authenticated users."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    strava_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True, nullable=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ftp: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Functional Threshold Power in watts
    profile_image: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Physical attributes
    weight_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_hr: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    resting_hr: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Training profile
    experience_level: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # beginner/intermediate/advanced/elite
    primary_discipline: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # road/mtb/gravel/track/indoor
    default_weekly_hours: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Equipment
    has_power_meter: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    has_indoor_trainer: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # Strava OAuth tokens
    strava_access_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    strava_refresh_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    strava_token_expires_at: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Unix timestamp

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    activities: Mapped[List["Activity"]] = relationship(
        "Activity", back_populates="user", cascade="all, delete-orphan"
    )
    training_plans: Mapped[List["TrainingPlan"]] = relationship(
        "TrainingPlan", back_populates="user", cascade="all, delete-orphan"
    )
    fitness_metrics: Mapped[List["FitnessMetric"]] = relationship(
        "FitnessMetric", back_populates="user", cascade="all, delete-orphan"
    )
    fitness_signatures: Mapped[List["FitnessSignature"]] = relationship(
        "FitnessSignature", back_populates="user", cascade="all, delete-orphan"
    )
    training_loads: Mapped[List["TrainingLoadRecord"]] = relationship(
        "TrainingLoadRecord", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, name='{self.name}', strava_id={self.strava_id})>"

    @property
    def is_token_expired(self) -> bool:
        """Check if the Strava access token has expired."""
        if self.strava_token_expires_at is None:
            return True
        return datetime.utcnow().timestamp() >= self.strava_token_expires_at
