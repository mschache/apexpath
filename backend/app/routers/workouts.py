"""Workouts API router for managing planned workouts and exports."""

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.planned_workout import PlannedWorkout
from app.models.user import User
from app.schemas.workout import (
    ExportFormat,
    ExportResponse,
    WorkoutCompleteRequest,
    WorkoutResponse,
    WorkoutSkipRequest,
)
from app.services.auth_service import get_current_user
from app.services.export_service import export_service

router = APIRouter(tags=["workouts"])


# Content type mappings for export formats
EXPORT_CONTENT_TYPES = {
    ExportFormat.ZWO: "application/xml",
    ExportFormat.MRC: "text/plain",
}


@router.get("/upcoming", response_model=List[WorkoutResponse])
async def get_upcoming_workouts(
    limit: int = Query(5, ge=1, le=20, description="Maximum number of workouts to return"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[PlannedWorkout]:
    """
    Get upcoming planned workouts for the current user.

    Returns workouts scheduled for today or later that haven't been completed.

    Args:
        limit: Maximum number of workouts to return (default: 5)
        current_user: The authenticated user
        db: Database session

    Returns:
        List of upcoming workouts ordered by scheduled date
    """
    from datetime import datetime
    from app.models.training_plan import TrainingPlan

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # Query workouts through the plan relationship to filter by user
    workouts = db.query(PlannedWorkout).join(
        TrainingPlan, PlannedWorkout.plan_id == TrainingPlan.id
    ).filter(
        TrainingPlan.user_id == current_user.id,
        PlannedWorkout.date >= today,
        PlannedWorkout.completed == False
    ).order_by(PlannedWorkout.date).limit(limit).all()

    return workouts


@router.get("/{workout_id}", response_model=WorkoutResponse)
async def get_workout(
    workout_id: int,
    db: Session = Depends(get_db),
) -> PlannedWorkout:
    """
    Get workout details by ID.

    Args:
        workout_id: Unique identifier of the workout
        db: Database session

    Returns:
        Workout details

    Raises:
        HTTPException: 404 if workout not found
    """
    workout = db.query(PlannedWorkout).filter(PlannedWorkout.id == workout_id).first()

    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workout with id {workout_id} not found",
        )

    return workout


@router.get("/{workout_id}/export")
async def export_workout(
    workout_id: int,
    format: ExportFormat = Query(..., description="Export format (zwo or mrc)"),
    ftp: int = Query(200, ge=100, le=500, description="Athlete's FTP for reference"),
    db: Session = Depends(get_db),
) -> Response:
    """
    Export workout to cycling platform format.

    Supported formats:
    - **zwo**: Zwift Workout file (XML)
    - **mrc**: Rouvy/ErgVideo format (tab-separated)

    Args:
        workout_id: Unique identifier of the workout
        format: Export format (zwo or mrc)
        ftp: Athlete's FTP in watts (default: 200)
        db: Database session

    Returns:
        File download response with appropriate content type

    Raises:
        HTTPException: 404 if workout not found
    """
    workout = db.query(PlannedWorkout).filter(PlannedWorkout.id == workout_id).first()

    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workout with id {workout_id} not found",
        )

    # Generate export content based on format
    if format == ExportFormat.ZWO:
        content = export_service.export_to_zwo(workout, ftp)
    elif format == ExportFormat.MRC:
        content = export_service.export_to_mrc(workout, ftp)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported export format: {format}",
        )

    # Generate filename
    filename = export_service.generate_filename(workout, format.value)
    content_type = EXPORT_CONTENT_TYPES[format]

    # Return file response
    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(content.encode("utf-8"))),
        },
    )


@router.get("/{workout_id}/export/metadata", response_model=ExportResponse)
async def get_export_metadata(
    workout_id: int,
    format: ExportFormat = Query(..., description="Export format (zwo or mrc)"),
    ftp: int = Query(200, ge=100, le=500, description="Athlete's FTP for reference"),
    db: Session = Depends(get_db),
) -> ExportResponse:
    """
    Get export metadata without downloading the file.

    Useful for showing file info before download.

    Args:
        workout_id: Unique identifier of the workout
        format: Export format (zwo or mrc)
        ftp: Athlete's FTP in watts
        db: Database session

    Returns:
        Export metadata including filename, format, and size
    """
    workout = db.query(PlannedWorkout).filter(PlannedWorkout.id == workout_id).first()

    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workout with id {workout_id} not found",
        )

    # Generate content to calculate size
    if format == ExportFormat.ZWO:
        content = export_service.export_to_zwo(workout, ftp)
    else:
        content = export_service.export_to_mrc(workout, ftp)

    return ExportResponse(
        filename=export_service.generate_filename(workout, format.value),
        format=format,
        content_type=EXPORT_CONTENT_TYPES[format],
        size_bytes=len(content.encode("utf-8")),
    )


@router.post("/{workout_id}/complete", response_model=WorkoutResponse)
async def complete_workout(
    workout_id: int,
    request: Optional[WorkoutCompleteRequest] = None,
    db: Session = Depends(get_db),
) -> PlannedWorkout:
    """
    Mark a workout as complete.

    Args:
        workout_id: Unique identifier of the workout
        request: Optional completion details (linked activity ID)
        db: Database session

    Returns:
        Updated workout

    Raises:
        HTTPException: 404 if workout not found
        HTTPException: 400 if workout already completed
    """
    workout = db.query(PlannedWorkout).filter(PlannedWorkout.id == workout_id).first()

    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workout with id {workout_id} not found",
        )

    if workout.completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workout is already completed",
        )

    # Update workout completion status
    workout.completed = True

    # Link to activity if provided
    if request and request.completed_activity_id:
        workout.completed_activity_id = request.completed_activity_id

    db.commit()
    db.refresh(workout)

    return workout


@router.post("/{workout_id}/skip", response_model=WorkoutResponse)
async def skip_workout(
    workout_id: int,
    request: Optional[WorkoutSkipRequest] = None,
    db: Session = Depends(get_db),
) -> PlannedWorkout:
    """
    Mark a workout as skipped (uncomplete it).

    Args:
        workout_id: Unique identifier of the workout
        request: Optional skip reason (for logging)
        db: Database session

    Returns:
        Updated workout

    Raises:
        HTTPException: 404 if workout not found
    """
    workout = db.query(PlannedWorkout).filter(PlannedWorkout.id == workout_id).first()

    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workout with id {workout_id} not found",
        )

    # Mark workout as not completed and unlink activity
    workout.completed = False
    workout.completed_activity_id = None

    db.commit()
    db.refresh(workout)

    return workout
