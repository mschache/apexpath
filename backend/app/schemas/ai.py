"""Pydantic schemas for AI training plan generation API."""

from datetime import date as date_type
from typing import Optional

from pydantic import BaseModel, Field


# --- Fitness Signature Schemas ---

class FitnessSignatureBase(BaseModel):
    """Base schema for fitness signature (3-parameter model)."""
    threshold_power: float = Field(..., ge=0, description="Threshold Power (TP) in watts")
    high_intensity_energy: float = Field(..., ge=0, description="High Intensity Energy (HIE) in kJ")
    peak_power: float = Field(..., ge=0, description="Peak Power (PP) in watts")
    weight_kg: Optional[float] = Field(None, ge=0, description="Athlete weight in kg")


class FitnessSignatureResponse(FitnessSignatureBase):
    """Schema for fitness signature API responses."""
    id: int = Field(..., description="Unique signature ID")
    user_id: int = Field(..., description="User ID")
    date: date_type = Field(..., description="Date of signature")
    source: str = Field(..., description="Source of measurement")

    class Config:
        from_attributes = True


# --- 3D Training Load Schemas ---

class TrainingLoad3D(BaseModel):
    """3-dimensional training load values."""
    low: float = Field(default=0, description="Low (aerobic) system load")
    high: float = Field(default=0, description="High (anaerobic) system load")
    peak: float = Field(default=0, description="Peak (neuromuscular) system load")


class XSSBreakdownSchema(BaseModel):
    """XSS breakdown across training systems."""
    total: float = Field(default=0, ge=0, description="Total XSS")
    low: float = Field(default=0, ge=0, description="Low intensity XSS")
    high: float = Field(default=0, ge=0, description="High intensity XSS")
    peak: float = Field(default=0, ge=0, description="Peak intensity XSS")


class TrainingLoadRecordResponse(BaseModel):
    """Schema for training load record response."""
    id: int = Field(..., description="Record ID")
    user_id: int = Field(..., description="User ID")
    date: date_type = Field(..., description="Date of record")

    # Training Load
    tl_low: float = Field(..., description="Low system Training Load")
    tl_high: float = Field(..., description="High system Training Load")
    tl_peak: float = Field(..., description="Peak system Training Load")

    # Recovery Load
    rl_low: float = Field(..., description="Low system Recovery Load")
    rl_high: float = Field(..., description="High system Recovery Load")
    rl_peak: float = Field(..., description="Peak system Recovery Load")

    # Form
    form_low: float = Field(..., description="Low system Form")
    form_high: float = Field(..., description="High system Form")
    form_peak: float = Field(..., description="Peak system Form")

    # Daily XSS
    xss_total: float = Field(..., description="Total daily XSS")
    xss_low: float = Field(..., description="Low daily XSS")
    xss_high: float = Field(..., description="High daily XSS")
    xss_peak: float = Field(..., description="Peak daily XSS")

    # Status
    status: str = Field(..., description="Training status")

    class Config:
        from_attributes = True


# --- Athlete Context Schemas ---

class DayAvailability(BaseModel):
    """Availability for a single day."""
    available: bool = Field(default=False, description="Is training available this day")
    start_time: Optional[str] = Field(None, description="Preferred start time (HH:MM)")
    duration: int = Field(default=60, ge=15, le=480, description="Available duration in minutes")


class ForecastConfigCreate(BaseModel):
    """Schema for creating a training forecast."""
    program_type: str = Field(
        default="goal",
        description="Type of program: goal, event, or race"
    )
    target_date: date_type = Field(..., description="Target date for the plan")
    max_weekly_hours: float = Field(
        default=10.0,
        ge=3,
        le=30,
        description="Maximum training hours per week"
    )
    event_readiness: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Desired readiness level (1=low, 5=peak)"
    )
    periodization_level: int = Field(
        default=50,
        ge=0,
        le=100,
        description="Periodization phase (0=early base, 100=race peak)"
    )
    polarization_ratio: str = Field(
        default="80/20",
        description="Training intensity ratio (easy/hard)"
    )
    recovery_demands: int = Field(
        default=50,
        ge=0,
        le=100,
        description="Recovery needs (0=aggressive, 100=conservative)"
    )
    available_days: dict[str, DayAvailability] = Field(
        default_factory=lambda: {
            "Monday": DayAvailability(available=True, duration=60),
            "Tuesday": DayAvailability(available=True, duration=60),
            "Wednesday": DayAvailability(available=True, duration=60),
            "Thursday": DayAvailability(available=True, duration=60),
            "Friday": DayAvailability(available=True, duration=60),
            "Saturday": DayAvailability(available=True, duration=90),
            "Sunday": DayAvailability(available=True, duration=90),
        },
        description="Training availability by day"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "program_type": "event",
                "target_date": "2025-06-01",
                "max_weekly_hours": 10,
                "event_readiness": 4,
                "periodization_level": 30,
                "polarization_ratio": "80/20",
                "recovery_demands": 50,
                "available_days": {
                    "Monday": {"available": True, "duration": 60},
                    "Tuesday": {"available": True, "duration": 90},
                    "Wednesday": {"available": False, "duration": 0},
                    "Thursday": {"available": True, "duration": 60},
                    "Friday": {"available": True, "duration": 60},
                    "Saturday": {"available": True, "duration": 120},
                    "Sunday": {"available": True, "duration": 90}
                }
            }
        }


class AthleteContextResponse(BaseModel):
    """Schema for athlete context used by AI planner."""
    user_id: int = Field(..., description="User ID")
    ftp: int = Field(..., ge=0, description="Functional Threshold Power")

    # Fitness signature
    signature: FitnessSignatureBase = Field(..., description="Current fitness signature")

    # 3D Training Load
    training_load: TrainingLoad3D = Field(..., description="Current training load")
    recovery_load: TrainingLoad3D = Field(..., description="Current recovery load")
    form: TrainingLoad3D = Field(..., description="Current form")
    status: str = Field(..., description="Training readiness status")

    # Metrics
    weekly_xss_average: float = Field(..., ge=0, description="Average weekly XSS")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "ftp": 250,
                "signature": {
                    "threshold_power": 250,
                    "high_intensity_energy": 25,
                    "peak_power": 800,
                    "weight_kg": 75
                },
                "training_load": {"low": 45.5, "high": 28.3, "peak": 12.1},
                "recovery_load": {"low": 52.3, "high": 35.6, "peak": 15.8},
                "form": {"low": -6.8, "high": -7.3, "peak": -3.7},
                "status": "tired",
                "weekly_xss_average": 420.5
            }
        }


# --- Plan Generation Response Schemas ---

class PlannedWorkoutSummary(BaseModel):
    """Summary of a planned workout."""
    date: date_type = Field(..., description="Workout date")
    name: str = Field(..., description="Workout name")
    workout_type: str = Field(..., description="Type of workout")
    duration_minutes: int = Field(..., description="Duration in minutes")
    target_tss: Optional[int] = Field(None, description="Target TSS")
    target_xss: Optional[XSSBreakdownSchema] = Field(None, description="Target XSS breakdown")


class PlanPhaseInfo(BaseModel):
    """Information about a training phase."""
    name: str = Field(..., description="Phase name")
    weeks: int = Field(..., ge=1, description="Number of weeks")


class PlanSummaryResponse(BaseModel):
    """Summary statistics for a generated plan."""
    total_weeks: int = Field(..., ge=0, description="Total weeks in plan")
    total_xss: float = Field(..., ge=0, description="Total XSS in plan")
    avg_weekly_hours: float = Field(..., ge=0, description="Average weekly hours")
    phases: list[PlanPhaseInfo] = Field(default_factory=list, description="Training phases")


class PredictedFitnessResponse(BaseModel):
    """Predicted fitness at target date."""
    threshold_power: float = Field(..., description="Predicted TP")
    high_intensity_energy: float = Field(..., description="Predicted HIE")
    peak_power: float = Field(..., description="Predicted PP")
    training_load: TrainingLoad3D = Field(..., description="Predicted training load")
    form: TrainingLoad3D = Field(..., description="Predicted form")


class GeneratedPlanResponse(BaseModel):
    """Response schema for AI-generated training plan."""
    plan_id: int = Field(..., description="Training plan ID")
    workouts: list[PlannedWorkoutSummary] = Field(
        default_factory=list,
        description="Generated workouts"
    )
    summary: PlanSummaryResponse = Field(..., description="Plan summary")
    predicted_fitness: PredictedFitnessResponse = Field(
        ...,
        description="Predicted fitness at target date"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "plan_id": 1,
                "workouts": [
                    {
                        "date": "2025-01-20",
                        "name": "Week 1 Monday: Endurance",
                        "workout_type": "endurance",
                        "duration_minutes": 60,
                        "target_tss": 50,
                        "target_xss": {"total": 50, "low": 40, "high": 8, "peak": 2}
                    },
                    {
                        "date": "2025-01-21",
                        "name": "Week 1 Tuesday: Threshold Intervals",
                        "workout_type": "threshold",
                        "duration_minutes": 75,
                        "target_tss": 85,
                        "target_xss": {"total": 85, "low": 34, "high": 38, "peak": 13}
                    }
                ],
                "summary": {
                    "total_weeks": 12,
                    "total_xss": 5040,
                    "avg_weekly_hours": 10.5,
                    "phases": [
                        {"name": "Base", "weeks": 5},
                        {"name": "Build", "weeks": 4},
                        {"name": "Peak", "weeks": 2},
                        {"name": "Taper", "weeks": 1}
                    ]
                },
                "predicted_fitness": {
                    "threshold_power": 262,
                    "high_intensity_energy": 27,
                    "peak_power": 820,
                    "training_load": {"low": 65.2, "high": 42.1, "peak": 18.5},
                    "form": {"low": 8.5, "high": 5.2, "peak": 3.1}
                }
            }
        }


# --- Training Load History Schemas ---

class TrainingLoadHistoryRequest(BaseModel):
    """Request for training load history."""
    days: int = Field(default=90, ge=7, le=365, description="Number of days")
    recalculate: bool = Field(default=False, description="Force recalculation")


class TrainingLoadHistoryResponse(BaseModel):
    """Response with training load history."""
    records: list[TrainingLoadRecordResponse] = Field(
        default_factory=list,
        description="Training load records"
    )
    summary: dict = Field(default_factory=dict, description="Summary statistics")


# --- Adapt Plan Schemas ---

class AdaptPlanRequest(BaseModel):
    """Request to adapt/re-optimize an existing plan."""
    reason: Optional[str] = Field(
        None,
        description="Reason for adaptation (e.g., 'missed workouts', 'ahead of schedule')"
    )
    maintain_target_date: bool = Field(
        default=True,
        description="Keep the same target date"
    )


class AdaptPlanResponse(BaseModel):
    """Response from plan adaptation."""
    message: str = Field(..., description="Adaptation result message")
    workouts_modified: int = Field(..., ge=0, description="Number of workouts modified")
    workouts_added: int = Field(..., ge=0, description="Number of workouts added")
    workouts_removed: int = Field(..., ge=0, description="Number of workouts removed")
