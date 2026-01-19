"""Training plans API router for managing training plans and workouts."""

import logging
from datetime import date, datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.training_plan import TrainingPlan, TrainingPhilosophy
from app.models.planned_workout import PlannedWorkout, WorkoutType
from app.models.user import User
from app.schemas.plans import (
    TrainingPlanCreate,
    TrainingPlanResponse,
    TrainingPlanUpdate,
    TrainingPlanWithWorkouts,
    TrainingPlanSummary,
    PlannedWorkoutCreate,
    PlannedWorkoutResponse,
    PlannedWorkoutUpdate,
    ComplianceStats,
)
from app.services.auth_service import get_current_user
from app.services.plan_generator import PlanGenerator, PlanPhilosophy
from app.services.adaptation_service import AdaptationService

logger = logging.getLogger(__name__)

# Initialize services
plan_generator = PlanGenerator()
adaptation_service = AdaptationService()

router = APIRouter()


# ============== Plan CRUD Endpoints ==============

@router.get("", response_model=List[TrainingPlanSummary])
async def list_plans(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    philosophy: Optional[TrainingPhilosophy] = Query(None, description="Filter by training philosophy"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[TrainingPlanSummary]:
    """
    List all training plans for the current user.

    Returns summary information including compliance statistics.
    """
    query = db.query(TrainingPlan).filter(TrainingPlan.user_id == current_user.id)

    if is_active is not None:
        query = query.filter(TrainingPlan.is_active == is_active)
    if philosophy:
        query = query.filter(TrainingPlan.philosophy == philosophy)

    plans = query.order_by(TrainingPlan.start_date.desc()).offset(skip).limit(limit).all()

    # Build summary responses with compliance data
    summaries = []
    for plan in plans:
        total = len(plan.workouts)
        completed = len([w for w in plan.workouts if w.completed])

        summaries.append(TrainingPlanSummary(
            id=plan.id,
            name=plan.name,
            philosophy=plan.philosophy,
            start_date=plan.start_date,
            end_date=plan.end_date,
            weekly_hours=plan.weekly_hours,
            goal_event=plan.goal_event,
            is_active=plan.is_active,
            total_workouts=total,
            completed_workouts=completed,
            compliance_rate=completed / total if total > 0 else 0.0,
        ))

    return summaries


@router.get("/active", response_model=TrainingPlanWithWorkouts)
async def get_active_plan(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TrainingPlan:
    """
    Get the current active training plan with all workouts.
    """
    plan = db.query(TrainingPlan).filter(
        TrainingPlan.user_id == current_user.id,
        TrainingPlan.is_active == True
    ).first()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active training plan found",
        )

    return plan


@router.get("/{plan_id}", response_model=TrainingPlanWithWorkouts)
async def get_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TrainingPlan:
    """
    Get detailed information about a specific training plan.

    Includes all workouts associated with the plan.
    """
    plan = db.query(TrainingPlan).filter(
        TrainingPlan.id == plan_id,
        TrainingPlan.user_id == current_user.id
    ).first()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} not found",
        )

    return plan


@router.post("", response_model=TrainingPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_plan(
    plan_data: TrainingPlanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TrainingPlan:
    """
    Create a new training plan.

    If set as active, any existing active plan will be deactivated.
    """
    # If this plan is active, deactivate any existing active plans
    if plan_data.is_active:
        db.query(TrainingPlan).filter(
            TrainingPlan.user_id == current_user.id,
            TrainingPlan.is_active == True
        ).update({"is_active": False})

    plan = TrainingPlan(
        user_id=current_user.id,
        name=plan_data.name,
        philosophy=plan_data.philosophy,
        start_date=plan_data.start_date,
        end_date=plan_data.end_date,
        weekly_hours=plan_data.weekly_hours,
        goal_event=plan_data.goal_event,
        is_active=plan_data.is_active,
    )

    db.add(plan)
    db.commit()
    db.refresh(plan)

    logger.info(f"Created training plan {plan.id} for user {current_user.id}")

    return plan


@router.patch("/{plan_id}", response_model=TrainingPlanResponse)
async def update_plan(
    plan_id: int,
    plan_data: TrainingPlanUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TrainingPlan:
    """
    Update a training plan's metadata.
    """
    plan = db.query(TrainingPlan).filter(
        TrainingPlan.id == plan_id,
        TrainingPlan.user_id == current_user.id
    ).first()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} not found",
        )

    # If setting this plan as active, deactivate others
    if plan_data.is_active and not plan.is_active:
        db.query(TrainingPlan).filter(
            TrainingPlan.user_id == current_user.id,
            TrainingPlan.id != plan_id,
            TrainingPlan.is_active == True
        ).update({"is_active": False})

    # Update fields
    update_data = plan_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(plan, field, value)

    db.commit()
    db.refresh(plan)

    logger.info(f"Updated training plan {plan_id} for user {current_user.id}")

    return plan


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Delete a training plan and all associated workouts.

    This action cannot be undone.
    """
    plan = db.query(TrainingPlan).filter(
        TrainingPlan.id == plan_id,
        TrainingPlan.user_id == current_user.id
    ).first()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} not found",
        )

    db.delete(plan)
    db.commit()

    logger.info(f"Deleted training plan {plan_id} for user {current_user.id}")


@router.post("/{plan_id}/activate", response_model=TrainingPlanResponse)
async def activate_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TrainingPlan:
    """
    Activate a training plan and deactivate all others.
    """
    plan = db.query(TrainingPlan).filter(
        TrainingPlan.id == plan_id,
        TrainingPlan.user_id == current_user.id
    ).first()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} not found",
        )

    # Deactivate all other plans
    db.query(TrainingPlan).filter(
        TrainingPlan.user_id == current_user.id,
        TrainingPlan.id != plan_id
    ).update({"is_active": False})

    plan.is_active = True
    db.commit()
    db.refresh(plan)

    logger.info(f"Activated training plan {plan_id} for user {current_user.id}")

    return plan


# ============== Workout Endpoints ==============

@router.get("/{plan_id}/workouts", response_model=List[PlannedWorkoutResponse])
async def get_plan_workouts(
    plan_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    workout_type: Optional[WorkoutType] = None,
    completed: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[PlannedWorkout]:
    """
    Get all workouts for a specific training plan.

    Supports filtering by date range, workout type, and completion status.
    """
    # Verify plan ownership
    plan = db.query(TrainingPlan).filter(
        TrainingPlan.id == plan_id,
        TrainingPlan.user_id == current_user.id
    ).first()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} not found",
        )

    # Build query
    query = db.query(PlannedWorkout).filter(PlannedWorkout.plan_id == plan_id)

    if start_date:
        query = query.filter(PlannedWorkout.date >= start_date)
    if end_date:
        query = query.filter(PlannedWorkout.date <= end_date)
    if workout_type:
        query = query.filter(PlannedWorkout.workout_type == workout_type)
    if completed is not None:
        query = query.filter(PlannedWorkout.completed == completed)

    workouts = query.order_by(PlannedWorkout.date).all()

    return workouts


@router.get("/{plan_id}/workouts/upcoming", response_model=List[PlannedWorkoutResponse])
async def get_upcoming_workouts(
    plan_id: int,
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[PlannedWorkout]:
    """
    Get upcoming workouts for the next N days.
    """
    # Verify plan ownership
    plan = db.query(TrainingPlan).filter(
        TrainingPlan.id == plan_id,
        TrainingPlan.user_id == current_user.id
    ).first()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} not found",
        )

    today = date.today()
    end_date = today + timedelta(days=days)

    workouts = db.query(PlannedWorkout).filter(
        PlannedWorkout.plan_id == plan_id,
        PlannedWorkout.date >= today,
        PlannedWorkout.date <= end_date,
        PlannedWorkout.completed == False
    ).order_by(PlannedWorkout.date).all()

    return workouts


@router.post("/{plan_id}/workouts", response_model=PlannedWorkoutResponse, status_code=status.HTTP_201_CREATED)
async def create_workout(
    plan_id: int,
    workout_data: PlannedWorkoutCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PlannedWorkout:
    """
    Create a new workout in a training plan.
    """
    # Verify plan ownership
    plan = db.query(TrainingPlan).filter(
        TrainingPlan.id == plan_id,
        TrainingPlan.user_id == current_user.id
    ).first()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} not found",
        )

    workout = PlannedWorkout(
        plan_id=plan_id,
        date=workout_data.date,
        name=workout_data.name,
        workout_type=workout_data.workout_type,
        duration_minutes=workout_data.duration_minutes,
        description=workout_data.description,
        intervals_json=workout_data.intervals_json,
        target_tss=workout_data.target_tss,
        target_if=workout_data.target_if,
    )

    db.add(workout)
    db.commit()
    db.refresh(workout)

    logger.info(f"Created workout {workout.id} in plan {plan_id}")

    return workout


@router.patch("/{plan_id}/workouts/{workout_id}", response_model=PlannedWorkoutResponse)
async def update_workout(
    plan_id: int,
    workout_id: int,
    workout_data: PlannedWorkoutUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PlannedWorkout:
    """
    Update a specific workout within a plan.
    """
    # Verify plan ownership and workout existence
    plan = db.query(TrainingPlan).filter(
        TrainingPlan.id == plan_id,
        TrainingPlan.user_id == current_user.id
    ).first()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} not found",
        )

    workout = db.query(PlannedWorkout).filter(
        PlannedWorkout.id == workout_id,
        PlannedWorkout.plan_id == plan_id,
    ).first()

    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workout {workout_id} not found in plan {plan_id}",
        )

    # Update fields
    update_data = workout_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(workout, field, value)

    db.commit()
    db.refresh(workout)

    logger.info(f"Updated workout {workout_id} in plan {plan_id}")

    return workout


@router.delete("/{plan_id}/workouts/{workout_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workout(
    plan_id: int,
    workout_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Delete a workout from a training plan.
    """
    # Verify plan ownership
    plan = db.query(TrainingPlan).filter(
        TrainingPlan.id == plan_id,
        TrainingPlan.user_id == current_user.id
    ).first()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} not found",
        )

    workout = db.query(PlannedWorkout).filter(
        PlannedWorkout.id == workout_id,
        PlannedWorkout.plan_id == plan_id,
    ).first()

    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workout {workout_id} not found in plan {plan_id}",
        )

    db.delete(workout)
    db.commit()

    logger.info(f"Deleted workout {workout_id} from plan {plan_id}")


@router.post("/{plan_id}/workouts/{workout_id}/complete", response_model=PlannedWorkoutResponse)
async def complete_workout(
    plan_id: int,
    workout_id: int,
    activity_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PlannedWorkout:
    """
    Mark a workout as completed, optionally linking to a Strava activity.
    """
    # Verify plan ownership
    plan = db.query(TrainingPlan).filter(
        TrainingPlan.id == plan_id,
        TrainingPlan.user_id == current_user.id
    ).first()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} not found",
        )

    workout = db.query(PlannedWorkout).filter(
        PlannedWorkout.id == workout_id,
        PlannedWorkout.plan_id == plan_id,
    ).first()

    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workout {workout_id} not found in plan {plan_id}",
        )

    workout.completed = True
    if activity_id:
        workout.completed_activity_id = activity_id

    db.commit()
    db.refresh(workout)

    logger.info(f"Marked workout {workout_id} as completed")

    return workout


# ============== Compliance Endpoints ==============

@router.get("/{plan_id}/compliance", response_model=ComplianceStats)
async def get_compliance_stats(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ComplianceStats:
    """
    Get compliance statistics for a training plan.

    Returns completion rates and TSS compliance.
    """
    # Verify plan ownership
    plan = db.query(TrainingPlan).filter(
        TrainingPlan.id == plan_id,
        TrainingPlan.user_id == current_user.id
    ).first()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} not found",
        )

    # Get all workouts that should be completed (scheduled before today)
    today = date.today()
    past_workouts = [w for w in plan.workouts if w.date.date() <= today]
    total_past = len(past_workouts)
    completed = len([w for w in past_workouts if w.completed])

    # Calculate TSS compliance
    planned_tss = sum(w.target_tss or 0 for w in past_workouts)
    # Note: Actual TSS would come from linked activities - simplified here
    actual_tss = planned_tss * (completed / total_past) if total_past > 0 else 0

    return ComplianceStats(
        total_workouts=len(plan.workouts),
        completed_workouts=len([w for w in plan.workouts if w.completed]),
        past_workouts=total_past,
        past_completed=completed,
        completion_rate=completed / total_past if total_past > 0 else 0.0,
        planned_tss=planned_tss,
        actual_tss=actual_tss,
        tss_compliance=actual_tss / planned_tss if planned_tss > 0 else 0.0,
    )


# ============== Plan Generation & Adaptation Endpoints ==============

@router.post("/{plan_id}/generate-workouts", response_model=List[PlannedWorkoutResponse])
async def generate_workouts(
    plan_id: int,
    training_days: List[int] = Query(..., description="Training days (0=Monday, 6=Sunday)"),
    ftp: int = Query(..., ge=50, le=500, description="Functional Threshold Power"),
    current_ctl: float = Query(0, ge=0, description="Current Chronic Training Load"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[PlannedWorkout]:
    """
    Generate workouts for an existing training plan.

    Uses the plan's philosophy to create appropriate workouts:
    - **polarized**: 80/20 easy/hard distribution
    - **sweet_spot**: Focus on 88-94% FTP
    - **traditional**: Base -> Build -> Peak -> Taper periodization
    """
    plan = db.query(TrainingPlan).filter(
        TrainingPlan.id == plan_id,
        TrainingPlan.user_id == current_user.id
    ).first()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} not found",
        )

    # Delete existing workouts if any
    db.query(PlannedWorkout).filter(PlannedWorkout.plan_id == plan_id).delete()

    # Map TrainingPhilosophy to PlanPhilosophy
    philosophy_map = {
        TrainingPhilosophy.POLARIZED: PlanPhilosophy.POLARIZED,
        TrainingPhilosophy.SWEET_SPOT: PlanPhilosophy.SWEET_SPOT,
        TrainingPhilosophy.TRADITIONAL: PlanPhilosophy.TRADITIONAL,
    }
    plan_philosophy = philosophy_map.get(plan.philosophy, PlanPhilosophy.POLARIZED)

    # Generate workouts
    workouts = plan_generator.generate_plan(
        user_id=current_user.id,
        plan_id=plan.id,
        philosophy=plan_philosophy,
        start_date=plan.start_date.date() if hasattr(plan.start_date, 'date') else plan.start_date,
        end_date=plan.end_date.date() if hasattr(plan.end_date, 'date') else plan.end_date,
        weekly_hours=plan.weekly_hours,
        training_days=training_days,
        current_ctl=current_ctl,
        ftp=ftp,
    )

    # Add workouts to database
    for workout in workouts:
        db.add(workout)

    db.commit()

    # Refresh to get IDs
    for workout in workouts:
        db.refresh(workout)

    logger.info(f"Generated {len(workouts)} workouts for plan {plan_id}")

    return workouts


@router.post("/{plan_id}/adapt")
async def trigger_adaptation(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Trigger plan adaptation based on recent workout completions.

    This analyzes recent performance and adjusts future workouts accordingly:
    - Increases intensity if athlete is consistently exceeding targets
    - Reduces volume after missed workouts
    - Inserts recovery weeks after consecutive misses
    """
    plan = db.query(TrainingPlan).filter(
        TrainingPlan.id == plan_id,
        TrainingPlan.user_id == current_user.id
    ).first()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} not found",
        )

    try:
        result = adaptation_service.adapt_plan(plan_id, db)
        logger.info(f"Triggered adaptation for plan {plan_id}: {result}")
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{plan_id}/workouts/{workout_id}/skip", response_model=PlannedWorkoutResponse)
async def skip_workout(
    plan_id: int,
    workout_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PlannedWorkout:
    """
    Mark a workout as skipped.

    This may trigger adaptation rules if multiple workouts are skipped.
    """
    plan = db.query(TrainingPlan).filter(
        TrainingPlan.id == plan_id,
        TrainingPlan.user_id == current_user.id
    ).first()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} not found",
        )

    workout = db.query(PlannedWorkout).filter(
        PlannedWorkout.id == workout_id,
        PlannedWorkout.plan_id == plan_id,
    ).first()

    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workout {workout_id} not found in plan {plan_id}",
        )

    try:
        updated_workout = adaptation_service.mark_workout_skipped(workout_id, db)
        logger.info(f"Marked workout {workout_id} as skipped")
        return updated_workout
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
