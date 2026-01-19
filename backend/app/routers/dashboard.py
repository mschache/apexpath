"""Dashboard API router for aggregated dashboard data."""

from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.activity import Activity
from app.models.fitness_metric import FitnessMetric
from app.models.user import User
from app.services.auth_service import get_current_user


router = APIRouter()


class WeeklyStats(BaseModel):
    """Weekly aggregated statistics."""
    distance_meters: float
    duration_seconds: int
    tss: float
    activity_count: int


class FitnessStats(BaseModel):
    """Current fitness metrics."""
    ctl: float
    atl: float
    tsb: float


class RecentActivity(BaseModel):
    """Simplified activity for dashboard display."""
    id: int
    name: str
    date: str
    duration_seconds: int
    distance_meters: Optional[float]
    tss: Optional[float]
    average_power: Optional[float]
    average_hr: Optional[float]
    activity_type: str


class DashboardSummary(BaseModel):
    """Complete dashboard summary response."""
    weekly: WeeklyStats
    fitness: FitnessStats
    recent_activities: List[RecentActivity]
    ftp: Optional[int]


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardSummary:
    """
    Get aggregated dashboard summary in a single request.

    This endpoint combines weekly stats, fitness metrics, and recent activities
    into a single response for optimal dashboard performance.

    Returns:
        DashboardSummary with weekly stats, fitness data, and recent activities
    """
    today = date.today()
    # Week starts on Monday (weekday() returns 0 for Monday)
    week_start = today - timedelta(days=today.weekday())

    # Weekly stats (single aggregated query)
    weekly_result = db.query(
        func.count(Activity.id).label("count"),
        func.coalesce(func.sum(Activity.distance_meters), 0).label("distance"),
        func.coalesce(func.sum(Activity.duration_seconds), 0).label("duration"),
        func.coalesce(func.sum(Activity.tss), 0).label("tss"),
    ).filter(
        Activity.user_id == current_user.id,
        func.date(Activity.date) >= week_start
    ).first()

    # Latest fitness metrics
    latest_metric = db.query(FitnessMetric).filter(
        FitnessMetric.user_id == current_user.id
    ).order_by(FitnessMetric.date.desc()).first()

    # Recent activities (last 5)
    recent = db.query(Activity).filter(
        Activity.user_id == current_user.id
    ).order_by(Activity.date.desc()).limit(5).all()

    return DashboardSummary(
        weekly=WeeklyStats(
            distance_meters=float(weekly_result.distance) if weekly_result else 0,
            duration_seconds=int(weekly_result.duration) if weekly_result else 0,
            tss=float(weekly_result.tss) if weekly_result else 0,
            activity_count=int(weekly_result.count) if weekly_result else 0,
        ),
        fitness=FitnessStats(
            ctl=round(latest_metric.ctl, 1) if latest_metric else 0,
            atl=round(latest_metric.atl, 1) if latest_metric else 0,
            tsb=round(latest_metric.tsb, 1) if latest_metric else 0,
        ),
        recent_activities=[
            RecentActivity(
                id=a.id,
                name=a.name,
                date=str(a.date.date() if hasattr(a.date, 'date') else a.date),
                duration_seconds=a.duration_seconds,
                distance_meters=a.distance_meters,
                tss=a.tss,
                average_power=a.average_power,
                average_hr=a.average_hr,
                activity_type=a.activity_type,
            )
            for a in recent
        ],
        ftp=current_user.ftp,
    )
