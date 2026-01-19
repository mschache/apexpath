"""Training load model for 3D training load tracking (Xert/Banister impulse-response model)."""

from datetime import datetime
from datetime import date as date_type
from typing import TYPE_CHECKING, Optional
import enum

from sqlalchemy import Integer, Float, Date, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class TrainingStatus(str, enum.Enum):
    """Training readiness status based on form values."""
    VERY_FRESH = "very_fresh"    # Green - Extended recovery, high readiness
    FRESH = "fresh"              # Blue - Recovered, ready for training
    TIRED = "tired"              # Yellow - High/Peak systems need recovery
    VERY_TIRED = "very_tired"    # Red - All systems need recovery
    DETRAINING = "detraining"    # Brown - Prolonged inactivity


class TrainingLoadRecord(Base):
    """
    Daily 3D training load tracking using the Banister impulse-response model.

    Tracks three separate training load systems with different time constants:
    - Low (Aerobic): 60-day time constant, slow adaptation
    - High (Anaerobic): 22-day time constant, moderate adaptation
    - Peak (Neuromuscular): 22-day time constant, moderate adaptation

    Each system has:
    - Training Load (TL): Fitness accumulation (positive adaptation)
    - Recovery Load (RL): Fatigue accumulation (negative short-term effect)
    - Form: TL - RL (readiness indicator)
    """

    __tablename__ = "training_loads"
    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_training_load_user_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    date: Mapped[date_type] = mapped_column(Date, index=True)

    # Training Load (fitness) - 3D components
    tl_low: Mapped[float] = mapped_column(Float, default=0.0)   # Low system TL (60-day constant)
    tl_high: Mapped[float] = mapped_column(Float, default=0.0)  # High system TL (22-day constant)
    tl_peak: Mapped[float] = mapped_column(Float, default=0.0)  # Peak system TL (22-day constant)

    # Recovery Load (fatigue) - 3D components
    rl_low: Mapped[float] = mapped_column(Float, default=0.0)
    rl_high: Mapped[float] = mapped_column(Float, default=0.0)
    rl_peak: Mapped[float] = mapped_column(Float, default=0.0)

    # Form (readiness) - calculated but stored for quick access
    form_low: Mapped[float] = mapped_column(Float, default=0.0)   # tl_low - rl_low
    form_high: Mapped[float] = mapped_column(Float, default=0.0)
    form_peak: Mapped[float] = mapped_column(Float, default=0.0)

    # Daily XSS (eXcess Strain Score) breakdown
    xss_total: Mapped[float] = mapped_column(Float, default=0.0)
    xss_low: Mapped[float] = mapped_column(Float, default=0.0)
    xss_high: Mapped[float] = mapped_column(Float, default=0.0)
    xss_peak: Mapped[float] = mapped_column(Float, default=0.0)

    # Training status (derived from form values)
    status: Mapped[str] = mapped_column(
        String(50), default=TrainingStatus.FRESH.value
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="training_loads")

    def __repr__(self) -> str:
        return (
            f"<TrainingLoadRecord(id={self.id}, date={self.date}, "
            f"TL=[{self.tl_low:.1f}, {self.tl_high:.1f}, {self.tl_peak:.1f}], "
            f"Form=[{self.form_low:.1f}, {self.form_high:.1f}, {self.form_peak:.1f}], "
            f"status={self.status})>"
        )

    @property
    def total_tl(self) -> float:
        """Total training load across all systems."""
        return self.tl_low + self.tl_high + self.tl_peak

    @property
    def total_rl(self) -> float:
        """Total recovery load across all systems."""
        return self.rl_low + self.rl_high + self.rl_peak

    @property
    def total_form(self) -> float:
        """Overall form indicator (weighted average)."""
        # Weight Low system more heavily as it represents base fitness
        return (self.form_low * 0.5) + (self.form_high * 0.3) + (self.form_peak * 0.2)

    def calculate_form(self) -> None:
        """Update form values from TL and RL."""
        self.form_low = self.tl_low - self.rl_low
        self.form_high = self.tl_high - self.rl_high
        self.form_peak = self.tl_peak - self.rl_peak

    def update_status(self) -> None:
        """
        Determine training status from form values.

        Status is determined by the combination of form values:
        - Very Fresh (Green): All forms positive, high overall form
        - Fresh (Blue): At least one system ready, moderate overall form
        - Tired (Yellow): High/Peak negative, Low still positive
        - Very Tired (Red): All systems negative
        - Detraining (Brown): Very low TL values indicating prolonged inactivity
        """
        # Check for detraining (very low TL across all systems)
        if self.total_tl < 10:
            self.status = TrainingStatus.DETRAINING.value
            return

        # Calculate overall form state
        all_negative = (
            self.form_low < 0 and
            self.form_high < 0 and
            self.form_peak < 0
        )
        all_positive = (
            self.form_low >= 0 and
            self.form_high >= 0 and
            self.form_peak >= 0
        )
        high_overall_form = self.total_form > 10

        if all_negative:
            self.status = TrainingStatus.VERY_TIRED.value
        elif all_positive and high_overall_form:
            self.status = TrainingStatus.VERY_FRESH.value
        elif all_positive or self.form_low >= 0:
            self.status = TrainingStatus.FRESH.value
        else:
            self.status = TrainingStatus.TIRED.value
