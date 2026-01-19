"""Planned workout model for scheduled training sessions."""

from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import Integer, String, DateTime, Boolean, ForeignKey, Enum, Text
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.training_plan import TrainingPlan
    from app.models.activity import Activity


class WorkoutType(str, PyEnum):
    """Workout type categories."""
    ENDURANCE = "endurance"
    TEMPO = "tempo"
    THRESHOLD = "threshold"
    VO2MAX = "vo2max"
    RECOVERY = "recovery"
    SPRINT = "sprint"
    RACE = "race"


class PlannedWorkout(Base):
    """Planned workout model for scheduled training sessions."""

    __tablename__ = "planned_workouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    plan_id: Mapped[int] = mapped_column(Integer, ForeignKey("training_plans.id"), index=True)

    # Workout details
    date: Mapped[datetime] = mapped_column(DateTime, index=True)
    name: Mapped[str] = mapped_column(String(255))
    workout_type: Mapped[WorkoutType] = mapped_column(
        Enum(WorkoutType),
        default=WorkoutType.ENDURANCE
    )
    duration_minutes: Mapped[int] = mapped_column(Integer)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Structured intervals stored as JSON
    # Example: [{"name": "Warmup", "duration": 600, "power_target": 0.5},
    #           {"name": "Interval", "duration": 300, "power_target": 1.0, "repeats": 5}]
    intervals_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Targets
    target_tss: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    target_if: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Intensity Factor (percentage)

    # Completion tracking
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_activity_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("activities.id"), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    plan: Mapped["TrainingPlan"] = relationship("TrainingPlan", back_populates="workouts")
    completed_activity: Mapped[Optional["Activity"]] = relationship(
        "Activity", foreign_keys=[completed_activity_id]
    )

    def __repr__(self) -> str:
        return f"<PlannedWorkout(id={self.id}, name='{self.name}', date={self.date})>"
