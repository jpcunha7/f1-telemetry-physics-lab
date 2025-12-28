"""
Corner detection and analysis module for F1 Telemetry Physics Lab.

Detects corners from telemetry and creates detailed corner catalogs with
entry speed, minimum speed, exit speed, braking distances, and performance metrics.

Uses FastF1 circuit information when available to provide accurate corner data for all tracks.

Author: João Pedro Cunha
"""

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy.signal import find_peaks

from f1telemetry.config import Config, DEFAULT_CONFIG
from f1telemetry.physics import smooth_signal

logger = logging.getLogger(__name__)


@dataclass
class Corner:
    """Detailed information about a detected corner.

    Attributes:
        corner_id: Sequential corner number (1, 2, 3...)
        apex_idx: Index in telemetry array of apex (minimum speed point)
        apex_distance: Distance at apex (m)
        entry_idx: Index where braking starts
        entry_distance: Distance where braking starts (m)
        exit_idx: Index where full throttle is reapplied
        exit_distance: Distance where full throttle is reapplied (m)
        entry_speed: Speed at braking point (km/h)
        min_speed: Minimum speed at apex (km/h)
        exit_speed: Speed at throttle reapply point (km/h)
        brake_start_distance: Distance where brake is first applied (m)
        brake_distance: Total braking distance (m)
        peak_deceleration: Maximum deceleration in corner (m/s², negative)
        throttle_reapply_distance: Distance from apex to full throttle (m)
        corner_type: Classification based on speed ('slow', 'medium', 'fast')
    """

    corner_id: int
    apex_idx: int
    apex_distance: float
    entry_idx: int
    entry_distance: float
    exit_idx: int
    exit_distance: float
    entry_speed: float
    min_speed: float
    exit_speed: float
    brake_start_distance: float
    brake_distance: float
    peak_deceleration: float
    throttle_reapply_distance: float
    corner_type: str


def get_circuit_corners(
    session, telemetry: pd.DataFrame, config: Config = DEFAULT_CONFIG
) -> list[Corner]:
    """
    Get corners from FastF1 circuit information and match them with telemetry data.

    This provides accurate corner data for all corners on the circuit, using the
    circuit's official corner information from FastF1.

    Args:
        session: FastF1 Session object
        telemetry: Telemetry DataFrame with Speed, Distance, Brake, Throttle
        config: Configuration object

    Returns:
        List of Corner objects with telemetry-based metrics for each circuit corner
    """
    try:
        # Get circuit info from session using get_circuit_info() method
        circuit_info = session.get_circuit_info()

        if circuit_info is None:
            logger.warning("Circuit info not available, falling back to telemetry-based detection")
            return detect_corners(telemetry, config=config)

        # Check if corners data is available
        if (
            not hasattr(circuit_info, "corners")
            or circuit_info.corners is None
            or circuit_info.corners.empty
        ):
            logger.warning(
                "Circuit corners data not available, falling back to telemetry-based detection"
            )
            return detect_corners(telemetry, config=config)

        corners_df = circuit_info.corners
        logger.info(f"Found {len(corners_df)} corners from circuit info")

        # Extract required data from telemetry
        speed = telemetry["Speed"].values
        distance = telemetry["Distance"].values

        has_brake = "Brake" in telemetry.columns
        has_throttle = "Throttle" in telemetry.columns
        has_accel = "Acceleration" in telemetry.columns

        brake = telemetry["Brake"].values if has_brake else np.zeros_like(speed)
        throttle = telemetry["Throttle"].values if has_throttle else np.zeros_like(speed)
        acceleration = telemetry["Acceleration"].values if has_accel else np.zeros_like(speed)

        corners = []

        # Process each corner from circuit info
        for idx, corner_row in corners_df.iterrows():
            corner_num = int(corner_row["Number"])
            corner_distance = corner_row.get("Distance", None)

            # If Distance is not available in circuit info, try to find corner by position
            if pd.isna(corner_distance) or corner_distance is None:
                # Skip corners without distance information
                logger.debug(f"Corner {corner_num} has no distance information, skipping")
                continue

            # Find closest telemetry point to corner distance
            apex_idx = np.argmin(np.abs(distance - corner_distance))

            # Ensure we're at a local minimum in speed (apex)
            # Search within a window around the distance-based position
            search_window = 50  # samples
            start_idx = max(0, apex_idx - search_window)
            end_idx = min(len(speed), apex_idx + search_window)

            # Find local minimum speed in this window
            window_speeds = speed[start_idx:end_idx]
            if len(window_speeds) > 0:
                min_speed_offset = np.argmin(window_speeds)
                apex_idx = start_idx + min_speed_offset

            try:
                # Analyze corner characteristics
                corner = _analyze_corner(
                    corner_id=corner_num,
                    apex_idx=apex_idx,
                    distance=distance,
                    speed=speed,
                    brake=brake,
                    throttle=throttle,
                    acceleration=acceleration,
                    config=config,
                )
                corners.append(corner)

            except Exception as e:
                logger.warning(f"Failed to analyze corner {corner_num}: {e}")
                continue

        # Sort corners by corner_id to maintain proper order
        corners.sort(key=lambda c: c.corner_id)

        logger.info(f"Successfully analyzed {len(corners)} corners from circuit info")
        return corners

    except Exception as e:
        logger.error(f"Error getting circuit corners: {e}", exc_info=True)
        logger.warning("Falling back to telemetry-based corner detection")
        return detect_corners(telemetry, config=config)


def detect_corners(
    telemetry: pd.DataFrame,
    min_speed_threshold: float = 100.0,
    config: Config = DEFAULT_CONFIG,
) -> list[Corner]:
    """
    Detect corners from telemetry using speed local minima.

    Corners are identified as local minima in speed where the speed drops below
    a threshold. For each corner, we analyze the braking phase, apex, and exit
    to extract detailed performance metrics.

    Detection algorithm:
    1. Smooth speed signal to reduce noise
    2. Find local minima using peak detection on inverted signal
    3. Filter by minimum speed threshold and prominence
    4. For each minimum, search backward for brake onset and forward for throttle reapply
    5. Extract all relevant metrics

    Args:
        telemetry: Telemetry DataFrame with Speed, Distance, Brake, Throttle, Acceleration
        min_speed_threshold: Only consider corners with min speed below this (km/h)
        config: Configuration object

    Returns:
        List of Corner objects sorted by distance

    Raises:
        ValueError: If required telemetry channels are missing
    """
    required_cols = ["Speed", "Distance"]
    missing = [col for col in required_cols if col not in telemetry.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    speed = telemetry["Speed"].values
    distance = telemetry["Distance"].values

    # Optional channels
    has_brake = "Brake" in telemetry.columns
    has_throttle = "Throttle" in telemetry.columns
    has_accel = "Acceleration" in telemetry.columns

    brake = telemetry["Brake"].values if has_brake else np.zeros_like(speed)
    throttle = telemetry["Throttle"].values if has_throttle else np.zeros_like(speed)
    acceleration = telemetry["Acceleration"].values if has_accel else np.zeros_like(speed)

    # Smooth speed for robust peak detection
    speed_smooth = smooth_signal(speed, config.smoothing_window, config.smoothing_polyorder)

    # Find local minima in speed (corners/apex points)
    # Use prominence to filter out small speed variations
    minima_indices, properties = find_peaks(
        -speed_smooth,  # Invert for minima detection
        prominence=config.corner_prominence,  # Require drop from surrounding speeds
        distance=config.corner_min_distance,  # Minimum samples between corners
        height=-min_speed_threshold,  # Maximum speed at apex
    )

    if len(minima_indices) == 0:
        logger.warning("No corners detected in telemetry")
        return []

    logger.info(f"Detected {len(minima_indices)} potential corners")

    corners = []

    for corner_num, apex_idx in enumerate(minima_indices, start=1):
        try:
            # Extract corner characteristics
            corner = _analyze_corner(
                corner_id=corner_num,
                apex_idx=apex_idx,
                distance=distance,
                speed=speed,
                brake=brake,
                throttle=throttle,
                acceleration=acceleration,
                config=config,
            )
            corners.append(corner)

        except Exception as e:
            logger.warning(f"Failed to analyze corner {corner_num} at idx {apex_idx}: {e}")
            continue

    logger.info(f"Successfully analyzed {len(corners)} corners")
    return corners


def _analyze_corner(
    corner_id: int,
    apex_idx: int,
    distance: np.ndarray,
    speed: np.ndarray,
    brake: np.ndarray,
    throttle: np.ndarray,
    acceleration: np.ndarray,
    config: Config,
) -> Corner:
    """
    Analyze a single corner in detail.

    Args:
        corner_id: Corner number
        apex_idx: Index of apex in arrays
        distance: Distance array
        speed: Speed array
        brake: Brake array
        throttle: Throttle array
        acceleration: Acceleration array
        config: Configuration

    Returns:
        Corner object with all metrics
    """
    # Apex metrics
    apex_distance = float(distance[apex_idx])
    min_speed = float(speed[apex_idx])

    # Search window sizes
    lookback_max = min(100, apex_idx)  # Look back up to 100 samples
    lookforward_max = min(100, len(speed) - apex_idx - 1)

    # Find entry point (where braking starts)
    # Search backward from apex for significant brake application
    entry_idx = apex_idx
    brake_threshold = config.brake_threshold

    for i in range(apex_idx - 1, apex_idx - lookback_max, -1):
        if brake[i] < brake_threshold and brake[i + 1] >= brake_threshold:
            # Found transition to braking
            entry_idx = i + 1
            break

    # Find exit point (where full throttle is reapplied)
    # Search forward from apex for throttle > 95%
    exit_idx = apex_idx
    throttle_threshold = 95.0

    for i in range(apex_idx + 1, apex_idx + lookforward_max):
        if throttle[i] >= throttle_threshold:
            exit_idx = i
            break

    # Extract metrics at key points
    entry_distance = float(distance[entry_idx])
    entry_speed = float(speed[entry_idx])
    exit_distance = float(distance[exit_idx])
    exit_speed = float(speed[exit_idx])

    # Braking metrics
    brake_start_distance = entry_distance
    brake_distance = apex_distance - entry_distance

    # Find peak deceleration in braking zone
    braking_zone_accel = acceleration[entry_idx:apex_idx]
    peak_deceleration = float(np.min(braking_zone_accel)) if len(braking_zone_accel) > 0 else 0.0

    # Exit metrics
    throttle_reapply_distance = exit_distance - apex_distance

    # Classify corner by minimum speed
    if min_speed < 80:
        corner_type = "slow"
    elif min_speed < 150:
        corner_type = "medium"
    else:
        corner_type = "fast"

    return Corner(
        corner_id=corner_id,
        apex_idx=apex_idx,
        apex_distance=apex_distance,
        entry_idx=entry_idx,
        entry_distance=entry_distance,
        exit_idx=exit_idx,
        exit_distance=exit_distance,
        entry_speed=entry_speed,
        min_speed=min_speed,
        exit_speed=exit_speed,
        brake_start_distance=brake_start_distance,
        brake_distance=brake_distance,
        peak_deceleration=peak_deceleration,
        throttle_reapply_distance=throttle_reapply_distance,
        corner_type=corner_type,
    )


def analyze_corner_comparison(corner1: Corner, corner2: Corner) -> dict:
    """
    Compare two corners and compute deltas.

    Args:
        corner1: Corner from driver 1
        corner2: Corner from driver 2

    Returns:
        Dictionary with comparison metrics
    """
    return {
        "corner_id": corner1.corner_id,
        "entry_speed_delta": corner1.entry_speed - corner2.entry_speed,
        "min_speed_delta": corner1.min_speed - corner2.min_speed,
        "exit_speed_delta": corner1.exit_speed - corner2.exit_speed,
        "brake_distance_delta": corner1.brake_distance - corner2.brake_distance,
        "peak_decel_delta": corner1.peak_deceleration - corner2.peak_deceleration,
        "throttle_distance_delta": corner1.throttle_reapply_distance
        - corner2.throttle_reapply_distance,
    }


def create_corner_report_table(
    corners1: list[Corner],
    corners2: list[Corner],
    driver1_name: str,
    driver2_name: str,
) -> pd.DataFrame:
    """
    Create comprehensive corner comparison table.

    Args:
        corners1: Corners from driver 1
        corners2: Corners from driver 2
        driver1_name: Name/code for driver 1
        driver2_name: Name/code for driver 2

    Returns:
        DataFrame with corner-by-corner comparison
    """
    # Match corners by proximity (should be aligned if using same track)
    min_corners = min(len(corners1), len(corners2))

    if len(corners1) != len(corners2):
        logger.warning(
            f"Corner count mismatch: {driver1_name}={len(corners1)}, "
            f"{driver2_name}={len(corners2)}. Using first {min_corners} corners."
        )

    rows = []

    for i in range(min_corners):
        c1 = corners1[i]
        c2 = corners2[i]

        row = {
            "Corner": c1.corner_id,
            "Type": c1.corner_type,
            "Distance": int(c1.apex_distance),
            f"{driver1_name}_Entry_Speed": round(c1.entry_speed, 1),
            f"{driver2_name}_Entry_Speed": round(c2.entry_speed, 1),
            "Entry_Delta": round(c1.entry_speed - c2.entry_speed, 1),
            f"{driver1_name}_Min_Speed": round(c1.min_speed, 1),
            f"{driver2_name}_Min_Speed": round(c2.min_speed, 1),
            "Min_Delta": round(c1.min_speed - c2.min_speed, 1),
            f"{driver1_name}_Exit_Speed": round(c1.exit_speed, 1),
            f"{driver2_name}_Exit_Speed": round(c2.exit_speed, 1),
            "Exit_Delta": round(c1.exit_speed - c2.exit_speed, 1),
            f"{driver1_name}_Brake_Dist": round(c1.brake_distance, 1),
            f"{driver2_name}_Brake_Dist": round(c2.brake_distance, 1),
            "Brake_Dist_Delta": round(c1.brake_distance - c2.brake_distance, 1),
        }
        rows.append(row)

    return pd.DataFrame(rows)


def create_corner_markers_map(
    telemetry: pd.DataFrame,
    corners: list[Corner],
    driver_name: str,
    config: Config = DEFAULT_CONFIG,
) -> go.Figure:
    """
    Create track map with corner markers and labels.

    Args:
        telemetry: Telemetry DataFrame with X, Y, Distance
        corners: List of Corner objects
        driver_name: Name of driver
        config: Configuration for plot styling

    Returns:
        Plotly figure with track map and corner markers

    Raises:
        ValueError: If position data is not available
    """
    if "X" not in telemetry.columns or "Y" not in telemetry.columns:
        raise ValueError("Position data (X, Y) not available in telemetry")

    fig = go.Figure()

    # Plot track line
    fig.add_trace(
        go.Scatter(
            x=telemetry["X"],
            y=telemetry["Y"],
            mode="lines",
            line=dict(color="gray", width=2),
            name="Track",
            showlegend=False,
        )
    )

    # Add corner markers
    corner_x = []
    corner_y = []
    corner_labels = []
    corner_colors = []

    color_map = {"slow": "#FF1E1E", "medium": "#FFA500", "fast": "#00FF00"}

    for corner in corners:
        x_val = telemetry.iloc[corner.apex_idx]["X"]
        y_val = telemetry.iloc[corner.apex_idx]["Y"]

        corner_x.append(x_val)
        corner_y.append(y_val)
        corner_labels.append(f"C{corner.corner_id}")
        corner_colors.append(color_map.get(corner.corner_type, "white"))

    fig.add_trace(
        go.Scatter(
            x=corner_x,
            y=corner_y,
            mode="markers+text",
            marker=dict(size=12, color=corner_colors, line=dict(width=2, color="white")),
            text=corner_labels,
            textposition="top center",
            textfont=dict(size=10, color="white"),
            name="Corners",
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Min Speed: %{customdata[0]:.1f} km/h<br>"
                "Entry: %{customdata[1]:.1f} km/h<br>"
                "Exit: %{customdata[2]:.1f} km/h<br>"
                "Type: %{customdata[3]}<br>"
                "<extra></extra>"
            ),
            customdata=np.array(
                [[c.min_speed, c.entry_speed, c.exit_speed, c.corner_type] for c in corners]
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
        title=f"Track Map with Corner Catalog ({driver_name})",
        template=config.plot_theme,
        width=config.plot_width,
        height=config.plot_height,
        annotations=[
            dict(
                x=0.02,
                y=0.98,
                xref="paper",
                yref="paper",
                text="Red = Slow | Orange = Medium | Green = Fast",
                showarrow=False,
                bgcolor="rgba(0,0,0,0.5)",
                font=dict(size=10),
                align="left",
            )
        ],
    )

    return fig


def create_corner_speed_profile(
    telemetry: pd.DataFrame,
    corner: Corner,
    driver_name: str,
    config: Config = DEFAULT_CONFIG,
) -> go.Figure:
    """
    Create detailed speed profile for a single corner.

    Args:
        telemetry: Telemetry DataFrame
        corner: Corner object to analyze
        driver_name: Name of driver
        config: Configuration for plot styling

    Returns:
        Plotly figure showing corner speed profile with phases
    """
    # Extract data around corner
    start_idx = max(0, corner.entry_idx - 20)
    end_idx = min(len(telemetry), corner.exit_idx + 20)

    corner_data = telemetry.iloc[start_idx:end_idx].copy()

    fig = go.Figure()

    # Speed trace
    fig.add_trace(
        go.Scatter(
            x=corner_data["Distance"],
            y=corner_data["Speed"],
            mode="lines",
            line=dict(color="#1E90FF", width=3),
            name="Speed",
        )
    )

    # Mark key points
    # Entry point
    fig.add_vline(
        x=corner.entry_distance,
        line_dash="dash",
        line_color="#FF1E1E",
        annotation_text=f"Entry: {corner.entry_speed:.0f} km/h",
        annotation_position="top left",
    )

    # Apex
    fig.add_vline(
        x=corner.apex_distance,
        line_dash="solid",
        line_color="#00FF00",
        annotation_text=f"Apex: {corner.min_speed:.0f} km/h",
        annotation_position="top",
    )

    # Exit
    fig.add_vline(
        x=corner.exit_distance,
        line_dash="dash",
        line_color="#FFA500",
        annotation_text=f"Exit: {corner.exit_speed:.0f} km/h",
        annotation_position="top right",
    )

    fig.update_layout(
        title=f"Corner {corner.corner_id} Speed Profile ({driver_name})",
        xaxis_title="Distance (m)",
        yaxis_title="Speed (km/h)",
        template=config.plot_theme,
        width=config.plot_width,
        height=config.plot_height,
        hovermode="x unified",
    )

    return fig
