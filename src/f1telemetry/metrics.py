"""
Metrics computation module for F1 Telemetry Physics Lab.

Computes lap comparison metrics and segment analysis.

Author: João Pedro Cunha
"""

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

from f1telemetry.config import Config, DEFAULT_CONFIG
from f1telemetry.alignment import compute_delta_time
from f1telemetry.physics import detect_braking_zones, detect_corners

logger = logging.getLogger(__name__)


@dataclass
class SegmentComparison:
    """Comparison data for a segment of the lap."""

    segment_num: int
    start_distance: float
    end_distance: float
    driver1_time: float  # seconds
    driver2_time: float  # seconds
    time_delta: float  # seconds (positive = driver1 slower)
    winner: str  # "driver1", "driver2", or "tie"


def divide_lap_into_segments(
    distance_array: np.ndarray,
    num_segments: int,
) -> list[tuple[float, float]]:
    """
    Divide a lap into equal-distance segments.

    Args:
        distance_array: Array of distance values
        num_segments: Number of segments to create

    Returns:
        List of (start_distance, end_distance) tuples
    """
    min_dist = distance_array.min()
    max_dist = distance_array.max()
    segment_length = (max_dist - min_dist) / num_segments

    segments = []
    for i in range(num_segments):
        start = min_dist + i * segment_length
        end = min_dist + (i + 1) * segment_length
        segments.append((start, end))

    return segments


def compute_segment_times(
    telemetry: pd.DataFrame,
    segments: list[tuple[float, float]],
) -> list[float]:
    """
    Compute time taken for each segment.

    Args:
        telemetry: Telemetry DataFrame with Distance and Speed
        segments: List of (start_distance, end_distance) tuples

    Returns:
        List of segment times in seconds
    """
    distance = telemetry['Distance'].values
    speed_ms = telemetry['Speed'].values / 3.6  # Convert to m/s

    segment_times = []

    for start_dist, end_dist in segments:
        # Find indices within this segment
        mask = (distance >= start_dist) & (distance < end_dist)
        segment_distances = distance[mask]
        segment_speeds = speed_ms[mask]

        if len(segment_distances) < 2:
            segment_times.append(0.0)
            continue

        # Compute time: sum of dt = dx / v
        distance_deltas = np.diff(segment_distances, prepend=segment_distances[0])
        epsilon = 0.1 / 3.6
        time_deltas = distance_deltas / (segment_speeds + epsilon)
        total_time = np.sum(time_deltas)

        segment_times.append(float(total_time))

    return segment_times


def compare_segments(
    telemetry1: pd.DataFrame,
    telemetry2: pd.DataFrame,
    config: Config = DEFAULT_CONFIG,
) -> list[SegmentComparison]:
    """
    Compare lap performance segment by segment.

    Args:
        telemetry1: Aligned telemetry for driver 1
        telemetry2: Aligned telemetry for driver 2
        config: Configuration with num_segments

    Returns:
        List of SegmentComparison objects
    """
    # Create segments
    distance_array = telemetry1['Distance'].values
    segments = divide_lap_into_segments(distance_array, config.num_segments)

    # Compute times for each driver
    times1 = compute_segment_times(telemetry1, segments)
    times2 = compute_segment_times(telemetry2, segments)

    # Create comparisons
    comparisons = []
    for i, ((start, end), t1, t2) in enumerate(zip(segments, times1, times2)):
        delta = t1 - t2

        # Determine winner
        if abs(delta) < 0.01:  # Less than 10ms difference
            winner = "tie"
        elif delta < 0:
            winner = "driver1"
        else:
            winner = "driver2"

        comparison = SegmentComparison(
            segment_num=i + 1,
            start_distance=start,
            end_distance=end,
            driver1_time=t1,
            driver2_time=t2,
            time_delta=delta,
            winner=winner,
        )
        comparisons.append(comparison)

    return comparisons


def generate_insights(
    telemetry1: pd.DataFrame,
    telemetry2: pd.DataFrame,
    driver1_name: str,
    driver2_name: str,
    delta_time: np.ndarray,
    segment_comparisons: list[SegmentComparison],
) -> list[str]:
    """
    Generate text insights from lap comparison.

    Args:
        telemetry1: Aligned telemetry for driver 1
        telemetry2: Aligned telemetry for driver 2
        driver1_name: Name/code for driver 1
        driver2_name: Name/code for driver 2
        delta_time: Delta time array
        segment_comparisons: Segment comparison results

    Returns:
        List of insight strings
    """
    insights = []

    # Overall delta
    final_delta = delta_time[-1]
    if abs(final_delta) < 0.01:
        insights.append(f"⏱️ The laps are virtually identical (Δt = {final_delta:.3f}s)")
    elif final_delta < 0:
        insights.append(
            f"⏱️ {driver1_name} is {abs(final_delta):.3f}s faster than {driver2_name}"
        )
    else:
        insights.append(
            f"⏱️ {driver2_name} is {abs(final_delta):.3f}s faster than {driver1_name}"
        )

    # Maximum delta
    max_delta_idx = np.argmax(np.abs(delta_time))
    max_delta = delta_time[max_delta_idx]
    max_delta_dist = telemetry1['Distance'].values[max_delta_idx]

    if abs(max_delta) > 0.05:
        leader = driver2_name if max_delta > 0 else driver1_name
        insights.append(
            f"📍 Maximum gap of {abs(max_delta):.3f}s occurs at {max_delta_dist:.0f}m "
            f"(favoring {leader})"
        )

    # Segment winners
    driver1_wins = sum(1 for s in segment_comparisons if s.winner == "driver1")
    driver2_wins = sum(1 for s in segment_comparisons if s.winner == "driver2")

    insights.append(
        f"📊 Segment wins: {driver1_name} ({driver1_wins}), "
        f"{driver2_name} ({driver2_wins})"
    )

    # Biggest segment gain
    biggest_gain = max(segment_comparisons, key=lambda s: abs(s.time_delta))
    if abs(biggest_gain.time_delta) > 0.05:
        leader = driver1_name if biggest_gain.time_delta < 0 else driver2_name
        insights.append(
            f"🏁 Biggest segment gain: {leader} in segment {biggest_gain.segment_num} "
            f"({abs(biggest_gain.time_delta):.3f}s)"
        )

    # Speed comparison
    avg_speed1 = telemetry1['Speed'].mean()
    avg_speed2 = telemetry2['Speed'].mean()
    max_speed1 = telemetry1['Speed'].max()
    max_speed2 = telemetry2['Speed'].max()

    insights.append(
        f"🏎️ Average speed: {driver1_name} {avg_speed1:.1f} km/h, "
        f"{driver2_name} {avg_speed2:.1f} km/h"
    )
    insights.append(
        f"⚡ Top speed: {driver1_name} {max_speed1:.1f} km/h, "
        f"{driver2_name} {max_speed2:.1f} km/h"
    )

    return insights


def create_comparison_summary(
    lap1: object,
    lap2: object,
    telemetry1: pd.DataFrame,
    telemetry2: pd.DataFrame,
    driver1_name: str,
    driver2_name: str,
    config: Config = DEFAULT_CONFIG,
) -> dict:
    """
    Create a comprehensive comparison summary.

    Args:
        lap1: FastF1 Lap object for driver 1
        lap2: FastF1 Lap object for driver 2
        telemetry1: Aligned telemetry for driver 1
        telemetry2: Aligned telemetry for driver 2
        driver1_name: Name/code for driver 1
        driver2_name: Name/code for driver 2
        config: Configuration

    Returns:
        Dictionary with comparison summary
    """
    # Compute delta time
    delta_time = compute_delta_time(telemetry1, telemetry2)

    # Segment comparison
    segment_comparisons = compare_segments(telemetry1, telemetry2, config)

    # Generate insights
    insights = generate_insights(
        telemetry1,
        telemetry2,
        driver1_name,
        driver2_name,
        delta_time,
        segment_comparisons,
    )

    # Detect features
    braking_zones1 = detect_braking_zones(telemetry1, config=config)
    braking_zones2 = detect_braking_zones(telemetry2, config=config)
    corners1 = detect_corners(telemetry1, config=config)
    corners2 = detect_corners(telemetry2, config=config)

    return {
        "driver1_name": driver1_name,
        "driver2_name": driver2_name,
        "lap1_time": getattr(lap1, 'LapTime', None),
        "lap2_time": getattr(lap2, 'LapTime', None),
        "delta_time": delta_time,
        "final_delta": float(delta_time[-1]),
        "segment_comparisons": segment_comparisons,
        "insights": insights,
        "braking_zones1": braking_zones1,
        "braking_zones2": braking_zones2,
        "corners1": corners1,
        "corners2": corners2,
    }
