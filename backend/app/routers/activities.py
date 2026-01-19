"""Activities API router for managing Strava activities."""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.activity import Activity
from app.models.user import User
from app.schemas.activity import ActivityCreate, ActivityResponse, ActivitySyncResponse
from app.services.auth_service import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[ActivityResponse])
async def list_activities(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of records to return"),
    activity_type: Optional[str] = Query(None, description="Filter by activity type (e.g., Ride, VirtualRide)"),
    from_date: Optional[datetime] = Query(None, description="Filter activities from this date"),
    to_date: Optional[datetime] = Query(None, description="Filter activities up to this date"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Activity]:
    """
    List activities for the current user.

    Args:
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
        activity_type: Optional filter by activity type
        from_date: Optional filter for activities after this date
        to_date: Optional filter for activities before this date
        current_user: The authenticated user
        db: Database session

    Returns:
        List of activities
    """
    query = db.query(Activity).filter(Activity.user_id == current_user.id)

    if activity_type:
        query = query.filter(Activity.activity_type == activity_type)
    if from_date:
        query = query.filter(Activity.date >= from_date)
    if to_date:
        query = query.filter(Activity.date <= to_date)

    query = query.order_by(Activity.date.desc())
    activities = query.offset(skip).limit(limit).all()

    return activities


@router.get("/{activity_id}", response_model=ActivityResponse)
async def get_activity(
    activity_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Activity:
    """
    Get activity details by ID.

    Args:
        activity_id: Unique identifier of the activity
        current_user: The authenticated user
        db: Database session

    Returns:
        Activity details

    Raises:
        HTTPException: 404 if activity not found or doesn't belong to user
    """
    activity = db.query(Activity).filter(
        Activity.id == activity_id,
        Activity.user_id == current_user.id
    ).first()

    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Activity with id {activity_id} not found",
        )

    return activity


@router.post("/sync", response_model=ActivitySyncResponse)
async def sync_activities(
    days: int = Query(30, ge=1, le=365, description="Number of days to sync"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ActivitySyncResponse:
    """
    Sync activities from Strava.

    This endpoint fetches activities from the Strava API and stores them
    in the local database. Existing activities are updated if modified.

    Args:
        days: Number of days to sync (default: 30)
        current_user: The authenticated user
        db: Database session

    Returns:
        Sync summary with counts of new and updated activities
    """
    # Import here to avoid circular dependencies
    from app.services.strava_service import strava_service, StravaAPIError

    try:
        # Calculate the date range
        from_date = datetime.utcnow().timestamp() - (days * 24 * 60 * 60)

        # Fetch activities from Strava
        logger.info(f"Syncing activities for user {current_user.id} from last {days} days")
        strava_activities = await strava_service.get_activities(
            access_token=current_user.strava_access_token,
            after=int(from_date),
        )

        new_count = 0
        updated_count = 0

        for strava_activity in strava_activities:
            # Check if activity already exists
            existing = db.query(Activity).filter(
                Activity.strava_id == strava_activity["id"]
            ).first()

            if existing:
                # Update existing activity
                existing.name = strava_activity.get("name", "Unnamed Activity")
                existing.activity_type = strava_activity.get("type", "Ride")
                existing.duration_seconds = strava_activity.get("elapsed_time", 0)
                existing.distance_meters = strava_activity.get("distance")
                existing.average_power = strava_activity.get("average_watts")
                existing.average_hr = strava_activity.get("average_heartrate")
                existing.max_hr = strava_activity.get("max_heartrate")
                existing.elevation_gain = strava_activity.get("total_elevation_gain")
                existing.average_speed = strava_activity.get("average_speed")
                existing.max_speed = strava_activity.get("max_speed")
                existing.calories = strava_activity.get("calories")
                updated_count += 1
            else:
                # Create new activity
                activity = Activity(
                    user_id=current_user.id,
                    strava_id=strava_activity["id"],
                    name=strava_activity.get("name", "Unnamed Activity"),
                    activity_type=strava_activity.get("type", "Ride"),
                    date=datetime.fromisoformat(strava_activity["start_date"].replace("Z", "+00:00")),
                    duration_seconds=strava_activity.get("elapsed_time", 0),
                    distance_meters=strava_activity.get("distance"),
                    average_power=strava_activity.get("average_watts"),
                    average_hr=strava_activity.get("average_heartrate"),
                    max_hr=strava_activity.get("max_heartrate"),
                    elevation_gain=strava_activity.get("total_elevation_gain"),
                    average_speed=strava_activity.get("average_speed"),
                    max_speed=strava_activity.get("max_speed"),
                    calories=strava_activity.get("calories"),
                )
                db.add(activity)
                new_count += 1

        db.commit()

        logger.info(f"Sync complete: {new_count} new, {updated_count} updated activities")

        return ActivitySyncResponse(
            new_activities=new_count,
            updated_activities=updated_count,
            total_synced=new_count + updated_count,
        )

    except StravaAPIError as e:
        logger.error(f"Strava API error during sync: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to sync activities from Strava: {e.message}",
        )


@router.delete("/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_activity(
    activity_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """
    Delete an activity.

    Note: This only deletes from the local database, not from Strava.

    Args:
        activity_id: Unique identifier of the activity
        current_user: The authenticated user
        db: Database session

    Raises:
        HTTPException: 404 if activity not found or doesn't belong to user
    """
    activity = db.query(Activity).filter(
        Activity.id == activity_id,
        Activity.user_id == current_user.id
    ).first()

    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Activity with id {activity_id} not found",
        )

    db.delete(activity)
    db.commit()

    logger.info(f"Deleted activity {activity_id} for user {current_user.id}")
