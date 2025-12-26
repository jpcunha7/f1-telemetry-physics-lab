"""
G-G diagram module for F1 Telemetry Physics Lab.

Creates g-g diagrams (friction circle plots) showing longitudinal and lateral
acceleration capabilities. Provides insight into tire grip utilization and
vehicle dynamics.

Author: João Pedro Cunha

IMPORTANT PHYSICS DISCLAIMERS:
- Longitudinal acceleration computed from dv/dt using discrete telemetry
- Lateral acceleration approximated using v²/R where R from position data
- Does NOT account for: track banking, elevation changes, aerodynamic downforce variation
- Does NOT account for: tire degradation, temperature, pressure effects
- Assumes constant vehicle mass and ignores fuel consumption
- These are APPROXIMATIONS suitable for comparative analysis, not absolute measurements
"""

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from f1telemetry.config import Config, DEFAULT_CONFIG
from f1telemetry.physics import smooth_signal

logger = logging.getLogger(__name__)

# Physical constants
GRAVITY = 9.81  # m/s² - gravitational acceleration


@dataclass
class AccelerationData:
    """Container for computed acceleration data.

    Attributes:
        ax: Longitudinal acceleration (m/s²), positive = accelerating
        ay: Lateral acceleration (m/s²), positive = left turn
        speed: Speed at each point (m/s)
        distance: Distance at each point (m)
        combined_g: Combined acceleration magnitude (g-force)
        brake_mask: Boolean mask indicating braking zones
        traction_mask: Boolean mask indicating traction zones
        cornering_mask: Boolean mask indicating high lateral-g zones
    """

    ax: np.ndarray
    ay: np.ndarray
    speed: np.ndarray
    distance: np.ndarray
    combined_g: np.ndarray
    brake_mask: np.ndarray
    traction_mask: np.ndarray
    cornering_mask: np.ndarray


def compute_heading_from_position(
    x: np.ndarray, y: np.ndarray, distance: np.ndarray, config: Config
) -> np.ndarray:
    """
    Compute heading angle from X, Y position data.

    Heading is the direction of travel, computed from the gradient of position.

    Args:
        x: X position array (m)
        y: Y position array (m)
        distance: Distance array (m) for smoothing reference
        config: Configuration for smoothing

    Returns:
        Array of heading angles (radians)
    """
    # Compute dx/dt and dy/dt using numerical differentiation
    dx = np.gradient(x)
    dy = np.gradient(y)

    # Heading angle: atan2(dy, dx)
    heading = np.arctan2(dy, dx)

    # Smooth heading to reduce noise (heading can be noisy near low speeds)
    heading_smooth = smooth_signal(heading, config.smoothing_window, config.smoothing_polyorder)

    return heading_smooth


def compute_curvature_from_heading(
    heading: np.ndarray, distance: np.ndarray, config: Config
) -> np.ndarray:
    """
    Compute track curvature from heading angle.

    Curvature κ = dθ/ds where θ is heading and s is distance along track.
    Units: 1/m (inverse meters)

    Args:
        heading: Heading angle array (radians)
        distance: Distance array (m)
        config: Configuration for smoothing

    Returns:
        Array of curvature values (1/m)
    """
    # Compute dθ/ds
    dheading = np.gradient(heading)
    ddistance = np.gradient(distance)

    # Avoid division by zero
    ddistance = np.clip(ddistance, 0.1, None)

    curvature = dheading / ddistance

    # Smooth curvature to reduce noise
    curvature_smooth = smooth_signal(curvature, config.smoothing_window, config.smoothing_polyorder)

    return curvature_smooth


def compute_accelerations(
    telemetry: pd.DataFrame, config: Config = DEFAULT_CONFIG
) -> AccelerationData:
    """
    Compute longitudinal and lateral accelerations from telemetry.

    Physics:
    - Longitudinal: ax = dv/dt, approximated from speed and distance
    - Lateral: ay = v²·κ where κ is curvature from position data

    Args:
        telemetry: Telemetry DataFrame with Speed, Distance, and optionally X, Y
        config: Configuration for smoothing and thresholds

    Returns:
        AccelerationData object with computed values

    Raises:
        ValueError: If required columns are missing
    """
    if "Speed" not in telemetry.columns or "Distance" not in telemetry.columns:
        raise ValueError("Telemetry must contain Speed and Distance columns")

    speed_kmh = telemetry["Speed"].values
    distance = telemetry["Distance"].values

    # Convert speed to m/s
    speed_ms = speed_kmh / 3.6

    # Smooth speed before differentiation
    speed_smooth = smooth_signal(speed_ms, config.smoothing_window, config.smoothing_polyorder)

    # LONGITUDINAL ACCELERATION: ax = dv/dt
    # Use dx and v to compute dt = dx/v, then ax = dv/dt
    dx = np.gradient(distance)
    dv = np.gradient(speed_smooth)

    # Compute time deltas: dt = dx / v
    epsilon = 0.1 / 3.6  # Small epsilon to avoid division by zero
    dt = dx / (speed_smooth + epsilon)
    dt = np.clip(dt, 0.001, 10)  # Reasonable bounds

    # ax = dv / dt
    ax = dv / dt

    # Smooth longitudinal acceleration
    ax = smooth_signal(ax, config.smoothing_window, config.smoothing_polyorder)

    # LATERAL ACCELERATION: ay = v² · κ
    # First, check if position data is available
    if "X" in telemetry.columns and "Y" in telemetry.columns:
        x = telemetry["X"].values
        y = telemetry["Y"].values

        # Compute heading from position
        heading = compute_heading_from_position(x, y, distance, config)

        # Compute curvature from heading
        curvature = compute_curvature_from_heading(heading, distance, config)

        # Compute lateral acceleration: ay = v² · κ
        ay = speed_smooth**2 * curvature

        # Smooth lateral acceleration
        ay = smooth_signal(ay, config.smoothing_window, config.smoothing_polyorder)

        # Clip to reasonable bounds (F1 cars can pull ~5-6g lateral max)
        ay = np.clip(ay, -6 * GRAVITY, 6 * GRAVITY)

    else:
        logger.warning("Position data (X, Y) not available. Lateral acceleration set to zero.")
        ay = np.zeros_like(ax)

    # COMBINED ACCELERATION MAGNITUDE
    combined_g = np.sqrt(ax**2 + ay**2) / GRAVITY

    # CREATE MASKS FOR DIFFERENT DRIVING PHASES
    # Braking: ax < -1g
    brake_mask = ax < -GRAVITY

    # Traction: ax > 0.5g
    traction_mask = ax > 0.5 * GRAVITY

    # Cornering: |ay| > 1g
    cornering_mask = np.abs(ay) > GRAVITY

    logger.info(
        f"Computed accelerations: "
        f"max_ax={np.max(ax)/GRAVITY:.2f}g, "
        f"min_ax={np.min(ax)/GRAVITY:.2f}g, "
        f"max_ay={np.max(np.abs(ay))/GRAVITY:.2f}g, "
        f"max_combined={np.max(combined_g):.2f}g"
    )

    return AccelerationData(
        ax=ax,
        ay=ay,
        speed=speed_ms,
        distance=distance,
        combined_g=combined_g,
        brake_mask=brake_mask,
        traction_mask=traction_mask,
        cornering_mask=cornering_mask,
    )


def create_gg_plot(
    telemetry1: pd.DataFrame,
    telemetry2: pd.DataFrame,
    driver1_name: str,
    driver2_name: str,
    config: Config = DEFAULT_CONFIG,
) -> go.Figure:
    """
    Create g-g diagram comparing two drivers.

    The g-g diagram (friction circle) plots lateral vs longitudinal acceleration,
    showing the grip envelope and how drivers utilize available tire grip.

    Args:
        telemetry1: Telemetry for driver 1
        telemetry2: Telemetry for driver 2
        driver1_name: Name/code for driver 1
        driver2_name: Name/code for driver 2
        config: Configuration for plot styling

    Returns:
        Plotly figure with g-g diagram
    """
    # Compute accelerations
    accel1 = compute_accelerations(telemetry1, config)
    accel2 = compute_accelerations(telemetry2, config)

    # Convert to g-forces
    ax1_g = accel1.ax / GRAVITY
    ay1_g = accel1.ay / GRAVITY
    ax2_g = accel2.ax / GRAVITY
    ay2_g = accel2.ay / GRAVITY

    # Subsample for plotting (too many points makes plot slow)
    subsample = 5
    ax1_plot = ax1_g[::subsample]
    ay1_plot = ay1_g[::subsample]
    ax2_plot = ax2_g[::subsample]
    ay2_plot = ay2_g[::subsample]

    fig = go.Figure()

    # Driver 1 scatter
    fig.add_trace(
        go.Scattergl(
            x=ay1_plot,
            y=ax1_plot,
            mode="markers",
            marker=dict(size=3, color="#FF1E1E", opacity=0.4),
            name=driver1_name,
        )
    )

    # Driver 2 scatter
    fig.add_trace(
        go.Scattergl(
            x=ay2_plot,
            y=ax2_plot,
            mode="markers",
            marker=dict(size=3, color="#1E90FF", opacity=0.4),
            name=driver2_name,
        )
    )

    # Add reference circles for grip levels
    theta = np.linspace(0, 2 * np.pi, 100)
    for g_level in [1, 2, 3, 4]:
        x_circle = g_level * np.cos(theta)
        y_circle = g_level * np.sin(theta)
        fig.add_trace(
            go.Scatter(
                x=x_circle,
                y=y_circle,
                mode="lines",
                line=dict(color="gray", dash="dot", width=1),
                showlegend=False,
                hoverinfo="skip",
            )
        )

    # Add axis lines
    fig.add_hline(y=0, line_color="gray", line_width=1)
    fig.add_vline(x=0, line_color="gray", line_width=1)

    # Add quadrant labels
    annotations = [
        dict(x=0, y=4.5, text="Acceleration", showarrow=False, font=dict(size=10, color="gray")),
        dict(x=0, y=-4.5, text="Braking", showarrow=False, font=dict(size=10, color="gray")),
        dict(
            x=-4.5,
            y=0,
            text="Right",
            showarrow=False,
            font=dict(size=10, color="gray"),
            textangle=-90,
        ),
        dict(
            x=4.5,
            y=0,
            text="Left",
            showarrow=False,
            font=dict(size=10, color="gray"),
            textangle=-90,
        ),
    ]

    fig.update_layout(
        title=f"G-G Diagram ({driver1_name} vs {driver2_name})",
        xaxis_title="Lateral Acceleration (g)",
        yaxis_title="Longitudinal Acceleration (g)",
        template=config.plot_theme,
        width=config.plot_width,
        height=config.plot_width,  # Square aspect ratio
        xaxis=dict(range=[-5, 5], scaleanchor="y", scaleratio=1),
        yaxis=dict(range=[-5, 5]),
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
        annotations=annotations,
    )

    return fig


def create_acceleration_heatmap(
    telemetry: pd.DataFrame,
    driver_name: str,
    config: Config = DEFAULT_CONFIG,
) -> go.Figure:
    """
    Create 2D histogram heatmap of acceleration distribution.

    Args:
        telemetry: Telemetry DataFrame
        driver_name: Name of driver
        config: Configuration for plot styling

    Returns:
        Plotly figure with heatmap
    """
    accel = compute_accelerations(telemetry, config)

    ax_g = accel.ax / GRAVITY
    ay_g = accel.ay / GRAVITY

    fig = go.Figure()

    fig.add_trace(
        go.Histogram2d(
            x=ay_g,
            y=ax_g,
            nbinsx=50,
            nbinsy=50,
            colorscale="Hot",
            showscale=True,
            colorbar=dict(title="Count"),
        )
    )

    # Add axis lines
    fig.add_hline(y=0, line_color="white", line_width=1)
    fig.add_vline(x=0, line_color="white", line_width=1)

    fig.update_layout(
        title=f"Acceleration Heatmap ({driver_name})",
        xaxis_title="Lateral Acceleration (g)",
        yaxis_title="Longitudinal Acceleration (g)",
        template=config.plot_theme,
        width=config.plot_width,
        height=config.plot_width,
        xaxis=dict(range=[-5, 5]),
        yaxis=dict(range=[-5, 5]),
    )

    return fig


def create_combined_g_force_plot(
    telemetry1: pd.DataFrame,
    telemetry2: pd.DataFrame,
    driver1_name: str,
    driver2_name: str,
    config: Config = DEFAULT_CONFIG,
) -> go.Figure:
    """
    Create plot of combined g-force vs distance.

    Shows total grip utilization around the lap.

    Args:
        telemetry1: Telemetry for driver 1
        telemetry2: Telemetry for driver 2
        driver1_name: Name/code for driver 1
        driver2_name: Name/code for driver 2
        config: Configuration for plot styling

    Returns:
        Plotly figure
    """
    accel1 = compute_accelerations(telemetry1, config)
    accel2 = compute_accelerations(telemetry2, config)

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=accel1.distance,
            y=accel1.combined_g,
            mode="lines",
            line=dict(color="#FF1E1E", width=2),
            name=driver1_name,
        )
    )

    fig.add_trace(
        go.Scatter(
            x=accel2.distance,
            y=accel2.combined_g,
            mode="lines",
            line=dict(color="#1E90FF", width=2),
            name=driver2_name,
        )
    )

    # Add reference lines for g-force levels
    for g_level in [1, 2, 3, 4]:
        fig.add_hline(
            y=g_level,
            line_dash="dot",
            line_color="gray",
            line_width=1,
            annotation_text=f"{g_level}g",
            annotation_position="right",
        )

    fig.update_layout(
        title=f"Combined G-Force vs Distance ({driver1_name} vs {driver2_name})",
        xaxis_title="Distance (m)",
        yaxis_title="Combined G-Force (g)",
        template=config.plot_theme,
        width=config.plot_width,
        height=config.plot_height,
        hovermode="x unified",
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
    )

    return fig


def analyze_grip_utilization(accel_data: AccelerationData) -> dict:
    """
    Analyze grip utilization statistics.

    Args:
        accel_data: AccelerationData object

    Returns:
        Dictionary with utilization statistics
    """
    ax_g = accel_data.ax / GRAVITY
    ay_g = accel_data.ay / GRAVITY

    return {
        "max_longitudinal_accel_g": float(np.max(ax_g)),
        "max_longitudinal_decel_g": float(np.min(ax_g)),
        "max_lateral_accel_g": float(np.max(np.abs(ay_g))),
        "max_combined_g": float(np.max(accel_data.combined_g)),
        "avg_combined_g": float(np.mean(accel_data.combined_g)),
        "percent_time_braking": float(np.sum(accel_data.brake_mask) / len(ax_g) * 100),
        "percent_time_accelerating": float(np.sum(accel_data.traction_mask) / len(ax_g) * 100),
        "percent_time_high_lateral": float(np.sum(accel_data.cornering_mask) / len(ay_g) * 100),
    }
