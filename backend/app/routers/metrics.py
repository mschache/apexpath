"""Fitness metrics API router for CTL/ATL/TSB tracking."""

import logging
from datetime import date, datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.activity import Activity
from app.models.fitness_metric import FitnessMetric
from app.models.user import User
from app.schemas.metrics import (
    FitnessMetricResponse,
    FitnessSummaryResponse,
    MetricsCalculateResponse,
    PowerZone,
    PowerZonesResponse,
)
from app.services.auth_service import get_current_user
from app.services.metrics_service import MetricsService

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize the metrics service
metrics_service = MetricsService()

# Constants for PMC calculation
CTL_TIME_CONSTANT = 42  # days (fitness)
ATL_TIME_CONSTANT = 7   # days (fatigue)


def calculate_ewma_factor(time_constant: int) -> float:
    """Calculate the exponential weighted moving average factor."""
    return 2.0 / (time_constant + 1)


@router.get("/", response_model=List[FitnessMetricResponse])
async def list_metrics(
    from_date: Optional[date] = Query(None, description="Start date for metrics"),
    to_date: Optional[date] = Query(None, description="End date for metrics"),
    limit: int = Query(90, ge=1, le=365, description="Maximum number of days to return"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[FitnessMetric]:
    """
    List fitness metrics for the current user.

    Args:
        from_date: Optional start date filter
        to_date: Optional end date filter
        limit: Maximum number of records to return
        current_user: The authenticated user
        db: Database session

    Returns:
        List of fitness metrics
    """
    query = db.query(FitnessMetric).filter(FitnessMetric.user_id == current_user.id)

    if from_date:
        query = query.filter(FitnessMetric.date >= from_date)
    if to_date:
        query = query.filter(FitnessMetric.date <= to_date)

    query = query.order_by(FitnessMetric.date.desc())
    metrics = query.limit(limit).all()

    return metrics


@router.get("/current", response_model=FitnessMetricResponse)
async def get_current_metrics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FitnessMetric:
    """
    Get the most recent fitness metrics for the current user.

    Args:
        current_user: The authenticated user
        db: Database session

    Returns:
        Most recent fitness metrics

    Raises:
        HTTPException: 404 if no metrics found
    """
    metric = db.query(FitnessMetric).filter(
        FitnessMetric.user_id == current_user.id
    ).order_by(FitnessMetric.date.desc()).first()

    if not metric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No fitness metrics found. Please calculate metrics first.",
        )

    return metric


@router.get("/summary", response_model=FitnessSummaryResponse)
async def get_fitness_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FitnessSummaryResponse:
    """
    Get a summary of the user's fitness metrics.

    Includes current CTL/ATL/TSB plus trends over the last 7 and 30 days.

    Args:
        current_user: The authenticated user
        db: Database session

    Returns:
        Fitness summary with trends
    """
    today = date.today()

    # Get metrics for different time periods
    current = db.query(FitnessMetric).filter(
        FitnessMetric.user_id == current_user.id
    ).order_by(FitnessMetric.date.desc()).first()

    week_ago = db.query(FitnessMetric).filter(
        FitnessMetric.user_id == current_user.id,
        FitnessMetric.date <= today - timedelta(days=7)
    ).order_by(FitnessMetric.date.desc()).first()

    month_ago = db.query(FitnessMetric).filter(
        FitnessMetric.user_id == current_user.id,
        FitnessMetric.date <= today - timedelta(days=30)
    ).order_by(FitnessMetric.date.desc()).first()

    # Calculate total TSS for different periods
    week_tss = db.query(func.sum(FitnessMetric.daily_tss)).filter(
        FitnessMetric.user_id == current_user.id,
        FitnessMetric.date >= today - timedelta(days=7)
    ).scalar() or 0

    month_tss = db.query(func.sum(FitnessMetric.daily_tss)).filter(
        FitnessMetric.user_id == current_user.id,
        FitnessMetric.date >= today - timedelta(days=30)
    ).scalar() or 0

    return FitnessSummaryResponse(
        current_ctl=current.ctl if current else 0,
        current_atl=current.atl if current else 0,
        current_tsb=current.tsb if current else 0,
        ctl_7d_change=(current.ctl - week_ago.ctl) if current and week_ago else 0,
        ctl_30d_change=(current.ctl - month_ago.ctl) if current and month_ago else 0,
        week_tss=week_tss,
        month_tss=month_tss,
        last_updated=current.date if current else None,
    )


@router.post("/calculate", response_model=MetricsCalculateResponse)
async def calculate_metrics(
    days: int = Query(90, ge=1, le=365, description="Number of days to calculate"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MetricsCalculateResponse:
    """
    Calculate and store fitness metrics from activities.

    This calculates CTL (Chronic Training Load / Fitness), ATL (Acute Training Load / Fatigue),
    and TSB (Training Stress Balance / Form) based on the activities in the database.

    CTL uses a 42-day exponentially weighted moving average.
    ATL uses a 7-day exponentially weighted moving average.
    TSB = CTL - ATL

    Args:
        days: Number of days to calculate (default: 90)
        current_user: The authenticated user
        db: Database session

    Returns:
        Summary of calculated metrics
    """
    today = date.today()
    start_date = today - timedelta(days=days)

    logger.info(f"Calculating metrics for user {current_user.id} from {start_date} to {today}")

    # Get all activities with TSS in the date range
    activities = db.query(Activity).filter(
        Activity.user_id == current_user.id,
        Activity.date >= start_date,
        Activity.tss.isnot(None)
    ).order_by(Activity.date).all()

    # Group activities by date and sum TSS
    daily_tss = {}
    for activity in activities:
        activity_date = activity.date.date()
        if activity_date not in daily_tss:
            daily_tss[activity_date] = 0
        daily_tss[activity_date] += activity.tss or 0

    # Get the most recent metric before start_date for continuity
    previous_metric = db.query(FitnessMetric).filter(
        FitnessMetric.user_id == current_user.id,
        FitnessMetric.date < start_date
    ).order_by(FitnessMetric.date.desc()).first()

    # Initialize CTL and ATL
    ctl = previous_metric.ctl if previous_metric else 0.0
    atl = previous_metric.atl if previous_metric else 0.0

    # Calculate factors
    ctl_factor = calculate_ewma_factor(CTL_TIME_CONSTANT)
    atl_factor = calculate_ewma_factor(ATL_TIME_CONSTANT)

    metrics_created = 0
    metrics_updated = 0

    # Calculate metrics for each day
    current_date = start_date
    while current_date <= today:
        tss = daily_tss.get(current_date, 0)

        # Update CTL and ATL using EWMA
        ctl = ctl + ctl_factor * (tss - ctl)
        atl = atl + atl_factor * (tss - atl)
        tsb = ctl - atl

        # Find or create metric for this date
        metric = db.query(FitnessMetric).filter(
            FitnessMetric.user_id == current_user.id,
            FitnessMetric.date == current_date
        ).first()

        if metric:
            metric.daily_tss = tss
            metric.ctl = ctl
            metric.atl = atl
            metric.tsb = tsb
            metrics_updated += 1
        else:
            metric = FitnessMetric(
                user_id=current_user.id,
                date=current_date,
                daily_tss=tss,
                ctl=ctl,
                atl=atl,
                tsb=tsb,
            )
            db.add(metric)
            metrics_created += 1

        current_date += timedelta(days=1)

    db.commit()

    logger.info(f"Metrics calculation complete: {metrics_created} created, {metrics_updated} updated")

    return MetricsCalculateResponse(
        days_calculated=days,
        metrics_created=metrics_created,
        metrics_updated=metrics_updated,
        current_ctl=ctl,
        current_atl=atl,
        current_tsb=tsb,
    )


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def clear_metrics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """
    Clear all fitness metrics for the current user.

    Use with caution - this will delete all historical metric data.

    Args:
        current_user: The authenticated user
        db: Database session
    """
    db.query(FitnessMetric).filter(
        FitnessMetric.user_id == current_user.id
    ).delete()
    db.commit()

    logger.info(f"Cleared all fitness metrics for user {current_user.id}")


@router.get("/zones", response_model=PowerZonesResponse)
async def get_power_zones(
    ftp_override: Optional[int] = Query(
        None,
        ge=50,
        le=500,
        description="Override FTP value (optional, uses user's stored FTP if not provided)"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PowerZonesResponse:
    """
    Get power training zones based on FTP.

    Returns the standard 6-zone power model:
    - Zone 1 (Recovery): < 55% FTP
    - Zone 2 (Endurance): 55-75% FTP
    - Zone 3 (Tempo): 76-90% FTP
    - Zone 4 (Threshold): 91-105% FTP
    - Zone 5 (VO2max): 106-120% FTP
    - Zone 6 (Anaerobic): > 120% FTP

    Args:
        ftp_override: Optional FTP value to use instead of user's stored FTP
        current_user: The authenticated user
        db: Database session

    Returns:
        Power zones with watt ranges

    Raises:
        HTTPException: 400 if no FTP available
    """
    # Use override FTP or user's stored FTP
    ftp = ftp_override or current_user.ftp

    if not ftp or ftp <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No FTP set. Please set your FTP in profile or provide ftp_override parameter."
        )

    # Calculate zones using the metrics service
    zones_data = metrics_service.get_power_zones(ftp)

    # Convert to response model
    zones = {
        zone_key: PowerZone(
            name=zone_info["name"],
            min_watts=zone_info["min_watts"],
            max_watts=zone_info["max_watts"],
            min_percent=zone_info["min_percent"],
            max_percent=zone_info["max_percent"]
        )
        for zone_key, zone_info in zones_data.items()
    }

    return PowerZonesResponse(ftp=ftp, zones=zones)


@router.post("/recalculate", response_model=MetricsCalculateResponse)
async def recalculate_metrics(
    days: int = Query(90, ge=7, le=365, description="Number of days to recalculate"),
    force: bool = Query(False, description="Force recalculation of all metrics"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MetricsCalculateResponse:
    """
    Recalculate all fitness metrics (typically after FTP change).

    This should be called after:
    - User updates their FTP
    - Activities are manually edited
    - Historical activities are synced

    The recalculation will:
    1. Retrieve all activities in the date range
    2. Recalculate TSS for activities if needed
    3. Recalculate CTL/ATL/TSB for each day
    4. Store updated metrics in the database

    Args:
        days: Number of days to recalculate (default: 90)
        force: If True, recalculate even for days that already have metrics
        current_user: The authenticated user
        db: Database session

    Returns:
        Summary of recalculated metrics
    """
    logger.info(f"Recalculating metrics for user {current_user.id}, days={days}, force={force}")

    # Count existing metrics before recalculation
    existing_count = db.query(FitnessMetric).filter(
        FitnessMetric.user_id == current_user.id
    ).count()

    # Use the metrics service for calculation
    metrics = metrics_service.calculate_fitness_history(
        db=db,
        user_id=current_user.id,
        days=days,
        recalculate=force
    )

    # Count after recalculation
    new_count = db.query(FitnessMetric).filter(
        FitnessMetric.user_id == current_user.id
    ).count()

    metrics_created = max(0, new_count - existing_count)

    # Get current values from the most recent metric
    latest = metrics[-1] if metrics else None
    current_ctl = latest.ctl if latest else 0.0
    current_atl = latest.atl if latest else 0.0
    current_tsb = latest.tsb if latest else 0.0

    logger.info(f"Recalculation complete: {len(metrics)} days processed")

    return MetricsCalculateResponse(
        days_calculated=len(metrics),
        metrics_created=metrics_created,
        metrics_updated=len(metrics) - metrics_created if force else 0,
        current_ctl=current_ctl,
        current_atl=current_atl,
        current_tsb=current_tsb,
    )


@router.get("/tss/calculate")
async def calculate_tss(
    duration_seconds: int = Query(..., ge=60, description="Workout duration in seconds"),
    normalized_power: int = Query(..., ge=0, description="Normalized power in watts"),
    ftp_override: Optional[int] = Query(
        None,
        ge=50,
        le=500,
        description="Override FTP value"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Calculate TSS for a workout.

    TSS = (duration x NP x IF) / (FTP x 3600) x 100
    where IF = NP / FTP

    Args:
        duration_seconds: Workout duration in seconds
        normalized_power: Normalized Power in watts
        ftp_override: Optional FTP override
        current_user: The authenticated user
        db: Database session

    Returns:
        Calculated TSS and related metrics
    """
    ftp = ftp_override or current_user.ftp

    if not ftp or ftp <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No FTP set. Please set your FTP in profile or provide ftp_override parameter."
        )

    tss = metrics_service.calculate_tss(
        duration_seconds=duration_seconds,
        normalized_power=normalized_power,
        ftp=ftp
    )

    intensity_factor = metrics_service.calculate_intensity_factor(
        normalized_power=normalized_power,
        ftp=ftp
    )

    return {
        "tss": tss,
        "intensity_factor": intensity_factor,
        "duration_seconds": duration_seconds,
        "normalized_power": normalized_power,
        "ftp_used": ftp,
    }


@router.get("/tss/estimate-from-hr")
async def estimate_tss_from_hr(
    duration_seconds: int = Query(..., ge=60, description="Workout duration in seconds"),
    avg_hr: int = Query(..., ge=40, le=250, description="Average heart rate"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Estimate TSS from heart rate data.

    Useful when power data is not available. Uses heart rate based TSS (hrTSS).
    Less accurate than power-based TSS but provides a reasonable estimate.

    Args:
        duration_seconds: Workout duration in seconds
        avg_hr: Average heart rate during workout
        current_user: The authenticated user
        db: Database session

    Returns:
        Estimated TSS and calculation parameters
    """
    # Get user's HR parameters (use defaults if not set)
    lthr = getattr(current_user, 'lthr', None) or 170
    max_hr = getattr(current_user, 'max_hr', None) or 190
    rest_hr = getattr(current_user, 'rest_hr', None) or 60

    if avg_hr > max_hr:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Average HR ({avg_hr}) cannot exceed max HR ({max_hr})"
        )

    try:
        estimated_tss = metrics_service.estimate_tss_from_hr(
            duration_seconds=duration_seconds,
            avg_hr=avg_hr,
            max_hr=max_hr,
            lthr=lthr,
            rest_hr=rest_hr
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    # Calculate intensity factor for reference
    hr_reserve = lthr - rest_hr
    hr_if = (avg_hr - rest_hr) / hr_reserve if hr_reserve > 0 else 0

    return {
        "estimated_tss": estimated_tss,
        "duration_seconds": duration_seconds,
        "avg_hr": avg_hr,
        "hr_intensity_factor": round(min(hr_if, 1.2), 2),
        "parameters_used": {
            "lthr": lthr,
            "max_hr": max_hr,
            "rest_hr": rest_hr
        },
        "note": "hrTSS is an estimate. Power-based TSS is more accurate when available."
    }
