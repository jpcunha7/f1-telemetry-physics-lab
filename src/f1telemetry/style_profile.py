"""
Driver style profile module.

Analyzes aggregated driver behavior across multiple laps.

Author: João Pedro Cunha
"""

import logging
from typing import List, Dict, Any
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from f1telemetry.config import Config, DEFAULT_CONFIG

logger = logging.getLogger(__name__)


def aggregate_telemetry_stats(
    telemetry_list: List[pd.DataFrame],
    driver_name: str,
) -> Dict[str, Any]:
    """
    Compute aggregated statistics across multiple laps.

    Args:
        telemetry_list: List of telemetry DataFrames (one per lap)
        driver_name: Driver name

    Returns:
        Dictionary with aggregated metrics
    """
    stats = {
        "driver_name": driver_name,
        "num_laps": len(telemetry_list),
    }

    # Collect data across all laps
    all_speeds = []
    all_throttles = []
    all_brakes = []
    all_gears = []
    all_long_accel = []
    all_lat_accel = []

    for tel in telemetry_list:
        if "Speed" in tel.columns:
            all_speeds.extend(tel["Speed"].values)
        if "Throttle" in tel.columns:
            all_throttles.extend(tel["Throttle"].values)
        if "Brake" in tel.columns:
            all_brakes.extend(tel["Brake"].values)
        if "nGear" in tel.columns:
            all_gears.extend(tel["nGear"].values)
        if "LongAccel" in tel.columns:
            all_long_accel.extend(tel["LongAccel"].values)
        if "LatAccel" in tel.columns:
            all_lat_accel.extend(tel["LatAccel"].values)

    # Speed statistics
    if all_speeds:
        stats["avg_speed"] = np.mean(all_speeds)
        stats["max_speed"] = np.max(all_speeds)
        stats["min_speed"] = np.min(all_speeds)
        stats["speed_std"] = np.std(all_speeds)

    # Throttle statistics
    if all_throttles:
        stats["avg_throttle"] = np.mean(all_throttles)
        stats["percent_full_throttle"] = (
            (np.array(all_throttles) >= 99).sum() / len(all_throttles) * 100
        )
        stats["percent_partial_throttle"] = (
            ((np.array(all_throttles) > 0) & (np.array(all_throttles) < 99)).sum()
            / len(all_throttles)
            * 100
        )

    # Brake statistics
    if all_brakes:
        stats["avg_brake"] = np.mean(all_brakes)
        stats["percent_braking"] = (np.array(all_brakes) > 10).sum() / len(all_brakes) * 100

    # Gear statistics
    if all_gears:
        gear_counts = pd.Series(all_gears).value_counts()
        stats["most_common_gear"] = int(gear_counts.idxmax())
        stats["avg_gear"] = np.mean(all_gears)

    # Acceleration statistics
    if all_long_accel:
        stats["avg_long_accel"] = np.mean(all_long_accel)
        stats["max_accel"] = np.max(all_long_accel)
        stats["max_decel"] = np.min(all_long_accel)
        stats["percent_accelerating"] = (
            (np.array(all_long_accel) > 0.5).sum() / len(all_long_accel) * 100
        )
        stats["percent_decelerating"] = (
            (np.array(all_long_accel) < -0.5).sum() / len(all_long_accel) * 100
        )

    if all_lat_accel:
        stats["avg_lat_accel"] = np.mean(np.abs(all_lat_accel))
        stats["max_lat_accel"] = np.max(np.abs(all_lat_accel))

    return stats


def create_throttle_brake_distribution_plot(
    telemetry_list: List[pd.DataFrame],
    driver_name: str,
    config: Config = DEFAULT_CONFIG,
) -> go.Figure:
    """
    Create histogram of throttle and brake application.

    Args:
        telemetry_list: List of telemetry DataFrames
        driver_name: Driver name
        config: Configuration instance

    Returns:
        Plotly figure
    """
    fig = make_subplots(
        rows=1, cols=2, subplot_titles=("Throttle Distribution", "Brake Distribution")
    )

    # Collect throttle and brake data
    all_throttles = []
    all_brakes = []

    for tel in telemetry_list:
        if "Throttle" in tel.columns:
            all_throttles.extend(tel["Throttle"].values)
        if "Brake" in tel.columns:
            all_brakes.extend(tel["Brake"].values)

    # Throttle histogram
    if all_throttles:
        fig.add_trace(
            go.Histogram(
                x=all_throttles,
                nbinsx=50,
                name="Throttle",
                marker=dict(color="#00ff00"),
            ),
            row=1,
            col=1,
        )

    # Brake histogram
    if all_brakes:
        fig.add_trace(
            go.Histogram(
                x=all_brakes,
                nbinsx=50,
                name="Brake",
                marker=dict(color="#ff0000"),
            ),
            row=1,
            col=2,
        )

    fig.update_xaxes(title_text="Throttle (%)", row=1, col=1)
    fig.update_xaxes(title_text="Brake Pressure (%)", row=1, col=2)
    fig.update_yaxes(title_text="Frequency", row=1, col=1)
    fig.update_yaxes(title_text="Frequency", row=1, col=2)

    fig.update_layout(
        title=f"Input Distribution - {driver_name}",
        template="plotly_dark",
        height=400,
        showlegend=False,
    )

    return fig


def create_acceleration_distribution_plot(
    telemetry_list: List[pd.DataFrame],
    driver_name: str,
    config: Config = DEFAULT_CONFIG,
) -> go.Figure:
    """
    Create histogram of longitudinal and lateral acceleration.

    Args:
        telemetry_list: List of telemetry DataFrames
        driver_name: Driver name
        config: Configuration instance

    Returns:
        Plotly figure
    """
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Longitudinal Accel", "Lateral Accel"))

    # Collect accel data
    all_long_accel = []
    all_lat_accel = []

    for tel in telemetry_list:
        if "LongAccel" in tel.columns:
            all_long_accel.extend(tel["LongAccel"].values)
        if "LatAccel" in tel.columns:
            all_lat_accel.extend(tel["LatAccel"].values)

    # Longitudinal accel histogram
    if all_long_accel:
        fig.add_trace(
            go.Histogram(
                x=all_long_accel,
                nbinsx=100,
                name="Longitudinal",
                marker=dict(color="#1e90ff"),
            ),
            row=1,
            col=1,
        )

    # Lateral accel histogram
    if all_lat_accel:
        fig.add_trace(
            go.Histogram(
                x=all_lat_accel,
                nbinsx=100,
                name="Lateral",
                marker=dict(color="#ff1e90"),
            ),
            row=1,
            col=2,
        )

    fig.update_xaxes(title_text="Longitudinal Accel (g)", row=1, col=1)
    fig.update_xaxes(title_text="Lateral Accel (g)", row=1, col=2)
    fig.update_yaxes(title_text="Frequency", row=1, col=1)
    fig.update_yaxes(title_text="Frequency", row=1, col=2)

    fig.update_layout(
        title=f"Acceleration Distribution - {driver_name}",
        template="plotly_dark",
        height=400,
        showlegend=False,
    )

    return fig


def create_speed_distribution_plot(
    telemetry_list: List[pd.DataFrame],
    driver_name: str,
    config: Config = DEFAULT_CONFIG,
) -> go.Figure:
    """
    Create histogram of speed distribution.

    Args:
        telemetry_list: List of telemetry DataFrames
        driver_name: Driver name
        config: Configuration instance

    Returns:
        Plotly figure
    """
    all_speeds = []

    for tel in telemetry_list:
        if "Speed" in tel.columns:
            all_speeds.extend(tel["Speed"].values)

    fig = go.Figure()

    if all_speeds:
        fig.add_trace(
            go.Histogram(
                x=all_speeds,
                nbinsx=80,
                name="Speed",
                marker=dict(color="#ffa500"),
            )
        )

    fig.update_layout(
        title=f"Speed Distribution - {driver_name}",
        xaxis_title="Speed (km/h)",
        yaxis_title="Frequency",
        template="plotly_dark",
        height=400,
    )

    return fig


def compare_driver_styles(
    stats1: Dict[str, Any],
    stats2: Dict[str, Any],
) -> pd.DataFrame:
    """
    Create comparison table of driver style metrics.

    Args:
        stats1: Stats for driver 1
        stats2: Stats for driver 2

    Returns:
        DataFrame with side-by-side comparison
    """
    metrics = [
        "avg_speed",
        "max_speed",
        "percent_full_throttle",
        "percent_braking",
        "avg_long_accel",
        "max_accel",
        "max_decel",
        "avg_lat_accel",
        "max_lat_accel",
    ]

    rows = []
    for metric in metrics:
        if metric in stats1 and metric in stats2:
            row = {
                "Metric": metric.replace("_", " ").title(),
                stats1["driver_name"]: f"{stats1[metric]:.2f}",
                stats2["driver_name"]: f"{stats2[metric]:.2f}",
                "Delta": f"{stats1[metric] - stats2[metric]:+.2f}",
            }
            rows.append(row)

    return pd.DataFrame(rows)
