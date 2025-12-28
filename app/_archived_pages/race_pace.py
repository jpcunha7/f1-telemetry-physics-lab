"""
Race Pace & Stints Analysis Page.

Analyzes race pace, stint strategies, and lap-by-lap performance.

Author: João Pedro Cunha
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import streamlit as st
import logging

from f1telemetry import (
    config as cfg,
    data_loader,
    race_pace,
)

logger = logging.getLogger(__name__)


def render():
    """Render the Race Pace & Stints page."""
    st.header("Race Pace & Stint Analysis")

    st.markdown(
        """
    Analyze race pace, stint strategies, and performance degradation over race distance.
    This analysis works best with **Race (R)** sessions.
    """
    )

    # Sidebar inputs
    st.sidebar.markdown("---")
    st.sidebar.subheader("Race Pace Settings")

    year = st.sidebar.number_input(
        "Year", min_value=2018, max_value=2025, value=2024, step=1, key="race_pace_year"
    )
    event = st.sidebar.text_input("Event Name or Round", value="Monaco", key="race_pace_event")
    session_type = st.sidebar.selectbox(
        "Session Type", options=["R", "S"], index=0, key="race_pace_session"
    )

    driver1 = st.sidebar.text_input(
        "Driver 1", value="VER", max_chars=3, key="race_pace_driver1"
    ).upper()

    compare_mode = st.sidebar.checkbox(
        "Compare with Driver 2", value=False, key="race_pace_compare"
    )
    if compare_mode:
        driver2 = st.sidebar.text_input(
            "Driver 2", value="HAM", max_chars=3, key="race_pace_driver2"
        ).upper()
    else:
        driver2 = None

    # Lap filters
    with st.sidebar.expander("Lap Filters"):
        exclude_outliers = st.checkbox("Exclude outlier laps", value=True, key="race_pace_outliers")
        outlier_threshold = st.slider(
            "Outlier threshold (x median)",
            min_value=1.1,
            max_value=2.0,
            value=1.3,
            step=0.1,
            key="race_pace_threshold",
        )

    load_button = st.sidebar.button("Load Race Data", type="primary", key="race_pace_load")

    if load_button:
        try:
            with st.spinner("Loading race session..."):
                config = cfg.Config()
                session = data_loader.load_session(year, event, session_type, config)

                # Load laps for driver 1
                driver1_laps = session.laps.pick_driver(driver1)
                if driver1_laps.empty:
                    st.error(f"No laps found for {driver1}")
                    return

                # Filter laps
                driver1_laps_filtered = race_pace.filter_valid_laps(
                    driver1_laps,
                    exclude_outliers=exclude_outliers,
                    outlier_threshold=outlier_threshold,
                )

                # Detect stints
                stints1 = race_pace.detect_stints(driver1_laps_filtered)

                # Store in session state
                st.session_state.race_pace_loaded = True
                st.session_state.race_session = session
                st.session_state.race_driver1 = driver1
                st.session_state.race_laps1 = driver1_laps_filtered
                st.session_state.race_stints1 = stints1

                # Load driver 2 if compare mode
                if compare_mode and driver2:
                    driver2_laps = session.laps.pick_driver(driver2)
                    if not driver2_laps.empty:
                        driver2_laps_filtered = race_pace.filter_valid_laps(
                            driver2_laps,
                            exclude_outliers=exclude_outliers,
                            outlier_threshold=outlier_threshold,
                        )
                        stints2 = race_pace.detect_stints(driver2_laps_filtered)

                        st.session_state.race_driver2 = driver2
                        st.session_state.race_laps2 = driver2_laps_filtered
                        st.session_state.race_stints2 = stints2
                    else:
                        st.warning(f"No laps found for {driver2}")
                        st.session_state.race_driver2 = None
                else:
                    st.session_state.race_driver2 = None

                st.success("Race data loaded successfully!")

        except Exception as e:
            st.error(f"Error loading race data: {str(e)}")
            logger.error(f"Race pace loading error: {e}", exc_info=True)
            return

    # Display analysis if data loaded
    if not st.session_state.get("race_pace_loaded", False):
        st.info("Load race data using the sidebar to begin analysis")
        return

    # Race pace plot
    st.subheader(f"Race Pace - {st.session_state.race_driver1}")

    fig_pace = race_pace.create_race_pace_plot(
        st.session_state.race_laps1,
        st.session_state.race_driver1,
        stints=st.session_state.race_stints1,
        config=cfg.DEFAULT_CONFIG,
    )
    st.plotly_chart(fig_pace, use_container_width=True)

    # Stint summary table
    st.subheader("Stint Summary")
    stint_table = race_pace.create_stint_summary_table(
        st.session_state.race_stints1, st.session_state.race_driver1
    )

    if not stint_table.empty:
        display_cols = [
            "stint_number",
            "start_lap",
            "end_lap",
            "compound",
            "num_laps",
            "median_lap_time_str",
            "best_lap_time_str",
            "consistency_std_str",
            "pace_drop_s_str",
        ]
        st.dataframe(
            stint_table[[col for col in display_cols if col in stint_table.columns]],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No stints detected")

    # Comparison mode
    if st.session_state.get("race_driver2"):
        st.markdown("---")
        st.subheader(
            f"Comparison: {st.session_state.race_driver1} vs {st.session_state.race_driver2}"
        )

        # Comparison plot
        fig_compare = race_pace.compare_race_pace(
            st.session_state.race_laps1,
            st.session_state.race_laps2,
            st.session_state.race_driver1,
            st.session_state.race_driver2,
            config=cfg.DEFAULT_CONFIG,
        )
        st.plotly_chart(fig_compare, use_container_width=True)

        # Driver 2 stint table
        st.subheader(f"{st.session_state.race_driver2} Stints")
        stint_table2 = race_pace.create_stint_summary_table(
            st.session_state.race_stints2, st.session_state.race_driver2
        )

        if not stint_table2.empty:
            st.dataframe(
                stint_table2[[col for col in display_cols if col in stint_table2.columns]],
                use_container_width=True,
                hide_index=True,
            )
