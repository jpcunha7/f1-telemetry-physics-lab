"""
Insight summary component.

Generates and displays a deterministic, data-driven insight summary.

Author: João Pedro Cunha
"""

import streamlit as st
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np


def generate_insight_summary(
    comparison_summary: Dict[str, Any],
    minisector_data: Optional[pd.DataFrame],
    corners1: Optional[List[Any]],
    corners2: Optional[List[Any]],
    decompositions: Optional[List[Any]],
    driver1_name: str,
    driver2_name: str,
) -> Dict[str, Any]:
    """
    Generate comprehensive insight summary from analysis data.

    Args:
        comparison_summary: Comparison summary dictionary
        minisector_data: Minisector delta data (deprecated, not used)
        corners1: Corner data for driver 1
        corners2: Corner data for driver 2
        decompositions: Corner delta decompositions
        driver1_name: Driver 1 name
        driver2_name: Driver 2 name

    Returns:
        Dictionary with insights
    """
    insights = {
        "total_delta": comparison_summary["final_delta"],
        "faster_driver": driver1_name if comparison_summary["final_delta"] < 0 else driver2_name,
        "top_locations": [],
        "sector_breakdown": {},
        "breakdown": {},
        "key_findings": [],
    }

    # Sector-based analysis (3 sectors in F1)
    # We'll divide the lap into 3 sectors based on track distance
    if "delta_time" in comparison_summary and len(comparison_summary["delta_time"]) > 0:
        total_distance = len(comparison_summary["delta_time"])
        sector_size = total_distance // 3

        sectors_info = []
        for sector_num in range(3):
            start_idx = sector_num * sector_size
            end_idx = (sector_num + 1) * sector_size if sector_num < 2 else total_distance

            sector_deltas = comparison_summary["delta_time"][start_idx:end_idx]
            sector_delta = sector_deltas[-1] - sector_deltas[0] if len(sector_deltas) > 0 else 0

            sectors_info.append(
                {
                    "sector": f"Sector {sector_num + 1}",
                    "delta": sector_delta,
                    "favoring": driver1_name if sector_delta < 0 else driver2_name,
                }
            )
            insights["sector_breakdown"][f"Sector {sector_num + 1}"] = sector_delta

        # Add top sectors to top_locations
        sectors_sorted = sorted(sectors_info, key=lambda x: abs(x["delta"]), reverse=True)
        for sector_info in sectors_sorted:
            insights["top_locations"].append(sector_info)

    # Breakdown: braking vs corner vs traction
    if decompositions:
        total_braking = sum(d.braking_contribution for d in decompositions)
        total_corner = sum(d.mid_corner_contribution for d in decompositions)
        total_traction = sum(d.traction_contribution for d in decompositions)

        insights["breakdown"] = {
            "braking": total_braking,
            "corner": total_corner,
            "traction": total_traction,
        }

        # Key findings based on breakdown
        max_phase = max(insights["breakdown"], key=lambda k: abs(insights["breakdown"][k]))
        max_value = insights["breakdown"][max_phase]

        if abs(max_value) > 0.05:  # Threshold for significance
            if max_value < 0:
                insights["key_findings"].append(
                    f"{driver1_name} gains most time in {max_phase} phase ({abs(max_value):.3f}s)"
                )
            else:
                insights["key_findings"].append(
                    f"{driver2_name} gains most time in {max_phase} phase ({abs(max_value):.3f}s)"
                )

    # Corner-specific insights
    if corners1 and corners2:
        min_corners = min(len(corners1), len(corners2))
        if min_corners > 0:
            # Compare minimum speeds
            avg_min_speed_1 = np.mean([c.min_speed for c in corners1[:min_corners]])
            avg_min_speed_2 = np.mean([c.min_speed for c in corners2[:min_corners]])

            if abs(avg_min_speed_1 - avg_min_speed_2) > 2.0:
                if avg_min_speed_1 > avg_min_speed_2:
                    insights["key_findings"].append(
                        f"{driver1_name} carries more speed through corners (avg {avg_min_speed_1 - avg_min_speed_2:.1f} km/h faster)"
                    )
                else:
                    insights["key_findings"].append(
                        f"{driver2_name} carries more speed through corners (avg {avg_min_speed_2 - avg_min_speed_1:.1f} km/h faster)"
                    )

    return insights


def render_insight_summary(
    comparison_summary: Dict[str, Any],
    minisector_data: Optional[pd.DataFrame],
    corners1: Optional[List[Any]],
    corners2: Optional[List[Any]],
    decompositions: Optional[List[Any]],
    driver1_name: str,
    driver2_name: str,
) -> None:
    """
    Render insight summary component.

    Args:
        comparison_summary: Comparison summary dictionary
        minisector_data: Minisector delta data
        corners1: Corner data for driver 1
        corners2: Corner data for driver 2
        decompositions: Corner delta decompositions
        driver1_name: Driver 1 name
        driver2_name: Driver 2 name
    """
    insights = generate_insight_summary(
        comparison_summary,
        minisector_data,
        corners1,
        corners2,
        decompositions,
        driver1_name,
        driver2_name,
    )

    st.subheader("Insight Summary")

    # Total delta
    delta_sign = "+" if insights["total_delta"] > 0 else ""
    st.markdown(
        f"**Overall:** {insights['faster_driver']} is **{abs(insights['total_delta']):.3f}s faster** "
        f"({delta_sign}{insights['total_delta']:.3f}s)"
    )

    # Sector breakdown
    if insights["sector_breakdown"]:
        st.markdown("**Sector Breakdown:**")
        col1, col2, col3 = st.columns(3)

        with col1:
            sector1_delta = insights["sector_breakdown"].get("Sector 1", 0)
            st.metric("Sector 1", f"{sector1_delta:+.3f}s")

        with col2:
            sector2_delta = insights["sector_breakdown"].get("Sector 2", 0)
            st.metric("Sector 2", f"{sector2_delta:+.3f}s")

        with col3:
            sector3_delta = insights["sector_breakdown"].get("Sector 3", 0)
            st.metric("Sector 3", f"{sector3_delta:+.3f}s")

    # Top sectors
    if insights["top_locations"]:
        st.markdown("**Sectors Ranked by Time Difference:**")
        for i, loc in enumerate(insights["top_locations"], 1):
            delta_sign = "+" if loc["delta"] > 0 else ""
            st.markdown(
                f"{i}. {loc['sector']}: "
                f"{delta_sign}{loc['delta']:.3f}s favoring **{loc['favoring']}**"
            )

    # Breakdown
    if insights["breakdown"]:
        st.markdown("**Performance Breakdown (by phase):**")
        col1, col2, col3 = st.columns(3)

        with col1:
            braking = insights["breakdown"]["braking"]
            st.metric("Braking", f"{braking:+.3f}s")

        with col2:
            corner = insights["breakdown"]["corner"]
            st.metric("Corner", f"{corner:+.3f}s")

        with col3:
            traction = insights["breakdown"]["traction"]
            st.metric("Traction", f"{traction:+.3f}s")

    # Key findings
    if insights["key_findings"]:
        st.markdown("**Key Findings:**")
        for finding in insights["key_findings"]:
            st.markdown(f"- {finding}")

    # Assumptions & Limitations expander
    with st.expander("Assumptions & Limitations"):
        st.markdown(
            """
        **Physics Approximations:**
        - Longitudinal acceleration estimated from speed changes (kinematic equations)
        - Lateral acceleration approximated from track curvature (requires X/Y data)
        - Braking zones detected from brake pressure threshold and speed reduction
        - Corner detection based on local speed minima

        **What We Ignore:**
        - Vehicle mass, inertia, and differential settings
        - Aerodynamic effects (drag, downforce, DRS)
        - Track elevation changes
        - Tire degradation and temperature
        - Fuel load variations

        **Interpretation:**
        - Use insights for **relative comparison** only
        - Results are approximate and smoothed to reduce noise
        - When uncertain, language uses "suggests" or "likely" rather than "proves"
        """
        )
