"""Training plan model for structured training programs."""

from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Integer, String, DateTime, Boolean, Float, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.planned_workout import PlannedWorkout


class TrainingPhilosophy(str, PyEnum):
    """Training philosophy options."""
    POLARIZED = "polarized"
    SWEET_SPOT = "sweet_spot"
    TRADITIONAL = "traditional"


class TrainingPlan(Base):
    """Training plan model for structured training programs."""

    __tablename__ = "training_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)

    # Plan details
    name: Mapped[str] = mapped_column(String(255))
    philosophy: Mapped[TrainingPhilosophy] = mapped_column(
        Enum(TrainingPhilosophy),
        default=TrainingPhilosophy.POLARIZED
    )
    start_date: Mapped[datetime] = mapped_column(DateTime)
    end_date: Mapped[datetime] = mapped_column(DateTime)
    weekly_hours: Mapped[float] = mapped_column(Float)  # Target hours per week
    goal_event: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Optional goal event name

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="training_plans")
    workouts: Mapped[List["PlannedWorkout"]] = relationship(
        "PlannedWorkout", back_populates="plan", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<TrainingPlan(id={self.id}, name='{self.name}', philosophy={self.philosophy})>"
