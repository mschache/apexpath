"""AI Training Service using Google Gemini for plan generation.

This service implements Gemini-powered training plan generation using the
Xert/Banister impulse-response model with 3-dimensional training load tracking.
"""

import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional

import google.generativeai as genai
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.config import settings
from app.models.activity import Activity
from app.models.fitness_signature import FitnessSignature, SignatureSource
from app.models.planned_workout import PlannedWorkout, WorkoutType
from app.models.training_load import TrainingLoadRecord, TrainingStatus
from app.models.training_plan import TrainingPlan
from app.models.user import User
from app.services.xss_service import xss_service, XSSBreakdown


@dataclass
class ForecastConfig:
    """Configuration for AI-generated training forecast."""
    program_type: str  # 'goal' | 'event' | 'race'
    target_date: date
    max_weekly_hours: float
    event_readiness: int  # 1-5 scale
    periodization_level: int  # 0-100 (0=early base, 100=late intensity)
    polarization_ratio: str  # e.g., "80/20"
    recovery_demands: int  # 0-100 (0=aggressive, 100=conservative)
    available_days: dict  # {day_name: {available: bool, start_time: str, duration: int}}


@dataclass
class PlanSummary:
    """Summary of generated training plan."""
    total_weeks: int
    total_xss: float
    avg_weekly_hours: float
    phases: list[dict]


@dataclass
class PredictedFitness:
    """Predicted fitness at target date."""
    threshold_power: float
    high_intensity_energy: float
    peak_power: float
    training_load: dict
    form: dict


class AITrainingService:
    """Gemini-powered training plan generation."""

    def __init__(self):
        """Initialize the AI service with Gemini configuration."""
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel(settings.GEMINI_MODEL)
        else:
            self.model = None

    def _get_function_declarations(self) -> list:
        """Define function calling tools for Gemini."""
        return [
            {
                "name": "create_workout",
                "description": "Create a planned workout with specific intervals and targets",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": "Workout date in YYYY-MM-DD format"
                        },
                        "name": {
                            "type": "string",
                            "description": "Descriptive workout name"
                        },
                        "workout_type": {
                            "type": "string",
                            "enum": ["endurance", "tempo", "threshold", "vo2max", "recovery", "sprint", "race"],
                            "description": "Type of workout"
                        },
                        "duration_minutes": {
                            "type": "integer",
                            "description": "Total workout duration in minutes"
                        },
                        "description": {
                            "type": "string",
                            "description": "Detailed workout description"
                        },
                        "target_xss_total": {
                            "type": "number",
                            "description": "Target total XSS for this workout"
                        },
                        "target_xss_low": {
                            "type": "number",
                            "description": "Target Low (aerobic) XSS"
                        },
                        "target_xss_high": {
                            "type": "number",
                            "description": "Target High (anaerobic) XSS"
                        },
                        "target_xss_peak": {
                            "type": "number",
                            "description": "Target Peak (neuromuscular) XSS"
                        },
                        "intervals": {
                            "type": "object",
                            "description": "Interval structure for the workout",
                            "properties": {
                                "warmup": {
                                    "type": "object",
                                    "properties": {
                                        "duration": {"type": "integer"},
                                        "power_low": {"type": "number"},
                                        "power_high": {"type": "number"}
                                    }
                                },
                                "main_sets": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "duration": {"type": "integer"},
                                            "power": {"type": "number"},
                                            "rest_duration": {"type": "integer"},
                                            "rest_power": {"type": "number"},
                                            "repeats": {"type": "integer"}
                                        }
                                    }
                                },
                                "cooldown": {
                                    "type": "object",
                                    "properties": {
                                        "duration": {"type": "integer"},
                                        "power_low": {"type": "number"},
                                        "power_high": {"type": "number"}
                                    }
                                }
                            }
                        }
                    },
                    "required": ["date", "name", "workout_type", "duration_minutes"]
                }
            }
        ]

    async def generate_training_plan(
        self,
        user_id: int,
        plan_id: int,
        config: ForecastConfig,
        db: Session
    ) -> list[PlannedWorkout]:
        """
        Generate personalized training plan using Gemini.

        Steps:
        1. Gather athlete context (signature, TL/RL, history)
        2. Send to Gemini with forecast config
        3. Process Gemini response to create workouts
        4. Return generated plan

        Args:
            user_id: User ID
            plan_id: Training plan ID to associate workouts with
            config: Forecast configuration
            db: Database session

        Returns:
            List of PlannedWorkout objects
        """
        if not self.model:
            # Fallback to rule-based generation if no API key
            return self._generate_fallback_plan(user_id, plan_id, config, db)

        # Build context
        context = self._build_athlete_context(user_id, db)

        # Create prompt
        prompt = self._build_forecast_prompt(context, config)

        try:
            # Generate with Gemini
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=8192,
                )
            )

            # Parse response and create workouts
            workouts = self._parse_gemini_response(response.text, user_id, plan_id, config, db)

            return workouts

        except Exception as e:
            print(f"Gemini API error: {e}")
            # Fallback to rule-based generation
            return self._generate_fallback_plan(user_id, plan_id, config, db)

    def _build_athlete_context(self, user_id: int, db: Session) -> dict:
        """Gather all athlete data for AI context."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {}

        # Get current fitness signature
        signature = self._get_fitness_signature(user_id, db)

        # Get current training load
        training_load = xss_service.get_current_training_load(db, user_id)

        # Get recent activities
        recent_activities = self._get_recent_activities(user_id, db, days=28)

        # Calculate weekly averages
        weekly_xss = xss_service.get_weekly_xss_average(db, user_id, weeks=4)

        return {
            "user": {
                "ftp": user.ftp or 200,
                "name": user.name,
            },
            "signature": signature,
            "training_load": {
                "tl_low": training_load.tl_low if training_load else 0,
                "tl_high": training_load.tl_high if training_load else 0,
                "tl_peak": training_load.tl_peak if training_load else 0,
                "form_low": training_load.form_low if training_load else 0,
                "form_high": training_load.form_high if training_load else 0,
                "form_peak": training_load.form_peak if training_load else 0,
                "status": training_load.status if training_load else "fresh",
            } if training_load else None,
            "recent_activities": recent_activities,
            "weekly_xss_average": weekly_xss,
        }

    def _get_fitness_signature(self, user_id: int, db: Session) -> dict:
        """Get current fitness signature or estimate from FTP."""
        signature = (
            db.query(FitnessSignature)
            .filter(FitnessSignature.user_id == user_id)
            .order_by(FitnessSignature.date.desc())
            .first()
        )

        if signature:
            return {
                "threshold_power": signature.threshold_power,
                "high_intensity_energy": signature.high_intensity_energy,
                "peak_power": signature.peak_power,
                "weight_kg": signature.weight_kg,
            }

        # Estimate from user's FTP if no signature exists
        user = db.query(User).filter(User.id == user_id).first()
        ftp = user.ftp if user and user.ftp else 200

        return {
            "threshold_power": ftp,
            "high_intensity_energy": ftp * 0.1,  # Estimated 10 kJ
            "peak_power": ftp * 2.0,  # Estimated 200% FTP
            "weight_kg": 75,  # Default weight
        }

    def _get_recent_activities(
        self,
        user_id: int,
        db: Session,
        days: int = 28
    ) -> list[dict]:
        """Get recent activities formatted for AI context."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        activities = (
            db.query(Activity)
            .filter(
                and_(
                    Activity.user_id == user_id,
                    Activity.date >= start_date,
                    Activity.date <= end_date
                )
            )
            .order_by(Activity.date.desc())
            .limit(20)
            .all()
        )

        return [
            {
                "date": a.date.strftime("%Y-%m-%d"),
                "name": a.name,
                "type": a.activity_type,
                "duration_minutes": a.duration_seconds // 60,
                "tss": a.tss,
                "average_power": a.average_power,
                "normalized_power": a.normalized_power,
            }
            for a in activities
        ]

    def _build_forecast_prompt(self, context: dict, config: ForecastConfig) -> str:
        """Build comprehensive prompt for Gemini."""
        # Format recent activities
        activities_text = ""
        for a in context.get("recent_activities", [])[:10]:
            activities_text += f"  - {a['date']}: {a['name']} ({a['type']}) - {a['duration_minutes']}min, TSS: {a.get('tss', 'N/A')}\n"

        # Format available days
        available_days_text = ""
        for day, info in config.available_days.items():
            if info.get("available", False):
                available_days_text += f"  - {day}: {info.get('duration', 60)}min available\n"

        tl = context.get("training_load", {}) or {}

        return f"""You are an expert cycling coach using the Xert training methodology.
Generate a personalized day-by-day training plan based on the athlete's data.

## Athlete Profile
- Current FTP: {context.get('signature', {}).get('threshold_power', 200)}W
- Weight: {context.get('signature', {}).get('weight_kg', 75)}kg
- Current Training Load: Low={tl.get('tl_low', 0):.1f}, High={tl.get('tl_high', 0):.1f}, Peak={tl.get('tl_peak', 0):.1f}
- Current Form: Low={tl.get('form_low', 0):.1f}, High={tl.get('form_high', 0):.1f}, Peak={tl.get('form_peak', 0):.1f}
- Training Status: {tl.get('status', 'fresh')}
- Weekly XSS Average: {context.get('weekly_xss_average', 0):.0f}

## Recent Training (Last 4 Weeks)
{activities_text or "  No recent activities recorded"}

## Plan Configuration
- Program Type: {config.program_type}
- Target Date: {config.target_date}
- Max Weekly Hours: {config.max_weekly_hours}
- Event Readiness: {config.event_readiness}/5
- Periodization Level: {config.periodization_level} (0=early base, 100=race peak)
- Polarization: {config.polarization_ratio}
- Recovery Demands: {config.recovery_demands} (0=aggressive, 100=conservative)

## Available Days
{available_days_text or "  All days available, 60min default"}

## Training Principles (IMPORTANT)
1. **Impulse-Response Model**: TL builds slowly (60/22/22 day constants), RL recovers faster
2. **Form Management**: Negative form = fatigued, positive = fresh. Target slight negative during build.
3. **Periodization**: Base (aerobic) → Build (threshold) → Peak (race-specific) → Taper
4. **Polarization**: {config.polarization_ratio} - mostly easy with hard days HARD
5. **Progressive Overload**: Increase weekly XSS by 5-10% max, recovery week every 4th week
6. **XSS Targets**:
   - Recovery: 20-40 XSS (mostly Low)
   - Endurance: 50-80 XSS (80% Low, 15% High, 5% Peak)
   - Tempo: 60-90 XSS (60% Low, 30% High, 10% Peak)
   - Threshold: 70-100 XSS (40% Low, 45% High, 15% Peak)
   - VO2max: 80-120 XSS (30% Low, 40% High, 30% Peak)

## Instructions
Generate a training plan as a JSON array of workouts. For each workout include:
- date: YYYY-MM-DD format
- name: Descriptive name
- workout_type: endurance/tempo/threshold/vo2max/recovery/sprint
- duration_minutes: Total duration
- description: What the workout involves
- target_xss: {{total, low, high, peak}}

Return ONLY a valid JSON array with the workouts, no other text. Example format:
[
  {{
    "date": "2025-01-20",
    "name": "Week 1 Monday: Endurance",
    "workout_type": "endurance",
    "duration_minutes": 60,
    "description": "Steady Zone 2 ride, maintain 65-75% FTP",
    "target_xss": {{"total": 55, "low": 44, "high": 9, "peak": 2}}
  }}
]
"""

    def _parse_gemini_response(
        self,
        response_text: str,
        user_id: int,
        plan_id: int,
        config: ForecastConfig,
        db: Session
    ) -> list[PlannedWorkout]:
        """Parse Gemini response and create workout objects."""
        workouts = []

        try:
            # Extract JSON from response (handle markdown code blocks)
            json_text = response_text
            if "```json" in response_text:
                json_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                json_text = response_text.split("```")[1].split("```")[0]

            workout_data = json.loads(json_text.strip())

            # Get user's FTP for interval calculations
            user = db.query(User).filter(User.id == user_id).first()
            ftp = user.ftp if user and user.ftp else 200

            for w in workout_data:
                workout = self._create_workout_from_ai(w, plan_id, ftp)
                if workout:
                    workouts.append(workout)

        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            print(f"Response was: {response_text[:500]}...")
            # Fallback to rule-based
            return self._generate_fallback_plan(user_id, plan_id, config, db)

        return workouts

    def _create_workout_from_ai(
        self,
        data: dict,
        plan_id: int,
        ftp: int
    ) -> Optional[PlannedWorkout]:
        """Create a PlannedWorkout from AI-generated data."""
        try:
            # Parse workout type
            workout_type_str = data.get("workout_type", "endurance").lower()
            workout_type_map = {
                "endurance": WorkoutType.ENDURANCE,
                "tempo": WorkoutType.TEMPO,
                "threshold": WorkoutType.THRESHOLD,
                "vo2max": WorkoutType.VO2MAX,
                "recovery": WorkoutType.RECOVERY,
                "sprint": WorkoutType.SPRINT,
                "race": WorkoutType.RACE,
            }
            workout_type = workout_type_map.get(workout_type_str, WorkoutType.ENDURANCE)

            # Parse date
            date_str = data.get("date")
            if date_str:
                workout_date = datetime.strptime(date_str, "%Y-%m-%d")
            else:
                return None

            # Calculate TSS from XSS (approximate)
            xss = data.get("target_xss", {})
            target_tss = xss.get("total", 50) if isinstance(xss, dict) else 50

            # Estimate IF from workout type
            if_estimates = {
                WorkoutType.RECOVERY: 55,
                WorkoutType.ENDURANCE: 65,
                WorkoutType.TEMPO: 82,
                WorkoutType.THRESHOLD: 91,
                WorkoutType.VO2MAX: 110,
                WorkoutType.SPRINT: 130,
                WorkoutType.RACE: 95,
            }
            target_if = if_estimates.get(workout_type, 70)

            # Generate intervals for intensity workouts
            intervals_json = None
            duration = data.get("duration_minutes", 60)
            if workout_type in [WorkoutType.VO2MAX, WorkoutType.THRESHOLD, WorkoutType.TEMPO]:
                intervals_json = self._generate_intervals(workout_type, duration, ftp)

            return PlannedWorkout(
                plan_id=plan_id,
                date=workout_date,
                name=data.get("name", f"{workout_type.value.title()} Workout"),
                workout_type=workout_type,
                duration_minutes=duration,
                description=data.get("description", ""),
                intervals_json=intervals_json,
                target_tss=int(target_tss),
                target_if=target_if,
                completed=False
            )

        except Exception as e:
            print(f"Error creating workout: {e}")
            return None

    def _generate_intervals(
        self,
        workout_type: WorkoutType,
        duration_minutes: int,
        ftp: int
    ) -> dict:
        """Generate interval structure for a workout."""
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
            interval_duration = 180
            rest_duration = 180
            repeats = max(3, min(8, main_set_duration // (interval_duration + rest_duration)))
            structure["intervals"].append({
                "duration": interval_duration,
                "power": 1.10,
                "rest_duration": rest_duration,
                "rest_power": 0.5,
                "repeats": repeats
            })

        elif workout_type == WorkoutType.THRESHOLD:
            interval_duration = 600
            rest_duration = 300
            repeats = max(2, min(4, main_set_duration // (interval_duration + rest_duration)))
            structure["intervals"].append({
                "duration": interval_duration,
                "power": 0.91,
                "rest_duration": rest_duration,
                "rest_power": 0.55,
                "repeats": repeats
            })

        elif workout_type == WorkoutType.TEMPO:
            interval_duration = 900
            rest_duration = 300
            repeats = max(2, min(3, main_set_duration // (interval_duration + rest_duration)))
            structure["intervals"].append({
                "duration": interval_duration,
                "power": 0.82,
                "rest_duration": rest_duration,
                "rest_power": 0.55,
                "repeats": repeats
            })

        return structure

    def _generate_fallback_plan(
        self,
        user_id: int,
        plan_id: int,
        config: ForecastConfig,
        db: Session
    ) -> list[PlannedWorkout]:
        """Generate rule-based plan when AI is unavailable."""
        workouts = []
        user = db.query(User).filter(User.id == user_id).first()
        ftp = user.ftp if user and user.ftp else 200

        current_date = date.today()
        end_date = config.target_date
        total_days = (end_date - current_date).days
        total_weeks = max(1, total_days // 7)

        # Determine training days from config
        training_days = []
        day_map = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
                   "Friday": 4, "Saturday": 5, "Sunday": 6}
        for day_name, info in config.available_days.items():
            if info.get("available", False):
                if day_name in day_map:
                    training_days.append(day_map[day_name])

        if not training_days:
            training_days = [0, 2, 4, 5]  # Default: Mon, Wed, Fri, Sat

        # Parse polarization ratio
        try:
            easy_pct, hard_pct = map(int, config.polarization_ratio.split("/"))
        except:
            easy_pct, hard_pct = 80, 20

        week_num = 0
        while current_date <= end_date:
            # Get training days for this week
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

            # Recovery week every 4th week
            is_recovery = (week_num + 1) % 4 == 0
            multiplier = 0.6 if is_recovery else 1.0

            # Adjust for periodization level
            if config.periodization_level < 30:
                phase = "base"
            elif config.periodization_level < 70:
                phase = "build"
            else:
                phase = "peak"

            hours_per_session = (config.max_weekly_hours * multiplier) / len(week_training_days)

            # Number of hard days based on polarization
            num_hard = max(1, min(2, int(len(week_training_days) * hard_pct / 100)))

            for i, day in enumerate(week_training_days):
                if is_recovery:
                    workout_type = WorkoutType.RECOVERY
                    duration = int(hours_per_session * 60 * 0.8)
                elif i < num_hard:
                    if phase == "base":
                        workout_type = WorkoutType.TEMPO
                    elif phase == "build":
                        workout_type = WorkoutType.THRESHOLD
                    else:
                        workout_type = WorkoutType.VO2MAX
                    duration = int(hours_per_session * 60 * 0.9)
                else:
                    workout_type = WorkoutType.ENDURANCE
                    duration = int(hours_per_session * 60 * 1.1)

                # Calculate TSS
                tss_rates = {
                    WorkoutType.RECOVERY: 30,
                    WorkoutType.ENDURANCE: 50,
                    WorkoutType.TEMPO: 70,
                    WorkoutType.THRESHOLD: 85,
                    WorkoutType.VO2MAX: 100,
                }
                target_tss = int((duration / 60) * tss_rates.get(workout_type, 50))

                if_values = {
                    WorkoutType.RECOVERY: 55,
                    WorkoutType.ENDURANCE: 65,
                    WorkoutType.TEMPO: 82,
                    WorkoutType.THRESHOLD: 91,
                    WorkoutType.VO2MAX: 110,
                }

                # Generate intervals
                intervals_json = None
                if workout_type in [WorkoutType.VO2MAX, WorkoutType.THRESHOLD, WorkoutType.TEMPO]:
                    intervals_json = self._generate_intervals(workout_type, duration, ftp)

                workout = PlannedWorkout(
                    plan_id=plan_id,
                    date=datetime.combine(day, datetime.min.time()),
                    name=f"Week {week_num + 1} {day.strftime('%A')}: {workout_type.value.title()}",
                    workout_type=workout_type,
                    duration_minutes=duration,
                    description=f"{phase.title()} phase {workout_type.value} workout",
                    intervals_json=intervals_json,
                    target_tss=target_tss,
                    target_if=if_values.get(workout_type, 70),
                    completed=False
                )
                workouts.append(workout)

            current_date += timedelta(days=7)
            week_num += 1

        return workouts

    def get_plan_summary(self, workouts: list[PlannedWorkout]) -> PlanSummary:
        """Generate summary statistics for a training plan."""
        if not workouts:
            return PlanSummary(total_weeks=0, total_xss=0, avg_weekly_hours=0, phases=[])

        total_xss = sum(w.target_tss or 0 for w in workouts)
        total_minutes = sum(w.duration_minutes for w in workouts)

        # Calculate weeks
        dates = [w.date for w in workouts]
        min_date = min(dates)
        max_date = max(dates)
        total_weeks = max(1, (max_date - min_date).days // 7 + 1)

        # Identify phases (simplified)
        phases = []
        week_workouts = {}
        for w in workouts:
            week_num = (w.date - min_date).days // 7
            if week_num not in week_workouts:
                week_workouts[week_num] = []
            week_workouts[week_num].append(w)

        return PlanSummary(
            total_weeks=total_weeks,
            total_xss=total_xss,
            avg_weekly_hours=round(total_minutes / 60 / total_weeks, 1),
            phases=[{"name": "Training", "weeks": total_weeks}]
        )

    def predict_fitness_at_target(
        self,
        workouts: list[PlannedWorkout],
        current_load: Optional[TrainingLoadRecord],
        db: Session
    ) -> PredictedFitness:
        """Predict fitness metrics at the target date based on planned workouts."""
        if not workouts or not current_load:
            return PredictedFitness(
                threshold_power=200,
                high_intensity_energy=10,
                peak_power=400,
                training_load={"low": 0, "high": 0, "peak": 0},
                form={"low": 0, "high": 0, "peak": 0}
            )

        # Convert workouts to XSS predictions
        planned_xss = []
        for w in workouts:
            tss = w.target_tss or 50
            # Estimate XSS breakdown based on workout type
            if w.workout_type == WorkoutType.RECOVERY:
                xss = XSSBreakdown(total=tss * 0.8, low=tss * 0.7, high=tss * 0.08, peak=tss * 0.02)
            elif w.workout_type == WorkoutType.ENDURANCE:
                xss = XSSBreakdown(total=tss, low=tss * 0.8, high=tss * 0.15, peak=tss * 0.05)
            elif w.workout_type in [WorkoutType.TEMPO, WorkoutType.THRESHOLD]:
                xss = XSSBreakdown(total=tss, low=tss * 0.45, high=tss * 0.40, peak=tss * 0.15)
            else:  # VO2max, Sprint
                xss = XSSBreakdown(total=tss, low=tss * 0.30, high=tss * 0.40, peak=tss * 0.30)
            planned_xss.append(xss)

        # Predict future load
        predictions = xss_service.predict_future_load(
            current_load,
            planned_xss,
            days_ahead=len(workouts)
        )

        if predictions:
            final = predictions[-1]
            return PredictedFitness(
                threshold_power=200,  # Would need more sophisticated modeling
                high_intensity_energy=10,
                peak_power=400,
                training_load={
                    "low": round(final.tl_low, 1),
                    "high": round(final.tl_high, 1),
                    "peak": round(final.tl_peak, 1)
                },
                form={
                    "low": round(final.form_low, 1),
                    "high": round(final.form_high, 1),
                    "peak": round(final.form_peak, 1)
                }
            )

        return PredictedFitness(
            threshold_power=200,
            high_intensity_energy=10,
            peak_power=400,
            training_load={"low": 0, "high": 0, "peak": 0},
            form={"low": 0, "high": 0, "peak": 0}
        )


# Create singleton instance
ai_training_service = AITrainingService()
