"""AI Training Plan Generation API router."""

import logging
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.fitness_signature import FitnessSignature
from app.models.planned_workout import PlannedWorkout
from app.models.training_load import TrainingLoadRecord
from app.models.training_plan import TrainingPlan, TrainingPhilosophy
from app.models.user import User
from app.schemas.ai import (
    AdaptPlanRequest,
    AdaptPlanResponse,
    AthleteContextResponse,
    FitnessSignatureBase,
    ForecastConfigCreate,
    GeneratedPlanResponse,
    PlannedWorkoutSummary,
    PlanPhaseInfo,
    PlanSummaryResponse,
    PredictedFitnessResponse,
    TrainingLoad3D,
    TrainingLoadHistoryResponse,
    TrainingLoadRecordResponse,
    XSSBreakdownSchema,
)
from app.services.ai_service import ai_training_service, ForecastConfig
from app.services.auth_service import get_current_user
from app.services.xss_service import xss_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/context", response_model=AthleteContextResponse)
async def get_athlete_context(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AthleteContextResponse:
    """
    Get current athlete metrics for AI planner UI display.

    Returns the athlete's current fitness signature, training load,
    recovery load, form, and training status.

    Args:
        current_user: The authenticated user
        db: Database session

    Returns:
        AthleteContextResponse with current metrics
    """
    ftp = current_user.ftp or 200

    # Get current fitness signature
    signature = (
        db.query(FitnessSignature)
        .filter(FitnessSignature.user_id == current_user.id)
        .order_by(FitnessSignature.date.desc())
        .first()
    )

    if signature:
        sig_data = FitnessSignatureBase(
            threshold_power=signature.threshold_power,
            high_intensity_energy=signature.high_intensity_energy,
            peak_power=signature.peak_power,
            weight_kg=signature.weight_kg,
        )
    else:
        # Estimate from FTP
        sig_data = FitnessSignatureBase(
            threshold_power=ftp,
            high_intensity_energy=ftp * 0.1,
            peak_power=ftp * 2.0,
            weight_kg=75,
        )

    # Get current training load
    training_load = xss_service.get_current_training_load(db, current_user.id)

    if training_load:
        tl = TrainingLoad3D(
            low=training_load.tl_low,
            high=training_load.tl_high,
            peak=training_load.tl_peak,
        )
        rl = TrainingLoad3D(
            low=training_load.rl_low,
            high=training_load.rl_high,
            peak=training_load.rl_peak,
        )
        form = TrainingLoad3D(
            low=training_load.form_low,
            high=training_load.form_high,
            peak=training_load.form_peak,
        )
        status = training_load.status
    else:
        tl = TrainingLoad3D(low=0, high=0, peak=0)
        rl = TrainingLoad3D(low=0, high=0, peak=0)
        form = TrainingLoad3D(low=0, high=0, peak=0)
        status = "fresh"

    # Get weekly XSS average
    weekly_xss = xss_service.get_weekly_xss_average(db, current_user.id, weeks=4)

    return AthleteContextResponse(
        user_id=current_user.id,
        ftp=ftp,
        signature=sig_data,
        training_load=tl,
        recovery_load=rl,
        form=form,
        status=status,
        weekly_xss_average=weekly_xss,
    )


@router.post("/generate-plan", response_model=GeneratedPlanResponse)
async def generate_ai_plan(
    config: ForecastConfigCreate,
    plan_name: Optional[str] = Query(None, description="Optional name for the plan"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GeneratedPlanResponse:
    """
    Generate AI-powered training plan using Gemini.

    Creates a personalized training plan based on the athlete's current
    fitness, training load, and the specified forecast configuration.

    Args:
        config: Forecast configuration
        plan_name: Optional name for the training plan
        current_user: The authenticated user
        db: Database session

    Returns:
        GeneratedPlanResponse with workouts, summary, and predictions
    """
    logger.info(f"Generating AI plan for user {current_user.id}")

    # Create the training plan
    plan_name = plan_name or f"AI Plan - Target {config.target_date}"
    training_plan = TrainingPlan(
        user_id=current_user.id,
        name=plan_name,
        philosophy=TrainingPhilosophy.POLARIZED,  # AI plans use adaptive philosophy
        start_date=date.today(),
        end_date=config.target_date,
        weekly_hours=config.max_weekly_hours,
        goal_event=config.program_type,
        is_active=True,
    )
    db.add(training_plan)
    db.flush()  # Get the plan ID

    # Convert schema to service config
    available_days_dict = {}
    for day_name, day_info in config.available_days.items():
        if isinstance(day_info, dict):
            available_days_dict[day_name] = day_info
        else:
            available_days_dict[day_name] = {
                "available": day_info.available,
                "start_time": day_info.start_time,
                "duration": day_info.duration,
            }

    forecast_config = ForecastConfig(
        program_type=config.program_type,
        target_date=config.target_date,
        max_weekly_hours=config.max_weekly_hours,
        event_readiness=config.event_readiness,
        periodization_level=config.periodization_level,
        polarization_ratio=config.polarization_ratio,
        recovery_demands=config.recovery_demands,
        available_days=available_days_dict,
    )

    # Generate workouts using AI service
    workouts = await ai_training_service.generate_training_plan(
        user_id=current_user.id,
        plan_id=training_plan.id,
        config=forecast_config,
        db=db,
    )

    # Save workouts to database
    for workout in workouts:
        db.add(workout)

    db.commit()

    # Get plan summary
    summary = ai_training_service.get_plan_summary(workouts)

    # Get predicted fitness
    current_load = xss_service.get_current_training_load(db, current_user.id)
    predicted = ai_training_service.predict_fitness_at_target(workouts, current_load, db)

    # Convert workouts to response format
    workout_summaries = [
        PlannedWorkoutSummary(
            date=w.date.date() if hasattr(w.date, 'date') else w.date,
            name=w.name,
            workout_type=w.workout_type.value if hasattr(w.workout_type, 'value') else w.workout_type,
            duration_minutes=w.duration_minutes,
            target_tss=w.target_tss,
            target_xss=None,  # Could be populated from workout metadata
        )
        for w in workouts
    ]

    return GeneratedPlanResponse(
        plan_id=training_plan.id,
        workouts=workout_summaries,
        summary=PlanSummaryResponse(
            total_weeks=summary.total_weeks,
            total_xss=summary.total_xss,
            avg_weekly_hours=summary.avg_weekly_hours,
            phases=[PlanPhaseInfo(name=p["name"], weeks=p["weeks"]) for p in summary.phases],
        ),
        predicted_fitness=PredictedFitnessResponse(
            threshold_power=predicted.threshold_power,
            high_intensity_energy=predicted.high_intensity_energy,
            peak_power=predicted.peak_power,
            training_load=TrainingLoad3D(**predicted.training_load),
            form=TrainingLoad3D(**predicted.form),
        ),
    )


@router.post("/adapt-plan/{plan_id}", response_model=AdaptPlanResponse)
async def adapt_plan(
    plan_id: int,
    request: AdaptPlanRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AdaptPlanResponse:
    """
    Re-optimize plan based on actual vs planned training.

    Analyzes completed workouts and adjusts future workouts to
    optimize for the target date.

    Args:
        plan_id: Training plan ID
        request: Adaptation parameters
        current_user: The authenticated user
        db: Database session

    Returns:
        AdaptPlanResponse with modification summary
    """
    # Verify plan exists and belongs to user
    plan = db.query(TrainingPlan).filter(
        TrainingPlan.id == plan_id,
        TrainingPlan.user_id == current_user.id
    ).first()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Training plan not found"
        )

    # Get incomplete workouts
    incomplete_workouts = db.query(PlannedWorkout).filter(
        PlannedWorkout.plan_id == plan_id,
        PlannedWorkout.completed == False,
        PlannedWorkout.date >= date.today()
    ).all()

    if not incomplete_workouts:
        return AdaptPlanResponse(
            message="No future workouts to adapt",
            workouts_modified=0,
            workouts_added=0,
            workouts_removed=0,
        )

    # For now, simple adaptation logic
    # In a full implementation, this would call AI to regenerate
    workouts_modified = 0

    # Get current form to adjust intensity
    current_load = xss_service.get_current_training_load(db, current_user.id)

    if current_load:
        # If very tired, reduce upcoming workout intensity
        if current_load.status == "very_tired":
            for workout in incomplete_workouts[:3]:  # Adjust next 3 workouts
                if workout.target_tss:
                    workout.target_tss = int(workout.target_tss * 0.8)
                workouts_modified += 1

        # If very fresh, can increase intensity slightly
        elif current_load.status == "very_fresh":
            for workout in incomplete_workouts[:3]:
                if workout.target_tss:
                    workout.target_tss = int(workout.target_tss * 1.1)
                workouts_modified += 1

    db.commit()

    return AdaptPlanResponse(
        message=f"Plan adapted based on current form: {current_load.status if current_load else 'unknown'}",
        workouts_modified=workouts_modified,
        workouts_added=0,
        workouts_removed=0,
    )


@router.get("/training-load/history", response_model=TrainingLoadHistoryResponse)
async def get_training_load_history(
    days: int = Query(default=90, ge=7, le=365, description="Number of days"),
    recalculate: bool = Query(default=False, description="Force recalculation"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TrainingLoadHistoryResponse:
    """
    Get 3D training load history.

    Returns the training load, recovery load, and form for each day
    in the specified period.

    Args:
        days: Number of days to retrieve
        recalculate: Whether to force recalculation
        current_user: The authenticated user
        db: Database session

    Returns:
        TrainingLoadHistoryResponse with daily records
    """
    if recalculate:
        records = xss_service.calculate_training_load_history(
            db=db,
            user_id=current_user.id,
            days=days,
            recalculate=True,
        )
    else:
        # Get existing records
        start_date = date.today() - timedelta(days=days)
        records = (
            db.query(TrainingLoadRecord)
            .filter(
                TrainingLoadRecord.user_id == current_user.id,
                TrainingLoadRecord.date >= start_date,
            )
            .order_by(TrainingLoadRecord.date)
            .all()
        )

        # Calculate if no records exist
        if not records:
            records = xss_service.calculate_training_load_history(
                db=db,
                user_id=current_user.id,
                days=days,
                recalculate=False,
            )

    # Calculate summary
    if records:
        total_xss = sum(r.xss_total for r in records)
        avg_form = sum(r.total_form for r in records) / len(records)
        latest = records[-1] if records else None
    else:
        total_xss = 0
        avg_form = 0
        latest = None

    return TrainingLoadHistoryResponse(
        records=[TrainingLoadRecordResponse.model_validate(r) for r in records],
        summary={
            "total_records": len(records),
            "total_xss": round(total_xss, 1),
            "avg_form": round(avg_form, 1),
            "current_status": latest.status if latest else "unknown",
        },
    )


@router.post("/training-load/calculate")
async def calculate_training_load(
    days: int = Query(default=90, ge=7, le=365, description="Number of days"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Calculate and store 3D training load from activities.

    Processes all activities in the specified period and calculates
    XSS, training load, recovery load, and form for each day.

    Args:
        days: Number of days to calculate
        current_user: The authenticated user
        db: Database session

    Returns:
        Summary of calculated metrics
    """
    logger.info(f"Calculating 3D training load for user {current_user.id}, days={days}")

    records = xss_service.calculate_training_load_history(
        db=db,
        user_id=current_user.id,
        days=days,
        recalculate=True,
    )

    latest = records[-1] if records else None

    return {
        "message": "Training load calculated successfully",
        "days_calculated": len(records),
        "current_tl": {
            "low": round(latest.tl_low, 1) if latest else 0,
            "high": round(latest.tl_high, 1) if latest else 0,
            "peak": round(latest.tl_peak, 1) if latest else 0,
        },
        "current_form": {
            "low": round(latest.form_low, 1) if latest else 0,
            "high": round(latest.form_high, 1) if latest else 0,
            "peak": round(latest.form_peak, 1) if latest else 0,
        },
        "status": latest.status if latest else "unknown",
    }


@router.post("/fitness-signature/estimate")
async def estimate_fitness_signature(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Estimate fitness signature from historical data.

    Analyzes recent activities to estimate the 3-parameter
    fitness signature (TP, HIE, PP).

    Args:
        current_user: The authenticated user
        db: Database session

    Returns:
        Estimated fitness signature
    """
    ftp = current_user.ftp or 200

    # Simple estimation based on FTP
    # A full implementation would analyze power curves
    tp = ftp
    hie = ftp * 0.1  # ~10 kJ for average cyclist
    pp = ftp * 2.0   # ~200% FTP for peak power

    # Create or update signature
    existing = (
        db.query(FitnessSignature)
        .filter(
            FitnessSignature.user_id == current_user.id,
            FitnessSignature.date == date.today(),
        )
        .first()
    )

    if existing:
        existing.threshold_power = tp
        existing.high_intensity_energy = hie
        existing.peak_power = pp
        existing.source = "estimated"
    else:
        signature = FitnessSignature(
            user_id=current_user.id,
            date=date.today(),
            threshold_power=tp,
            high_intensity_energy=hie,
            peak_power=pp,
            weight_kg=75,
            source="estimated",
        )
        db.add(signature)

    db.commit()

    return {
        "message": "Fitness signature estimated",
        "signature": {
            "threshold_power": tp,
            "high_intensity_energy": round(hie, 1),
            "peak_power": round(pp, 0),
        },
        "source": "estimated",
        "note": "Estimates based on FTP. Breakthrough activities provide more accurate signatures.",
    }


@router.get("/xss/calculate")
async def calculate_xss(
    duration_seconds: int = Query(..., ge=60, description="Workout duration in seconds"),
    average_power: Optional[int] = Query(None, ge=0, description="Average power in watts"),
    normalized_power: Optional[int] = Query(None, ge=0, description="Normalized power in watts"),
    max_power: Optional[int] = Query(None, ge=0, description="Max power in watts"),
    activity_type: str = Query("Ride", description="Activity type"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Calculate XSS breakdown for a workout.

    Calculates total XSS and allocation to Low/High/Peak systems
    based on workout parameters.

    Args:
        duration_seconds: Workout duration
        average_power: Average power (optional)
        normalized_power: Normalized power (optional)
        max_power: Maximum power (optional)
        activity_type: Type of activity
        current_user: The authenticated user
        db: Database session

    Returns:
        XSS breakdown
    """
    ftp = current_user.ftp or 200

    xss = xss_service.calculate_xss_from_activity(
        duration_seconds=duration_seconds,
        average_power=average_power,
        normalized_power=normalized_power,
        max_power=max_power,
        ftp=ftp,
        activity_type=activity_type,
    )

    return {
        "total": xss.total,
        "low": xss.low,
        "high": xss.high,
        "peak": xss.peak,
        "duration_seconds": duration_seconds,
        "ftp_used": ftp,
        "activity_type": activity_type,
    }
