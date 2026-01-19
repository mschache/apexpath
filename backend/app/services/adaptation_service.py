from datetime import date, datetime, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.planned_workout import PlannedWorkout, WorkoutType
from app.models.training_plan import TrainingPlan


class AdaptationService:
    """Adapt training plans based on completed workouts"""

    # Thresholds for adaptation triggers
    TSS_OVERREACH_THRESHOLD = 1.20  # 20% over planned
    TSS_UNDERREACH_THRESHOLD = 0.80  # 20% under planned
    CONSECUTIVE_MISS_THRESHOLD = 3   # Trigger recovery after 3 misses
    VOLUME_REDUCTION_FACTOR = 0.90   # 10% reduction
    INTENSITY_INCREASE_FACTOR = 1.05 # 5% increase

    def adapt_plan(self, plan_id: int, db: Session) -> dict:
        """
        Check recent completions and adapt future workouts

        Rules:
        - If actual TSS > planned TSS by 20%: increase future intensity
        - If workout missed: reduce next week's volume by 10%
        - If 3+ consecutive misses: insert recovery week
        - If completed easier than planned: consider increasing difficulty

        Returns:
            dict with adaptation summary
        """
        plan = db.query(TrainingPlan).filter(TrainingPlan.id == plan_id).first()
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")

        # Get recent completed and missed workouts
        recent_workouts = self._get_recent_workouts(plan_id, db, days=14)

        adaptations = {
            "plan_id": plan_id,
            "adaptations_made": [],
            "consecutive_misses": 0,
            "compliance_rate": 0.0
        }

        if not recent_workouts:
            return adaptations

        today = datetime.combine(date.today(), datetime.min.time())

        # Calculate compliance
        completed = [w for w in recent_workouts if w.completed]
        # Consider workouts without linked activity as potentially missed
        not_completed = [w for w in recent_workouts if not w.completed and w.date < today]

        if recent_workouts:
            adaptations["compliance_rate"] = len(completed) / len(recent_workouts) if recent_workouts else 0.0

        # Check for consecutive misses
        consecutive_misses = self._count_consecutive_misses(plan_id, db)
        adaptations["consecutive_misses"] = consecutive_misses

        if consecutive_misses >= self.CONSECUTIVE_MISS_THRESHOLD:
            # Insert recovery week
            self._insert_recovery_week(plan_id, db)
            adaptations["adaptations_made"].append({
                "type": "recovery_week_inserted",
                "reason": f"{consecutive_misses} consecutive missed workouts"
            })
        elif not_completed:
            # Reduce volume for next week
            reduction = self._reduce_upcoming_volume(plan_id, db)
            if reduction:
                adaptations["adaptations_made"].append({
                    "type": "volume_reduced",
                    "reason": "missed workouts",
                    "reduction_percent": (1 - self.VOLUME_REDUCTION_FACTOR) * 100
                })

        # Check TSS performance via linked activities
        for workout in completed:
            if workout.completed_activity and workout.target_tss:
                # Get actual TSS from linked activity if available
                actual_tss = getattr(workout.completed_activity, 'tss', None)
                if actual_tss and workout.target_tss:
                    tss_ratio = actual_tss / workout.target_tss

                    if tss_ratio > self.TSS_OVERREACH_THRESHOLD:
                        # Athlete exceeded expectations - consider increasing
                        self._increase_future_intensity(plan_id, workout.workout_type, db)
                        adaptations["adaptations_made"].append({
                            "type": "intensity_increased",
                            "workout_type": workout.workout_type.value,
                            "reason": f"TSS overreach ({tss_ratio:.1%})"
                        })
                    elif tss_ratio < self.TSS_UNDERREACH_THRESHOLD:
                        # Athlete underperformed - check if pattern
                        adaptations["adaptations_made"].append({
                            "type": "monitoring",
                            "workout_type": workout.workout_type.value,
                            "reason": f"TSS underreach ({tss_ratio:.1%})"
                        })

        db.commit()
        return adaptations

    def link_activity_to_workout(
        self,
        workout_id: int,
        activity_id: int,
        db: Session
    ) -> PlannedWorkout:
        """Link completed Strava activity to planned workout"""
        workout = db.query(PlannedWorkout).filter(PlannedWorkout.id == workout_id).first()
        if not workout:
            raise ValueError(f"Workout {workout_id} not found")

        workout.completed_activity_id = activity_id
        workout.completed = True

        db.commit()
        db.refresh(workout)
        return workout

    def mark_workout_completed(self, workout_id: int, db: Session) -> PlannedWorkout:
        """Mark a workout as completed without linking to activity"""
        workout = db.query(PlannedWorkout).filter(PlannedWorkout.id == workout_id).first()
        if not workout:
            raise ValueError(f"Workout {workout_id} not found")

        workout.completed = True
        db.commit()
        db.refresh(workout)
        return workout

    def mark_workout_skipped(self, workout_id: int, db: Session) -> PlannedWorkout:
        """
        Mark a workout as skipped.
        Note: The current model doesn't have a 'skipped' status,
        so we keep completed=False and could add a note in description.
        """
        workout = db.query(PlannedWorkout).filter(PlannedWorkout.id == workout_id).first()
        if not workout:
            raise ValueError(f"Workout {workout_id} not found")

        # Keep completed=False, add skipped note to description
        if workout.description:
            workout.description = f"[SKIPPED] {workout.description}"
        else:
            workout.description = "[SKIPPED]"

        db.commit()
        db.refresh(workout)
        return workout

    def calculate_compliance(self, plan_id: int, db: Session) -> dict:
        """
        Calculate plan completion percentage and statistics

        Returns:
            {
                "total_workouts": int,
                "completed": int,
                "skipped": int,
                "pending": int,
                "compliance_rate": float,
                "tss_compliance": float,
                "duration_compliance": float
            }
        """
        today = datetime.combine(date.today(), datetime.min.time())

        workouts = db.query(PlannedWorkout).filter(
            PlannedWorkout.plan_id == plan_id,
            PlannedWorkout.date < today
        ).all()

        if not workouts:
            return {
                "total_workouts": 0,
                "completed": 0,
                "skipped": 0,
                "pending": 0,
                "compliance_rate": 0.0,
                "tss_compliance": 0.0,
                "duration_compliance": 0.0
            }

        completed = [w for w in workouts if w.completed]
        # Consider skipped if description contains [SKIPPED]
        skipped = [w for w in workouts if not w.completed and w.description and "[SKIPPED]" in w.description]
        pending = [w for w in workouts if not w.completed and (not w.description or "[SKIPPED]" not in w.description)]

        # Calculate TSS compliance for completed workouts with linked activities
        tss_planned = sum(w.target_tss or 0 for w in completed if w.target_tss)
        tss_actual = 0.0
        for w in completed:
            if w.completed_activity:
                activity_tss = getattr(w.completed_activity, 'tss', None)
                if activity_tss:
                    tss_actual += activity_tss
        tss_compliance = tss_actual / tss_planned if tss_planned > 0 else 0.0

        # Calculate duration compliance (we don't have actual duration in current model)
        # So we use a simple completion-based metric
        duration_planned = sum(w.duration_minutes or 0 for w in completed)
        duration_compliance = 1.0 if completed else 0.0  # Simplified - completed = achieved duration

        return {
            "total_workouts": len(workouts),
            "completed": len(completed),
            "skipped": len(skipped),
            "pending": len(pending),
            "compliance_rate": len(completed) / len(workouts) if workouts else 0.0,
            "tss_compliance": round(tss_compliance, 2),
            "duration_compliance": round(duration_compliance, 2)
        }

    def get_upcoming_workouts(
        self,
        plan_id: int,
        db: Session,
        days: int = 7
    ) -> List[PlannedWorkout]:
        """Get upcoming workouts for the next N days"""
        today = datetime.combine(date.today(), datetime.min.time())
        end_date = datetime.combine(date.today() + timedelta(days=days), datetime.min.time())

        return db.query(PlannedWorkout).filter(
            PlannedWorkout.plan_id == plan_id,
            PlannedWorkout.date >= today,
            PlannedWorkout.date <= end_date,
            PlannedWorkout.completed == False
        ).order_by(PlannedWorkout.date).all()

    def auto_match_activities(
        self,
        plan_id: int,
        activities: List[dict],
        db: Session
    ) -> List[dict]:
        """
        Automatically match Strava activities to planned workouts

        Args:
            plan_id: Plan ID to match against
            activities: List of activity dicts with date, tss, duration
            db: Database session

        Returns:
            List of matched workout-activity pairs
        """
        matches = []

        for activity in activities:
            activity_date = activity.get("date")
            if not activity_date:
                continue

            # Convert to datetime if needed
            if isinstance(activity_date, date) and not isinstance(activity_date, datetime):
                activity_datetime = datetime.combine(activity_date, datetime.min.time())
            else:
                activity_datetime = activity_date

            # Find planned workout on same day (match by date portion)
            workout = db.query(PlannedWorkout).filter(
                PlannedWorkout.plan_id == plan_id,
                func.date(PlannedWorkout.date) == activity_datetime.date(),
                PlannedWorkout.completed == False
            ).first()

            if workout:
                # Check if activity type matches (basic heuristic)
                activity_type = activity.get("type", "").lower()

                if self._activity_matches_workout(activity_type, workout.workout_type):
                    matches.append({
                        "workout_id": workout.id,
                        "activity_id": activity.get("id"),
                        "activity_date": activity_datetime.date(),
                        "workout_type": workout.workout_type.value,
                        "confidence": "high" if activity_type == "ride" else "medium"
                    })

        return matches

    # Private helper methods

    def _get_recent_workouts(
        self,
        plan_id: int,
        db: Session,
        days: int = 14
    ) -> List[PlannedWorkout]:
        """Get workouts from the last N days"""
        start_datetime = datetime.combine(date.today() - timedelta(days=days), datetime.min.time())
        today = datetime.combine(date.today(), datetime.min.time())

        return db.query(PlannedWorkout).filter(
            PlannedWorkout.plan_id == plan_id,
            PlannedWorkout.date >= start_datetime,
            PlannedWorkout.date < today
        ).order_by(PlannedWorkout.date.desc()).all()

    def _count_consecutive_misses(self, plan_id: int, db: Session) -> int:
        """Count consecutive missed workouts from today backwards"""
        today = datetime.combine(date.today(), datetime.min.time())

        workouts = db.query(PlannedWorkout).filter(
            PlannedWorkout.plan_id == plan_id,
            PlannedWorkout.date < today
        ).order_by(PlannedWorkout.date.desc()).limit(10).all()

        consecutive = 0
        for workout in workouts:
            if not workout.completed:
                consecutive += 1
            else:
                break

        return consecutive

    def _insert_recovery_week(self, plan_id: int, db: Session) -> None:
        """Convert the next week's workouts to recovery workouts"""
        start_datetime = datetime.combine(date.today(), datetime.min.time())
        end_datetime = datetime.combine(date.today() + timedelta(days=7), datetime.min.time())

        upcoming = db.query(PlannedWorkout).filter(
            PlannedWorkout.plan_id == plan_id,
            PlannedWorkout.date >= start_datetime,
            PlannedWorkout.date < end_datetime,
            PlannedWorkout.completed == False
        ).all()

        for workout in upcoming:
            workout.workout_type = WorkoutType.RECOVERY
            workout.duration_minutes = int(workout.duration_minutes * 0.6)
            workout.target_tss = int(workout.target_tss * 0.5) if workout.target_tss else None
            workout.target_if = 50  # 50% as integer
            workout.name = f"[Recovery] {workout.name}"
            workout.description = "Easy recovery spin - take it easy!"

    def _reduce_upcoming_volume(self, plan_id: int, db: Session) -> bool:
        """Reduce volume for the next week's workouts"""
        start_datetime = datetime.combine(date.today(), datetime.min.time())
        end_datetime = datetime.combine(date.today() + timedelta(days=7), datetime.min.time())

        upcoming = db.query(PlannedWorkout).filter(
            PlannedWorkout.plan_id == plan_id,
            PlannedWorkout.date >= start_datetime,
            PlannedWorkout.date < end_datetime,
            PlannedWorkout.completed == False
        ).all()

        if not upcoming:
            return False

        for workout in upcoming:
            workout.duration_minutes = int(workout.duration_minutes * self.VOLUME_REDUCTION_FACTOR)
            if workout.target_tss:
                workout.target_tss = int(workout.target_tss * self.VOLUME_REDUCTION_FACTOR)

        return True

    def _increase_future_intensity(
        self,
        plan_id: int,
        workout_type: WorkoutType,
        db: Session
    ) -> None:
        """Increase intensity for future workouts of the same type"""
        today = datetime.combine(date.today(), datetime.min.time())

        future_workouts = db.query(PlannedWorkout).filter(
            PlannedWorkout.plan_id == plan_id,
            PlannedWorkout.workout_type == workout_type,
            PlannedWorkout.date > today,
            PlannedWorkout.completed == False
        ).limit(3).all()  # Only adjust next 3 similar workouts

        for workout in future_workouts:
            if workout.target_if:
                # target_if is stored as integer percentage
                new_if = int(min(workout.target_if * self.INTENSITY_INCREASE_FACTOR, 120))
                workout.target_if = new_if
            if workout.target_tss:
                workout.target_tss = int(workout.target_tss * self.INTENSITY_INCREASE_FACTOR)

    def _activity_matches_workout(
        self,
        activity_type: str,
        workout_type: WorkoutType
    ) -> bool:
        """Check if a Strava activity type matches a planned workout type"""
        cycling_types = ["ride", "virtualride", "cycling", "indoor_cycling"]

        if activity_type.lower().replace(" ", "") in [t.replace("_", "") for t in cycling_types]:
            return True

        return False
