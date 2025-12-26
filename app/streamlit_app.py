"""
Streamlit dashboard for F1 Telemetry Physics Lab.

Professional race engineering telemetry analysis tool.

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
    minisectors,
    corners as corners_module,
    delta_decomp,
    gg_diagram,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration - NO EMOJIS
st.set_page_config(
    page_title="F1 Telemetry Physics Lab",
    page_icon="🏁",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize session state
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False


def sidebar_inputs():
    """Render sidebar input controls."""
    st.sidebar.title("F1 Telemetry Physics Lab")
    st.sidebar.markdown("Professional Race Engineering Tool")
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
        index=3,
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
    st.sidebar.subheader("Analysis Settings")

    resolution = st.sidebar.slider(
        "Distance Resolution (m)",
        min_value=1.0,
        max_value=20.0,
        value=5.0,
        step=1.0,
    )

    num_minisectors = st.sidebar.slider(
        "Number of Minisectors",
        min_value=20,
        max_value=100,
        value=50,
        step=5,
    )

    st.sidebar.markdown("---")

    load_button = st.sidebar.button("Load Data", type="primary", use_container_width=True)

    return {
        'year': year,
        'event': event,
        'session_type': session_type,
        'driver1': driver1,
        'driver2': driver2,
        'lap1': lap1,
        'lap2': lap2,
        'resolution': resolution,
        'num_minisectors': num_minisectors,
        'load_button': load_button,
    }


def load_data(params):
    """Load and process telemetry data."""
    try:
        with st.spinner("Loading session data..."):
            # Create config
            config = cfg.Config(
                distance_resolution=params['resolution'],
                num_minisectors=params['num_minisectors'],
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

            # Compute minisectors
            with st.spinner("Computing minisector analysis..."):
                minisector_data = minisectors.compute_minisector_deltas(
                    tel1, tel2, config.num_minisectors, config
                )

            # Detect corners
            with st.spinner("Detecting corners..."):
                corners1 = corners_module.detect_corners(tel1, config=config)
                corners2 = corners_module.detect_corners(tel2, config=config)

            # Corner decomposition
            with st.spinner("Analyzing delta decomposition..."):
                decompositions = []
                min_corners = min(len(corners1), len(corners2))
                for i in range(min_corners):
                    decomp = delta_decomp.decompose_corner_delta(
                        corners1[i], corners2[i], tel1, tel2
                    )
                    decompositions.append(decomp)

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
            st.session_state.minisector_data = minisector_data
            st.session_state.corners1 = corners1
            st.session_state.corners2 = corners2
            st.session_state.decompositions = decompositions

            st.success("Data loaded successfully!")

    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        logger.error(f"Data loading error: {e}", exc_info=True)


def page_overview():
    """Overview page with session summary."""
    st.header("Session Overview")

    if not st.session_state.data_loaded:
        st.info("Load data using the sidebar to begin analysis")
        return

    # Session info
    info = st.session_state.session_info
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Event", info['event_name'])
        st.metric("Location", info['location'])

    with col2:
        st.metric("Country", info['country'])
        st.metric("Session", info['session_type'])

    with col3:
        st.metric("Date", info['date'])

    with col4:
        lap_delta = st.session_state.comparison_summary['lap_time_delta']
        st.metric(
            "Lap Time Delta",
            f"{abs(lap_delta):.3f}s",
            delta=f"{st.session_state.driver1_name if lap_delta > 0 else st.session_state.driver2_name} faster"
        )

    st.markdown("---")

    # Key insights
    st.subheader("Key Performance Insights")
    insights = st.session_state.comparison_summary['insights']

    cols = st.columns(2)
    for idx, insight in enumerate(insights):
        with cols[idx % 2]:
            st.markdown(f"- {insight}")

    # Quick stats
    st.markdown("---")
    st.subheader("Quick Statistics")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"**{st.session_state.driver1_name} - Fastest Lap:** {st.session_state.lap1['LapTime']}")
        if st.session_state.corners1:
            st.markdown(f"**Corners Detected:** {len(st.session_state.corners1)}")

    with col2:
        st.markdown(f"**{st.session_state.driver2_name} - Fastest Lap:** {st.session_state.lap2['LapTime']}")
        if st.session_state.corners2:
            st.markdown(f"**Corners Detected:** {len(st.session_state.corners2)}")


def page_lap_compare():
    """Enhanced lap comparison page."""
    st.header("Lap Comparison")

    if not st.session_state.data_loaded:
        st.info("Load data using the sidebar to begin analysis")
        return

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

    # Throttle & Brake
    st.subheader("Throttle & Brake Application")
    fig_tb = viz.create_throttle_brake_plot(
        st.session_state.telemetry1,
        st.session_state.telemetry2,
        st.session_state.driver1_name,
        st.session_state.driver2_name,
        st.session_state.config,
    )
    st.plotly_chart(fig_tb, use_container_width=True)


def page_minisectors():
    """Minisector analysis and delta decomposition page."""
    st.header("Minisector Analysis & Delta Decomposition")

    if not st.session_state.data_loaded:
        st.info("Load data using the sidebar to begin analysis")
        return

    # Minisector bar chart
    st.subheader("Minisector Time Deltas")
    fig_minisectors = minisectors.create_minisector_bar_chart(
        st.session_state.minisector_data,
        st.session_state.driver1_name,
        st.session_state.driver2_name,
        st.session_state.config,
    )
    st.plotly_chart(fig_minisectors, use_container_width=True)

    # Top gains/losses
    st.subheader("Top Gains & Losses")
    gains, losses = minisectors.get_top_minisector_gains(st.session_state.minisector_data, n=5)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"**Top 5 Gains ({st.session_state.driver1_name} faster)**")
        st.dataframe(gains[['Minisector', 'Time_Delta', 'Distance_Start', 'Speed_Driver1', 'Speed_Driver2']], hide_index=True)

    with col2:
        st.markdown(f"**Top 5 Losses ({st.session_state.driver1_name} slower)**")
        st.dataframe(losses[['Minisector', 'Time_Delta', 'Distance_Start', 'Speed_Driver1', 'Speed_Driver2']], hide_index=True)

    # Delta decomposition
    st.markdown("---")
    st.subheader("Corner Delta Decomposition")

    if st.session_state.decompositions:
        # Waterfall chart
        fig_waterfall = delta_decomp.create_decomposition_waterfall(
            st.session_state.decompositions,
            st.session_state.driver1_name,
            st.session_state.driver2_name,
            st.session_state.config,
        )
        st.plotly_chart(fig_waterfall, use_container_width=True)

        # Phase contribution bar
        fig_phases = delta_decomp.create_phase_contribution_bar(
            st.session_state.decompositions,
            st.session_state.driver1_name,
            st.session_state.driver2_name,
            st.session_state.config,
        )
        st.plotly_chart(fig_phases, use_container_width=True)

        # Decomposition table
        st.subheader("Detailed Decomposition Table")
        decomp_table = delta_decomp.create_decomposition_table(
            st.session_state.decompositions,
            st.session_state.driver1_name,
            st.session_state.driver2_name,
        )
        st.dataframe(decomp_table, use_container_width=True, hide_index=True)

        # Weakness pattern analysis
        pattern = delta_decomp.analyze_weakness_pattern(st.session_state.decompositions)
        st.markdown("---")
        st.subheader("Performance Pattern Analysis")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Phase Distribution:**")
            for phase, pct in pattern['phase_percentages'].items():
                st.markdown(f"- {phase.replace('_', ' ').title()}: {pct:.1f}%")

        with col2:
            st.markdown(f"**Primary Weakness:** {pattern['primary_weakness'].replace('_', ' ').title()}")
            st.markdown("**Total Delta by Phase:**")
            for phase, delta in pattern['phase_total_deltas'].items():
                st.markdown(f"- {phase.replace('_', ' ').title()}: {delta:+.3f}s")


def page_track_map():
    """Track map with corner markers and minisector deltas."""
    st.header("Track Map & Corner Catalog")

    if not st.session_state.data_loaded:
        st.info("Load data using the sidebar to begin analysis")
        return

    # Check for position data
    if "X" not in st.session_state.telemetry1.columns:
        st.warning("Position data (X, Y) not available for this session. Track maps cannot be displayed.")
        return

    # Minisector track map
    st.subheader("Minisector Delta Track Map")

    driver_choice = st.radio(
        "View deltas from perspective of:",
        [st.session_state.driver1_name, st.session_state.driver2_name],
        horizontal=True,
    )

    tel_choice = st.session_state.telemetry1 if driver_choice == st.session_state.driver1_name else st.session_state.telemetry2

    try:
        fig_minisector_map = minisectors.create_minisector_track_map(
            tel_choice,
            st.session_state.minisector_data,
            driver_choice,
            st.session_state.config,
        )
        st.plotly_chart(fig_minisector_map, use_container_width=True)
    except Exception as e:
        st.error(f"Error creating minisector track map: {e}")

    # Corner markers map
    st.markdown("---")
    st.subheader("Corner Catalog Map")

    corners_choice = st.session_state.corners1 if driver_choice == st.session_state.driver1_name else st.session_state.corners2

    if corners_choice:
        try:
            fig_corners_map = corners_module.create_corner_markers_map(
                tel_choice,
                corners_choice,
                driver_choice,
                st.session_state.config,
            )
            st.plotly_chart(fig_corners_map, use_container_width=True)
        except Exception as e:
            st.error(f"Error creating corner map: {e}")

        # Corner comparison table
        st.markdown("---")
        st.subheader("Corner-by-Corner Comparison")
        corner_table = corners_module.create_corner_report_table(
            st.session_state.corners1,
            st.session_state.corners2,
            st.session_state.driver1_name,
            st.session_state.driver2_name,
        )
        st.dataframe(corner_table, use_container_width=True, hide_index=True)
    else:
        st.info("No corners detected in telemetry data.")


def page_gg_diagram():
    """G-G diagram and acceleration analysis page."""
    st.header("G-G Diagram & Acceleration Analysis")

    if not st.session_state.data_loaded:
        st.info("Load data using the sidebar to begin analysis")
        return

    # G-G diagram
    st.subheader("G-G Diagram (Friction Circle)")

    st.markdown("""
    **Physics Note:** The g-g diagram shows longitudinal vs lateral acceleration.
    - Longitudinal: computed from speed change (braking = negative, traction = positive)
    - Lateral: approximated from track curvature and speed (requires X,Y position data)
    - Approximations do not account for: downforce, banking, elevation, tire degradation
    """)

    try:
        fig_gg = gg_diagram.create_gg_plot(
            st.session_state.telemetry1,
            st.session_state.telemetry2,
            st.session_state.driver1_name,
            st.session_state.driver2_name,
            st.session_state.config,
        )
        st.plotly_chart(fig_gg, use_container_width=True)
    except Exception as e:
        st.error(f"Error creating G-G diagram: {e}")

    # Combined g-force
    st.markdown("---")
    st.subheader("Combined G-Force vs Distance")

    try:
        fig_combined_g = gg_diagram.create_combined_g_force_plot(
            st.session_state.telemetry1,
            st.session_state.telemetry2,
            st.session_state.driver1_name,
            st.session_state.driver2_name,
            st.session_state.config,
        )
        st.plotly_chart(fig_combined_g, use_container_width=True)
    except Exception as e:
        st.error(f"Error creating combined g-force plot: {e}")

    # Grip utilization stats
    st.markdown("---")
    st.subheader("Grip Utilization Statistics")

    try:
        accel1 = gg_diagram.compute_accelerations(st.session_state.telemetry1, st.session_state.config)
        accel2 = gg_diagram.compute_accelerations(st.session_state.telemetry2, st.session_state.config)

        stats1 = gg_diagram.analyze_grip_utilization(accel1)
        stats2 = gg_diagram.analyze_grip_utilization(accel2)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"**{st.session_state.driver1_name}**")
            st.markdown(f"- Max Longitudinal Accel: {stats1['max_longitudinal_accel_g']:.2f}g")
            st.markdown(f"- Max Braking Decel: {stats1['max_longitudinal_decel_g']:.2f}g")
            st.markdown(f"- Max Lateral: {stats1['max_lateral_accel_g']:.2f}g")
            st.markdown(f"- Max Combined: {stats1['max_combined_g']:.2f}g")
            st.markdown(f"- Time Braking: {stats1['percent_time_braking']:.1f}%")
            st.markdown(f"- Time Accelerating: {stats1['percent_time_accelerating']:.1f}%")

        with col2:
            st.markdown(f"**{st.session_state.driver2_name}**")
            st.markdown(f"- Max Longitudinal Accel: {stats2['max_longitudinal_accel_g']:.2f}g")
            st.markdown(f"- Max Braking Decel: {stats2['max_longitudinal_decel_g']:.2f}g")
            st.markdown(f"- Max Lateral: {stats2['max_lateral_accel_g']:.2f}g")
            st.markdown(f"- Max Combined: {stats2['max_combined_g']:.2f}g")
            st.markdown(f"- Time Braking: {stats2['percent_time_braking']:.1f}%")
            st.markdown(f"- Time Accelerating: {stats2['percent_time_accelerating']:.1f}%")

    except Exception as e:
        st.error(f"Error computing grip statistics: {e}")


def page_data_qa():
    """Data QA and session explorer page."""
    st.header("Data Quality & Session Explorer")

    if not st.session_state.data_loaded:
        st.info("Load data using the sidebar to begin analysis")
        return

    # Data availability
    st.subheader("Telemetry Channel Availability")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"**{st.session_state.driver1_name} Channels:**")
        for col in st.session_state.telemetry1.columns:
            st.markdown(f"- {col}")

    with col2:
        st.markdown(f"**{st.session_state.driver2_name} Channels:**")
        for col in st.session_state.telemetry2.columns:
            st.markdown(f"- {col}")

    # Data preview
    st.markdown("---")
    st.subheader("Telemetry Data Preview")

    tab1, tab2 = st.tabs([st.session_state.driver1_name, st.session_state.driver2_name])

    with tab1:
        st.dataframe(st.session_state.telemetry1.head(100), use_container_width=True)
        st.markdown(f"**Total samples:** {len(st.session_state.telemetry1)}")

    with tab2:
        st.dataframe(st.session_state.telemetry2.head(100), use_container_width=True)
        st.markdown(f"**Total samples:** {len(st.session_state.telemetry2)}")

    # Configuration display
    st.markdown("---")
    st.subheader("Analysis Configuration")

    config_df = pd.DataFrame([st.session_state.config.to_dict()]).T
    config_df.columns = ['Value']
    st.dataframe(config_df, use_container_width=True)

    # Cache management
    st.markdown("---")
    st.subheader("Cache Management")

    if st.button("Clear FastF1 Cache"):
        cache_dir = st.session_state.config.cache_dir
        if cache_dir.exists():
            import shutil
            shutil.rmtree(cache_dir)
            cache_dir.mkdir(parents=True, exist_ok=True)
            st.success(f"Cache cleared: {cache_dir}")
        else:
            st.info("No cache directory found")


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
            "Overview",
            "Lap Compare",
            "Minisectors & Delta Decomp",
            "Track Map & Corners",
            "G-G Diagram",
            "Data QA",
        ],
        index=0,
    )

    # Display selected page
    if page == "Overview":
        page_overview()
    elif page == "Lap Compare":
        page_lap_compare()
    elif page == "Minisectors & Delta Decomp":
        page_minisectors()
    elif page == "Track Map & Corners":
        page_track_map()
    elif page == "G-G Diagram":
        page_gg_diagram()
    elif page == "Data QA":
        page_data_qa()

    # Footer
    st.sidebar.markdown("---")
    st.sidebar.markdown("**F1 Telemetry Physics Lab**")
    st.sidebar.markdown("Author: João Pedro Cunha")
    st.sidebar.markdown("Version: 0.2.0")
    st.sidebar.markdown("Data Source: FastF1")


if __name__ == "__main__":
    main()
