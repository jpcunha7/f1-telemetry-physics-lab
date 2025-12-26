"""
Physics computation module for F1 Telemetry Physics Lab.

Computes derived signals like acceleration, braking zones, and cornering metrics.

Author: João Pedro Cunha

Note: These are approximate calculations. We ignore:
- Vehicle mass and drag model
- Track elevation changes
- Tire degradation effects
- Detailed aerodynamic modeling
"""

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
from scipy.signal import savgol_filter, find_peaks

from f1telemetry.config import Config, DEFAULT_CONFIG

logger = logging.getLogger(__name__)


def smooth_signal(
    signal: np.ndarray,
    window_length: int = 11,
    polyorder: int = 3,
) -> np.ndarray:
    """
    Smooth a signal using Savitzky-Golay filter to reduce noise.

    Args:
        signal: Input signal array
        window_length: Length of filter window (must be odd)
        polyorder: Polynomial order for fitting

    Returns:
        Smoothed signal
    """
    if len(signal) < window_length:
        logger.warning(f"Signal too short for smoothing (len={len(signal)})")
        return signal

    # Ensure window length is odd
    if window_length % 2 == 0:
        window_length += 1

    try:
        return savgol_filter(signal, window_length, polyorder)
    except Exception as e:
        logger.warning(f"Smoothing failed: {e}, returning original signal")
        return signal


def compute_acceleration(
    telemetry: pd.DataFrame,
    config: Config = DEFAULT_CONFIG,
) -> np.ndarray:
    """
    Compute longitudinal acceleration from speed and distance.

    Uses the kinematic equation: a = dv/dt
    Approximated from distance and speed data.

    Args:
        telemetry: Telemetry DataFrame with Distance and Speed columns
        config: Configuration for smoothing parameters

    Returns:
        Array of acceleration in m/s²
    """
    speed_kmh = telemetry['Speed'].values
    distance = telemetry['Distance'].values

    # Convert speed to m/s
    speed_ms = speed_kmh / 3.6

    # Smooth speed before differentiation to reduce noise
    speed_smooth = smooth_signal(
        speed_ms,
        config.smoothing_window,
        config.smoothing_polyorder,
    )

    # Compute time deltas: dt = dx / v
    epsilon = 0.1 / 3.6  # Small epsilon to avoid division by zero
    time_deltas = np.diff(distance) / (speed_smooth[:-1] + epsilon)
    time_deltas = np.clip(time_deltas, 0.001, 10)  # Reasonable bounds

    # Compute acceleration: a = dv / dt
    speed_deltas = np.diff(speed_smooth)
    acceleration = speed_deltas / time_deltas

    # Prepend first value to match original length
    acceleration = np.concatenate([[acceleration[0]], acceleration])

    # Smooth acceleration to reduce noise further
    acceleration = smooth_signal(
        acceleration,
        config.smoothing_window,
        config.smoothing_polyorder,
    )

    return acceleration


@dataclass
class BrakingZone:
    """Information about a detected braking zone."""

    start_idx: int
    end_idx: int
    start_distance: float
    end_distance: float
    entry_speed: float  # km/h
    min_speed: float  # km/h
    peak_deceleration: float  # m/s² (negative)
    braking_distance: float  # meters
    duration: float  # approximate seconds


def detect_braking_zones(
    telemetry: pd.DataFrame,
    acceleration: Optional[np.ndarray] = None,
    config: Config = DEFAULT_CONFIG,
) -> list[BrakingZone]:
    """
    Detect braking zones from telemetry data.

    Args:
        telemetry: Telemetry DataFrame with Brake, Speed, Distance
        acceleration: Pre-computed acceleration (optional)
        config: Configuration with brake_threshold

    Returns:
        List of BrakingZone objects
    """
    if 'Brake' not in telemetry.columns:
        logger.warning("No Brake column in telemetry, cannot detect braking zones")
        return []

    brake = telemetry['Brake'].values
    speed = telemetry['Speed'].values
    distance = telemetry['Distance'].values

    # Compute acceleration if not provided
    if acceleration is None:
        acceleration = compute_acceleration(telemetry, config)

    # Find braking zones: brake > threshold
    braking_mask = brake > config.brake_threshold

    # Find contiguous braking regions
    braking_diff = np.diff(np.concatenate([[0], braking_mask.astype(int), [0]]))
    brake_starts = np.where(braking_diff == 1)[0]
    brake_ends = np.where(braking_diff == -1)[0]

    zones = []
    for start, end in zip(brake_starts, brake_ends):
        if end <= start or end - start < 3:  # Skip very short zones
            continue

        zone_accel = acceleration[start:end]
        zone_speed = speed[start:end]
        zone_distance = distance[start:end]

        # Estimate duration (approximate)
        speed_avg_ms = np.mean(zone_speed) / 3.6
        duration = (zone_distance[-1] - zone_distance[0]) / max(speed_avg_ms, 1.0)

        zone = BrakingZone(
            start_idx=int(start),
            end_idx=int(end),
            start_distance=float(zone_distance[0]),
            end_distance=float(zone_distance[-1]),
            entry_speed=float(zone_speed[0]),
            min_speed=float(zone_speed.min()),
            peak_deceleration=float(zone_accel.min()),
            braking_distance=float(zone_distance[-1] - zone_distance[0]),
            duration=float(duration),
        )
        zones.append(zone)

    logger.info(f"Detected {len(zones)} braking zones")
    return zones


@dataclass
class Corner:
    """Information about a detected corner."""

    idx: int
    distance: float
    min_speed: float  # km/h
    entry_speed: float  # km/h (speed before corner)
    exit_speed: float  # km/h (speed after corner)
    exit_acceleration: float  # m/s² (average in exit phase)


def detect_corners(
    telemetry: pd.DataFrame,
    acceleration: Optional[np.ndarray] = None,
    config: Config = DEFAULT_CONFIG,
) -> list[Corner]:
    """
    Detect corners as local minima in speed.

    Args:
        telemetry: Telemetry DataFrame
        acceleration: Pre-computed acceleration (optional)
        config: Configuration with speed_threshold_corner

    Returns:
        List of Corner objects
    """
    speed = telemetry['Speed'].values
    distance = telemetry['Distance'].values

    # Smooth speed for peak detection
    speed_smooth = smooth_signal(speed, config.smoothing_window, config.smoothing_polyorder)

    # Compute acceleration if not provided
    if acceleration is None:
        acceleration = compute_acceleration(telemetry, config)

    # Find local minima in speed (corners/apex points)
    # Only consider points below a certain speed threshold
    minima_indices, _ = find_peaks(
        -speed_smooth,  # Invert for minima detection
        prominence=10,  # Require at least 10 km/h drop
        distance=20,  # Minimum distance between corners
    )

    # Filter by speed threshold
    minima_indices = [
        idx for idx in minima_indices
        if speed_smooth[idx] < config.speed_threshold_corner
    ]

    corners = []
    for idx in minima_indices:
        # Look back/forward for entry/exit speeds
        lookback = min(30, idx)
        lookforward = min(30, len(speed) - idx - 1)

        entry_speed = float(speed[idx - lookback]) if lookback > 0 else float(speed[idx])
        exit_speed = float(speed[idx + lookforward]) if lookforward > 0 else float(speed[idx])

        # Average acceleration in exit phase
        exit_accel = float(np.mean(acceleration[idx:idx + lookforward])) if lookforward > 5 else 0.0

        corner = Corner(
            idx=int(idx),
            distance=float(distance[idx]),
            min_speed=float(speed[idx]),
            entry_speed=entry_speed,
            exit_speed=exit_speed,
            exit_acceleration=exit_accel,
        )
        corners.append(corner)

    logger.info(f"Detected {len(corners)} corners")
    return corners


def add_physics_channels(
    telemetry: pd.DataFrame,
    config: Config = DEFAULT_CONFIG,
) -> pd.DataFrame:
    """
    Add computed physics channels to telemetry DataFrame.

    Adds:
    - Acceleration (m/s²)

    Args:
        telemetry: Input telemetry DataFrame
        config: Configuration

    Returns:
        Telemetry with additional physics channels
    """
    telemetry = telemetry.copy()

    # Compute acceleration
    telemetry['Acceleration'] = compute_acceleration(telemetry, config)

    return telemetry
