"""XSS (eXcess Strain Score) calculation service for 3D training load tracking.

This service implements the Xert-style 3-dimensional training load model:
- Low (Aerobic): Long, slow adaptation with 60-day time constant
- High (Anaerobic): Moderate adaptation with 22-day time constant
- Peak (Neuromuscular): Moderate adaptation with 22-day time constant

The model tracks:
- Training Load (TL): Fitness accumulation (positive adaptation)
- Recovery Load (RL): Fatigue accumulation (faster decay)
- Form: TL - RL (readiness indicator)
"""

from dataclasses import dataclass
from datetime import date, timedelta
from math import exp
from typing import Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.activity import Activity
from app.models.training_load import TrainingLoadRecord, TrainingStatus
from app.models.fitness_signature import FitnessSignature


@dataclass
class XSSBreakdown:
    """Breakdown of XSS across three training systems."""
    total: float
    low: float    # Low intensity / aerobic
    high: float   # High intensity / anaerobic
    peak: float   # Peak / neuromuscular


@dataclass
class TrainingLoad3D:
    """3D training load values."""
    low: float
    high: float
    peak: float


class XSSService:
    """Calculate Xert-style strain scores and manage 3D training load."""

    # Time constants for each system (days)
    TIME_CONSTANTS = {
        'low': 60,    # Aerobic system - slow adaptation
        'high': 22,   # Anaerobic system - moderate
        'peak': 22,   # Neuromuscular - moderate
    }

    # Recovery load decays faster than training load
    RECOVERY_TIME_CONSTANTS = {
        'low': 7,     # Recovery from low intensity work
        'high': 5,    # Recovery from high intensity work
        'peak': 5,    # Recovery from peak work
    }

    # Intensity thresholds (as fraction of FTP)
    INTENSITY_THRESHOLDS = {
        'low_max': 0.75,     # Below 75% FTP = primarily Low XSS
        'high_threshold': 1.0,  # 75-100% FTP = primarily High XSS
        'peak_threshold': 1.2,  # Above 120% FTP = adds Peak XSS
    }

    def calculate_xss_from_activity(
        self,
        duration_seconds: int,
        average_power: Optional[float],
        normalized_power: Optional[float],
        max_power: Optional[float],
        ftp: int,
        activity_type: str
    ) -> XSSBreakdown:
        """
        Calculate 3D XSS breakdown from activity data.

        XSS is similar to TSS but allocates strain across three systems
        based on the intensity and duration of the effort.

        Args:
            duration_seconds: Total duration in seconds
            average_power: Average power in watts (optional)
            normalized_power: Normalized power in watts (optional)
            max_power: Maximum power achieved (optional)
            ftp: Functional Threshold Power in watts
            activity_type: Type of activity (e.g., "Ride", "VirtualRide")

        Returns:
            XSSBreakdown with total, low, high, peak values
        """
        if ftp <= 0 or duration_seconds <= 0:
            return XSSBreakdown(total=0, low=0, high=0, peak=0)

        # Use NP if available, otherwise average power, otherwise estimate
        power = normalized_power or average_power

        if power is None or power <= 0:
            # Estimate from duration for non-power activities
            return self._estimate_xss_from_duration(duration_seconds, activity_type)

        # Calculate total XSS (similar to TSS)
        intensity_factor = power / ftp
        total_xss = (duration_seconds * power * intensity_factor) / (ftp * 3600) * 100

        # Allocate to systems based on intensity
        xss_low, xss_high, xss_peak = self.allocate_xss_by_intensity(
            total_xss=total_xss,
            intensity_factor=intensity_factor,
            duration_seconds=duration_seconds,
            max_power=max_power,
            ftp=ftp
        )

        return XSSBreakdown(
            total=round(total_xss, 1),
            low=round(xss_low, 1),
            high=round(xss_high, 1),
            peak=round(xss_peak, 1)
        )

    def allocate_xss_by_intensity(
        self,
        total_xss: float,
        intensity_factor: float,
        duration_seconds: int,
        max_power: Optional[float],
        ftp: int
    ) -> tuple[float, float, float]:
        """
        Allocate XSS to Low/High/Peak based on intensity and duration.

        Allocation rules:
        - Longer, easier efforts → more Low XSS
        - Shorter, harder efforts → more High/Peak XSS
        - Very high power spikes → Peak XSS contribution

        Args:
            total_xss: Total XSS to allocate
            intensity_factor: NP/FTP ratio
            duration_seconds: Duration in seconds
            max_power: Maximum power achieved
            ftp: Functional Threshold Power

        Returns:
            Tuple of (low_xss, high_xss, peak_xss)
        """
        if total_xss <= 0:
            return (0.0, 0.0, 0.0)

        # Base allocation based on intensity factor
        if intensity_factor <= self.INTENSITY_THRESHOLDS['low_max']:
            # Low intensity: mostly aerobic
            # The lower the intensity, the more goes to Low
            low_ratio = 0.7 + (0.2 * (1 - intensity_factor / self.INTENSITY_THRESHOLDS['low_max']))
            high_ratio = 1 - low_ratio - 0.05
            peak_ratio = 0.05
        elif intensity_factor <= self.INTENSITY_THRESHOLDS['high_threshold']:
            # Moderate intensity: mix of Low and High
            progress = (intensity_factor - self.INTENSITY_THRESHOLDS['low_max']) / \
                      (self.INTENSITY_THRESHOLDS['high_threshold'] - self.INTENSITY_THRESHOLDS['low_max'])
            low_ratio = 0.5 - (0.3 * progress)  # 50% -> 20%
            high_ratio = 0.4 + (0.4 * progress)  # 40% -> 80%
            peak_ratio = 0.1 * progress  # 0% -> 10%
        else:
            # High intensity: mostly High and Peak
            low_ratio = 0.15
            high_ratio = 0.55
            peak_ratio = 0.30

        # Adjust for duration (longer efforts = more Low contribution)
        hours = duration_seconds / 3600
        if hours > 2:
            # Long efforts shift more to Low system
            duration_shift = min(0.15, (hours - 2) * 0.05)
            low_ratio += duration_shift
            high_ratio -= duration_shift * 0.7
            peak_ratio -= duration_shift * 0.3

        # Adjust for max power spikes (neuromuscular contribution)
        if max_power and ftp > 0:
            max_power_ratio = max_power / ftp
            if max_power_ratio > self.INTENSITY_THRESHOLDS['peak_threshold']:
                # High power spikes add Peak contribution
                peak_bonus = min(0.15, (max_power_ratio - self.INTENSITY_THRESHOLDS['peak_threshold']) * 0.1)
                peak_ratio += peak_bonus
                high_ratio -= peak_bonus * 0.7
                low_ratio -= peak_bonus * 0.3

        # Normalize ratios
        total_ratio = low_ratio + high_ratio + peak_ratio
        low_ratio /= total_ratio
        high_ratio /= total_ratio
        peak_ratio /= total_ratio

        return (
            total_xss * low_ratio,
            total_xss * high_ratio,
            total_xss * peak_ratio
        )

    def _estimate_xss_from_duration(
        self,
        duration_seconds: int,
        activity_type: str
    ) -> XSSBreakdown:
        """
        Estimate XSS from duration when no power data is available.

        Uses typical XSS values per hour based on activity type.
        """
        hours = duration_seconds / 3600

        # XSS per hour estimates by activity type
        xss_per_hour = {
            'Ride': 50,
            'VirtualRide': 60,  # Indoor tends to be more consistent
            'Run': 70,
            'Walk': 25,
            'Hike': 40,
            'Swim': 55,
        }

        base_xss = hours * xss_per_hour.get(activity_type, 50)

        # Estimate allocation (assume moderate intensity for non-power activities)
        return XSSBreakdown(
            total=round(base_xss, 1),
            low=round(base_xss * 0.65, 1),
            high=round(base_xss * 0.28, 1),
            peak=round(base_xss * 0.07, 1)
        )

    def update_training_load(
        self,
        current_record: TrainingLoadRecord,
        xss: XSSBreakdown,
        days_elapsed: float = 1.0
    ) -> TrainingLoadRecord:
        """
        Apply exponential decay and add new XSS contribution.

        The impulse-response model:
        TL_new = TL_old * exp(-t/tau) + XSS
        RL_new = RL_old * exp(-t/tau_r) + XSS

        Args:
            current_record: Current TrainingLoadRecord
            xss: XSS breakdown to apply
            days_elapsed: Days since last update (default 1.0)

        Returns:
            Updated TrainingLoadRecord
        """
        # Calculate decay factors for TL
        tl_decay = {
            'low': exp(-days_elapsed / self.TIME_CONSTANTS['low']),
            'high': exp(-days_elapsed / self.TIME_CONSTANTS['high']),
            'peak': exp(-days_elapsed / self.TIME_CONSTANTS['peak']),
        }

        # Calculate decay factors for RL (faster decay)
        rl_decay = {
            'low': exp(-days_elapsed / self.RECOVERY_TIME_CONSTANTS['low']),
            'high': exp(-days_elapsed / self.RECOVERY_TIME_CONSTANTS['high']),
            'peak': exp(-days_elapsed / self.RECOVERY_TIME_CONSTANTS['peak']),
        }

        # Update Training Load (fitness)
        current_record.tl_low = current_record.tl_low * tl_decay['low'] + xss.low
        current_record.tl_high = current_record.tl_high * tl_decay['high'] + xss.high
        current_record.tl_peak = current_record.tl_peak * tl_decay['peak'] + xss.peak

        # Update Recovery Load (fatigue)
        current_record.rl_low = current_record.rl_low * rl_decay['low'] + xss.low
        current_record.rl_high = current_record.rl_high * rl_decay['high'] + xss.high
        current_record.rl_peak = current_record.rl_peak * rl_decay['peak'] + xss.peak

        # Store daily XSS
        current_record.xss_total = xss.total
        current_record.xss_low = xss.low
        current_record.xss_high = xss.high
        current_record.xss_peak = xss.peak

        # Update form and status
        current_record.calculate_form()
        current_record.update_status()

        return current_record

    def apply_decay_only(
        self,
        current_record: TrainingLoadRecord,
        days_elapsed: float = 1.0
    ) -> TrainingLoadRecord:
        """
        Apply decay without adding new training (rest day).

        Args:
            current_record: Current TrainingLoadRecord
            days_elapsed: Days since last update

        Returns:
            Updated TrainingLoadRecord
        """
        return self.update_training_load(
            current_record,
            XSSBreakdown(total=0, low=0, high=0, peak=0),
            days_elapsed
        )

    def calculate_training_load_history(
        self,
        db: Session,
        user_id: int,
        days: int = 90,
        recalculate: bool = False
    ) -> list[TrainingLoadRecord]:
        """
        Calculate 3D training load for each day in the specified range.

        Args:
            db: Database session
            user_id: User ID to calculate metrics for
            days: Number of days to calculate (default 90)
            recalculate: If True, recalculate all metrics

        Returns:
            List of TrainingLoadRecord objects
        """
        end_date = date.today()
        # Need extra history for time constant calculations
        history_start = end_date - timedelta(days=days + max(self.TIME_CONSTANTS.values()))
        result_start = end_date - timedelta(days=days)

        # Get user's FTP
        from app.models.user import User
        user = db.query(User).filter(User.id == user_id).first()
        ftp = user.ftp if user and user.ftp else 200  # Default FTP if not set

        # Get all activities in the date range
        activities = (
            db.query(Activity)
            .filter(
                and_(
                    Activity.user_id == user_id,
                    Activity.date >= history_start,
                    Activity.date <= end_date
                )
            )
            .order_by(Activity.date)
            .all()
        )

        # Build daily XSS (accumulate if multiple activities per day)
        daily_xss: dict[date, XSSBreakdown] = {}
        for activity in activities:
            activity_date = activity.date.date() if hasattr(activity.date, 'date') else activity.date
            xss = self.calculate_xss_from_activity(
                duration_seconds=activity.duration_seconds,
                average_power=activity.average_power,
                normalized_power=activity.normalized_power,
                max_power=getattr(activity, 'max_power', None),
                ftp=ftp,
                activity_type=activity.activity_type
            )

            if activity_date in daily_xss:
                existing = daily_xss[activity_date]
                daily_xss[activity_date] = XSSBreakdown(
                    total=existing.total + xss.total,
                    low=existing.low + xss.low,
                    high=existing.high + xss.high,
                    peak=existing.peak + xss.peak
                )
            else:
                daily_xss[activity_date] = xss

        # Load existing records
        existing_records = (
            db.query(TrainingLoadRecord)
            .filter(
                and_(
                    TrainingLoadRecord.user_id == user_id,
                    TrainingLoadRecord.date >= result_start,
                    TrainingLoadRecord.date <= end_date
                )
            )
            .all()
        )
        existing_by_date = {r.date: r for r in existing_records}

        # Calculate training load for each day
        results: list[TrainingLoadRecord] = []
        current_date = history_start
        prev_record: Optional[TrainingLoadRecord] = None

        # Initialize from earliest existing record or start fresh
        initial_record = TrainingLoadRecord(
            user_id=user_id,
            date=history_start,
            tl_low=0, tl_high=0, tl_peak=0,
            rl_low=0, rl_high=0, rl_peak=0,
            form_low=0, form_high=0, form_peak=0,
            xss_total=0, xss_low=0, xss_high=0, xss_peak=0,
            status=TrainingStatus.FRESH.value
        )

        while current_date <= end_date:
            xss = daily_xss.get(current_date, XSSBreakdown(total=0, low=0, high=0, peak=0))

            # Get or create record for this date
            if not recalculate and current_date in existing_by_date:
                record = existing_by_date[current_date]
                prev_record = record
                if current_date >= result_start:
                    results.append(record)
                current_date += timedelta(days=1)
                continue

            # Create new record based on previous
            if prev_record:
                record = TrainingLoadRecord(
                    user_id=user_id,
                    date=current_date,
                    tl_low=prev_record.tl_low,
                    tl_high=prev_record.tl_high,
                    tl_peak=prev_record.tl_peak,
                    rl_low=prev_record.rl_low,
                    rl_high=prev_record.rl_high,
                    rl_peak=prev_record.rl_peak,
                    form_low=0, form_high=0, form_peak=0,
                    xss_total=0, xss_low=0, xss_high=0, xss_peak=0,
                    status=TrainingStatus.FRESH.value
                )
            else:
                record = TrainingLoadRecord(
                    user_id=user_id,
                    date=current_date,
                    tl_low=0, tl_high=0, tl_peak=0,
                    rl_low=0, rl_high=0, rl_peak=0,
                    form_low=0, form_high=0, form_peak=0,
                    xss_total=0, xss_low=0, xss_high=0, xss_peak=0,
                    status=TrainingStatus.FRESH.value
                )

            # Apply decay and add XSS
            self.update_training_load(record, xss, days_elapsed=1.0)

            # Update or insert
            if current_date in existing_by_date:
                existing = existing_by_date[current_date]
                existing.tl_low = record.tl_low
                existing.tl_high = record.tl_high
                existing.tl_peak = record.tl_peak
                existing.rl_low = record.rl_low
                existing.rl_high = record.rl_high
                existing.rl_peak = record.rl_peak
                existing.form_low = record.form_low
                existing.form_high = record.form_high
                existing.form_peak = record.form_peak
                existing.xss_total = record.xss_total
                existing.xss_low = record.xss_low
                existing.xss_high = record.xss_high
                existing.xss_peak = record.xss_peak
                existing.status = record.status
                record = existing
            else:
                db.add(record)

            prev_record = record
            if current_date >= result_start:
                results.append(record)

            current_date += timedelta(days=1)

        db.commit()
        return results

    def get_current_training_load(
        self,
        db: Session,
        user_id: int
    ) -> Optional[TrainingLoadRecord]:
        """
        Get the most recent training load record for a user.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            Latest TrainingLoadRecord or None
        """
        return (
            db.query(TrainingLoadRecord)
            .filter(TrainingLoadRecord.user_id == user_id)
            .order_by(TrainingLoadRecord.date.desc())
            .first()
        )

    def get_weekly_xss_average(
        self,
        db: Session,
        user_id: int,
        weeks: int = 4
    ) -> float:
        """
        Calculate average weekly XSS over the specified number of weeks.

        Args:
            db: Database session
            user_id: User ID
            weeks: Number of weeks to average

        Returns:
            Average weekly XSS
        """
        end_date = date.today()
        start_date = end_date - timedelta(weeks=weeks)

        records = (
            db.query(TrainingLoadRecord)
            .filter(
                and_(
                    TrainingLoadRecord.user_id == user_id,
                    TrainingLoadRecord.date >= start_date,
                    TrainingLoadRecord.date <= end_date
                )
            )
            .all()
        )

        if not records:
            return 0.0

        total_xss = sum(r.xss_total for r in records)
        return round(total_xss / weeks, 1)

    def predict_future_load(
        self,
        current_record: TrainingLoadRecord,
        planned_xss: list[XSSBreakdown],
        days_ahead: int = 7
    ) -> list[TrainingLoadRecord]:
        """
        Predict future training load based on planned workouts.

        Args:
            current_record: Current TrainingLoadRecord
            planned_xss: List of planned XSS for each future day
            days_ahead: Number of days to predict

        Returns:
            List of predicted TrainingLoadRecord objects
        """
        predictions = []
        prev = current_record

        for i in range(days_ahead):
            # Create prediction record
            pred = TrainingLoadRecord(
                user_id=current_record.user_id,
                date=current_record.date + timedelta(days=i + 1),
                tl_low=prev.tl_low,
                tl_high=prev.tl_high,
                tl_peak=prev.tl_peak,
                rl_low=prev.rl_low,
                rl_high=prev.rl_high,
                rl_peak=prev.rl_peak,
                form_low=0, form_high=0, form_peak=0,
                xss_total=0, xss_low=0, xss_high=0, xss_peak=0,
                status=TrainingStatus.FRESH.value
            )

            # Apply planned XSS or just decay
            if i < len(planned_xss):
                self.update_training_load(pred, planned_xss[i])
            else:
                self.apply_decay_only(pred)

            predictions.append(pred)
            prev = pred

        return predictions


# Create a singleton instance for convenience
xss_service = XSSService()
