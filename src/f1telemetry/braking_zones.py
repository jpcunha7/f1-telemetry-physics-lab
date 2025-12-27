"""
Braking zone detection and analysis module.

Detects and analyzes braking zones from telemetry data.

Author: João Pedro Cunha
"""

import logging
from typing import List, Dict, Any, Tuple
import numpy as np
import pandas as pd
from f1telemetry.config import Config, DEFAULT_CONFIG

logger = logging.getLogger(__name__)


class BrakingZone:
    """Represents a single braking zone."""

    def __init__(
        self,
        zone_id: int,
        start_distance: float,
        end_distance: float,
        entry_speed: float,
        min_speed: float,
        exit_speed: float,
        max_decel: float,
        duration: float,
    ):
        self.zone_id = zone_id
        self.start_distance = start_distance
        self.end_distance = end_distance
        self.entry_speed = entry_speed
        self.min_speed = min_speed
        self.exit_speed = exit_speed
        self.max_decel = max_decel
        self.duration = duration

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "zone_id": self.zone_id,
            "start_distance": self.start_distance,
            "end_distance": self.end_distance,
            "entry_speed": self.entry_speed,
            "min_speed": self.min_speed,
            "exit_speed": self.exit_speed,
            "max_decel": self.max_decel,
            "duration": self.duration,
        }


def detect_braking_zones(
    telemetry: pd.DataFrame,
    config: Config = DEFAULT_CONFIG,
    brake_threshold: float = 10.0,
    min_zone_length: float = 20.0,
    min_speed_drop: float = 20.0,
) -> List[BrakingZone]:
    """
    Detect braking zones from telemetry data.

    A braking zone is defined as a continuous region where:
    1. Brake pressure exceeds threshold
    2. Speed decreases significantly
    3. Zone length exceeds minimum

    Args:
        telemetry: Telemetry dataframe with Distance, Speed, Brake channels
        config: Configuration instance
        brake_threshold: Minimum brake pressure to consider (0-100)
        min_zone_length: Minimum zone length in meters
        min_speed_drop: Minimum speed reduction to qualify as braking zone

    Returns:
        List of BrakingZone objects
    """
    if "Brake" not in telemetry.columns:
        logger.warning("Brake channel not available, cannot detect braking zones")
        return []

    zones = []
    in_zone = False
    zone_start_idx = 0
    zone_id = 1

    distance = telemetry["Distance"].values
    speed = telemetry["Speed"].values
    brake = telemetry["Brake"].values

    for i in range(1, len(telemetry)):
        braking = brake[i] > brake_threshold

        if braking and not in_zone:
            # Start of new braking zone
            in_zone = True
            zone_start_idx = i

        elif not braking and in_zone:
            # End of braking zone
            zone_end_idx = i - 1

            # Validate zone
            zone_length = distance[zone_end_idx] - distance[zone_start_idx]
            speed_drop = speed[zone_start_idx] - min(speed[zone_start_idx : zone_end_idx + 1])

            if zone_length >= min_zone_length and speed_drop >= min_speed_drop:
                # Extract zone metrics
                zone_distances = distance[zone_start_idx : zone_end_idx + 1]
                zone_speeds = speed[zone_start_idx : zone_end_idx + 1]

                # Compute deceleration if available
                if "LongAccel" in telemetry.columns:
                    max_decel = abs(
                        telemetry["LongAccel"].iloc[zone_start_idx : zone_end_idx + 1].min()
                    )
                else:
                    max_decel = 0.0

                # Estimate duration (approximate from distance and speed)
                avg_speed = np.mean(zone_speeds)
                duration = zone_length / (avg_speed / 3.6) if avg_speed > 0 else 0.0

                zone = BrakingZone(
                    zone_id=zone_id,
                    start_distance=zone_distances[0],
                    end_distance=zone_distances[-1],
                    entry_speed=zone_speeds[0],
                    min_speed=zone_speeds.min(),
                    exit_speed=zone_speeds[-1],
                    max_decel=max_decel,
                    duration=duration,
                )
                zones.append(zone)
                zone_id += 1

            in_zone = False

    logger.info(f"Detected {len(zones)} braking zones")
    return zones


def compare_braking_zones(
    zones1: List[BrakingZone],
    zones2: List[BrakingZone],
    distance_tolerance: float = 50.0,
) -> pd.DataFrame:
    """
    Compare braking zones between two drivers.

    Matches zones based on proximity of start distance.

    Args:
        zones1: Braking zones for driver 1
        zones2: Braking zones for driver 2
        distance_tolerance: Maximum distance difference to match zones (meters)

    Returns:
        DataFrame with zone comparisons
    """
    comparisons = []

    for z1 in zones1:
        # Find closest matching zone in zones2
        best_match = None
        min_diff = float("inf")

        for z2 in zones2:
            diff = abs(z1.start_distance - z2.start_distance)
            if diff < min_diff and diff < distance_tolerance:
                min_diff = diff
                best_match = z2

        if best_match:
            comp = {
                "Zone_ID": z1.zone_id,
                "Start_Dist_Driver1": z1.start_distance,
                "Start_Dist_Driver2": best_match.start_distance,
                "Brake_Start_Delta_m": z1.start_distance - best_match.start_distance,
                "Entry_Speed_Driver1": z1.entry_speed,
                "Entry_Speed_Driver2": best_match.entry_speed,
                "Entry_Speed_Delta": z1.entry_speed - best_match.entry_speed,
                "Min_Speed_Driver1": z1.min_speed,
                "Min_Speed_Driver2": best_match.min_speed,
                "Min_Speed_Delta": z1.min_speed - best_match.min_speed,
                "Exit_Speed_Driver1": z1.exit_speed,
                "Exit_Speed_Driver2": best_match.exit_speed,
                "Exit_Speed_Delta": z1.exit_speed - best_match.exit_speed,
                "Max_Decel_Driver1": z1.max_decel,
                "Max_Decel_Driver2": best_match.max_decel,
                "Max_Decel_Delta": z1.max_decel - best_match.max_decel,
                "Duration_Driver1": z1.duration,
                "Duration_Driver2": best_match.duration,
                "Duration_Delta": z1.duration - best_match.duration,
            }
            comparisons.append(comp)

    df = pd.DataFrame(comparisons)

    # Estimate delta contribution (approximate)
    if not df.empty:
        # Simple approximation: time delta ~ distance_delta / avg_speed
        df["Approx_Time_Delta_s"] = df.apply(
            lambda row: (
                (row["Start_Dist_Driver1"] - row["Start_Dist_Driver2"])
                / ((row["Entry_Speed_Driver1"] + row["Entry_Speed_Driver2"]) / 2 / 3.6)
                if (row["Entry_Speed_Driver1"] + row["Entry_Speed_Driver2"]) > 0
                else 0
            ),
            axis=1,
        )

    return df


def get_top_braking_differences(
    comparison_df: pd.DataFrame, n: int = 3, sort_by: str = "Brake_Start_Delta_m"
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Get top N zones with largest differences.

    Args:
        comparison_df: DataFrame from compare_braking_zones
        n: Number of top zones to return
        sort_by: Column to sort by

    Returns:
        Tuple of (top gains, top losses) DataFrames
    """
    if comparison_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    sorted_df = comparison_df.sort_values(by=sort_by, ascending=False)

    # Top gains (driver 1 brakes later = positive delta)
    top_gains = sorted_df.head(n)

    # Top losses (driver 1 brakes earlier = negative delta)
    top_losses = sorted_df.tail(n).sort_values(by=sort_by)

    return top_gains, top_losses


def create_braking_zones_summary(
    zones1: List[BrakingZone],
    zones2: List[BrakingZone],
    driver1_name: str,
    driver2_name: str,
) -> Dict[str, Any]:
    """
    Create summary statistics for braking zones.

    Args:
        zones1: Braking zones for driver 1
        zones2: Braking zones for driver 2
        driver1_name: Name of driver 1
        driver2_name: Name of driver 2

    Returns:
        Dictionary with summary statistics
    """
    summary = {
        "num_zones_driver1": len(zones1),
        "num_zones_driver2": len(zones2),
        "driver1_name": driver1_name,
        "driver2_name": driver2_name,
    }

    if zones1:
        summary["avg_max_decel_driver1"] = np.mean([z.max_decel for z in zones1])
        summary["total_braking_distance_driver1"] = sum(
            [z.end_distance - z.start_distance for z in zones1]
        )

    if zones2:
        summary["avg_max_decel_driver2"] = np.mean([z.max_decel for z in zones2])
        summary["total_braking_distance_driver2"] = sum(
            [z.end_distance - z.start_distance for z in zones2]
        )

    return summary
