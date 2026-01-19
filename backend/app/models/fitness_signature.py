"""Fitness signature model for storing 3-parameter fitness model (Xert-style)."""

from datetime import datetime
from datetime import date as date_type
from typing import TYPE_CHECKING, Optional
import enum

from sqlalchemy import Integer, Float, Date, DateTime, ForeignKey, String, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class SignatureSource(str, enum.Enum):
    """Source of fitness signature measurement."""
    ESTIMATED = "estimated"      # Calculated from historical data
    BREAKTHROUGH = "breakthrough"  # Detected from breakthrough activity
    MANUAL = "manual"            # Manually entered by user


class FitnessSignature(Base):
    """
    3-parameter fitness model (Xert-style fitness signature).

    This model captures the athlete's current fitness across three key metrics:
    - Threshold Power (TP): Sustainable power output (~FTP)
    - High Intensity Energy (HIE): Anaerobic work capacity above TP
    - Peak Power (PP): Maximum neuromuscular power output
    """

    __tablename__ = "fitness_signatures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    date: Mapped[date_type] = mapped_column(Date, index=True)

    # Core fitness parameters
    threshold_power: Mapped[float] = mapped_column(Float)  # TP - watts (similar to FTP)
    high_intensity_energy: Mapped[float] = mapped_column(Float)  # HIE - kJ (anaerobic capacity)
    peak_power: Mapped[float] = mapped_column(Float)  # PP - watts (neuromuscular)

    # Athlete physical data for relative calculations
    weight_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Source of the signature
    source: Mapped[str] = mapped_column(
        String(50), default=SignatureSource.ESTIMATED.value
    )

    # Optional: linked to breakthrough activity
    activity_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("activities.id"), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="fitness_signatures")

    def __repr__(self) -> str:
        return f"<FitnessSignature(id={self.id}, date={self.date}, TP={self.threshold_power}, HIE={self.high_intensity_energy}, PP={self.peak_power})>"

    @property
    def tp_per_kg(self) -> Optional[float]:
        """Threshold power relative to body weight (W/kg)."""
        if self.weight_kg and self.weight_kg > 0:
            return self.threshold_power / self.weight_kg
        return None

    @property
    def pp_per_kg(self) -> Optional[float]:
        """Peak power relative to body weight (W/kg)."""
        if self.weight_kg and self.weight_kg > 0:
            return self.peak_power / self.weight_kg
        return None
