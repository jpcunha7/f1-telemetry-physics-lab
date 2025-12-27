"""
Lap selector component with metadata display.

Provides intelligent lap selection with lap metadata and filters.

Author: João Pedro Cunha
"""

import streamlit as st
from typing import Dict, Any, Optional, Tuple
import pandas as pd
from fastf1.core import Session


def get_available_laps(
    session: Session,
    driver: str,
    valid_only: bool = False,
    exclude_in_out: bool = True,
    compound_filter: Optional[str] = None,
) -> pd.DataFrame:
    """
    Get available laps for a driver with metadata.

    Args:
        session: FastF1 Session object
        driver: Three-letter driver code
        valid_only: Only include valid laps
        exclude_in_out: Exclude in/out laps
        compound_filter: Filter by compound (SOFT, MEDIUM, HARD, etc.)

    Returns:
        DataFrame with lap metadata
    """
    driver_laps = session.laps.pick_driver(driver)

    if driver_laps.empty:
        return pd.DataFrame()

    # Filter valid laps
    if valid_only and "IsAccurate" in driver_laps.columns:
        driver_laps = driver_laps[driver_laps["IsAccurate"]]

    # Exclude in/out laps (lap 1 and last lap typically)
    if exclude_in_out:
        max_lap = driver_laps["LapNumber"].max()
        driver_laps = driver_laps[
            (driver_laps["LapNumber"] > 1) & (driver_laps["LapNumber"] < max_lap)
        ]

    # Filter by compound
    if compound_filter and compound_filter != "All" and "Compound" in driver_laps.columns:
        driver_laps = driver_laps[driver_laps["Compound"] == compound_filter]

    # Create display labels
    lap_data = []
    for idx, lap in driver_laps.iterrows():
        lap_num = int(lap["LapNumber"])
        lap_time = lap["LapTime"]

        # Format lap time
        if hasattr(lap_time, "total_seconds"):
            lap_time_str = f"{lap_time.total_seconds():.3f}s"
        else:
            lap_time_str = f"{float(lap_time):.3f}s"

        # Build label
        label_parts = [f"Lap {lap_num}", lap_time_str]

        # Add compound if available
        if "Compound" in lap.index and pd.notna(lap["Compound"]):
            label_parts.append(lap["Compound"])

        # Add valid status
        if "IsAccurate" in lap.index:
            if lap["IsAccurate"]:
                label_parts.append("Valid")
            else:
                label_parts.append("Invalid")

        # Add session segment if available (Q1, Q2, Q3, etc.)
        if "Stint" in lap.index and pd.notna(lap["Stint"]):
            label_parts.append(f"Stint {int(lap['Stint'])}")

        label = " — ".join(label_parts)

        lap_data.append(
            {
                "lap_number": lap_num,
                "lap_time": lap_time,
                "lap_time_str": lap_time_str,
                "label": label,
                "compound": lap.get("Compound", None),
                "is_accurate": lap.get("IsAccurate", True),
            }
        )

    return pd.DataFrame(lap_data)


def render_lap_selector(
    session: Session,
    driver: str,
    driver_label: str,
    key_prefix: str,
) -> Tuple[str, Dict[str, Any]]:
    """
    Render lap selector with filters and metadata.

    Args:
        session: FastF1 Session object
        driver: Three-letter driver code
        driver_label: Display label for driver
        key_prefix: Unique key prefix for widgets

    Returns:
        Tuple of (lap_selection, lap_metadata)
        lap_selection: Either "fastest" or lap number as string
        lap_metadata: Dict with lap information
    """
    st.markdown(f"**{driver_label}**")

    # Lap selection mode
    lap_mode = st.radio(
        f"Lap selection for {driver}",
        options=["Fastest Valid Lap", "Select Specific Lap"],
        key=f"{key_prefix}_lap_mode",
        label_visibility="collapsed",
    )

    lap_metadata = {}

    if lap_mode == "Fastest Valid Lap":
        lap_selection = "fastest"
        lap_metadata = {
            "lap_number": "Fastest",
            "lap_time": "Auto",
            "compound": None,
        }

    else:
        # Show filters
        with st.expander("Lap Filters", expanded=False):
            col1, col2 = st.columns(2)

            with col1:
                valid_only = st.checkbox(
                    "Valid laps only", value=True, key=f"{key_prefix}_valid_only"
                )

            with col2:
                exclude_in_out = st.checkbox(
                    "Exclude in/out laps", value=True, key=f"{key_prefix}_exclude_in_out"
                )

            # Compound filter (only if data available)
            available_laps_all = get_available_laps(
                session, driver, valid_only=False, exclude_in_out=False
            )

            if not available_laps_all.empty and "compound" in available_laps_all.columns:
                compounds = available_laps_all["compound"].dropna().unique().tolist()
                if compounds:
                    compound_options = ["All"] + sorted(compounds)
                    compound_filter = st.selectbox(
                        "Tire compound", options=compound_options, key=f"{key_prefix}_compound"
                    )
                else:
                    compound_filter = None
            else:
                compound_filter = None

        # Get available laps with filters
        available_laps = get_available_laps(
            session,
            driver,
            valid_only=valid_only,
            exclude_in_out=exclude_in_out,
            compound_filter=compound_filter,
        )

        if available_laps.empty:
            st.warning(f"No laps available for {driver} with current filters")
            lap_selection = "fastest"
            lap_metadata = {"lap_number": "N/A", "lap_time": "N/A", "compound": None}
        else:
            # Create selectbox with lap labels
            lap_options = available_laps["label"].tolist()
            lap_numbers = available_laps["lap_number"].tolist()

            selected_idx = st.selectbox(
                f"Select lap for {driver}",
                options=range(len(lap_options)),
                format_func=lambda i: lap_options[i],
                key=f"{key_prefix}_lap_select",
                label_visibility="collapsed",
            )

            lap_selection = str(lap_numbers[selected_idx])
            lap_metadata = {
                "lap_number": lap_numbers[selected_idx],
                "lap_time": available_laps.iloc[selected_idx]["lap_time_str"],
                "compound": available_laps.iloc[selected_idx]["compound"],
            }

    return lap_selection, lap_metadata
