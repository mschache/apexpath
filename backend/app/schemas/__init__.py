"""Pydantic schemas package for API request/response models."""

from app.schemas.workout import (
    ExportFormat,
    ExportResponse,
    IntervalType,
    WorkoutCompleteRequest,
    WorkoutIntervalSchema,
    WorkoutResponse,
    WorkoutSkipRequest,
)
from app.schemas.metrics import (
    FitnessMetricResponse,
    FitnessHistoryResponse,
    FitnessSummary,
    PowerZone,
    PowerZonesResponse,
    RecalculateRequest,
    RecalculateResponse,
    CurrentFitnessResponse,
)
from app.schemas.activity import (
    ActivityBase,
    ActivityCreate,
    ActivityResponse,
    ActivitySyncResponse,
)
from app.schemas.plans import (
    TrainingPlanBase,
    TrainingPlanCreate,
    TrainingPlanUpdate,
    TrainingPlanResponse,
    TrainingPlanSummary,
    TrainingPlanWithWorkouts,
    PlannedWorkoutBase,
    PlannedWorkoutCreate,
    PlannedWorkoutUpdate,
    PlannedWorkoutResponse,
    ComplianceStats,
)

__all__ = [
    # Workout schemas
    "ExportFormat",
    "ExportResponse",
    "IntervalType",
    "WorkoutCompleteRequest",
    "WorkoutIntervalSchema",
    "WorkoutResponse",
    "WorkoutSkipRequest",
    # Metrics schemas
    "FitnessMetricResponse",
    "FitnessHistoryResponse",
    "FitnessSummary",
    "PowerZone",
    "PowerZonesResponse",
    "RecalculateRequest",
    "RecalculateResponse",
    "CurrentFitnessResponse",
    # Activity schemas
    "ActivityBase",
    "ActivityCreate",
    "ActivityResponse",
    "ActivitySyncResponse",
    # Training plan schemas
    "TrainingPlanBase",
    "TrainingPlanCreate",
    "TrainingPlanUpdate",
    "TrainingPlanResponse",
    "TrainingPlanSummary",
    "TrainingPlanWithWorkouts",
    "PlannedWorkoutBase",
    "PlannedWorkoutCreate",
    "PlannedWorkoutUpdate",
    "PlannedWorkoutResponse",
    "ComplianceStats",
]
