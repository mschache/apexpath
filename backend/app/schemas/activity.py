"""Pydantic schemas for activity-related API operations."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ActivityBase(BaseModel):
    """Base schema for activity data."""

    name: str = Field(..., description="Activity name")
    activity_type: str = Field(..., description="Activity type (e.g., Ride, VirtualRide)")
    date: datetime = Field(..., description="Activity date and time")
    duration_seconds: int = Field(..., ge=0, description="Duration in seconds")
    distance_meters: Optional[float] = Field(None, ge=0, description="Distance in meters")
    average_power: Optional[float] = Field(None, ge=0, description="Average power in watts")
    normalized_power: Optional[float] = Field(None, ge=0, description="Normalized power in watts")
    average_hr: Optional[float] = Field(None, ge=0, description="Average heart rate in bpm")
    max_hr: Optional[float] = Field(None, ge=0, description="Max heart rate in bpm")
    tss: Optional[float] = Field(None, ge=0, description="Training Stress Score")


class ActivityCreate(ActivityBase):
    """Schema for creating an activity."""

    strava_id: int = Field(..., description="Strava activity ID")


class ActivityResponse(ActivityBase):
    """Schema for activity API responses."""

    id: int = Field(..., description="Activity ID")
    user_id: int = Field(..., description="User ID")
    strava_id: int = Field(..., description="Strava activity ID")
    elevation_gain: Optional[float] = Field(None, description="Elevation gain in meters")
    average_speed: Optional[float] = Field(None, description="Average speed in m/s")
    max_speed: Optional[float] = Field(None, description="Max speed in m/s")
    calories: Optional[float] = Field(None, description="Calories burned")
    created_at: datetime = Field(..., description="Created timestamp")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "user_id": 42,
                "strava_id": 12345678,
                "name": "Morning Ride",
                "activity_type": "Ride",
                "date": "2024-01-15T08:30:00Z",
                "duration_seconds": 3600,
                "distance_meters": 30000,
                "average_power": 200,
                "normalized_power": 215,
                "average_hr": 145,
                "max_hr": 175,
                "tss": 65.0,
                "elevation_gain": 450,
                "average_speed": 8.33,
                "max_speed": 15.0,
                "calories": 850,
                "created_at": "2024-01-15T10:00:00Z"
            }
        }


class ActivitySyncResponse(BaseModel):
    """Schema for activity sync response."""

    new_activities: int = Field(..., ge=0, description="Number of new activities synced")
    updated_activities: int = Field(..., ge=0, description="Number of activities updated")
    total_synced: int = Field(..., ge=0, description="Total activities processed")

    class Config:
        json_schema_extra = {
            "example": {
                "new_activities": 5,
                "updated_activities": 2,
                "total_synced": 7
            }
        }
