"""
Multi-lap comparison and consistency analysis module for F1 Telemetry Physics Lab.

Enables comparison of one reference lap against multiple laps from the same driver
to identify consistency, mistakes, and driver fingerprint characteristics.

Author: João Pedro Cunha
"""

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from f1telemetry.config import Config, DEFAULT_CONFIG
from f1telemetry.minisectors import compute_minisector_deltas

logger = logging.getLogger(__name__)


@dataclass
class ConsistencyMetrics:
    """Consistency analysis for a driver across multiple laps.

    Attributes:
        n_laps: Number of laps analyzed
        avg_lap_time: Average lap time (s)
        std_lap_time: Standard deviation of lap times (s)
        consistency_score: 0-100 score, higher = more consistent
        outlier_lap_indices: Indices of laps that are statistical outliers
        best_lap_index: Index of fastest lap
        worst_lap_index: Index of slowest lap
    """

    n_laps: int
    avg_lap_time: float
    std_lap_time: float
    consistency_score: float
    outlier_lap_indices: list[int]
    best_lap_index: int
    worst_lap_index: int


@dataclass
class DriverFingerprint:
    """Driver characteristic fingerprint metrics.

    Attributes:
        avg_brake_onset_delta: Average brake onset distance relative to reference (m)
        avg_min_speed_delta: Average minimum speed delta in corners (km/h)
        throttle_aggressiveness: Score 0-100, higher = more aggressive on throttle
        braking_aggressiveness: Score 0-100, higher = later/harder braking
        consistency_index: Score 0-100, higher = more consistent
    """

    avg_brake_onset_delta: float
    avg_min_speed_delta: float
    throttle_aggressiveness: float
    braking_aggressiveness: float
    consistency_index: float


def compute_lap_consistency(lap_times: np.ndarray) -> ConsistencyMetrics:
    """
    Compute consistency metrics from lap times.

    Args:
        lap_times: Array of lap times (seconds)

    Returns:
        ConsistencyMetrics object

    Raises:
        ValueError: If less than 2 laps provided
    """
    if len(lap_times) < 2:
        raise ValueError("Need at least 2 laps for consistency analysis")

    n_laps = len(lap_times)
    avg_time = np.mean(lap_times)
    std_time = np.std(lap_times)

    # Consistency score: inverse of coefficient of variation, scaled to 0-100
    # Lower CV = higher consistency
    cv = std_time / avg_time if avg_time > 0 else 1.0
    consistency_score = max(0, min(100, 100 * (1 - cv * 10)))

    # Find outliers using 2-sigma rule
    threshold = 2 * std_time
    outlier_indices = [
        i for i, t in enumerate(lap_times) if abs(t - avg_time) > threshold
    ]

    best_idx = int(np.argmin(lap_times))
    worst_idx = int(np.argmax(lap_times))

    logger.info(
        f"Consistency analysis: {n_laps} laps, "
        f"avg={avg_time:.3f}s, std={std_time:.3f}s, "
        f"score={consistency_score:.1f}/100"
    )

    return ConsistencyMetrics(
        n_laps=n_laps,
        avg_lap_time=float(avg_time),
        std_lap_time=float(std_time),
        consistency_score=float(consistency_score),
        outlier_lap_indices=outlier_indices,
        best_lap_index=best_idx,
        worst_lap_index=worst_idx,
    )


def compute_minisector_variance(
    reference_telemetry: pd.DataFrame,
    comparison_telemetries: list[pd.DataFrame],
    n_minisectors: int = 50,
    config: Config = DEFAULT_CONFIG,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Compute variance in minisector times across multiple laps.

    Args:
        reference_telemetry: Reference lap telemetry
        comparison_telemetries: List of other lap telemetries to compare
        n_minisectors: Number of minisectors
        config: Configuration

    Returns:
        Tuple of (mean_deltas, std_deltas, minisector_ids)
        - mean_deltas: Mean time delta per minisector
        - std_deltas: Standard deviation per minisector
        - minisector_ids: Minisector ID array
    """
    if len(comparison_telemetries) == 0:
        raise ValueError("Need at least one comparison lap")

    # Compute minisector deltas for each comparison lap
    all_deltas = []

    for comp_tel in comparison_telemetries:
        try:
            minisector_data = compute_minisector_deltas(
                reference_telemetry, comp_tel, n_minisectors, config
            )
            all_deltas.append(minisector_data.time_delta)
        except Exception as e:
            logger.warning(f"Failed to compute minisector for a lap: {e}")
            continue

    if len(all_deltas) == 0:
        raise ValueError("Failed to compute minisectors for any comparison lap")

    # Stack into array (laps x minisectors)
    deltas_array = np.array(all_deltas)

    # Compute mean and std across laps
    mean_deltas = np.mean(deltas_array, axis=0)
    std_deltas = np.std(deltas_array, axis=0)

    minisector_ids = np.arange(n_minisectors)

    logger.info(
        f"Computed minisector variance for {len(all_deltas)} laps. "
        f"Max variance: {np.max(std_deltas):.3f}s"
    )

    return mean_deltas, std_deltas, minisector_ids


def identify_mistake_zones(
    mean_deltas: np.ndarray, std_deltas: np.ndarray, threshold_std: float = 0.05
) -> list[int]:
    """
    Identify minisectors with high variance (potential mistake zones).

    Args:
        mean_deltas: Mean time delta per minisector
        std_deltas: Standard deviation per minisector
        threshold_std: Threshold for flagging high variance (seconds)

    Returns:
        List of minisector indices with high variance
    """
    mistake_zones = [i for i, std in enumerate(std_deltas) if std > threshold_std]

    logger.info(f"Identified {len(mistake_zones)} potential mistake zones")

    return mistake_zones


def create_driver_fingerprint(
    reference_telemetry: pd.DataFrame,
    comparison_telemetries: list[pd.DataFrame],
    config: Config = DEFAULT_CONFIG,
) -> DriverFingerprint:
    """
    Create driver fingerprint from multiple laps.

    Extracts characteristic driving style metrics.

    Args:
        reference_telemetry: Reference lap (typically fastest)
        comparison_telemetries: Other laps from same driver
        config: Configuration

    Returns:
        DriverFingerprint object
    """
    # Compute average deltas across all laps
    mean_deltas, std_deltas, _ = compute_minisector_variance(
        reference_telemetry, comparison_telemetries, config=config
    )

    # Overall consistency from minisector variance
    avg_variance = np.mean(std_deltas)
    consistency_index = max(0, min(100, 100 * (1 - avg_variance * 20)))

    # Brake onset analysis (if brake data available)
    avg_brake_onset_delta = 0.0
    if "Brake" in reference_telemetry.columns:
        # Compare brake application points
        ref_brake = reference_telemetry["Brake"].values
        ref_distance = reference_telemetry["Distance"].values

        brake_onset_deltas = []
        for comp_tel in comparison_telemetries:
            if "Brake" not in comp_tel.columns:
                continue

            comp_brake = comp_tel["Brake"].values
            comp_distance = comp_tel["Distance"].values

            # Find first significant brake application
            ref_brake_idx = np.where(ref_brake > config.brake_threshold)[0]
            comp_brake_idx = np.where(comp_brake > config.brake_threshold)[0]

            if len(ref_brake_idx) > 0 and len(comp_brake_idx) > 0:
                ref_first = ref_distance[ref_brake_idx[0]]
                comp_first = comp_distance[comp_brake_idx[0]]
                brake_onset_deltas.append(comp_first - ref_first)

        if brake_onset_deltas:
            avg_brake_onset_delta = float(np.mean(brake_onset_deltas))

    # Minimum speed analysis
    avg_min_speed_delta = 0.0
    ref_min_speed = reference_telemetry["Speed"].min()

    for comp_tel in comparison_telemetries:
        comp_min_speed = comp_tel["Speed"].min()
        avg_min_speed_delta += comp_min_speed - ref_min_speed

    if len(comparison_telemetries) > 0:
        avg_min_speed_delta /= len(comparison_telemetries)

    # Throttle aggressiveness (if available)
    throttle_aggressiveness = 50.0  # Default neutral
    if "Throttle" in reference_telemetry.columns:
        ref_throttle = reference_telemetry["Throttle"].values
        avg_throttle = np.mean(ref_throttle)
        # Scale to 0-100 where higher = more aggressive
        throttle_aggressiveness = min(100, avg_throttle)

    # Braking aggressiveness
    braking_aggressiveness = 50.0  # Default neutral
    if avg_brake_onset_delta < 0:
        # Later braking = more aggressive
        braking_aggressiveness = min(100, 50 + abs(avg_brake_onset_delta) * 2)
    elif avg_brake_onset_delta > 0:
        # Earlier braking = less aggressive
        braking_aggressiveness = max(0, 50 - avg_brake_onset_delta * 2)

    return DriverFingerprint(
        avg_brake_onset_delta=float(avg_brake_onset_delta),
        avg_min_speed_delta=float(avg_min_speed_delta),
        throttle_aggressiveness=float(throttle_aggressiveness),
        braking_aggressiveness=float(braking_aggressiveness),
        consistency_index=float(consistency_index),
    )


def create_variance_plot(
    mean_deltas: np.ndarray,
    std_deltas: np.ndarray,
    minisector_ids: np.ndarray,
    driver_name: str,
    config: Config = DEFAULT_CONFIG,
) -> go.Figure:
    """
    Create plot showing mean delta and variance per minisector.

    Args:
        mean_deltas: Mean time delta per minisector
        std_deltas: Standard deviation per minisector
        minisector_ids: Minisector ID array
        driver_name: Name of driver
        config: Configuration for plot styling

    Returns:
        Plotly figure with error bars
    """
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=minisector_ids,
            y=mean_deltas,
            mode="markers",
            marker=dict(size=8, color="#FF1E1E"),
            error_y=dict(
                type="data",
                array=std_deltas,
                visible=True,
                color="rgba(255, 30, 30, 0.3)",
            ),
            name="Mean Delta ± Std Dev",
        )
    )

    fig.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1)

    fig.update_layout(
        title=f"Lap-to-Lap Variance by Minisector ({driver_name})",
        xaxis_title="Minisector Number",
        yaxis_title="Time Delta (s)",
        template=config.plot_theme,
        width=config.plot_width,
        height=config.plot_height,
        hovermode="x unified",
    )

    return fig


def create_consistency_distribution(
    lap_times: np.ndarray,
    driver_name: str,
    config: Config = DEFAULT_CONFIG,
) -> go.Figure:
    """
    Create histogram of lap time distribution.

    Args:
        lap_times: Array of lap times (seconds)
        driver_name: Name of driver
        config: Configuration for plot styling

    Returns:
        Plotly figure with histogram
    """
    fig = go.Figure()

    fig.add_trace(
        go.Histogram(
            x=lap_times,
            nbinsx=20,
            marker_color="#1E90FF",
            name="Lap Times",
        )
    )

    # Add mean line
    mean_time = np.mean(lap_times)
    fig.add_vline(
        x=mean_time,
        line_dash="dash",
        line_color="#FF1E1E",
        line_width=2,
        annotation_text=f"Mean: {mean_time:.3f}s",
        annotation_position="top right",
    )

    fig.update_layout(
        title=f"Lap Time Distribution ({driver_name})",
        xaxis_title="Lap Time (s)",
        yaxis_title="Count",
        template=config.plot_theme,
        width=config.plot_width,
        height=config.plot_height,
        showlegend=False,
    )

    return fig


def create_fingerprint_radar(
    fingerprint: DriverFingerprint,
    driver_name: str,
    config: Config = DEFAULT_CONFIG,
) -> go.Figure:
    """
    Create radar chart of driver fingerprint.

    Args:
        fingerprint: DriverFingerprint object
        driver_name: Name of driver
        config: Configuration for plot styling

    Returns:
        Plotly figure with radar chart
    """
    categories = [
        "Throttle Aggression",
        "Braking Aggression",
        "Consistency",
    ]

    values = [
        fingerprint.throttle_aggressiveness,
        fingerprint.braking_aggressiveness,
        fingerprint.consistency_index,
    ]

    # Close the radar chart
    values.append(values[0])
    categories_closed = categories + [categories[0]]

    fig = go.Figure()

    fig.add_trace(
        go.Scatterpolar(
            r=values,
            theta=categories_closed,
            fill="toself",
            fillcolor="rgba(255, 30, 30, 0.3)",
            line=dict(color="#FF1E1E", width=2),
            name=driver_name,
        )
    )

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100]),
        ),
        title=f"Driver Fingerprint ({driver_name})",
        template=config.plot_theme,
        width=config.plot_width * 0.7,
        height=config.plot_width * 0.7,
        showlegend=False,
    )

    return fig
