from enum import Enum
from typing import List, Optional
from datetime import date, datetime, timedelta
import math

from app.models.planned_workout import PlannedWorkout, WorkoutType
from app.models.training_plan import TrainingPlan, TrainingPhilosophy


class PlanPhilosophy(str, Enum):
    """Alias for TrainingPhilosophy for backward compatibility"""
    POLARIZED = "polarized"      # 80/20 easy/hard
    SWEET_SPOT = "sweet_spot"    # Focus on 88-94% FTP
    TRADITIONAL = "traditional"  # Base -> Build -> Peak -> Taper


class PlanGenerator:
    """Generate adaptive training plans based on user goals"""

    # Workout templates with power ranges (as % of FTP) and descriptions
    WORKOUT_TEMPLATES = {
        WorkoutType.ENDURANCE: {
            "power_range": (0.55, 0.75),
            "description": "Steady Zone 2 ride",
            "tss_per_hour": 50
        },
        WorkoutType.TEMPO: {
            "power_range": (0.76, 0.87),
            "description": "Sustained tempo effort",
            "tss_per_hour": 70
        },
        WorkoutType.THRESHOLD: {
            "power_range": (0.88, 0.94),
            "description": "Sweet spot intervals",
            "tss_per_hour": 85
        },
        WorkoutType.VO2MAX: {
            "power_range": (1.06, 1.20),
            "description": "High intensity intervals",
            "tss_per_hour": 100
        },
        WorkoutType.RECOVERY: {
            "power_range": (0.40, 0.55),
            "description": "Easy spin recovery",
            "tss_per_hour": 30
        },
        WorkoutType.RACE: {
            "power_range": (0.95, 1.10),
            "description": "Race simulation",
            "tss_per_hour": 95
        },
        WorkoutType.SPRINT: {
            "power_range": (1.50, 2.00),
            "description": "Sprint intervals",
            "tss_per_hour": 110
        },
    }

    def generate_plan(
        self,
        user_id: int,
        plan_id: int,
        philosophy: PlanPhilosophy,
        start_date: date,
        end_date: date,
        weekly_hours: float,
        training_days: List[int],  # 0=Monday, 6=Sunday
        current_ctl: float,
        ftp: int
    ) -> List[PlannedWorkout]:
        """
        Generate complete training plan with workouts

        Args:
            user_id: User ID
            plan_id: Training plan ID
            philosophy: Training philosophy (polarized, sweet_spot, traditional)
            start_date: Plan start date
            end_date: Plan end date
            weekly_hours: Target weekly training hours
            training_days: List of training day indices (0=Monday, 6=Sunday)
            current_ctl: Current Chronic Training Load
            ftp: Functional Threshold Power

        Returns:
            List of PlannedWorkout objects
        """
        if philosophy == PlanPhilosophy.POLARIZED:
            return self._generate_polarized_plan(
                user_id, plan_id, start_date, end_date,
                weekly_hours, training_days, current_ctl, ftp
            )
        elif philosophy == PlanPhilosophy.SWEET_SPOT:
            return self._generate_sweet_spot_plan(
                user_id, plan_id, start_date, end_date,
                weekly_hours, training_days, current_ctl, ftp
            )
        elif philosophy == PlanPhilosophy.TRADITIONAL:
            return self._generate_traditional_plan(
                user_id, plan_id, start_date, end_date,
                weekly_hours, training_days, current_ctl, ftp
            )
        else:
            raise ValueError(f"Unknown philosophy: {philosophy}")

    def _generate_polarized_plan(
        self,
        user_id: int,
        plan_id: int,
        start_date: date,
        end_date: date,
        weekly_hours: float,
        training_days: List[int],
        current_ctl: float,
        ftp: int
    ) -> List[PlannedWorkout]:
        """
        80/20 Polarized training:
        - 80% Zone 1-2 (endurance rides)
        - 20% Zone 4-5 (intervals)
        Weekly structure:
        - 2 interval sessions (VO2max, Threshold)
        - Remaining: endurance rides
        """
        workouts = []
        current_date = start_date
        week_num = 0

        while current_date <= end_date:
            week_start = current_date
            week_training_days = []

            # Find training days for this week
            for i in range(7):
                day = week_start + timedelta(days=i)
                if day > end_date:
                    break
                if day.weekday() in training_days:
                    week_training_days.append(day)

            if not week_training_days:
                current_date += timedelta(days=7)
                week_num += 1
                continue

            # Recovery week every 4th week
            is_recovery_week = (week_num + 1) % 4 == 0
            week_multiplier = 0.6 if is_recovery_week else 1.0

            # Calculate hours per day
            adjusted_hours = weekly_hours * week_multiplier
            hours_per_session = adjusted_hours / len(week_training_days)

            # Assign workout types (80/20 split)
            num_hard_days = max(1, min(2, len(week_training_days) // 3))

            for i, day in enumerate(week_training_days):
                if i < num_hard_days and not is_recovery_week:
                    # Hard day: alternate between VO2max and Threshold
                    workout_type = WorkoutType.VO2MAX if i % 2 == 0 else WorkoutType.THRESHOLD
                    duration = int(hours_per_session * 60 * 0.8)  # Hard workouts slightly shorter
                else:
                    # Easy day: endurance
                    workout_type = WorkoutType.RECOVERY if is_recovery_week else WorkoutType.ENDURANCE
                    duration = int(hours_per_session * 60 * 1.1)  # Easy workouts can be longer

                workout = self._create_workout(
                    user_id=user_id,
                    plan_id=plan_id,
                    scheduled_date=day,
                    workout_type=workout_type,
                    duration_minutes=duration,
                    ftp=ftp,
                    week_num=week_num + 1
                )
                workouts.append(workout)

            current_date += timedelta(days=7)
            week_num += 1

        return workouts

    def _generate_sweet_spot_plan(
        self,
        user_id: int,
        plan_id: int,
        start_date: date,
        end_date: date,
        weekly_hours: float,
        training_days: List[int],
        current_ctl: float,
        ftp: int
    ) -> List[PlannedWorkout]:
        """
        Sweet Spot training:
        - Focus on 88-94% FTP
        - Time efficient: high TSS per hour
        Weekly structure:
        - 2-3 sweet spot sessions
        - 1 endurance ride
        - 1 recovery ride
        """
        workouts = []
        current_date = start_date
        week_num = 0

        while current_date <= end_date:
            week_start = current_date
            week_training_days = []

            for i in range(7):
                day = week_start + timedelta(days=i)
                if day > end_date:
                    break
                if day.weekday() in training_days:
                    week_training_days.append(day)

            if not week_training_days:
                current_date += timedelta(days=7)
                week_num += 1
                continue

            # Recovery week every 4th week
            is_recovery_week = (week_num + 1) % 4 == 0
            week_multiplier = 0.6 if is_recovery_week else 1.0

            adjusted_hours = weekly_hours * week_multiplier
            hours_per_session = adjusted_hours / len(week_training_days)

            # Sweet spot focus: more threshold work
            num_sweet_spot = max(1, min(3, len(week_training_days) - 1))

            for i, day in enumerate(week_training_days):
                if is_recovery_week:
                    workout_type = WorkoutType.RECOVERY
                    duration = int(hours_per_session * 60)
                elif i < num_sweet_spot:
                    # Sweet spot session
                    workout_type = WorkoutType.THRESHOLD
                    duration = int(hours_per_session * 60)
                elif i == num_sweet_spot:
                    # One endurance ride
                    workout_type = WorkoutType.ENDURANCE
                    duration = int(hours_per_session * 60 * 1.2)  # Longer endurance
                else:
                    # Recovery
                    workout_type = WorkoutType.RECOVERY
                    duration = int(hours_per_session * 60 * 0.7)

                workout = self._create_workout(
                    user_id=user_id,
                    plan_id=plan_id,
                    scheduled_date=day,
                    workout_type=workout_type,
                    duration_minutes=duration,
                    ftp=ftp,
                    week_num=week_num + 1
                )
                workouts.append(workout)

            current_date += timedelta(days=7)
            week_num += 1

        return workouts

    def _generate_traditional_plan(
        self,
        user_id: int,
        plan_id: int,
        start_date: date,
        end_date: date,
        weekly_hours: float,
        training_days: List[int],
        current_ctl: float,
        ftp: int
    ) -> List[PlannedWorkout]:
        """
        Traditional periodization:
        - Base phase: Build aerobic engine (Zone 2) - 40% of plan
        - Build phase: Add intensity (Sweet Spot, Threshold) - 30% of plan
        - Peak phase: Race-specific (VO2max, short intervals) - 20% of plan
        - Taper phase: Reduce volume, maintain intensity - 10% of plan
        """
        workouts = []
        total_days = (end_date - start_date).days
        total_weeks = total_days // 7

        # Phase durations
        base_weeks = int(total_weeks * 0.4)
        build_weeks = int(total_weeks * 0.3)
        peak_weeks = int(total_weeks * 0.2)
        taper_weeks = max(1, total_weeks - base_weeks - build_weeks - peak_weeks)

        current_date = start_date
        week_num = 0

        while current_date <= end_date:
            # Determine current phase
            if week_num < base_weeks:
                phase = "base"
                volume_multiplier = 0.8 + (0.2 * week_num / max(1, base_weeks))
            elif week_num < base_weeks + build_weeks:
                phase = "build"
                phase_week = week_num - base_weeks
                volume_multiplier = 1.0 + (0.1 * phase_week / max(1, build_weeks))
            elif week_num < base_weeks + build_weeks + peak_weeks:
                phase = "peak"
                volume_multiplier = 1.0
            else:
                phase = "taper"
                phase_week = week_num - base_weeks - build_weeks - peak_weeks
                volume_multiplier = 0.8 - (0.3 * phase_week / max(1, taper_weeks))

            # Recovery week check
            is_recovery_week = (week_num + 1) % 4 == 0 and phase != "taper"
            if is_recovery_week:
                volume_multiplier *= 0.6

            week_training_days = []
            for i in range(7):
                day = current_date + timedelta(days=i)
                if day > end_date:
                    break
                if day.weekday() in training_days:
                    week_training_days.append(day)

            if not week_training_days:
                current_date += timedelta(days=7)
                week_num += 1
                continue

            adjusted_hours = weekly_hours * volume_multiplier
            hours_per_session = adjusted_hours / len(week_training_days)

            # Workout distribution by phase
            for i, day in enumerate(week_training_days):
                workout_type, duration = self._get_traditional_workout(
                    phase, i, len(week_training_days),
                    hours_per_session, is_recovery_week
                )

                workout = self._create_workout(
                    user_id=user_id,
                    plan_id=plan_id,
                    scheduled_date=day,
                    workout_type=workout_type,
                    duration_minutes=duration,
                    ftp=ftp,
                    week_num=week_num + 1,
                    phase=phase
                )
                workouts.append(workout)

            current_date += timedelta(days=7)
            week_num += 1

        return workouts

    def _get_traditional_workout(
        self,
        phase: str,
        day_index: int,
        total_days: int,
        hours_per_session: float,
        is_recovery_week: bool
    ) -> tuple:
        """Get workout type and duration for traditional periodization"""
        base_duration = int(hours_per_session * 60)

        if is_recovery_week:
            return WorkoutType.RECOVERY, int(base_duration * 0.8)

        if phase == "base":
            # Mostly endurance with occasional tempo
            if day_index == 0 and total_days > 2:
                return WorkoutType.TEMPO, base_duration
            return WorkoutType.ENDURANCE, int(base_duration * 1.1)

        elif phase == "build":
            # Mix of threshold and endurance
            if day_index < 2:
                return WorkoutType.THRESHOLD, base_duration
            elif day_index == 2:
                return WorkoutType.ENDURANCE, int(base_duration * 1.2)
            return WorkoutType.RECOVERY, int(base_duration * 0.7)

        elif phase == "peak":
            # High intensity focus
            if day_index == 0:
                return WorkoutType.VO2MAX, int(base_duration * 0.9)
            elif day_index == 1:
                return WorkoutType.THRESHOLD, base_duration
            elif day_index == 2:
                return WorkoutType.ENDURANCE, base_duration
            return WorkoutType.RECOVERY, int(base_duration * 0.6)

        else:  # taper
            # Reduced volume, some intensity
            if day_index == 0:
                return WorkoutType.THRESHOLD, int(base_duration * 0.7)
            return WorkoutType.RECOVERY, int(base_duration * 0.5)

    def _create_workout(
        self,
        user_id: int,
        plan_id: int,
        scheduled_date: date,
        workout_type: WorkoutType,
        duration_minutes: int,
        ftp: int,
        week_num: int,
        phase: Optional[str] = None
    ) -> PlannedWorkout:
        """Create a PlannedWorkout object with all details"""
        template = self.WORKOUT_TEMPLATES.get(workout_type, self.WORKOUT_TEMPLATES[WorkoutType.ENDURANCE])

        # Calculate target TSS
        target_tss = int((duration_minutes / 60) * template["tss_per_hour"])

        # Calculate Intensity Factor (average of power range) as percentage
        power_low, power_high = template["power_range"]
        target_if = int(((power_low + power_high) / 2) * 100)

        # Generate workout name
        day_name = scheduled_date.strftime("%A")
        name = f"Week {week_num} {day_name}: {workout_type.value.title()}"
        if phase:
            name = f"[{phase.title()}] {name}"

        # Generate interval structure for interval workouts
        intervals_json = None
        if workout_type in [WorkoutType.VO2MAX, WorkoutType.THRESHOLD, WorkoutType.TEMPO]:
            intervals_json = self.create_interval_workout(
                workout_type, duration_minutes, ftp
            )

        # Convert date to datetime for the model
        workout_datetime = datetime.combine(scheduled_date, datetime.min.time())

        return PlannedWorkout(
            plan_id=plan_id,
            date=workout_datetime,
            name=name,
            workout_type=workout_type,
            duration_minutes=duration_minutes,
            description=template["description"],
            intervals_json=intervals_json,
            target_tss=target_tss,
            target_if=target_if,
            completed=False
        )

    def create_interval_workout(
        self,
        workout_type: WorkoutType,
        duration_minutes: int,
        ftp: int
    ) -> dict:
        """
        Create interval structure as JSON

        Returns:
            {
                "warmup": {"duration": 600, "power_low": 0.5, "power_high": 0.7},
                "intervals": [
                    {"duration": 300, "power": 1.05, "rest_duration": 300, "rest_power": 0.5, "repeats": 5}
                ],
                "cooldown": {"duration": 300, "power_low": 0.5, "power_high": 0.6}
            }
            Power values as % of FTP (1.0 = 100% FTP)
        """
        total_seconds = duration_minutes * 60
        warmup_duration = 600  # 10 minutes
        cooldown_duration = 300  # 5 minutes

        main_set_duration = total_seconds - warmup_duration - cooldown_duration

        structure = {
            "warmup": {
                "duration": warmup_duration,
                "power_low": 0.5,
                "power_high": 0.7
            },
            "intervals": [],
            "cooldown": {
                "duration": cooldown_duration,
                "power_low": 0.5,
                "power_high": 0.6
            }
        }

        if workout_type == WorkoutType.VO2MAX:
            # VO2max: 3-5 minute intervals at 106-120% FTP
            interval_duration = 180  # 3 minutes
            rest_duration = 180  # 3 minutes
            interval_with_rest = interval_duration + rest_duration
            repeats = max(3, min(8, main_set_duration // interval_with_rest))

            structure["intervals"].append({
                "duration": interval_duration,
                "power": 1.10,
                "rest_duration": rest_duration,
                "rest_power": 0.5,
                "repeats": repeats
            })

        elif workout_type == WorkoutType.THRESHOLD:
            # Sweet spot: 8-20 minute intervals at 88-94% FTP
            interval_duration = 600  # 10 minutes
            rest_duration = 300  # 5 minutes
            interval_with_rest = interval_duration + rest_duration
            repeats = max(2, min(4, main_set_duration // interval_with_rest))

            structure["intervals"].append({
                "duration": interval_duration,
                "power": 0.91,
                "rest_duration": rest_duration,
                "rest_power": 0.55,
                "repeats": repeats
            })

        elif workout_type == WorkoutType.TEMPO:
            # Tempo: longer intervals at 76-87% FTP
            interval_duration = 900  # 15 minutes
            rest_duration = 300  # 5 minutes
            interval_with_rest = interval_duration + rest_duration
            repeats = max(2, min(3, main_set_duration // interval_with_rest))

            structure["intervals"].append({
                "duration": interval_duration,
                "power": 0.82,
                "rest_duration": rest_duration,
                "rest_power": 0.55,
                "repeats": repeats
            })

        return structure

    def estimate_weekly_tss(
        self,
        weekly_hours: float,
        philosophy: PlanPhilosophy
    ) -> float:
        """Estimate weekly TSS based on hours and philosophy"""
        # Average TSS per hour varies by philosophy
        tss_per_hour = {
            PlanPhilosophy.POLARIZED: 55,  # Mix of easy and hard
            PlanPhilosophy.SWEET_SPOT: 70,  # Higher intensity focus
            PlanPhilosophy.TRADITIONAL: 60,  # Varies by phase
        }
        return weekly_hours * tss_per_hour.get(philosophy, 60)
