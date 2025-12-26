"""
Streamlit dashboard for F1 Telemetry Physics Lab.

Interactive web application for lap comparison analysis.

Author: João Pedro Cunha
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import streamlit as st
import pandas as pd
import logging

from f1telemetry import (
    config as cfg,
    data_loader,
    alignment,
    physics,
    metrics,
    viz,
    report,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="F1 Telemetry Physics Lab",
    page_icon="🏎️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize session state
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
if 'telemetry1' not in st.session_state:
    st.session_state.telemetry1 = None
if 'telemetry2' not in st.session_state:
    st.session_state.telemetry2 = None
if 'comparison_summary' not in st.session_state:
    st.session_state.comparison_summary = None


def sidebar_inputs():
    """Render sidebar input controls."""
    st.sidebar.title("🏎️ F1 Telemetry Physics Lab")
    st.sidebar.markdown("---")

    # Session selection
    st.sidebar.subheader("Session Selection")

    year = st.sidebar.number_input(
        "Year",
        min_value=2018,
        max_value=2025,
        value=2024,
        step=1,
    )

    event = st.sidebar.text_input(
        "Event Name or Round",
        value="Monaco",
        help="E.g., 'Monaco', 'Monza', or round number",
    )

    session_type = st.sidebar.selectbox(
        "Session Type",
        options=["FP1", "FP2", "FP3", "Q", "S", "R"],
        index=3,  # Default to Q
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("Driver Selection")

    col1, col2 = st.sidebar.columns(2)

    with col1:
        driver1 = st.text_input(
            "Driver 1",
            value="VER",
            max_chars=3,
        ).upper()

        lap1_type = st.selectbox(
            "Lap 1",
            options=["fastest", "custom"],
            index=0,
            key="lap1_type",
        )

        if lap1_type == "custom":
            lap1 = str(st.number_input("Lap 1 Number", min_value=1, value=1, step=1))
        else:
            lap1 = "fastest"

    with col2:
        driver2 = st.text_input(
            "Driver 2",
            value="LEC",
            max_chars=3,
        ).upper()

        lap2_type = st.selectbox(
            "Lap 2",
            options=["fastest", "custom"],
            index=0,
            key="lap2_type",
        )

        if lap2_type == "custom":
            lap2 = str(st.number_input("Lap 2 Number", min_value=1, value=1, step=1))
        else:
            lap2 = "fastest"

    st.sidebar.markdown("---")
    st.sidebar.subheader("Settings")

    resolution = st.sidebar.slider(
        "Distance Resolution (m)",
        min_value=1.0,
        max_value=20.0,
        value=5.0,
        step=1.0,
    )

    num_segments = st.sidebar.slider(
        "Number of Segments",
        min_value=5,
        max_value=20,
        value=10,
        step=1,
    )

    st.sidebar.markdown("---")

    load_button = st.sidebar.button("🔄 Load Data", type="primary", use_container_width=True)

    return {
        'year': year,
        'event': event,
        'session_type': session_type,
        'driver1': driver1,
        'driver2': driver2,
        'lap1': lap1,
        'lap2': lap2,
        'resolution': resolution,
        'num_segments': num_segments,
        'load_button': load_button,
    }


def load_data(params):
    """Load and process telemetry data."""
    try:
        with st.spinner("Loading session data..."):
            # Create config
            config = cfg.Config(
                distance_resolution=params['resolution'],
                num_segments=params['num_segments'],
            )

            # Load data
            lap1, lap2, tel1_raw, tel2_raw, session = data_loader.load_lap_comparison_data(
                year=params['year'],
                event=params['event'],
                session_type=params['session_type'],
                driver1=params['driver1'],
                driver2=params['driver2'],
                lap1_selection=params['lap1'],
                lap2_selection=params['lap2'],
                config=config,
            )

            # Align laps
            tel1, tel2 = alignment.align_laps(tel1_raw, tel2_raw, config)

            # Add physics channels
            tel1 = physics.add_physics_channels(tel1, config)
            tel2 = physics.add_physics_channels(tel2, config)

            # Create comparison summary
            comparison_summary = metrics.create_comparison_summary(
                lap1, lap2,
                tel1, tel2,
                params['driver1'], params['driver2'],
                config,
            )

            # Store in session state
            st.session_state.data_loaded = True
            st.session_state.telemetry1 = tel1
            st.session_state.telemetry2 = tel2
            st.session_state.comparison_summary = comparison_summary
            st.session_state.lap1 = lap1
            st.session_state.lap2 = lap2
            st.session_state.session = session
            st.session_state.session_info = data_loader.get_session_info(session)
            st.session_state.driver1_name = params['driver1']
            st.session_state.driver2_name = params['driver2']
            st.session_state.config = config

            st.success("✅ Data loaded successfully!")

    except Exception as e:
        st.error(f"❌ Error loading data: {str(e)}")
        logger.error(f"Data loading error: {e}", exc_info=True)


def page_lap_compare():
    """Lap comparison page."""
    st.header("🏁 Lap Comparison")

    if not st.session_state.data_loaded:
        st.info("👈 Load data using the sidebar to begin analysis")
        return

    # Show insights
    st.subheader("📊 Key Insights")
    for insight in st.session_state.comparison_summary['insights']:
        st.markdown(f"- {insight}")

    st.markdown("---")

    # Speed comparison
    st.subheader("Speed Comparison")
    fig_speed = viz.create_speed_comparison_plot(
        st.session_state.telemetry1,
        st.session_state.telemetry2,
        st.session_state.driver1_name,
        st.session_state.driver2_name,
        st.session_state.config,
    )
    st.plotly_chart(fig_speed, use_container_width=True)

    # Delta time
    st.subheader("Delta Time Analysis")
    fig_delta = viz.create_delta_time_plot(
        st.session_state.comparison_summary['delta_time'],
        st.session_state.telemetry1['Distance'].values,
        st.session_state.driver1_name,
        st.session_state.driver2_name,
        st.session_state.config,
    )
    st.plotly_chart(fig_delta, use_container_width=True)

    # Segment comparison
    st.subheader("Segment-by-Segment Comparison")
    fig_segments = viz.create_segment_comparison_plot(
        st.session_state.comparison_summary['segment_comparisons'],
        st.session_state.driver1_name,
        st.session_state.driver2_name,
        st.session_state.config,
    )
    st.plotly_chart(fig_segments, use_container_width=True)


def page_track_map():
    """Track map page."""
    st.header("🗺️ Track Map")

    if not st.session_state.data_loaded:
        st.info("👈 Load data using the sidebar to begin analysis")
        return

    color_by = st.selectbox(
        "Color by:",
        options=['Speed', 'Throttle', 'Brake'],
        index=0,
    )

    fig_map = viz.create_track_map(
        st.session_state.telemetry1,
        st.session_state.telemetry2,
        st.session_state.driver1_name,
        st.session_state.driver2_name,
        color_by,
        st.session_state.config,
    )
    st.plotly_chart(fig_map, use_container_width=True)


def page_braking_cornering():
    """Braking and cornering analysis page."""
    st.header("🔧 Braking & Cornering Analysis")

    if not st.session_state.data_loaded:
        st.info("👈 Load data using the sidebar to begin analysis")
        return

    # Throttle and Brake
    st.subheader("Throttle & Brake Application")
    fig_tb = viz.create_throttle_brake_plot(
        st.session_state.telemetry1,
        st.session_state.telemetry2,
        st.session_state.driver1_name,
        st.session_state.driver2_name,
        st.session_state.config,
    )
    st.plotly_chart(fig_tb, use_container_width=True)

    # Gear selection
    st.subheader("Gear Selection")
    fig_gear = viz.create_gear_plot(
        st.session_state.telemetry1,
        st.session_state.telemetry2,
        st.session_state.driver1_name,
        st.session_state.driver2_name,
        st.session_state.config,
    )
    st.plotly_chart(fig_gear, use_container_width=True)

    # Acceleration
    st.subheader("Longitudinal Acceleration")
    fig_accel = viz.create_acceleration_plot(
        st.session_state.telemetry1,
        st.session_state.telemetry2,
        st.session_state.driver1_name,
        st.session_state.driver2_name,
        st.session_state.config,
    )
    st.plotly_chart(fig_accel, use_container_width=True)

    # Braking zones info
    st.subheader("Braking Zones")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"**{st.session_state.driver1_name}**")
        zones1 = st.session_state.comparison_summary['braking_zones1']
        if zones1:
            for i, zone in enumerate(zones1[:5], 1):
                st.markdown(
                    f"**Zone {i}:** {zone.start_distance:.0f}m - {zone.end_distance:.0f}m | "
                    f"Entry: {zone.entry_speed:.0f} km/h | "
                    f"Min: {zone.min_speed:.0f} km/h"
                )
        else:
            st.info("No braking zones detected")

    with col2:
        st.markdown(f"**{st.session_state.driver2_name}**")
        zones2 = st.session_state.comparison_summary['braking_zones2']
        if zones2:
            for i, zone in enumerate(zones2[:5], 1):
                st.markdown(
                    f"**Zone {i}:** {zone.start_distance:.0f}m - {zone.end_distance:.0f}m | "
                    f"Entry: {zone.entry_speed:.0f} km/h | "
                    f"Min: {zone.min_speed:.0f} km/h"
                )
        else:
            st.info("No braking zones detected")


def page_session_explorer():
    """Session explorer and data QA page."""
    st.header("🔍 Session Explorer / Data QA")

    if not st.session_state.data_loaded:
        st.info("👈 Load data using the sidebar to begin analysis")
        return

    # Session info
    st.subheader("Session Information")
    info = st.session_state.session_info
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Event", info['event_name'])
        st.metric("Location", info['location'])

    with col2:
        st.metric("Country", info['country'])
        st.metric("Session", info['session_type'])

    with col3:
        st.metric("Date", info['date'])

    # Telemetry data preview
    st.subheader("Telemetry Data Preview")

    tab1, tab2 = st.tabs([st.session_state.driver1_name, st.session_state.driver2_name])

    with tab1:
        st.dataframe(st.session_state.telemetry1.head(100), use_container_width=True)
        st.markdown(f"**Total samples:** {len(st.session_state.telemetry1)}")

    with tab2:
        st.dataframe(st.session_state.telemetry2.head(100), use_container_width=True)
        st.markdown(f"**Total samples:** {len(st.session_state.telemetry2)}")

    # Download report
    st.markdown("---")
    st.subheader("📥 Download Report")

    if st.button("Generate HTML Report", type="primary"):
        with st.spinner("Generating report..."):
            html_content = report.generate_html_report(
                st.session_state.lap1,
                st.session_state.lap2,
                st.session_state.telemetry1,
                st.session_state.telemetry2,
                st.session_state.session_info,
                st.session_state.driver1_name,
                st.session_state.driver2_name,
                st.session_state.config,
            )

        st.download_button(
            label="Download Report",
            data=html_content,
            file_name=f"f1_telemetry_report_{st.session_state.driver1_name}_vs_{st.session_state.driver2_name}.html",
            mime="text/html",
        )
        st.success("✅ Report generated!")


def main():
    """Main application."""
    # Sidebar
    params = sidebar_inputs()

    if params['load_button']:
        load_data(params)

    # Page navigation
    page = st.sidebar.radio(
        "Navigation",
        options=[
            "Lap Compare",
            "Track Map",
            "Braking & Cornering",
            "Session Explorer",
        ],
        index=0,
    )

    # Display selected page
    if page == "Lap Compare":
        page_lap_compare()
    elif page == "Track Map":
        page_track_map()
    elif page == "Braking & Cornering":
        page_braking_cornering()
    elif page == "Session Explorer":
        page_session_explorer()

    # Footer
    st.sidebar.markdown("---")
    st.sidebar.markdown("**F1 Telemetry Physics Lab**")
    st.sidebar.markdown("Author: João Pedro Cunha")
    st.sidebar.markdown("Data: FastF1")


if __name__ == "__main__":
    main()
