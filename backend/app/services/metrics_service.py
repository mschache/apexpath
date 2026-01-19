"""Cycling fitness metrics calculation service.

This service implements standard cycling training metrics including:
- Training Stress Score (TSS)
- Normalized Power (NP)
- Intensity Factor (IF)
- Chronic Training Load (CTL) - "Fitness"
- Acute Training Load (ATL) - "Fatigue"
- Training Stress Balance (TSB) - "Form"
"""

from datetime import date, timedelta
from typing import Optional

from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from app.models.activity import Activity
from app.models.fitness_metric import FitnessMetric
from app.models.user import User


class MetricsService:
    """Calculate cycling fitness metrics from power and heart rate data."""

    # Constants for training load calculations
    CTL_TIME_CONSTANT = 42  # Days for Chronic Training Load
    ATL_TIME_CONSTANT = 7   # Days for Acute Training Load
    ROLLING_AVG_WINDOW = 30  # Seconds for NP calculation

    # Power zone percentages of FTP
    POWER_ZONES = {
        "zone_1": {"name": "Recovery", "min": 0, "max": 55},
        "zone_2": {"name": "Endurance", "min": 55, "max": 75},
        "zone_3": {"name": "Tempo", "min": 76, "max": 90},
        "zone_4": {"name": "Threshold", "min": 91, "max": 105},
        "zone_5": {"name": "VO2max", "min": 106, "max": 120},
        "zone_6": {"name": "Anaerobic", "min": 121, "max": float("inf")},
    }

    def calculate_tss(
        self,
        duration_seconds: int,
        normalized_power: int,
        ftp: int
    ) -> float:
        """
        Calculate Training Stress Score (TSS).

        TSS quantifies the training load of a workout based on duration and intensity.
        TSS = (duration × NP × IF) / (FTP × 3600) × 100
        where IF (Intensity Factor) = NP / FTP

        Args:
            duration_seconds: Total duration of the workout in seconds
            normalized_power: Normalized Power in watts
            ftp: Functional Threshold Power in watts

        Returns:
            Training Stress Score as a float

        Raises:
            ValueError: If FTP is zero or negative
        """
        if ftp <= 0:
            raise ValueError("FTP must be greater than zero")

        if duration_seconds <= 0 or normalized_power <= 0:
            return 0.0

        intensity_factor = normalized_power / ftp
        tss = (duration_seconds * normalized_power * intensity_factor) / (ftp * 3600) * 100

        return round(tss, 1)

    def calculate_intensity_factor(self, normalized_power: int, ftp: int) -> float:
        """
        Calculate Intensity Factor (IF).

        IF = NP / FTP
        IF of 1.0 means the workout was at FTP intensity.

        Args:
            normalized_power: Normalized Power in watts
            ftp: Functional Threshold Power in watts

        Returns:
            Intensity Factor as a float
        """
        if ftp <= 0:
            raise ValueError("FTP must be greater than zero")

        if normalized_power <= 0:
            return 0.0

        return round(normalized_power / ftp, 2)

    def calculate_normalized_power(self, power_data: list[int]) -> int:
        """
        Calculate Normalized Power (NP) from a power stream.

        NP accounts for the variability of power output during a ride.
        Algorithm:
        1. Calculate 30-second rolling average of power
        2. Raise each value to the 4th power
        3. Take the average of these values
        4. Take the 4th root

        Args:
            power_data: List of power values in watts (1Hz sampling rate)

        Returns:
            Normalized Power in watts as an integer
        """
        if not power_data or len(power_data) < self.ROLLING_AVG_WINDOW:
            # Not enough data for rolling average, return average power
            if power_data:
                valid_values = [p for p in power_data if p is not None and p >= 0]
                if valid_values:
                    return int(sum(valid_values) / len(valid_values))
            return 0

        # Filter out None values and negative values
        cleaned_data = [p if p is not None and p >= 0 else 0 for p in power_data]

        # Step 1: Calculate 30-second rolling average
        rolling_averages = []
        for i in range(len(cleaned_data) - self.ROLLING_AVG_WINDOW + 1):
            window = cleaned_data[i:i + self.ROLLING_AVG_WINDOW]
            rolling_avg = sum(window) / self.ROLLING_AVG_WINDOW
            rolling_averages.append(rolling_avg)

        if not rolling_averages:
            return 0

        # Step 2 & 3: Raise to 4th power and average
        fourth_powers = [avg ** 4 for avg in rolling_averages]
        avg_fourth_power = sum(fourth_powers) / len(fourth_powers)

        # Step 4: Take 4th root
        normalized_power = avg_fourth_power ** 0.25

        return int(round(normalized_power))

    def calculate_ctl(
        self,
        tss_history: list[tuple[date, float]],
        target_date: date,
        initial_ctl: float = 0.0
    ) -> float:
        """
        Calculate Chronic Training Load (CTL) - "Fitness".

        CTL is a 42-day exponentially weighted moving average of TSS.
        It represents long-term training load and fitness.

        Formula: CTL_today = CTL_yesterday + (TSS_today - CTL_yesterday) / 42

        Args:
            tss_history: List of (date, tss) tuples sorted by date ascending
            target_date: The date to calculate CTL for
            initial_ctl: Starting CTL value (default 0)

        Returns:
            CTL value as a float
        """
        return self._calculate_ewma(
            tss_history=tss_history,
            target_date=target_date,
            time_constant=self.CTL_TIME_CONSTANT,
            initial_value=initial_ctl
        )

    def calculate_atl(
        self,
        tss_history: list[tuple[date, float]],
        target_date: date,
        initial_atl: float = 0.0
    ) -> float:
        """
        Calculate Acute Training Load (ATL) - "Fatigue".

        ATL is a 7-day exponentially weighted moving average of TSS.
        It represents short-term training load and fatigue.

        Formula: ATL_today = ATL_yesterday + (TSS_today - ATL_yesterday) / 7

        Args:
            tss_history: List of (date, tss) tuples sorted by date ascending
            target_date: The date to calculate ATL for
            initial_atl: Starting ATL value (default 0)

        Returns:
            ATL value as a float
        """
        return self._calculate_ewma(
            tss_history=tss_history,
            target_date=target_date,
            time_constant=self.ATL_TIME_CONSTANT,
            initial_value=initial_atl
        )

    def _calculate_ewma(
        self,
        tss_history: list[tuple[date, float]],
        target_date: date,
        time_constant: int,
        initial_value: float = 0.0
    ) -> float:
        """
        Calculate Exponentially Weighted Moving Average.

        Args:
            tss_history: List of (date, tss) tuples sorted by date ascending
            target_date: The date to calculate EWMA for
            time_constant: Number of days for the time constant (42 for CTL, 7 for ATL)
            initial_value: Starting value

        Returns:
            EWMA value as a float
        """
        if not tss_history:
            return initial_value

        # Convert to dict for faster lookup
        tss_by_date = {d: tss for d, tss in tss_history}

        # Find the earliest date we have data for
        earliest_date = min(tss_by_date.keys())

        # Start calculation from earliest date or 42 days before target
        start_date = max(
            earliest_date - timedelta(days=time_constant),
            earliest_date
        )

        ewma = initial_value
        current_date = start_date

        while current_date <= target_date:
            daily_tss = tss_by_date.get(current_date, 0.0)
            ewma = ewma + (daily_tss - ewma) / time_constant
            current_date += timedelta(days=1)

        return round(ewma, 1)

    def calculate_tsb(self, ctl: float, atl: float) -> float:
        """
        Calculate Training Stress Balance (TSB) - "Form".

        TSB = CTL - ATL

        Interpretation:
        - Positive TSB: Fresh/recovered state
        - Negative TSB: Fatigued state
        - Optimal race form: typically +15 to +25
        - Heavy training block: typically -10 to -30

        Args:
            ctl: Chronic Training Load
            atl: Acute Training Load

        Returns:
            TSB value as a float
        """
        return round(ctl - atl, 1)

    def estimate_tss_from_hr(
        self,
        duration_seconds: int,
        avg_hr: int,
        max_hr: int,
        lthr: int,
        rest_hr: int = 60
    ) -> float:
        """
        Estimate TSS from heart rate when power data is not available.

        Uses the heart rate based Training Stress Score (hrTSS) formula:
        hrTSS = (duration × hrIF × hrIF) / 3600 × 100
        where hrIF = (avg_hr - rest_hr) / (lthr - rest_hr)

        This is less accurate than power-based TSS but useful for non-power activities.

        Args:
            duration_seconds: Total duration of the workout in seconds
            avg_hr: Average heart rate during the workout
            max_hr: Maximum heart rate (used for validation)
            lthr: Lactate Threshold Heart Rate
            rest_hr: Resting heart rate (default 60)

        Returns:
            Estimated TSS as a float
        """
        if duration_seconds <= 0:
            return 0.0

        # Validate heart rate values
        if lthr <= rest_hr:
            raise ValueError("LTHR must be greater than resting heart rate")

        if avg_hr < rest_hr:
            return 0.0  # Invalid HR data

        # Calculate heart rate intensity factor
        hr_reserve = lthr - rest_hr
        if hr_reserve <= 0:
            return 0.0

        hr_intensity_factor = (avg_hr - rest_hr) / hr_reserve

        # Cap IF at reasonable values (max ~1.2 for very hard efforts)
        hr_intensity_factor = min(hr_intensity_factor, 1.2)
        hr_intensity_factor = max(hr_intensity_factor, 0.0)

        # Calculate hrTSS
        hr_tss = (duration_seconds * hr_intensity_factor * hr_intensity_factor) / 3600 * 100

        return round(hr_tss, 1)

    def calculate_fitness_history(
        self,
        db: Session,
        user_id: int,
        days: int = 90,
        recalculate: bool = False
    ) -> list[FitnessMetric]:
        """
        Calculate CTL/ATL/TSB for each day in the specified range.

        This method retrieves activity data, calculates daily TSS totals,
        and computes the fitness metrics for each day.

        Args:
            db: Database session
            user_id: User ID to calculate metrics for
            days: Number of days to calculate (default 90)
            recalculate: If True, recalculate all metrics. If False, only calculate missing days.

        Returns:
            List of FitnessMetric objects
        """
        end_date = date.today()
        # We need extra history for EWMA calculation
        start_date = end_date - timedelta(days=days + self.CTL_TIME_CONSTANT)

        # Get all activities with TSS in the date range
        activities = (
            db.query(Activity)
            .filter(
                and_(
                    Activity.user_id == user_id,
                    Activity.date >= start_date,
                    Activity.date <= end_date
                )
            )
            .all()
        )

        # Build TSS history (date -> total TSS for that day)
        daily_tss: dict[date, float] = {}
        for activity in activities:
            activity_date = activity.date.date() if hasattr(activity.date, 'date') else activity.date
            if activity.tss is not None:
                daily_tss[activity_date] = daily_tss.get(activity_date, 0.0) + activity.tss

        # Convert to sorted list of tuples
        tss_history = sorted(daily_tss.items(), key=lambda x: x[0])

        # Get or create fitness metrics for each day in the target range
        result_start_date = end_date - timedelta(days=days)
        metrics_list: list[FitnessMetric] = []

        # Get existing metrics if not recalculating
        existing_metrics: dict[date, FitnessMetric] = {}
        if not recalculate:
            existing = (
                db.query(FitnessMetric)
                .filter(
                    and_(
                        FitnessMetric.user_id == user_id,
                        FitnessMetric.date >= result_start_date,
                        FitnessMetric.date <= end_date
                    )
                )
                .all()
            )
            existing_metrics = {m.date: m for m in existing}

        # Calculate metrics for each day
        current_date = result_start_date
        while current_date <= end_date:
            # Skip if we already have this metric and not recalculating
            if not recalculate and current_date in existing_metrics:
                metrics_list.append(existing_metrics[current_date])
                current_date += timedelta(days=1)
                continue

            # Calculate CTL and ATL
            ctl = self.calculate_ctl(tss_history, current_date)
            atl = self.calculate_atl(tss_history, current_date)
            tsb = self.calculate_tsb(ctl, atl)
            daily_tss_value = daily_tss.get(current_date, 0.0)

            # Create or update metric
            if current_date in existing_metrics:
                metric = existing_metrics[current_date]
                metric.daily_tss = daily_tss_value
                metric.ctl = ctl
                metric.atl = atl
                metric.tsb = tsb
            else:
                metric = FitnessMetric(
                    user_id=user_id,
                    date=current_date,
                    daily_tss=daily_tss_value,
                    ctl=ctl,
                    atl=atl,
                    tsb=tsb
                )
                db.add(metric)

            metrics_list.append(metric)
            current_date += timedelta(days=1)

        db.commit()

        # Return only the requested range
        return [m for m in metrics_list if m.date >= result_start_date]

    def get_power_zones(self, ftp: int) -> dict[str, tuple[int, int]]:
        """
        Calculate power zones based on FTP.

        Standard 6-zone power model:
        - Zone 1 (Recovery): < 55% FTP
        - Zone 2 (Endurance): 55-75% FTP
        - Zone 3 (Tempo): 76-90% FTP
        - Zone 4 (Threshold): 91-105% FTP
        - Zone 5 (VO2max): 106-120% FTP
        - Zone 6 (Anaerobic): > 120% FTP

        Args:
            ftp: Functional Threshold Power in watts

        Returns:
            Dictionary mapping zone name to (min_watts, max_watts) tuple
        """
        if ftp <= 0:
            raise ValueError("FTP must be greater than zero")

        zones = {}
        for zone_key, zone_info in self.POWER_ZONES.items():
            min_watts = int(ftp * zone_info["min"] / 100)
            if zone_info["max"] == float("inf"):
                max_watts = None  # No upper limit for zone 6
            else:
                max_watts = int(ftp * zone_info["max"] / 100)

            zones[zone_key] = {
                "name": zone_info["name"],
                "min_watts": min_watts,
                "max_watts": max_watts,
                "min_percent": zone_info["min"],
                "max_percent": zone_info["max"] if zone_info["max"] != float("inf") else None
            }

        return zones

    def get_zone_for_power(self, power: int, ftp: int) -> str:
        """
        Determine which power zone a given power value falls into.

        Args:
            power: Power value in watts
            ftp: Functional Threshold Power in watts

        Returns:
            Zone key (e.g., "zone_1", "zone_4")
        """
        if ftp <= 0:
            raise ValueError("FTP must be greater than zero")

        percent_ftp = (power / ftp) * 100

        for zone_key, zone_info in self.POWER_ZONES.items():
            if zone_info["min"] <= percent_ftp <= zone_info["max"]:
                return zone_key

        # Should not reach here, but default to zone 6 for very high power
        return "zone_6"

    def analyze_power_distribution(
        self,
        power_data: list[int],
        ftp: int
    ) -> dict[str, float]:
        """
        Analyze time spent in each power zone.

        Args:
            power_data: List of power values in watts (1Hz sampling rate)
            ftp: Functional Threshold Power in watts

        Returns:
            Dictionary mapping zone names to percentage of time spent
        """
        if not power_data or ftp <= 0:
            return {zone: 0.0 for zone in self.POWER_ZONES}

        # Count seconds in each zone
        zone_counts = {zone: 0 for zone in self.POWER_ZONES}
        total_valid = 0

        for power in power_data:
            if power is not None and power >= 0:
                zone = self.get_zone_for_power(power, ftp)
                zone_counts[zone] += 1
                total_valid += 1

        if total_valid == 0:
            return {zone: 0.0 for zone in self.POWER_ZONES}

        # Convert to percentages
        return {
            zone: round((count / total_valid) * 100, 1)
            for zone, count in zone_counts.items()
        }

    def get_latest_metrics(
        self,
        db: Session,
        user_id: int
    ) -> Optional[FitnessMetric]:
        """
        Get the most recent fitness metrics for a user.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            Latest FitnessMetric or None if no metrics exist
        """
        return (
            db.query(FitnessMetric)
            .filter(FitnessMetric.user_id == user_id)
            .order_by(FitnessMetric.date.desc())
            .first()
        )


# Create a singleton instance for convenience
metrics_service = MetricsService()
