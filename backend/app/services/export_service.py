"""Export service for generating workout files in various cycling platform formats."""

import re
import xml.etree.ElementTree as ET
from datetime import date, datetime
from typing import Any, Optional
from xml.dom import minidom

from app.models.planned_workout import PlannedWorkout
from app.schemas.workout import IntervalType, WorkoutIntervalSchema


class ExportService:
    """Export workouts to various cycling platform formats."""

    AUTHOR = "Cycling Trainer"
    SPORT_TYPE = "bike"

    def export_to_zwo(self, workout: PlannedWorkout, ftp: int) -> str:
        """
        Generate Zwift Workout file (.zwo).

        Zwift uses XML format with power values as decimals of FTP.
        Zwift applies the user's FTP automatically when loading the workout.

        Args:
            workout: The planned workout to export
            ftp: Athlete's FTP (used for reference, not embedded in file)

        Returns:
            XML string representing the ZWO file

        Example output:
            <?xml version="1.0" encoding="UTF-8"?>
            <workout_file>
                <author>Cycling Trainer</author>
                <name>Sweet Spot 3x10</name>
                <description>3x10 minute sweet spot intervals</description>
                <sportType>bike</sportType>
                <workout>
                    <Warmup Duration="600" PowerLow="0.50" PowerHigh="0.70"/>
                    <IntervalsT Repeat="3" OnDuration="600" OnPower="0.90"
                               OffDuration="300" OffPower="0.50"/>
                    <Cooldown Duration="300" PowerLow="0.60" PowerHigh="0.40"/>
                </workout>
            </workout_file>
        """
        # Create root element
        root = ET.Element("workout_file")

        # Add metadata
        ET.SubElement(root, "author").text = self.AUTHOR
        ET.SubElement(root, "name").text = workout.name
        ET.SubElement(root, "description").text = workout.description or ""
        ET.SubElement(root, "sportType").text = self.SPORT_TYPE

        # Create workout element
        workout_elem = ET.SubElement(root, "workout")

        # Parse and add intervals
        segments = self._parse_intervals_json(workout.intervals_json)

        for segment in segments:
            self._add_zwo_segment(workout_elem, segment)

        # Convert to pretty-printed XML string
        xml_str = ET.tostring(root, encoding="unicode")
        dom = minidom.parseString(xml_str)
        pretty_xml = dom.toprettyxml(indent="    ", encoding="UTF-8")

        # Remove extra blank lines and return
        return pretty_xml.decode("utf-8")

    def _add_zwo_segment(self, parent: ET.Element, segment: dict[str, Any]) -> None:
        """Add a single segment to the ZWO workout element."""
        interval_type = segment["type"]
        duration = segment["duration"]
        power_low = segment["power_low"]
        power_high = segment["power_high"]
        repeat = segment.get("repeat", 1)
        cadence = segment.get("cadence")

        if interval_type == IntervalType.WARMUP:
            elem = ET.SubElement(parent, "Warmup")
            elem.set("Duration", str(duration))
            elem.set("PowerLow", f"{power_low:.2f}")
            elem.set("PowerHigh", f"{power_high:.2f}")

        elif interval_type == IntervalType.COOLDOWN:
            elem = ET.SubElement(parent, "Cooldown")
            elem.set("Duration", str(duration))
            elem.set("PowerLow", f"{power_low:.2f}")
            elem.set("PowerHigh", f"{power_high:.2f}")

        elif interval_type == IntervalType.RAMP:
            elem = ET.SubElement(parent, "Ramp")
            elem.set("Duration", str(duration))
            elem.set("PowerLow", f"{power_low:.2f}")
            elem.set("PowerHigh", f"{power_high:.2f}")

        elif interval_type in (IntervalType.WORK, IntervalType.REST):
            # For work/rest, if there's a repeat > 1 and we have paired intervals,
            # use IntervalsT format
            if repeat > 1 and "off_duration" in segment:
                elem = ET.SubElement(parent, "IntervalsT")
                elem.set("Repeat", str(repeat))
                elem.set("OnDuration", str(duration))
                elem.set("OnPower", f"{power_high:.2f}")
                elem.set("OffDuration", str(segment["off_duration"]))
                elem.set("OffPower", f"{segment.get('off_power', 0.50):.2f}")
            else:
                # Single steady state interval
                elem = ET.SubElement(parent, "SteadyState")
                elem.set("Duration", str(duration))
                elem.set("Power", f"{power_high:.2f}")
                if repeat > 1:
                    # Repeat by adding multiple elements
                    for _ in range(repeat - 1):
                        repeat_elem = ET.SubElement(parent, "SteadyState")
                        repeat_elem.set("Duration", str(duration))
                        repeat_elem.set("Power", f"{power_high:.2f}")

        else:  # STEADY or default
            elem = ET.SubElement(parent, "SteadyState")
            elem.set("Duration", str(duration))
            elem.set("Power", f"{power_high:.2f}")

        # Add cadence if specified
        if cadence and "elem" in dir():
            elem.set("Cadence", str(cadence))

    def export_to_erg(self, workout: PlannedWorkout, ftp: int) -> str:
        """
        Generate ERG format file for Wahoo/Garmin (.erg).

        ERG uses absolute watts (not % of FTP) in a similar structure to MRC.
        This format is compatible with Wahoo SYSTM, Wahoo KICKR, and Garmin.

        Args:
            workout: The planned workout to export
            ftp: Athlete's FTP in watts (used to calculate absolute watts)

        Returns:
            String representing the ERG file

        Example output:
            [COURSE HEADER]
            DESCRIPTION = Sweet Spot Intervals
            FTP = 250
            MINUTES WATTS
            [END COURSE HEADER]
            [COURSE DATA]
            0.00	125
            10.00	175
            10.01	225
            20.00	225
            [END COURSE DATA]

        First column: minutes from start
        Second column: absolute watts
        """
        lines = []

        # Header section
        lines.append("[COURSE HEADER]")
        lines.append(f"DESCRIPTION = {workout.description or workout.name}")
        lines.append(f"FTP = {ftp}")
        lines.append("MINUTES WATTS")
        lines.append("[END COURSE HEADER]")

        # Course data section
        lines.append("[COURSE DATA]")

        # Parse intervals and generate time/power pairs in absolute watts
        segments = self._parse_intervals_json(workout.intervals_json)
        data_points = self._generate_erg_data_points(segments, ftp)

        for time_minutes, watts in data_points:
            lines.append(f"{time_minutes:.2f}\t{watts}")

        lines.append("[END COURSE DATA]")

        return "\n".join(lines)

    def _generate_erg_data_points(
        self, segments: list[dict[str, Any]], ftp: int
    ) -> list[tuple[float, int]]:
        """
        Generate time/power data points for ERG format in absolute watts.

        Returns list of (time_in_minutes, watts) tuples.
        """
        data_points = []
        current_time = 0.0

        for segment in segments:
            duration_seconds = segment["duration"]
            duration_minutes = duration_seconds / 60.0
            # Convert decimal FTP values to absolute watts
            watts_low = int(segment["power_low"] * ftp)
            watts_high = int(segment["power_high"] * ftp)
            repeat = segment.get("repeat", 1)
            interval_type = segment["type"]

            for _ in range(repeat):
                if interval_type in (IntervalType.WARMUP, IntervalType.RAMP):
                    # Ramp from low to high
                    data_points.append((current_time, watts_low))
                    current_time += duration_minutes
                    data_points.append((current_time, watts_high))

                elif interval_type == IntervalType.COOLDOWN:
                    # Ramp from high to low (reverse)
                    data_points.append((current_time, watts_low))
                    current_time += duration_minutes
                    data_points.append((current_time, watts_high))

                else:
                    # Steady state - use the high power value
                    # Add start point
                    if not data_points or abs(data_points[-1][1] - watts_high) > 1:
                        # Small offset to create step change
                        if data_points:
                            data_points.append((current_time + 0.01, watts_high))
                        else:
                            data_points.append((current_time, watts_high))
                    else:
                        data_points.append((current_time, watts_high))

                    # Add end point
                    current_time += duration_minutes
                    data_points.append((current_time, watts_high))

                # Handle rest intervals in work/rest pairs
                if "off_duration" in segment:
                    off_duration_minutes = segment["off_duration"] / 60.0
                    off_watts = int(segment.get("off_power", 0.50) * ftp)
                    data_points.append((current_time + 0.01, off_watts))
                    current_time += off_duration_minutes
                    data_points.append((current_time, off_watts))

        return data_points

    def export_to_mrc(self, workout: PlannedWorkout, ftp: int) -> str:
        """
        Generate Rouvy/ErgVideo format (.mrc).

        MRC uses tab-separated values with time in minutes and power as % of FTP.

        Args:
            workout: The planned workout to export
            ftp: Athlete's FTP (used for reference in comments)

        Returns:
            String representing the MRC file

        Example output:
            [COURSE HEADER]
            VERSION = 2
            UNITS = ENGLISH
            DESCRIPTION = Sweet Spot Intervals
            FILE NAME = sweet_spot.mrc
            FTP = 250
            [END COURSE HEADER]
            [COURSE DATA]
            0	50
            10	70
            10.01	90
            20	90
            20.01	50
            25	50
            [END COURSE DATA]

        First column: minutes from start
        Second column: % of FTP
        """
        lines = []

        # Header section
        lines.append("[COURSE HEADER]")
        lines.append("VERSION = 2")
        lines.append("UNITS = ENGLISH")
        lines.append(f"DESCRIPTION = {workout.description or workout.name}")
        lines.append(f"FILE NAME = {self.generate_filename(workout, 'mrc')}")
        lines.append(f"FTP = {ftp}")
        lines.append("[END COURSE HEADER]")

        # Course data section
        lines.append("[COURSE DATA]")

        # Parse intervals and generate time/power pairs
        segments = self._parse_intervals_json(workout.intervals_json)
        data_points = self._generate_mrc_data_points(segments)

        for time_minutes, power_percent in data_points:
            lines.append(f"{time_minutes:.2f}\t{power_percent:.0f}")

        lines.append("[END COURSE DATA]")

        return "\n".join(lines)

    def _generate_mrc_data_points(
        self, segments: list[dict[str, Any]]
    ) -> list[tuple[float, float]]:
        """
        Generate time/power data points for MRC format.

        Returns list of (time_in_minutes, power_percent) tuples.
        """
        data_points = []
        current_time = 0.0

        for segment in segments:
            duration_seconds = segment["duration"]
            duration_minutes = duration_seconds / 60.0
            power_low = segment["power_low"] * 100  # Convert to percentage
            power_high = segment["power_high"] * 100
            repeat = segment.get("repeat", 1)
            interval_type = segment["type"]

            for _ in range(repeat):
                if interval_type in (IntervalType.WARMUP, IntervalType.RAMP):
                    # Ramp from low to high
                    data_points.append((current_time, power_low))
                    current_time += duration_minutes
                    data_points.append((current_time, power_high))

                elif interval_type == IntervalType.COOLDOWN:
                    # Ramp from high to low (reverse)
                    data_points.append((current_time, power_low))
                    current_time += duration_minutes
                    data_points.append((current_time, power_high))

                else:
                    # Steady state - use the high power value
                    # Add start point
                    if not data_points or abs(data_points[-1][1] - power_high) > 0.1:
                        # Small offset to create step change
                        if data_points:
                            data_points.append((current_time + 0.01, power_high))
                        else:
                            data_points.append((current_time, power_high))
                    else:
                        data_points.append((current_time, power_high))

                    # Add end point
                    current_time += duration_minutes
                    data_points.append((current_time, power_high))

                # Handle rest intervals in work/rest pairs
                if "off_duration" in segment:
                    off_duration_minutes = segment["off_duration"] / 60.0
                    off_power = segment.get("off_power", 0.50) * 100
                    data_points.append((current_time + 0.01, off_power))
                    current_time += off_duration_minutes
                    data_points.append((current_time, off_power))

        return data_points

    def _parse_intervals_json(
        self, intervals_json: Optional[list[dict[str, Any]]]
    ) -> list[dict[str, Any]]:
        """
        Parse interval JSON structure into flat list of segments.

        Supports both formats:
        1. Existing model format: [{"name": "Warmup", "duration": 600, "power_target": 0.5}]
        2. Extended format: [{"type": "warmup", "duration": 600, "power_low": 0.5, "power_high": 0.7}]

        Each output segment contains:
            - type: IntervalType
            - start_time: int (seconds from workout start)
            - duration: int (seconds)
            - power_low: float (decimal of FTP)
            - power_high: float (decimal of FTP)
            - cadence: Optional[int]
            - repeat: int

        Args:
            intervals_json: The intervals JSON from the workout model (list of dicts)

        Returns:
            List of segment dictionaries
        """
        segments = []
        current_time = 0

        if intervals_json is None:
            return segments

        # Handle both formats: dict with "intervals" key or direct list
        if isinstance(intervals_json, dict):
            intervals = intervals_json.get("intervals", [])
        else:
            intervals = intervals_json if intervals_json else []

        for interval in intervals:
            # Parse interval data
            if isinstance(interval, dict):
                # Get duration
                duration = interval.get("duration", 0)

                # Get power values - support both power_target and power_low/power_high
                power_target = interval.get("power_target")
                if power_target is not None:
                    # Single power target - use for both low and high
                    power_low = power_target
                    power_high = power_target
                else:
                    power_low = interval.get("power_low", 0.5)
                    power_high = interval.get("power_high", power_low)

                # Get interval type - infer from name if type not provided
                interval_type = interval.get("type")
                if interval_type is None:
                    # Infer type from interval name
                    name = interval.get("name", "").lower()
                    interval_type = self._infer_interval_type(name, power_high)

                # Convert string type to enum if needed
                if isinstance(interval_type, str):
                    try:
                        interval_type = IntervalType(interval_type)
                    except ValueError:
                        interval_type = IntervalType.STEADY

                cadence = interval.get("cadence")
                # Support both "repeat" and "repeats" field names
                repeat = interval.get("repeats") or interval.get("repeat") or 1

                segment = {
                    "type": interval_type,
                    "start_time": current_time,
                    "duration": duration,
                    "power_low": power_low,
                    "power_high": power_high,
                    "repeat": repeat,
                }

                if cadence:
                    segment["cadence"] = cadence

                # Check for paired work/rest intervals
                off_duration = interval.get("off_duration")
                off_power = interval.get("off_power")
                if off_duration:
                    segment["off_duration"] = off_duration
                    segment["off_power"] = off_power if off_power else 0.50

                segments.append(segment)

                # Update current time
                total_duration = duration * repeat
                if off_duration:
                    total_duration += off_duration * repeat
                current_time += total_duration

            elif isinstance(interval, WorkoutIntervalSchema):
                # Get power values
                power_target = interval.power_target
                if power_target is not None:
                    power_low = power_target
                    power_high = power_target
                else:
                    power_low = interval.power_low or 0.5
                    power_high = interval.power_high or power_low

                segment = {
                    "type": interval.type or IntervalType.STEADY,
                    "start_time": current_time,
                    "duration": interval.duration,
                    "power_low": power_low,
                    "power_high": power_high,
                    "repeat": interval.repeats or 1,
                }
                if interval.cadence:
                    segment["cadence"] = interval.cadence

                segments.append(segment)
                current_time += interval.duration * (interval.repeats or 1)

        return segments

    def _infer_interval_type(self, name: str, power: float) -> IntervalType:
        """Infer interval type from name or power level."""
        name_lower = name.lower()

        if "warmup" in name_lower or "warm up" in name_lower or "warm-up" in name_lower:
            return IntervalType.WARMUP
        elif "cooldown" in name_lower or "cool down" in name_lower or "cool-down" in name_lower:
            return IntervalType.COOLDOWN
        elif "recovery" in name_lower or "rest" in name_lower:
            return IntervalType.REST
        elif "ramp" in name_lower:
            return IntervalType.RAMP
        elif power < 0.55:
            return IntervalType.REST
        elif power >= 0.75:
            return IntervalType.WORK
        else:
            return IntervalType.STEADY

    def generate_filename(self, workout: PlannedWorkout, format: str) -> str:
        """
        Generate a safe filename for the workout export.

        Args:
            workout: The workout to generate a filename for
            format: The export format extension (zwo, mrc)

        Returns:
            Safe filename string: workout_name_date.extension
        """
        # Sanitize workout name
        safe_name = re.sub(r"[^\w\s-]", "", workout.name)
        safe_name = re.sub(r"[-\s]+", "_", safe_name).strip("_")
        safe_name = safe_name.lower()[:50]  # Limit length

        # Get date string from workout.date (datetime field in the model)
        workout_date = workout.date
        if isinstance(workout_date, datetime):
            date_str = workout_date.strftime("%Y%m%d")
        elif isinstance(workout_date, date):
            date_str = workout_date.strftime("%Y%m%d")
        else:
            date_str = str(workout_date).replace("-", "")[:8]

        return f"{safe_name}_{date_str}.{format}"


# Singleton instance
export_service = ExportService()
