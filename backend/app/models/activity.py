"""Activity model for storing synced Strava activities."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class Activity(Base):
    """Activity model for storing synced Strava activities."""

    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    strava_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)

    # Activity details
    name: Mapped[str] = mapped_column(String(255))
    activity_type: Mapped[str] = mapped_column(String(50))  # e.g., "Ride", "VirtualRide"
    date: Mapped[datetime] = mapped_column(DateTime, index=True)

    # Performance metrics
    duration_seconds: Mapped[int] = mapped_column(Integer)
    distance_meters: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    average_power: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # watts
    normalized_power: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # watts
    average_hr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # bpm
    max_hr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # bpm
    tss: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Training Stress Score

    # Additional metrics
    elevation_gain: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # meters
    average_speed: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # m/s
    max_speed: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # m/s
    calories: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="activities")

    def __repr__(self) -> str:
        return f"<Activity(id={self.id}, name='{self.name}', date={self.date})>"
