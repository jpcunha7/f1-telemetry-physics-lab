"""
Minisector analysis module for F1 Telemetry Physics Lab.

Implements fine-grained lap segmentation for detailed delta analysis.
Minisectors divide the track into small segments (typically 25-50) to identify
precisely where time is gained or lost.

Author: João Pedro Cunha
"""

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from f1telemetry.config import Config, DEFAULT_CONFIG

logger = logging.getLogger(__name__)


@dataclass
class MinisectorData:
    """Container for minisector analysis results."""

    minisector_id: np.ndarray  # Minisector number (0 to n_minisectors-1)
    distance_start: np.ndarray  # Start distance of each minisector (m)
    distance_end: np.ndarray  # End distance of each minisector (m)
    distance_center: np.ndarray  # Center distance for plotting (m)
    time_delta: np.ndarray  # Time delta in this minisector (s), positive = driver1 slower
    speed_avg_driver1: np.ndarray  # Average speed in minisector for driver 1 (km/h)
    speed_avg_driver2: np.ndarray  # Average speed in minisector for driver 2 (km/h)
    throttle_avg_driver1: np.ndarray  # Average throttle in minisector for driver 1 (%)
    throttle_avg_driver2: np.ndarray  # Average throttle in minisector for driver 2 (%)


def compute_minisector_deltas(
    telemetry1: pd.DataFrame,
    telemetry2: pd.DataFrame,
    n_minisectors: int = 50,
    config: Config = DEFAULT_CONFIG,
) -> MinisectorData:
    """
    Compute time deltas per minisector.

    Divides the lap into n_minisectors segments of equal distance and computes
    the time delta for each segment. This provides fine-grained insight into
    where drivers gain or lose time.

    Physics note:
    Time delta in a segment = integral(1/v) over distance
    Approximated by summing dt = dx/v for each sample point.

    Args:
        telemetry1: Aligned telemetry for driver 1 with Distance, Speed, Time
        telemetry2: Aligned telemetry for driver 2 with Distance, Speed, Time
        n_minisectors: Number of minisectors to divide the lap into
        config: Configuration object

    Returns:
        MinisectorData object with all computed metrics

    Raises:
        ValueError: If telemetry data is incompatible or invalid
    """
    # Validate inputs
    if len(telemetry1) != len(telemetry2):
        raise ValueError("Telemetry dataframes must have same length (should be aligned)")

    if "Distance" not in telemetry1.columns or "Speed" not in telemetry1.columns:
        raise ValueError("Telemetry must contain Distance and Speed columns")

    if n_minisectors < 5 or n_minisectors > 200:
        logger.warning(f"n_minisectors={n_minisectors} is unusual. Recommended: 25-50")

    distance = telemetry1["Distance"].values
    speed1 = telemetry1["Speed"].values
    speed2 = telemetry2["Speed"].values

    # Get optional channels
    throttle1 = telemetry1["Throttle"].values if "Throttle" in telemetry1.columns else None
    throttle2 = telemetry2["Throttle"].values if "Throttle" in telemetry2.columns else None

    # Define minisector boundaries
    minisector_boundaries = np.linspace(distance[0], distance[-1], n_minisectors + 1)

    # Initialize result arrays
    minisector_ids = np.arange(n_minisectors)
    distance_starts = minisector_boundaries[:-1]
    distance_ends = minisector_boundaries[1:]
    distance_centers = (distance_starts + distance_ends) / 2

    time_deltas = np.zeros(n_minisectors)
    speed_avg1 = np.zeros(n_minisectors)
    speed_avg2 = np.zeros(n_minisectors)
    throttle_avg1 = np.zeros(n_minisectors) if throttle1 is not None else None
    throttle_avg2 = np.zeros(n_minisectors) if throttle2 is not None else None

    # Compute metrics for each minisector
    for i in range(n_minisectors):
        # Find indices in this minisector
        mask = (distance >= distance_starts[i]) & (distance < distance_ends[i])

        if not np.any(mask):
            logger.warning(f"Minisector {i} has no data points")
            continue

        # Extract data for this segment
        dist_segment = distance[mask]
        speed1_segment = speed1[mask]
        speed2_segment = speed2[mask]

        # Compute time for each driver in this segment
        # time = integral(1/v) dx, approximated by sum(dx/v)
        dx = np.diff(dist_segment)

        # Use average speed between consecutive points to avoid division by zero
        epsilon = 0.1  # km/h
        v1_avg = (speed1_segment[:-1] + speed1_segment[1:]) / 2 + epsilon
        v2_avg = (speed2_segment[:-1] + speed2_segment[1:]) / 2 + epsilon

        # Convert km/h to m/s for time calculation
        time1_segment = np.sum(dx / (v1_avg / 3.6))
        time2_segment = np.sum(dx / (v2_avg / 3.6))

        # Delta: positive means driver1 is slower
        time_deltas[i] = time1_segment - time2_segment

        # Average metrics
        speed_avg1[i] = np.mean(speed1_segment)
        speed_avg2[i] = np.mean(speed2_segment)

        if throttle1 is not None and throttle2 is not None:
            throttle_avg1[i] = np.mean(throttle1[mask])
            throttle_avg2[i] = np.mean(throttle2[mask])

    logger.info(
        f"Computed {n_minisectors} minisectors. "
        f"Total delta: {np.sum(time_deltas):.3f}s, "
        f"Max gain: {np.min(time_deltas):.3f}s, "
        f"Max loss: {np.max(time_deltas):.3f}s"
    )

    return MinisectorData(
        minisector_id=minisector_ids,
        distance_start=distance_starts,
        distance_end=distance_ends,
        distance_center=distance_centers,
        time_delta=time_deltas,
        speed_avg_driver1=speed_avg1,
        speed_avg_driver2=speed_avg2,
        throttle_avg_driver1=throttle_avg1,
        throttle_avg_driver2=throttle_avg2,
    )


def minisector_data_to_dataframe(minisector_data: MinisectorData) -> pd.DataFrame:
    """
    Convert MinisectorData object to pandas DataFrame.

    Args:
        minisector_data: MinisectorData object from compute_minisector_deltas

    Returns:
        DataFrame with minisector analysis results
    """
    df = pd.DataFrame(
        {
            "Minisector": minisector_data.minisector_id,
            "Distance_Start": minisector_data.distance_start,
            "Distance_End": minisector_data.distance_end,
            "Time_Delta": minisector_data.time_delta,
            "Speed_Driver1": minisector_data.speed_avg_driver1,
            "Speed_Driver2": minisector_data.speed_avg_driver2,
        }
    )

    # Add throttle if available
    if minisector_data.throttle_avg_driver1 is not None:
        df["Throttle_Driver1"] = minisector_data.throttle_avg_driver1
        df["Throttle_Driver2"] = minisector_data.throttle_avg_driver2

    return df


def get_top_minisector_gains(minisector_data, n: int = 10) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Get top N minisectors with biggest gains and losses.

    Args:
        minisector_data: MinisectorData object or DataFrame from compute_minisector_deltas
        n: Number of top gains/losses to return

    Returns:
        Tuple of (top_gains_df, top_losses_df) where:
        - top_gains_df: DataFrame of minisectors where driver1 gained most (negative delta)
        - top_losses_df: DataFrame of minisectors where driver1 lost most (positive delta)
    """
    # Convert to dataframe if needed
    if isinstance(minisector_data, MinisectorData):
        df = minisector_data_to_dataframe(minisector_data)
    else:
        df = minisector_data

    # Sort by time delta
    df_sorted = df.sort_values("Time_Delta")

    # Top gains (most negative delta = driver1 faster)
    top_gains = df_sorted.head(n).copy()
    top_gains["Gain_Loss"] = "Gain"

    # Top losses (most positive delta = driver1 slower)
    top_losses = df_sorted.tail(n).copy()
    top_losses["Gain_Loss"] = "Loss"

    return top_gains, top_losses


def create_minisector_bar_chart(
    minisector_data,
    driver1_name: str,
    driver2_name: str,
    config: Config = DEFAULT_CONFIG,
) -> go.Figure:
    """
    Create bar chart visualization of minisector deltas.

    Args:
        minisector_data: MinisectorData object or DataFrame
        driver1_name: Name/code for driver 1
        driver2_name: Name/code for driver 2
        config: Configuration for plot styling

    Returns:
        Plotly figure with bar chart
    """
    # Handle both MinisectorData and DataFrame
    if isinstance(minisector_data, pd.DataFrame):
        minisector_ids = minisector_data["Minisector"].values
        time_deltas = minisector_data["Time_Delta"].values
    else:
        minisector_ids = minisector_data.minisector_id
        time_deltas = minisector_data.time_delta

    # Color bars based on who is faster
    colors = ["#1E90FF" if delta < 0 else "#FF1E1E" for delta in time_deltas]

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=minisector_ids,
            y=time_deltas,
            marker_color=colors,
            name="Time Delta",
            hovertemplate=(
                "<b>Minisector %{x}</b><br>"
                "Distance: %{customdata[0]:.0f}m - %{customdata[1]:.0f}m<br>"
                "Delta: %{y:.3f}s<br>"
                f"{driver1_name} Speed: " + "%{customdata[2]:.1f} km/h<br>"
                f"{driver2_name} Speed: " + "%{customdata[3]:.1f} km/h<br>"
                "<extra></extra>"
            ),
            customdata=np.column_stack(
                [
                    minisector_data["Distance_Start"].values
                    if isinstance(minisector_data, pd.DataFrame)
                    else minisector_data.distance_start,
                    minisector_data["Distance_End"].values
                    if isinstance(minisector_data, pd.DataFrame)
                    else minisector_data.distance_end,
                    minisector_data["Speed_Driver1"].values
                    if isinstance(minisector_data, pd.DataFrame)
                    else minisector_data.speed_avg_driver1,
                    minisector_data["Speed_Driver2"].values
                    if isinstance(minisector_data, pd.DataFrame)
                    else minisector_data.speed_avg_driver2,
                ]
            ),
        )
    )

    fig.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1)

    fig.update_layout(
        title=f"Minisector Time Deltas ({driver1_name} vs {driver2_name})",
        xaxis_title="Minisector Number",
        yaxis_title="Time Delta (s)",
        template=config.plot_theme,
        width=config.plot_width,
        height=config.plot_height,
        showlegend=False,
        annotations=[
            dict(
                x=0.02,
                y=0.98,
                xref="paper",
                yref="paper",
                text=f"Red = {driver1_name} slower<br>Blue = {driver1_name} faster",
                showarrow=False,
                bgcolor="rgba(0,0,0,0.5)",
                font=dict(size=10),
                align="left",
            )
        ],
    )

    return fig


def create_minisector_track_map(
    telemetry: pd.DataFrame,
    minisector_data,
    driver_name: str,
    config: Config = DEFAULT_CONFIG,
) -> go.Figure:
    """
    Create track map colored by minisector delta.

    Shows the track layout colored by time delta in each minisector, making it
    easy to see exactly where on track time is gained or lost.

    Args:
        telemetry: Telemetry DataFrame with X, Y, Distance columns
        minisector_data: MinisectorData object or DataFrame with delta information
        driver_name: Name of driver being analyzed
        config: Configuration for plot styling

    Returns:
        Plotly figure with track map

    Raises:
        ValueError: If position data (X, Y) is not available
    """
    if "X" not in telemetry.columns or "Y" not in telemetry.columns:
        raise ValueError("Position data (X, Y) not available in telemetry")

    # Handle both MinisectorData and DataFrame
    if isinstance(minisector_data, pd.DataFrame):
        distance_starts = minisector_data["Distance_Start"].values
        time_deltas = minisector_data["Time_Delta"].values
    else:
        distance_starts = minisector_data.distance_start
        time_deltas = minisector_data.time_delta

    # Assign each telemetry point to a minisector
    distance = telemetry["Distance"].values
    minisector_assignment = np.digitize(distance, distance_starts, right=False) - 1
    minisector_assignment = np.clip(minisector_assignment, 0, len(time_deltas) - 1)

    # Map time delta to each point
    delta_at_point = time_deltas[minisector_assignment]

    # Create color scale: blue for gains, red for losses
    max_abs_delta = np.max(np.abs(time_deltas))
    colorscale = [
        [0.0, "#0000FF"],  # Strong blue (big gain)
        [0.25, "#4169E1"],  # Medium blue
        [0.5, "#808080"],  # Gray (neutral)
        [0.75, "#FF6347"],  # Medium red
        [1.0, "#FF0000"],  # Strong red (big loss)
    ]

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=telemetry["X"],
            y=telemetry["Y"],
            mode="markers",
            marker=dict(
                size=4,
                color=delta_at_point,
                colorscale=colorscale,
                cmin=-max_abs_delta,
                cmax=max_abs_delta,
                showscale=True,
                colorbar=dict(
                    title="Delta (s)",
                    titleside="right",
                    tickmode="linear",
                    tick0=-max_abs_delta,
                    dtick=max_abs_delta / 2,
                ),
            ),
            name=driver_name,
            showlegend=False,
            hovertemplate=(
                "X: %{x:.0f}m<br>"
                "Y: %{y:.0f}m<br>"
                "Delta: %{marker.color:.3f}s<br>"
                "<extra></extra>"
            ),
        )
    )

    fig.update_xaxes(
        showgrid=False,
        showticklabels=False,
        zeroline=False,
        scaleanchor="y",
        scaleratio=1,
    )
    fig.update_yaxes(showgrid=False, showticklabels=False, zeroline=False)

    fig.update_layout(
        title=f"Track Map - Minisector Deltas ({driver_name})",
        template=config.plot_theme,
        width=config.plot_width,
        height=config.plot_height,
        annotations=[
            dict(
                x=0.02,
                y=0.98,
                xref="paper",
                yref="paper",
                text="Blue = Gaining time<br>Red = Losing time",
                showarrow=False,
                bgcolor="rgba(0,0,0,0.5)",
                font=dict(size=10),
                align="left",
            )
        ],
    )

    return fig


def create_minisector_comparison_table(
    minisector_data: MinisectorData,
    driver1_name: str,
    driver2_name: str,
    n_top: int = 10,
) -> pd.DataFrame:
    """
    Create comprehensive table of minisector analysis.

    Args:
        minisector_data: MinisectorData object
        driver1_name: Name/code for driver 1
        driver2_name: Name/code for driver 2
        n_top: Number of top gains/losses to highlight

    Returns:
        DataFrame with minisector analysis
    """
    df = pd.DataFrame(
        {
            "Minisector": minisector_data.minisector_id,
            "Distance_Start": minisector_data.distance_start.round(1),
            "Distance_End": minisector_data.distance_end.round(1),
            "Time_Delta_s": minisector_data.time_delta.round(4),
            f"{driver1_name}_Speed_kmh": minisector_data.speed_avg_driver1.round(1),
            f"{driver2_name}_Speed_kmh": minisector_data.speed_avg_driver2.round(1),
        }
    )

    # Add speed delta
    df["Speed_Delta_kmh"] = (
        minisector_data.speed_avg_driver1 - minisector_data.speed_avg_driver2
    ).round(1)

    # Add throttle if available
    if minisector_data.throttle_avg_driver1 is not None:
        df[f"{driver1_name}_Throttle_%"] = minisector_data.throttle_avg_driver1.round(1)
        df[f"{driver2_name}_Throttle_%"] = minisector_data.throttle_avg_driver2.round(1)

    # Add cumulative delta
    df["Cumulative_Delta_s"] = np.cumsum(minisector_data.time_delta).round(3)

    # Sort by biggest losses for easy identification
    df = df.sort_values("Time_Delta_s", ascending=False)

    return df
