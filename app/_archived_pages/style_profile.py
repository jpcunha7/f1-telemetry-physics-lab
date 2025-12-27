"""
Driver Style Profile Page.

Analyzes aggregated driver behavior across multiple laps.

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
    physics,
    style_profile,
)

logger = logging.getLogger(__name__)


def render():
    """Render the Driver Style Profile page."""
    st.header("Driver Style Profile")

    st.markdown(
        """
    Analyze aggregated driver behavior across multiple laps to identify driving style characteristics.
    This analysis compares throttle/brake application, acceleration patterns, and speed distributions.
    """
    )

    # Sidebar inputs
    st.sidebar.markdown("---")
    st.sidebar.subheader("Style Profile Settings")

    year = st.sidebar.number_input(
        "Year", min_value=2018, max_value=2025, value=2024, step=1, key="style_year"
    )
    event = st.sidebar.text_input("Event Name or Round", value="Monaco", key="style_event")
    session_type = st.sidebar.selectbox(
        "Session Type", options=["Q", "FP1", "FP2", "FP3", "R"], index=0, key="style_session"
    )

    driver1 = st.sidebar.text_input(
        "Driver 1", value="VER", max_chars=3, key="style_driver1"
    ).upper()

    compare_mode = st.sidebar.checkbox("Compare with Driver 2", value=False, key="style_compare")
    if compare_mode:
        driver2 = st.sidebar.text_input(
            "Driver 2", value="LEC", max_chars=3, key="style_driver2"
        ).upper()
    else:
        driver2 = None

    # Lap selection
    num_laps = st.sidebar.slider(
        "Number of laps to analyze",
        min_value=1,
        max_value=20,
        value=5,
        step=1,
        key="style_num_laps",
        help="Analyze the fastest N valid laps",
    )

    load_button = st.sidebar.button("Load Driver Style Data", type="primary", key="style_load")

    if load_button:
        try:
            with st.spinner("Loading session and telemetry..."):
                config = cfg.Config()
                session = data_loader.load_session(year, event, session_type, config)

                # Get driver 1 laps
                driver1_laps = session.laps.pick_driver(driver1)
                if driver1_laps.empty:
                    st.error(f"No laps found for {driver1}")
                    return

                # Get fastest N valid laps
                valid_laps1 = (
                    driver1_laps[driver1_laps["IsAccurate"]]
                    if "IsAccurate" in driver1_laps.columns
                    else driver1_laps
                )
                valid_laps1 = valid_laps1.sort_values("LapTime").head(num_laps)

                # Load telemetry for each lap
                telemetry_list1 = []
                for idx, lap in valid_laps1.iterrows():
                    try:
                        tel = data_loader.get_telemetry(lap)
                        # Add physics channels
                        tel = physics.add_physics_channels(tel, config)
                        telemetry_list1.append(tel)
                    except Exception as e:
                        logger.warning(f"Failed to load telemetry for lap {lap['LapNumber']}: {e}")

                if not telemetry_list1:
                    st.error("Failed to load any telemetry data")
                    return

                # Compute aggregated stats
                stats1 = style_profile.aggregate_telemetry_stats(telemetry_list1, driver1)

                # Store in session state
                st.session_state.style_loaded = True
                st.session_state.style_loaded_driver1 = driver1
                st.session_state.style_telemetry1 = telemetry_list1
                st.session_state.style_stats1 = stats1

                # Load driver 2 if compare mode
                if compare_mode and driver2:
                    driver2_laps = session.laps.pick_driver(driver2)
                    if not driver2_laps.empty:
                        valid_laps2 = (
                            driver2_laps[driver2_laps["IsAccurate"]]
                            if "IsAccurate" in driver2_laps.columns
                            else driver2_laps
                        )
                        valid_laps2 = valid_laps2.sort_values("LapTime").head(num_laps)

                        telemetry_list2 = []
                        for idx, lap in valid_laps2.iterrows():
                            try:
                                tel = data_loader.get_telemetry(lap)
                                tel = physics.add_physics_channels(tel, config)
                                telemetry_list2.append(tel)
                            except Exception as e:
                                logger.warning(
                                    f"Failed to load telemetry for lap {lap['LapNumber']}: {e}"
                                )

                        if telemetry_list2:
                            stats2 = style_profile.aggregate_telemetry_stats(
                                telemetry_list2, driver2
                            )
                            st.session_state.style_loaded_driver2 = driver2
                            st.session_state.style_telemetry2 = telemetry_list2
                            st.session_state.style_stats2 = stats2
                        else:
                            st.warning(f"Failed to load telemetry for {driver2}")
                            st.session_state.style_loaded_driver2 = None
                    else:
                        st.warning(f"No laps found for {driver2}")
                        st.session_state.style_loaded_driver2 = None
                else:
                    st.session_state.style_loaded_driver2 = None

                st.success(f"Loaded {len(telemetry_list1)} laps for analysis!")

        except Exception as e:
            st.error(f"Error loading style profile data: {str(e)}")
            logger.error(f"Style profile loading error: {e}", exc_info=True)
            return

    # Display analysis if data loaded
    if not st.session_state.get("style_loaded", False):
        st.info("Load driver style data using the sidebar to begin analysis")
        return

    # KPI Cards
    st.subheader(f"Driver Style Metrics - {st.session_state.style_loaded_driver1}")

    stats1 = st.session_state.style_stats1

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Avg Speed", f"{stats1.get('avg_speed', 0):.1f} km/h")
        st.metric("Max Speed", f"{stats1.get('max_speed', 0):.1f} km/h")

    with col2:
        st.metric("% Full Throttle", f"{stats1.get('percent_full_throttle', 0):.1f}%")
        st.metric("% Braking", f"{stats1.get('percent_braking', 0):.1f}%")

    with col3:
        st.metric("Max Accel", f"{stats1.get('max_accel', 0):.2f} g")
        st.metric("Max Decel", f"{stats1.get('max_decel', 0):.2f} g")

    with col4:
        st.metric("Avg Lat Accel", f"{stats1.get('avg_lat_accel', 0):.2f} g")
        st.metric("Max Lat Accel", f"{stats1.get('max_lat_accel', 0):.2f} g")

    st.markdown("---")

    # Distribution plots
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Throttle & Brake Distribution")
        fig_inputs = style_profile.create_throttle_brake_distribution_plot(
            st.session_state.style_telemetry1, st.session_state.style_loaded_driver1, cfg.DEFAULT_CONFIG
        )
        st.plotly_chart(fig_inputs, use_container_width=True)

    with col2:
        st.subheader("Acceleration Distribution")
        fig_accel = style_profile.create_acceleration_distribution_plot(
            st.session_state.style_telemetry1, st.session_state.style_loaded_driver1, cfg.DEFAULT_CONFIG
        )
        st.plotly_chart(fig_accel, use_container_width=True)

    # Speed distribution
    st.subheader("Speed Distribution")
    fig_speed = style_profile.create_speed_distribution_plot(
        st.session_state.style_telemetry1, st.session_state.style_loaded_driver1, cfg.DEFAULT_CONFIG
    )
    st.plotly_chart(fig_speed, use_container_width=True)

    # Comparison mode
    if st.session_state.get("style_loaded_driver2"):
        st.markdown("---")
        st.subheader(
            f"Style Comparison: {st.session_state.style_loaded_driver1} vs {st.session_state.style_loaded_driver2}"
        )

        # Comparison table
        comparison_table = style_profile.compare_driver_styles(
            st.session_state.style_stats1, st.session_state.style_stats2
        )

        if not comparison_table.empty:
            st.dataframe(comparison_table, use_container_width=True, hide_index=True)

        # Side-by-side plots
        st.subheader("Side-by-Side Comparison")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"**{st.session_state.style_loaded_driver1}**")
            fig1 = style_profile.create_throttle_brake_distribution_plot(
                st.session_state.style_telemetry1,
                st.session_state.style_loaded_driver1,
                cfg.DEFAULT_CONFIG,
            )
            st.plotly_chart(fig1, use_container_width=True)

        with col2:
            st.markdown(f"**{st.session_state.style_loaded_driver2}**")
            fig2 = style_profile.create_throttle_brake_distribution_plot(
                st.session_state.style_telemetry2,
                st.session_state.style_loaded_driver2,
                cfg.DEFAULT_CONFIG,
            )
            st.plotly_chart(fig2, use_container_width=True)
