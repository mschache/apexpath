"""Pydantic schemas for training plans and workouts API operations."""

from datetime import date, datetime
from typing import Optional, List, Any, Dict

from pydantic import BaseModel, Field

from app.models.training_plan import TrainingPhilosophy
from app.models.planned_workout import WorkoutType


# ============== Training Plan Schemas ==============

class TrainingPlanBase(BaseModel):
    """Base schema for training plan data."""

    name: str = Field(..., max_length=255, description="Plan name")
    philosophy: TrainingPhilosophy = Field(..., description="Training philosophy")
    start_date: datetime = Field(..., description="Plan start date")
    end_date: datetime = Field(..., description="Plan end date")
    weekly_hours: float = Field(..., ge=1, le=40, description="Target weekly hours")
    goal_event: Optional[str] = Field(None, max_length=255, description="Goal event name")
    is_active: bool = Field(True, description="Whether the plan is active")


class TrainingPlanCreate(TrainingPlanBase):
    """Schema for creating a training plan."""
    pass


class TrainingPlanUpdate(BaseModel):
    """Schema for updating a training plan."""

    name: Optional[str] = Field(None, max_length=255)
    philosophy: Optional[TrainingPhilosophy] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    weekly_hours: Optional[float] = Field(None, ge=1, le=40)
    goal_event: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None


class TrainingPlanResponse(TrainingPlanBase):
    """Schema for training plan API responses."""

    id: int = Field(..., description="Plan ID")
    user_id: int = Field(..., description="User ID")
    created_at: datetime = Field(..., description="Created timestamp")
    updated_at: datetime = Field(..., description="Updated timestamp")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "user_id": 42,
                "name": "Spring Build Phase",
                "philosophy": "polarized",
                "start_date": "2024-01-01T00:00:00Z",
                "end_date": "2024-03-31T00:00:00Z",
                "weekly_hours": 10.0,
                "goal_event": "Gran Fondo 2024",
                "is_active": True,
                "created_at": "2024-01-01T10:00:00Z",
                "updated_at": "2024-01-01T10:00:00Z"
            }
        }


class TrainingPlanSummary(BaseModel):
    """Schema for training plan summary/list view."""

    id: int = Field(..., description="Plan ID")
    name: str = Field(..., description="Plan name")
    philosophy: TrainingPhilosophy = Field(..., description="Training philosophy")
    start_date: datetime = Field(..., description="Plan start date")
    end_date: datetime = Field(..., description="Plan end date")
    weekly_hours: float = Field(..., description="Target weekly hours")
    goal_event: Optional[str] = Field(None, description="Goal event name")
    is_active: bool = Field(..., description="Whether the plan is active")
    total_workouts: int = Field(..., ge=0, description="Total workouts in plan")
    completed_workouts: int = Field(..., ge=0, description="Completed workouts")
    compliance_rate: float = Field(..., ge=0, le=1, description="Completion rate")

    class Config:
        from_attributes = True


# ============== Planned Workout Schemas ==============

class PlannedWorkoutBase(BaseModel):
    """Base schema for planned workout data."""

    date: datetime = Field(..., description="Workout date")
    name: str = Field(..., max_length=255, description="Workout name")
    workout_type: WorkoutType = Field(..., description="Type of workout")
    duration_minutes: int = Field(..., ge=10, le=600, description="Duration in minutes")
    description: Optional[str] = Field(None, description="Workout description")
    intervals_json: Optional[Dict[str, Any]] = Field(None, description="Structured intervals")
    target_tss: Optional[int] = Field(None, ge=0, description="Target TSS")
    target_if: Optional[int] = Field(None, ge=0, le=150, description="Target IF percentage")


class PlannedWorkoutCreate(PlannedWorkoutBase):
    """Schema for creating a planned workout."""
    pass


class PlannedWorkoutUpdate(BaseModel):
    """Schema for updating a planned workout."""

    date: Optional[datetime] = None
    name: Optional[str] = Field(None, max_length=255)
    workout_type: Optional[WorkoutType] = None
    duration_minutes: Optional[int] = Field(None, ge=10, le=600)
    description: Optional[str] = None
    intervals_json: Optional[Dict[str, Any]] = None
    target_tss: Optional[int] = Field(None, ge=0)
    target_if: Optional[int] = Field(None, ge=0, le=150)
    completed: Optional[bool] = None


class PlannedWorkoutResponse(PlannedWorkoutBase):
    """Schema for planned workout API responses."""

    id: int = Field(..., description="Workout ID")
    plan_id: int = Field(..., description="Training plan ID")
    completed: bool = Field(..., description="Whether workout is completed")
    completed_activity_id: Optional[int] = Field(None, description="Linked activity ID")
    created_at: datetime = Field(..., description="Created timestamp")
    updated_at: datetime = Field(..., description="Updated timestamp")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "plan_id": 1,
                "date": "2024-01-15T00:00:00Z",
                "name": "Sweet Spot 3x10",
                "workout_type": "threshold",
                "duration_minutes": 60,
                "description": "3x10 min at 88-94% FTP with 5 min recovery",
                "intervals_json": {
                    "warmup": {"duration": 600, "power_low": 0.5, "power_high": 0.7},
                    "intervals": [
                        {"duration": 600, "power": 0.9, "repeats": 3, "rest": 300}
                    ],
                    "cooldown": {"duration": 300, "power_low": 0.5, "power_high": 0.6}
                },
                "target_tss": 65,
                "target_if": 85,
                "completed": False,
                "completed_activity_id": None,
                "created_at": "2024-01-01T10:00:00Z",
                "updated_at": "2024-01-01T10:00:00Z"
            }
        }


class TrainingPlanWithWorkouts(TrainingPlanResponse):
    """Schema for training plan with all workouts."""

    workouts: List[PlannedWorkoutResponse] = Field(
        default_factory=list, description="All workouts in the plan"
    )


# ============== Compliance Schemas ==============

class ComplianceStats(BaseModel):
    """Schema for plan compliance statistics."""

    total_workouts: int = Field(..., ge=0, description="Total workouts in plan")
    completed_workouts: int = Field(..., ge=0, description="Total completed workouts")
    past_workouts: int = Field(..., ge=0, description="Workouts scheduled before today")
    past_completed: int = Field(..., ge=0, description="Completed workouts from past")
    completion_rate: float = Field(..., ge=0, le=1, description="Past workout completion rate")
    planned_tss: float = Field(..., ge=0, description="Total planned TSS for past workouts")
    actual_tss: float = Field(..., ge=0, description="Actual TSS achieved")
    tss_compliance: float = Field(..., ge=0, description="TSS compliance rate")

    class Config:
        json_schema_extra = {
            "example": {
                "total_workouts": 24,
                "completed_workouts": 18,
                "past_workouts": 20,
                "past_completed": 18,
                "completion_rate": 0.9,
                "planned_tss": 1200,
                "actual_tss": 1100,
                "tss_compliance": 0.917
            }
        }
