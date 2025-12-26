"""
Delta decomposition module for F1 Telemetry Physics Lab.

Decomposes time deltas into contributing factors: braking, mid-corner, and traction phases.
Provides transparent, physics-based attribution of time gains/losses.

Author: João Pedro Cunha
"""

import logging
from dataclasses import dataclass
from typing import Literal

import pandas as pd
import plotly.graph_objects as go

from f1telemetry.config import Config, DEFAULT_CONFIG
from f1telemetry.corners import Corner

logger = logging.getLogger(__name__)

DeltaPhase = Literal["braking", "mid_corner", "traction", "neutral"]


@dataclass
class CornerDecomposition:
    """Delta decomposition for a single corner.

    Attributes:
        corner_id: Corner number
        total_delta: Total time delta in corner (s), positive = driver1 slower
        braking_contribution: Time lost/gained in braking phase (s)
        mid_corner_contribution: Time lost/gained at apex/minimum speed (s)
        traction_contribution: Time lost/gained in exit/acceleration phase (s)
        dominant_phase: Which phase contributes most to the delta
        braking_quality: Qualitative assessment ('earlier', 'later', 'deeper', 'similar')
        mid_corner_quality: Qualitative assessment ('faster', 'slower', 'similar')
        traction_quality: Qualitative assessment ('better', 'worse', 'similar')
    """

    corner_id: int
    total_delta: float
    braking_contribution: float
    mid_corner_contribution: float
    traction_contribution: float
    dominant_phase: DeltaPhase
    braking_quality: str
    mid_corner_quality: str
    traction_quality: str


def decompose_corner_delta(
    corner1: Corner,
    corner2: Corner,
    telemetry1: pd.DataFrame,
    telemetry2: pd.DataFrame,
) -> CornerDecomposition:
    """
    Decompose time delta for a corner into contributing phases.

    Physics methodology:
    1. Braking phase: From brake onset to apex
       - Earlier braking = more time lost
       - Higher entry speed = potential time gain if maintained
    2. Mid-corner: At apex (minimum speed point)
       - Higher minimum speed = less time in slow phase
    3. Traction/Exit: From apex to full throttle
       - Earlier throttle application = time gain
       - Better exit speed = time gain

    Approximations:
    - Time in phase ≈ distance / average_speed
    - Delta = time1 - time2

    Args:
        corner1: Corner from driver 1
        corner2: Corner from driver 2
        telemetry1: Full telemetry from driver 1
        telemetry2: Full telemetry from driver 2

    Returns:
        CornerDecomposition object with phase-by-phase analysis
    """
    # BRAKING PHASE ANALYSIS
    # Time from entry to apex for each driver
    brake_dist_1 = corner1.brake_distance
    brake_dist_2 = corner2.brake_distance

    # Average speed in braking zone
    avg_speed_braking_1 = (corner1.entry_speed + corner1.min_speed) / 2
    avg_speed_braking_2 = (corner2.entry_speed + corner2.min_speed) / 2

    # Time in braking (convert speed from km/h to m/s)
    time_braking_1 = brake_dist_1 / (avg_speed_braking_1 / 3.6 + 0.01)
    time_braking_2 = brake_dist_2 / (avg_speed_braking_2 / 3.6 + 0.01)

    braking_delta = time_braking_1 - time_braking_2

    # MID-CORNER PHASE ANALYSIS
    # At apex, higher minimum speed means less time in slow phase
    # Approximate time impact using speed difference
    # Assumption: ~20m around apex at minimum speed
    apex_distance = 20.0  # meters

    time_apex_1 = apex_distance / (corner1.min_speed / 3.6 + 0.01)
    time_apex_2 = apex_distance / (corner2.min_speed / 3.6 + 0.01)

    mid_corner_delta = time_apex_1 - time_apex_2

    # TRACTION/EXIT PHASE ANALYSIS
    # Time from apex to full throttle
    traction_dist_1 = corner1.throttle_reapply_distance
    traction_dist_2 = corner2.throttle_reapply_distance

    avg_speed_traction_1 = (corner1.min_speed + corner1.exit_speed) / 2
    avg_speed_traction_2 = (corner2.min_speed + corner2.exit_speed) / 2

    time_traction_1 = traction_dist_1 / (avg_speed_traction_1 / 3.6 + 0.01)
    time_traction_2 = traction_dist_2 / (avg_speed_traction_2 / 3.6 + 0.01)

    traction_delta = time_traction_1 - time_traction_2

    # Total delta (may not sum exactly due to approximations)
    total_delta = braking_delta + mid_corner_delta + traction_delta

    # Determine dominant phase
    contributions = {
        "braking": abs(braking_delta),
        "mid_corner": abs(mid_corner_delta),
        "traction": abs(traction_delta),
    }

    dominant_phase: DeltaPhase = max(contributions, key=contributions.get)  # type: ignore

    # If all contributions are small, mark as neutral
    if max(contributions.values()) < 0.01:
        dominant_phase = "neutral"

    # Qualitative assessments
    braking_quality = _assess_braking(corner1, corner2)
    mid_corner_quality = _assess_mid_corner(corner1, corner2)
    traction_quality = _assess_traction(corner1, corner2)

    return CornerDecomposition(
        corner_id=corner1.corner_id,
        total_delta=total_delta,
        braking_contribution=braking_delta,
        mid_corner_contribution=mid_corner_delta,
        traction_contribution=traction_delta,
        dominant_phase=dominant_phase,
        braking_quality=braking_quality,
        mid_corner_quality=mid_corner_quality,
        traction_quality=traction_quality,
    )


def _assess_braking(corner1: Corner, corner2: Corner) -> str:
    """Assess braking phase quality."""
    brake_dist_diff = corner1.brake_distance - corner2.brake_distance
    entry_speed_diff = corner1.entry_speed - corner2.entry_speed

    if brake_dist_diff > 5:
        return "earlier_braking"
    elif brake_dist_diff < -5:
        return "later_braking"
    elif entry_speed_diff > 3:
        return "higher_entry"
    elif entry_speed_diff < -3:
        return "lower_entry"
    else:
        return "similar"


def _assess_mid_corner(corner1: Corner, corner2: Corner) -> str:
    """Assess mid-corner phase quality."""
    min_speed_diff = corner1.min_speed - corner2.min_speed

    if min_speed_diff > 2:
        return "faster_apex"
    elif min_speed_diff < -2:
        return "slower_apex"
    else:
        return "similar"


def _assess_traction(corner1: Corner, corner2: Corner) -> str:
    """Assess traction/exit phase quality."""
    exit_speed_diff = corner1.exit_speed - corner2.exit_speed
    throttle_dist_diff = corner1.throttle_reapply_distance - corner2.throttle_reapply_distance

    if exit_speed_diff > 3:
        return "better_exit"
    elif exit_speed_diff < -3:
        return "worse_exit"
    elif throttle_dist_diff < -5:
        return "earlier_throttle"
    elif throttle_dist_diff > 5:
        return "later_throttle"
    else:
        return "similar"


def assign_dominant_cause(decomposition: CornerDecomposition) -> str:
    """
    Assign human-readable dominant cause label.

    Args:
        decomposition: CornerDecomposition object

    Returns:
        String describing dominant cause of time delta
    """
    phase = decomposition.dominant_phase

    if phase == "braking":
        return f"Braking ({decomposition.braking_quality})"
    elif phase == "mid_corner":
        return f"Mid-corner ({decomposition.mid_corner_quality})"
    elif phase == "traction":
        return f"Traction ({decomposition.traction_quality})"
    else:
        return "Neutral (minimal difference)"


def create_decomposition_table(
    decompositions: list[CornerDecomposition],
    driver1_name: str,
    driver2_name: str,
) -> pd.DataFrame:
    """
    Create table showing delta decomposition for all corners.

    Args:
        decompositions: List of CornerDecomposition objects
        driver1_name: Name/code for driver 1
        driver2_name: Name/code for driver 2

    Returns:
        DataFrame with decomposition analysis
    """
    rows = []

    for decomp in decompositions:
        row = {
            "Corner": decomp.corner_id,
            "Total_Delta_s": round(decomp.total_delta, 3),
            "Braking_Delta_s": round(decomp.braking_contribution, 3),
            "Mid_Corner_Delta_s": round(decomp.mid_corner_contribution, 3),
            "Traction_Delta_s": round(decomp.traction_contribution, 3),
            "Dominant_Phase": decomp.dominant_phase,
            "Primary_Cause": assign_dominant_cause(decomp),
            "Braking_Assessment": decomp.braking_quality,
            "Mid_Corner_Assessment": decomp.mid_corner_quality,
            "Traction_Assessment": decomp.traction_quality,
        }
        rows.append(row)

    df = pd.DataFrame(rows)

    # Add summary row
    summary = {
        "Corner": "TOTAL",
        "Total_Delta_s": round(df["Total_Delta_s"].sum(), 3),
        "Braking_Delta_s": round(df["Braking_Delta_s"].sum(), 3),
        "Mid_Corner_Delta_s": round(df["Mid_Corner_Delta_s"].sum(), 3),
        "Traction_Delta_s": round(df["Traction_Delta_s"].sum(), 3),
        "Dominant_Phase": "-",
        "Primary_Cause": "-",
        "Braking_Assessment": "-",
        "Mid_Corner_Assessment": "-",
        "Traction_Assessment": "-",
    }

    df = pd.concat([df, pd.DataFrame([summary])], ignore_index=True)

    return df


def create_decomposition_waterfall(
    decompositions: list[CornerDecomposition],
    driver1_name: str,
    driver2_name: str,
    config: Config = DEFAULT_CONFIG,
) -> go.Figure:
    """
    Create waterfall chart showing cumulative delta decomposition.

    Args:
        decompositions: List of CornerDecomposition objects
        driver1_name: Name/code for driver 1
        driver2_name: Name/code for driver 2
        config: Configuration for plot styling

    Returns:
        Plotly waterfall figure
    """
    # Aggregate contributions by phase across all corners
    total_braking = sum(d.braking_contribution for d in decompositions)
    total_mid = sum(d.mid_corner_contribution for d in decompositions)
    total_traction = sum(d.traction_contribution for d in decompositions)
    total_delta = total_braking + total_mid + total_traction

    # Create waterfall chart
    fig = go.Figure(
        go.Waterfall(
            name="Delta Breakdown",
            orientation="v",
            measure=["relative", "relative", "relative", "total"],
            x=["Braking Phase", "Mid-Corner Phase", "Traction Phase", "Total Delta"],
            y=[total_braking, total_mid, total_traction, total_delta],
            text=[
                f"{total_braking:+.3f}s",
                f"{total_mid:+.3f}s",
                f"{total_traction:+.3f}s",
                f"{total_delta:+.3f}s",
            ],
            textposition="outside",
            connector={"line": {"color": "gray"}},
            decreasing={"marker": {"color": "#1E90FF"}},
            increasing={"marker": {"color": "#FF1E1E"}},
            totals={"marker": {"color": "#FFD700"}},
        )
    )

    fig.update_layout(
        title=f"Delta Decomposition Waterfall ({driver1_name} vs {driver2_name})",
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


def create_phase_contribution_bar(
    decompositions: list[CornerDecomposition],
    driver1_name: str,
    driver2_name: str,
    config: Config = DEFAULT_CONFIG,
) -> go.Figure:
    """
    Create stacked bar chart showing phase contributions per corner.

    Args:
        decompositions: List of CornerDecomposition objects
        driver1_name: Name/code for driver 1
        driver2_name: Name/code for driver 2
        config: Configuration for plot styling

    Returns:
        Plotly figure with stacked bars
    """
    corner_ids = [d.corner_id for d in decompositions]
    braking = [d.braking_contribution for d in decompositions]
    mid_corner = [d.mid_corner_contribution for d in decompositions]
    traction = [d.traction_contribution for d in decompositions]

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            name="Braking",
            x=corner_ids,
            y=braking,
            marker_color="#FF6B6B",
        )
    )

    fig.add_trace(
        go.Bar(
            name="Mid-Corner",
            x=corner_ids,
            y=mid_corner,
            marker_color="#4ECDC4",
        )
    )

    fig.add_trace(
        go.Bar(
            name="Traction",
            x=corner_ids,
            y=traction,
            marker_color="#95E1D3",
        )
    )

    fig.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1)

    fig.update_layout(
        title=f"Delta Decomposition by Corner ({driver1_name} vs {driver2_name})",
        xaxis_title="Corner Number",
        yaxis_title="Time Delta Contribution (s)",
        template=config.plot_theme,
        width=config.plot_width,
        height=config.plot_height,
        barmode="stack",
        hovermode="x unified",
        legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99),
    )

    return fig


def analyze_weakness_pattern(decompositions: list[CornerDecomposition]) -> dict:
    """
    Analyze patterns in weaknesses across corners.

    Args:
        decompositions: List of CornerDecomposition objects

    Returns:
        Dictionary with pattern analysis
    """
    phase_counts = {"braking": 0, "mid_corner": 0, "traction": 0, "neutral": 0}
    phase_deltas = {"braking": 0.0, "mid_corner": 0.0, "traction": 0.0}

    for decomp in decompositions:
        phase_counts[decomp.dominant_phase] += 1
        phase_deltas["braking"] += decomp.braking_contribution
        phase_deltas["mid_corner"] += decomp.mid_corner_contribution
        phase_deltas["traction"] += decomp.traction_contribution

    total_corners = len(decompositions)

    return {
        "dominant_phase_counts": phase_counts,
        "phase_percentages": {
            phase: (count / total_corners * 100) if total_corners > 0 else 0
            for phase, count in phase_counts.items()
        },
        "phase_total_deltas": phase_deltas,
        "primary_weakness": max(phase_deltas, key=lambda k: abs(phase_deltas[k])),
    }
