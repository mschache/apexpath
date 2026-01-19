"""Pydantic schemas for fitness metrics API operations."""

from datetime import date as date_type
from typing import Optional

from pydantic import BaseModel, Field


class FitnessMetricBase(BaseModel):
    """Base schema for fitness metric data."""

    date: date_type = Field(..., description="Date of the metric")
    daily_tss: float = Field(..., ge=0, description="Total TSS for the day")
    ctl: float = Field(..., description="Chronic Training Load (Fitness)")
    atl: float = Field(..., description="Acute Training Load (Fatigue)")
    tsb: float = Field(..., description="Training Stress Balance (Form)")


class FitnessMetricResponse(FitnessMetricBase):
    """Schema for fitness metric API responses."""

    id: int = Field(..., description="Unique metric ID")
    user_id: int = Field(..., description="User ID")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "user_id": 42,
                "date": "2024-01-15",
                "daily_tss": 75.5,
                "ctl": 55.2,
                "atl": 68.4,
                "tsb": -13.2
            }
        }


class FitnessHistoryResponse(BaseModel):
    """Schema for fitness history response with multiple days."""

    metrics: list[FitnessMetricResponse] = Field(
        ...,
        description="List of daily fitness metrics"
    )
    summary: "FitnessSummary" = Field(
        ...,
        description="Summary statistics for the period"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "metrics": [
                    {
                        "id": 1,
                        "user_id": 42,
                        "date": "2024-01-14",
                        "daily_tss": 0.0,
                        "ctl": 54.8,
                        "atl": 62.1,
                        "tsb": -7.3
                    },
                    {
                        "id": 2,
                        "user_id": 42,
                        "date": "2024-01-15",
                        "daily_tss": 75.5,
                        "ctl": 55.2,
                        "atl": 68.4,
                        "tsb": -13.2
                    }
                ],
                "summary": {
                    "current_ctl": 55.2,
                    "current_atl": 68.4,
                    "current_tsb": -13.2,
                    "avg_daily_tss": 37.8,
                    "total_tss": 2650.0,
                    "training_days": 45
                }
            }
        }


class FitnessSummary(BaseModel):
    """Summary statistics for a fitness period."""

    current_ctl: float = Field(..., description="Current CTL (most recent)")
    current_atl: float = Field(..., description="Current ATL (most recent)")
    current_tsb: float = Field(..., description="Current TSB (most recent)")
    avg_daily_tss: float = Field(..., ge=0, description="Average daily TSS")
    total_tss: float = Field(..., ge=0, description="Total TSS for the period")
    training_days: int = Field(..., ge=0, description="Number of days with training")

    class Config:
        json_schema_extra = {
            "example": {
                "current_ctl": 55.2,
                "current_atl": 68.4,
                "current_tsb": -13.2,
                "avg_daily_tss": 37.8,
                "total_tss": 2650.0,
                "training_days": 45
            }
        }


class PowerZone(BaseModel):
    """Schema for a single power zone."""

    name: str = Field(..., description="Zone name (e.g., 'Recovery', 'Threshold')")
    min_watts: int = Field(..., ge=0, description="Minimum power for this zone")
    max_watts: Optional[int] = Field(
        None,
        ge=0,
        description="Maximum power for this zone (null for highest zone)"
    )
    min_percent: int = Field(..., ge=0, description="Minimum % of FTP")
    max_percent: Optional[int] = Field(
        None,
        ge=0,
        description="Maximum % of FTP (null for highest zone)"
    )


class PowerZonesResponse(BaseModel):
    """Schema for power zones response."""

    ftp: int = Field(..., ge=0, description="User's FTP used to calculate zones")
    zones: dict[str, PowerZone] = Field(..., description="Power zones")

    class Config:
        json_schema_extra = {
            "example": {
                "ftp": 250,
                "zones": {
                    "zone_1": {
                        "name": "Recovery",
                        "min_watts": 0,
                        "max_watts": 137,
                        "min_percent": 0,
                        "max_percent": 55
                    },
                    "zone_2": {
                        "name": "Endurance",
                        "min_watts": 138,
                        "max_watts": 187,
                        "min_percent": 55,
                        "max_percent": 75
                    },
                    "zone_3": {
                        "name": "Tempo",
                        "min_watts": 190,
                        "max_watts": 225,
                        "min_percent": 76,
                        "max_percent": 90
                    },
                    "zone_4": {
                        "name": "Threshold",
                        "min_watts": 228,
                        "max_watts": 262,
                        "min_percent": 91,
                        "max_percent": 105
                    },
                    "zone_5": {
                        "name": "VO2max",
                        "min_watts": 265,
                        "max_watts": 300,
                        "min_percent": 106,
                        "max_percent": 120
                    },
                    "zone_6": {
                        "name": "Anaerobic",
                        "min_watts": 303,
                        "max_watts": None,
                        "min_percent": 121,
                        "max_percent": None
                    }
                }
            }
        }


class RecalculateRequest(BaseModel):
    """Schema for recalculate metrics request."""

    days: int = Field(
        default=90,
        ge=7,
        le=365,
        description="Number of days to recalculate (7-365)"
    )
    force: bool = Field(
        default=False,
        description="Force recalculation even for existing metrics"
    )


class RecalculateResponse(BaseModel):
    """Schema for recalculate metrics response."""

    message: str = Field(..., description="Status message")
    days_calculated: int = Field(..., ge=0, description="Number of days calculated")
    metrics_created: int = Field(..., ge=0, description="Number of new metrics created")
    metrics_updated: int = Field(..., ge=0, description="Number of metrics updated")


class CurrentFitnessResponse(BaseModel):
    """Schema for current fitness snapshot."""

    date: date_type = Field(..., description="Date of current metrics")
    ctl: float = Field(..., description="Current CTL (Fitness)")
    atl: float = Field(..., description="Current ATL (Fatigue)")
    tsb: float = Field(..., description="Current TSB (Form)")
    form_status: str = Field(
        ...,
        description="Human-readable form status (e.g., 'Fresh', 'Optimal', 'Fatigued')"
    )
    recommendation: str = Field(
        ...,
        description="Training recommendation based on current form"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "date": "2024-01-15",
                "ctl": 55.2,
                "atl": 68.4,
                "tsb": -13.2,
                "form_status": "Fatigued",
                "recommendation": "Consider a recovery day or light workout to manage fatigue."
            }
        }


class FitnessSummaryResponse(BaseModel):
    """Schema for fitness summary with trends."""

    current_ctl: float = Field(..., description="Current CTL (Fitness)")
    current_atl: float = Field(..., description="Current ATL (Fatigue)")
    current_tsb: float = Field(..., description="Current TSB (Form)")
    ctl_7d_change: float = Field(..., description="CTL change over last 7 days")
    ctl_30d_change: float = Field(..., description="CTL change over last 30 days")
    week_tss: float = Field(..., ge=0, description="Total TSS for last 7 days")
    month_tss: float = Field(..., ge=0, description="Total TSS for last 30 days")
    last_updated: Optional[date_type] = Field(None, description="Date of most recent metric")

    class Config:
        json_schema_extra = {
            "example": {
                "current_ctl": 55.2,
                "current_atl": 68.4,
                "current_tsb": -13.2,
                "ctl_7d_change": 3.5,
                "ctl_30d_change": 12.1,
                "week_tss": 420.0,
                "month_tss": 1850.0,
                "last_updated": "2024-01-15"
            }
        }


class MetricsCalculateResponse(BaseModel):
    """Schema for metrics calculation result."""

    days_calculated: int = Field(..., ge=0, description="Number of days calculated")
    metrics_created: int = Field(..., ge=0, description="Number of new metrics created")
    metrics_updated: int = Field(..., ge=0, description="Number of metrics updated")
    current_ctl: float = Field(..., description="Current CTL after calculation")
    current_atl: float = Field(..., description="Current ATL after calculation")
    current_tsb: float = Field(..., description="Current TSB after calculation")

    class Config:
        json_schema_extra = {
            "example": {
                "days_calculated": 90,
                "metrics_created": 45,
                "metrics_updated": 45,
                "current_ctl": 55.2,
                "current_atl": 68.4,
                "current_tsb": -13.2
            }
        }
