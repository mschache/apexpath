"""Fitness metric model for storing daily CTL/ATL/TSB values."""

from datetime import datetime
from datetime import date as date_type
from typing import TYPE_CHECKING

from sqlalchemy import Integer, Float, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class FitnessMetric(Base):
    """Daily fitness metrics (CTL, ATL, TSB) for a user."""

    __tablename__ = "fitness_metrics"
    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_user_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    date: Mapped[date_type] = mapped_column(Date, index=True)

    # Training Stress Score for the day (sum of all activities)
    daily_tss: Mapped[float] = mapped_column(Float, default=0.0)

    # Chronic Training Load (Fitness) - 42-day EWMA
    ctl: Mapped[float] = mapped_column(Float, default=0.0)

    # Acute Training Load (Fatigue) - 7-day EWMA
    atl: Mapped[float] = mapped_column(Float, default=0.0)

    # Training Stress Balance (Form) - CTL - ATL
    tsb: Mapped[float] = mapped_column(Float, default=0.0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="fitness_metrics")

    def __repr__(self) -> str:
        return f"<FitnessMetric(id={self.id}, date={self.date}, ctl={self.ctl}, atl={self.atl}, tsb={self.tsb})>"
