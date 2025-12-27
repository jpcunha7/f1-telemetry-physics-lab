"""
KPI cards component.

Displays key performance indicators in a card layout.

Author: João Pedro Cunha
"""

import streamlit as st
from typing import Dict, Any, Optional
import pandas as pd


def render_kpi_cards(
    comparison_summary: Dict[str, Any],
    driver1_name: str,
    driver2_name: str,
    minisector_data: Optional[pd.DataFrame] = None,
) -> None:
    """
    Render KPI cards with key metrics.

    Args:
        comparison_summary: Comparison summary dictionary
        driver1_name: Driver 1 name
        driver2_name: Driver 2 name
        minisector_data: Optional minisector data for segment analysis
    """
    col1, col2, col3, col4 = st.columns(4)

    # Total lap delta
    final_delta = comparison_summary["final_delta"]
    faster_driver = driver1_name if final_delta < 0 else driver2_name

    with col1:
        st.metric(
            "Total Lap Delta",
            f"{abs(final_delta):.3f}s",
            delta=f"{faster_driver} faster",
            delta_color="off",
        )

    # Max gap
    max_gap = comparison_summary.get("max_gap", 0.0)
    max_gap_location = comparison_summary.get("max_gap_location", 0)

    with col2:
        st.metric("Max Gap", f"{abs(max_gap):.3f}s", delta=f"at {max_gap_location:.0f}m")

    # Biggest gain segment
    if minisector_data is not None and not minisector_data.empty:
        # Find biggest gain and loss
        max_gain_idx = minisector_data["Time_Delta"].idxmin()
        max_loss_idx = minisector_data["Time_Delta"].idxmax()

        max_gain_sector = minisector_data.loc[max_gain_idx, "Minisector"]
        max_gain_delta = minisector_data.loc[max_gain_idx, "Time_Delta"]

        with col3:
            st.metric(
                f"Biggest Gain ({driver1_name})",
                f"{abs(max_gain_delta):.3f}s",
                delta=f"Sector {max_gain_sector}",
                delta_color="off",
            )

        max_loss_sector = minisector_data.loc[max_loss_idx, "Minisector"]
        max_loss_delta = minisector_data.loc[max_loss_idx, "Time_Delta"]

        with col4:
            st.metric(
                f"Biggest Loss ({driver1_name})",
                f"{abs(max_loss_delta):.3f}s",
                delta=f"Sector {max_loss_sector}",
                delta_color="off",
            )
    else:
        with col3:
            st.metric("Avg Speed Diff", "N/A")
        with col4:
            st.metric("Corner Performance", "N/A")
