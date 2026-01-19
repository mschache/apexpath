from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator

from app.models.planned_workout import WorkoutType, WorkoutStatus
from app.services.plan_generator import PlanPhilosophy


# ============== Interval Structure Schemas ==============

class WarmupCooldown(BaseModel):
    """Schema for warmup/cooldown structure"""
    duration: int = Field(..., description="Duration in seconds")
    power_low: float = Field(..., ge=0, le=2, description="Low power as % of FTP")
    power_high: float = Field(..., ge=0, le=2, description="High power as % of FTP")


class IntervalSet(BaseModel):
    """Schema for interval set structure"""
    duration: int = Field(..., description="Interval duration in seconds")
    power: float = Field(..., ge=0, le=2, description="Target power as % of FTP")
    rest_duration: int = Field(..., description="Rest duration in seconds")
    rest_power: float = Field(..., ge=0, le=2, description="Rest power as % of FTP")
    repeats: int = Field(..., ge=1, description="Number of repeats")


class IntervalStructure(BaseModel):
    """Schema for complete interval workout structure"""
    warmup: WarmupCooldown
    intervals: List[IntervalSet]
    cooldown: WarmupCooldown


# ============== Workout Schemas ==============

class WorkoutBase(BaseModel):
    """Base workout schema"""
    scheduled_date: date
    workout_type: WorkoutType
    title: str = Field(..., max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    duration_minutes: int = Field(..., ge=15, le=600)
    target_tss: Optional[float] = Field(None, ge=0)
    target_if: Optional[float] = Field(None, ge=0, le=2)


class WorkoutCreate(WorkoutBase):
    """Schema for creating a workout"""
    interval_structure: Optional[IntervalStructure] = None


class WorkoutUpdate(BaseModel):
    """Schema for updating a workout"""
    scheduled_date: Optional[date] = None
    workout_type: Optional[WorkoutType] = None
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    duration_minutes: Optional[int] = Field(None, ge=15, le=600)
    target_tss: Optional[float] = Field(None, ge=0)
    target_if: Optional[float] = Field(None, ge=0, le=2)
    interval_structure: Optional[IntervalStructure] = None


class WorkoutResponse(WorkoutBase):
    """Schema for workout response"""
    id: int
    plan_id: int
    user_id: int
    status: WorkoutStatus
    interval_structure: Optional[dict] = None
    completed_activity_id: Optional[int] = None
    actual_tss: Optional[float] = None
    actual_duration_minutes: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkoutLinkActivity(BaseModel):
    """Schema for linking activity to workout"""
    activity_id: int
    actual_tss: Optional[float] = None
    actual_duration_minutes: Optional[int] = None


# ============== Plan Schemas ==============

class PlanBase(BaseModel):
    """Base plan schema"""
    name: str = Field(..., max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    philosophy: PlanPhilosophy
    start_date: date
    end_date: date
    weekly_hours: float = Field(..., ge=1, le=40)
    training_days: List[int] = Field(..., min_length=1, max_length=7)
    target_event: Optional[str] = Field(None, max_length=255)

    @field_validator('training_days')
    @classmethod
    def validate_training_days(cls, v):
        if not all(0 <= day <= 6 for day in v):
            raise ValueError('Training days must be between 0 (Monday) and 6 (Sunday)')
        if len(v) != len(set(v)):
            raise ValueError('Training days must be unique')
        return sorted(v)

    @field_validator('end_date')
    @classmethod
    def validate_end_date(cls, v, info):
        start = info.data.get('start_date')
        if start and v <= start:
            raise ValueError('End date must be after start date')
        return v


class PlanCreate(PlanBase):
    """Schema for creating a training plan"""
    current_ctl: float = Field(0, ge=0, description="Current Chronic Training Load")
    ftp: int = Field(..., ge=50, le=500, description="Functional Threshold Power")
    target_ctl: Optional[float] = Field(None, ge=0)


class PlanUpdate(BaseModel):
    """Schema for updating a training plan"""
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    target_event: Optional[str] = Field(None, max_length=255)
    target_ctl: Optional[float] = Field(None, ge=0)


class PlanResponse(PlanBase):
    """Schema for plan response"""
    id: int
    user_id: int
    initial_ctl: Optional[float] = None
    target_ctl: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PlanWithWorkouts(PlanResponse):
    """Schema for plan response with workouts"""
    workouts: List[WorkoutResponse] = []


class PlanSummary(BaseModel):
    """Schema for plan summary/list view"""
    id: int
    name: str
    philosophy: PlanPhilosophy
    start_date: date
    end_date: date
    weekly_hours: float
    total_workouts: int
    completed_workouts: int
    compliance_rate: float

    class Config:
        from_attributes = True


# ============== Compliance & Adaptation Schemas ==============

class ComplianceStats(BaseModel):
    """Schema for plan compliance statistics"""
    total_workouts: int
    completed: int
    skipped: int
    pending: int
    compliance_rate: float
    tss_compliance: float
    duration_compliance: float


class AdaptationResult(BaseModel):
    """Schema for adaptation result"""
    plan_id: int
    adaptations_made: List[dict]
    consecutive_misses: int
    compliance_rate: float


class ActivityMatch(BaseModel):
    """Schema for auto-matched activity"""
    workout_id: int
    activity_id: int
    activity_date: date
    workout_type: str
    confidence: str  # "high", "medium", "low"


# ============== Utility Schemas ==============

class WeeklyTSSEstimate(BaseModel):
    """Schema for weekly TSS estimation"""
    weekly_hours: float
    philosophy: PlanPhilosophy
    estimated_weekly_tss: float


class PlanGenerationPreview(BaseModel):
    """Schema for plan generation preview (before creation)"""
    total_weeks: int
    total_workouts: int
    estimated_total_tss: float
    workout_type_distribution: dict  # e.g., {"endurance": 10, "threshold": 5, ...}
    weekly_breakdown: List[dict]  # List of weekly summaries
