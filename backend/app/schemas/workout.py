"""Pydantic schemas for workout-related API operations."""

from datetime import date, datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.models.planned_workout import WorkoutType


class ExportFormat(str, Enum):
    """Supported workout export formats."""
    ZWO = "zwo"  # Zwift Workout
    MRC = "mrc"  # Rouvy/ErgVideo


class IntervalType(str, Enum):
    """Types of workout intervals."""
    WARMUP = "warmup"
    WORK = "work"
    REST = "rest"
    COOLDOWN = "cooldown"
    RAMP = "ramp"
    STEADY = "steady"


class WorkoutIntervalSchema(BaseModel):
    """Schema for a single workout interval segment."""

    name: Optional[str] = Field(None, description="Interval name")
    type: Optional[IntervalType] = Field(None, description="Type of interval")
    duration: int = Field(..., ge=1, description="Duration in seconds")
    power_target: Optional[float] = Field(
        None,
        ge=0.0,
        le=2.0,
        description="Power target as decimal of FTP (0.50 = 50%)"
    )
    power_low: Optional[float] = Field(
        None,
        ge=0.0,
        le=2.0,
        description="Lower power target as decimal of FTP (for ramps)"
    )
    power_high: Optional[float] = Field(
        None,
        ge=0.0,
        le=2.0,
        description="Upper power target as decimal of FTP (for ramps)"
    )
    cadence: Optional[int] = Field(
        None,
        ge=40,
        le=150,
        description="Target cadence RPM"
    )
    repeats: Optional[int] = Field(None, ge=1, description="Number of repetitions")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Sweet Spot",
                "duration": 600,
                "power_target": 0.90,
                "cadence": 90,
                "repeats": 3
            }
        }


class WorkoutResponse(BaseModel):
    """Schema for workout API responses."""

    id: int = Field(..., description="Unique workout ID")
    plan_id: int = Field(..., description="ID of the training plan")
    date: datetime = Field(..., description="Scheduled date/time")
    name: str = Field(..., description="Workout name")
    workout_type: WorkoutType = Field(..., description="Type of workout")
    duration_minutes: int = Field(..., description="Duration in minutes")
    description: Optional[str] = Field(None, description="Workout description")
    intervals_json: Optional[list[dict[str, Any]]] = Field(
        None,
        description="Structured workout intervals"
    )
    target_tss: Optional[int] = Field(None, description="Target Training Stress Score")
    target_if: Optional[int] = Field(None, description="Target Intensity Factor (percentage)")
    completed: bool = Field(..., description="Whether workout is completed")
    completed_activity_id: Optional[int] = Field(None, description="Linked activity ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "plan_id": 1,
                "date": "2024-01-15T08:00:00Z",
                "name": "Sweet Spot 3x10",
                "workout_type": "threshold",
                "duration_minutes": 60,
                "description": "3x10 minute sweet spot intervals at 88-94% FTP",
                "intervals_json": [
                    {"name": "Warmup", "duration": 600, "power_target": 0.5},
                    {"name": "Sweet Spot", "duration": 600, "power_target": 0.90, "repeats": 3},
                    {"name": "Recovery", "duration": 300, "power_target": 0.50},
                    {"name": "Cooldown", "duration": 300, "power_target": 0.40}
                ],
                "target_tss": 65,
                "target_if": 85,
                "completed": False,
                "completed_activity_id": None,
                "created_at": "2024-01-10T10:00:00Z",
                "updated_at": "2024-01-10T10:00:00Z"
            }
        }


class WorkoutCompleteRequest(BaseModel):
    """Schema for marking a workout as complete."""

    completed_activity_id: Optional[int] = Field(
        None,
        description="ID of the linked activity"
    )


class WorkoutSkipRequest(BaseModel):
    """Schema for skipping/uncompleting a workout."""

    reason: Optional[str] = Field(None, max_length=500, description="Reason for skipping")


class ExportResponse(BaseModel):
    """Schema for export metadata response."""

    filename: str = Field(..., description="Generated filename")
    format: ExportFormat = Field(..., description="Export format")
    content_type: str = Field(..., description="MIME content type")
    size_bytes: int = Field(..., ge=0, description="File size in bytes")
