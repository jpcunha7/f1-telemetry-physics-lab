"""
Lap alignment module for F1 Telemetry Physics Lab.

Handles distance-based alignment, interpolation, and resampling of telemetry data.

Author: João Pedro Cunha
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd
from scipy.interpolate import interp1d

from f1telemetry.config import Config, DEFAULT_CONFIG

logger = logging.getLogger(__name__)


def validate_telemetry(telemetry: pd.DataFrame, name: str = "telemetry") -> None:
    """
    Validate telemetry DataFrame has required columns and valid data.

    Args:
        telemetry: Telemetry DataFrame to validate
        name: Name for logging purposes

    Raises:
        ValueError: If telemetry is invalid
    """
    if telemetry.empty:
        raise ValueError(f"{name} is empty")

    required_columns = ['Distance', 'Speed']
    missing = [col for col in required_columns if col not in telemetry.columns]
    if missing:
        raise ValueError(f"{name} missing required columns: {missing}")

    if telemetry['Distance'].isna().any():
        raise ValueError(f"{name} has NaN values in Distance column")

    if not telemetry['Distance'].is_monotonic_increasing:
        logger.warning(f"{name} Distance is not monotonic increasing, sorting...")


def create_distance_array(
    min_distance: float,
    max_distance: float,
    resolution: float,
) -> np.ndarray:
    """
    Create uniform distance array for alignment.

    Args:
        min_distance: Start distance in meters
        max_distance: End distance in meters
        resolution: Distance step in meters

    Returns:
        Array of distances with uniform spacing
    """
    return np.arange(min_distance, max_distance, resolution)


def interpolate_telemetry(
    telemetry: pd.DataFrame,
    distance_array: np.ndarray,
    columns_to_interpolate: Optional[list[str]] = None,
) -> pd.DataFrame:
    """
    Interpolate telemetry data to uniform distance grid.

    Args:
        telemetry: Original telemetry DataFrame
        distance_array: Target distance array for interpolation
        columns_to_interpolate: List of columns to interpolate (default: common telemetry channels)

    Returns:
        Interpolated telemetry DataFrame

    Raises:
        ValueError: If interpolation fails
    """
    if columns_to_interpolate is None:
        # Default columns to interpolate
        available_columns = telemetry.columns.tolist()
        columns_to_interpolate = [
            col for col in ['Speed', 'Throttle', 'Brake', 'nGear', 'RPM', 'DRS', 'X', 'Y']
            if col in available_columns
        ]

    # Ensure Distance is available and clean
    distances = telemetry['Distance'].values

    # Remove duplicates and sort by distance
    df_clean = telemetry[['Distance'] + columns_to_interpolate].copy()
    df_clean = df_clean.drop_duplicates(subset=['Distance'])
    df_clean = df_clean.sort_values('Distance')

    distances = df_clean['Distance'].values

    # Create interpolated data dictionary
    interpolated_data = {'Distance': distance_array}

    for col in columns_to_interpolate:
        try:
            values = df_clean[col].values

            # Handle NaN values by forward/backward fill before interpolation
            if pd.isna(values).any():
                values = pd.Series(values).fillna(method='ffill').fillna(method='bfill').values

            # Create interpolation function (linear)
            interp_func = interp1d(
                distances,
                values,
                kind='linear',
                bounds_error=False,
                fill_value=(values[0], values[-1]),
            )

            interpolated_data[col] = interp_func(distance_array)

        except Exception as e:
            logger.warning(f"Could not interpolate column {col}: {e}")

    return pd.DataFrame(interpolated_data)


def align_laps(
    telemetry1: pd.DataFrame,
    telemetry2: pd.DataFrame,
    config: Config = DEFAULT_CONFIG,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Align two laps by distance with uniform resampling.

    Args:
        telemetry1: First lap telemetry
        telemetry2: Second lap telemetry
        config: Configuration with distance_resolution

    Returns:
        Tuple of (aligned_telemetry1, aligned_telemetry2) with same distance grid

    Raises:
        ValueError: If alignment fails
    """
    # Validate input telemetry
    validate_telemetry(telemetry1, "telemetry1")
    validate_telemetry(telemetry2, "telemetry2")

    # Determine common distance range
    min_dist1 = telemetry1['Distance'].min()
    max_dist1 = telemetry1['Distance'].max()
    min_dist2 = telemetry2['Distance'].min()
    max_dist2 = telemetry2['Distance'].max()

    # Use overlapping distance range
    min_distance = max(min_dist1, min_dist2)
    max_distance = min(max_dist1, max_dist2)

    if min_distance >= max_distance:
        raise ValueError(
            f"No overlapping distance range found. "
            f"Lap 1: [{min_dist1:.0f}, {max_dist1:.0f}], "
            f"Lap 2: [{min_dist2:.0f}, {max_dist2:.0f}]"
        )

    logger.info(
        f"Aligning laps over distance range: [{min_distance:.0f}, {max_distance:.0f}] m "
        f"with resolution {config.distance_resolution} m"
    )

    # Create uniform distance array
    distance_array = create_distance_array(
        min_distance,
        max_distance,
        config.distance_resolution,
    )

    # Interpolate both telemetries
    aligned1 = interpolate_telemetry(telemetry1, distance_array)
    aligned2 = interpolate_telemetry(telemetry2, distance_array)

    logger.info(f"Aligned telemetry has {len(aligned1)} samples")

    return aligned1, aligned2


def compute_delta_time(
    telemetry1: pd.DataFrame,
    telemetry2: pd.DataFrame,
) -> np.ndarray:
    """
    Compute cumulative delta time between two aligned laps.

    Delta time shows how much time driver 1 is ahead/behind driver 2
    at each distance point. Positive means driver 1 is slower (behind).

    Args:
        telemetry1: Aligned telemetry for driver 1
        telemetry2: Aligned telemetry for driver 2

    Returns:
        Array of cumulative delta time in seconds

    Raises:
        ValueError: If telemetries are not aligned
    """
    if len(telemetry1) != len(telemetry2):
        raise ValueError(
            f"Telemetries must be aligned (same length). "
            f"Got {len(telemetry1)} vs {len(telemetry2)}"
        )

    # Get speeds in km/h
    speed1 = telemetry1['Speed'].values
    speed2 = telemetry2['Speed'].values

    # Get distance deltas
    distances = telemetry1['Distance'].values
    distance_deltas = np.diff(distances, prepend=distances[0])

    # Compute time deltas: dt = dx / v (convert speed to m/s)
    # Handle zero speed by using small epsilon
    epsilon = 0.1  # km/h
    speed1_ms = (speed1 + epsilon) / 3.6  # km/h to m/s
    speed2_ms = (speed2 + epsilon) / 3.6

    time_deltas1 = distance_deltas / speed1_ms
    time_deltas2 = distance_deltas / speed2_ms

    # Cumulative time difference (positive = driver 1 slower)
    delta_time = np.cumsum(time_deltas1 - time_deltas2)

    return delta_time


def resample_telemetry(
    telemetry: pd.DataFrame,
    new_resolution: float,
) -> pd.DataFrame:
    """
    Resample telemetry to a different distance resolution.

    Args:
        telemetry: Input telemetry DataFrame
        new_resolution: New distance resolution in meters

    Returns:
        Resampled telemetry DataFrame
    """
    min_dist = telemetry['Distance'].min()
    max_dist = telemetry['Distance'].max()

    new_distance_array = create_distance_array(min_dist, max_dist, new_resolution)

    return interpolate_telemetry(telemetry, new_distance_array)
