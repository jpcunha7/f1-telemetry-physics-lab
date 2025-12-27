"""
Streamlit dashboard for F1 Telemetry Physics Lab.

Professional race engineering telemetry analysis tool.

Author: João Pedro Cunha
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
# Add app to path for components
sys.path.insert(0, str(Path(__file__).parent))

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
    braking_zones,
)

# Import UI components
from components import (
    render_kpi_cards,
    render_insight_summary,
    render_event_selector,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration - NO EMOJIS
st.set_page_config(
    page_title="F1 Telemetry Physics Lab",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize session state
if "data_loaded" not in st.session_state:
    st.session_state.data_loaded = False


def get_available_drivers(year: int, event: str, session_type: str):
    """Get list of available drivers for a session."""
    try:
        # Try to load session to get drivers
        import fastf1
        session = fastf1.get_session(year, event, session_type)
        session.load()

        # Get unique drivers
        if hasattr(session, 'drivers') and session.drivers is not None:
            drivers = session.drivers
            # Get driver info
            driver_info = []
            for driver_code in drivers:
                try:
                    driver_data = session.get_driver(driver_code)
                    if driver_data is not None and 'Abbreviation' in driver_data:
                        full_name = f"{driver_data.get('FirstName', '')} {driver_data.get('LastName', '')}".strip()
                        if not full_name:
                            full_name = driver_code
                        driver_info.append({
                            'code': driver_code,
                            'full_name': full_name,
                            'display': f"{full_name} ({driver_code})"
                        })
                except:
                    driver_info.append({
                        'code': driver_code,
                        'full_name': driver_code,
                        'display': driver_code
                    })
            return driver_info
    except:
        pass

    # Fallback to common 2024 drivers if we can't load
    return [
        {'code': 'VER', 'full_name': 'Max Verstappen', 'display': 'Max Verstappen (VER)'},
        {'code': 'PER', 'full_name': 'Sergio Perez', 'display': 'Sergio Perez (PER)'},
        {'code': 'LEC', 'full_name': 'Charles Leclerc', 'display': 'Charles Leclerc (LEC)'},
        {'code': 'SAI', 'full_name': 'Carlos Sainz', 'display': 'Carlos Sainz (SAI)'},
        {'code': 'HAM', 'full_name': 'Lewis Hamilton', 'display': 'Lewis Hamilton (HAM)'},
        {'code': 'RUS', 'full_name': 'George Russell', 'display': 'George Russell (RUS)'},
        {'code': 'NOR', 'full_name': 'Lando Norris', 'display': 'Lando Norris (NOR)'},
        {'code': 'PIA', 'full_name': 'Oscar Piastri', 'display': 'Oscar Piastri (PIA)'},
        {'code': 'ALO', 'full_name': 'Fernando Alonso', 'display': 'Fernando Alonso (ALO)'},
        {'code': 'STR', 'full_name': 'Lance Stroll', 'display': 'Lance Stroll (STR)'},
    ]


def sidebar_inputs():
    """Render sidebar input controls."""
    st.sidebar.title("F1 Telemetry Physics Lab")
    st.sidebar.markdown("Professional Race Engineering Tool")
    st.sidebar.markdown("---")

    # Session selection
    st.sidebar.subheader("Session Selection")

    # Year selector as dropdown
    year = st.sidebar.selectbox(
        "Year",
        options=[2024, 2023, 2022, 2021, 2020, 2019, 2018],
        index=0,
    )

    # Event selector (use existing component)
    event, event_metadata = render_event_selector(year, key_prefix="sidebar_event")

    # Session type with full names
    session_type_map = {
        "Practice 1": "FP1",
        "Practice 2": "FP2",
        "Practice 3": "FP3",
        "Qualifying": "Q",
        "Sprint": "S",
        "Race": "R",
    }

    session_display = st.sidebar.selectbox(
        "Session Type",
        options=list(session_type_map.keys()),
        index=3,  # Qualifying by default
    )
    session_type = session_type_map[session_display]

    st.sidebar.markdown("---")
    st.sidebar.subheader("Driver Selection")

    # Get available drivers (use cached fallback for initial render)
    if 'driver_list' not in st.session_state:
        st.session_state.driver_list = get_available_drivers(year, event, session_type)

    driver_list = st.session_state.driver_list
    driver_displays = [d['display'] for d in driver_list]
    driver_codes = {d['display']: d['code'] for d in driver_list}

    col1, col2 = st.sidebar.columns(2)

    with col1:
        driver1_display = st.selectbox(
            "Driver 1",
            options=driver_displays,
            index=0,  # First driver by default
            key="driver1_select",
        )
        driver1 = driver_codes[driver1_display]

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
        driver2_display = st.selectbox(
            "Driver 2",
            options=driver_displays,
            index=min(2, len(driver_displays) - 1),  # Third driver by default if available
            key="driver2_select",
        )
        driver2 = driver_codes[driver2_display]

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

    load_button = st.sidebar.button("Load Data", type="primary", use_container_width=True)

    return {
        "year": year,
        "event": event,
        "session_type": session_type,
        "driver1": driver1,
        "driver2": driver2,
        "lap1": lap1,
        "lap2": lap2,
        "resolution": 1.0,  # Hardcoded to 1m
        "num_minisectors": 50,  # Hardcoded (will be replaced with sectors)
        "load_button": load_button,
    }


def load_data(params):
    """Load and process telemetry data."""
    try:
        with st.spinner("Loading session data..."):
            # Create config
            config = cfg.Config(
                distance_resolution=params["resolution"],
                num_minisectors=params["num_minisectors"],
            )

            # Load data
            lap1, lap2, tel1_raw, tel2_raw, session = data_loader.load_lap_comparison_data(
                year=params["year"],
                event=params["event"],
                session_type=params["session_type"],
                driver1=params["driver1"],
                driver2=params["driver2"],
                lap1_selection=params["lap1"],
                lap2_selection=params["lap2"],
                config=config,
            )

            # Align laps
            tel1, tel2 = alignment.align_laps(tel1_raw, tel2_raw, config)

            # Add physics channels
            tel1 = physics.add_physics_channels(tel1, config)
            tel2 = physics.add_physics_channels(tel2, config)

            # Compute minisectors
            with st.spinner("Computing minisector analysis..."):
                minisector_data_obj = minisectors.compute_minisector_deltas(
                    tel1, tel2, config.num_minisectors, config
                )
                # Convert to DataFrame for compatibility with components
                minisector_data = minisectors.minisector_data_to_dataframe(
                    minisector_data_obj
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

            # Detect braking zones
            with st.spinner("Detecting braking zones..."):
                braking_zones1 = braking_zones.detect_braking_zones(tel1, config)
                braking_zones2 = braking_zones.detect_braking_zones(tel2, config)
                braking_comparison = braking_zones.compare_braking_zones(
                    braking_zones1, braking_zones2
                )

            # Create comparison summary
            comparison_summary = metrics.create_comparison_summary(
                lap1,
                lap2,
                tel1,
                tel2,
                params["driver1"],
                params["driver2"],
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
            st.session_state.driver1_name = params["driver1"]
            st.session_state.driver2_name = params["driver2"]
            st.session_state.config = config
            st.session_state.minisector_data = minisector_data
            st.session_state.corners1 = corners1
            st.session_state.corners2 = corners2
            st.session_state.decompositions = decompositions
            st.session_state.braking_zones1 = braking_zones1
            st.session_state.braking_zones2 = braking_zones2
            st.session_state.braking_comparison = braking_comparison

            st.success("Data loaded successfully!")

    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        logger.error(f"Data loading error: {e}", exc_info=True)


def format_lap_time(lap_time):
    """Format lap time to MM:SS.mmm format."""
    try:
        # lap_time is typically a timedelta object
        if pd.isna(lap_time):
            return "N/A"

        total_seconds = lap_time.total_seconds()
        minutes = int(total_seconds // 60)
        seconds = total_seconds % 60

        return f"{minutes}:{seconds:06.3f}"
    except Exception:
        return str(lap_time)


def page_overview():
    """Overview page with session summary."""
    st.header("Session Overview")

    if not st.session_state.data_loaded:
        st.info("Load data using the sidebar to begin analysis")
        return

    # Session info
    info = st.session_state.session_info

    # Use 3 columns for better text display (avoid truncation)
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Event", info["event_name"])
        st.metric("Country", info["country"])

    with col2:
        st.metric("Location", info["location"])
        st.metric("Session", info["session_type"])

    with col3:
        st.metric("Date", info["date"])

    st.markdown("---")

    # Lap times in proper motor racing format
    col1, col2 = st.columns(2)
    with col1:
        lap1_time = format_lap_time(st.session_state.lap1['LapTime'])
        st.metric(f"{st.session_state.driver1_name} Lap Time", lap1_time)

    with col2:
        lap2_time = format_lap_time(st.session_state.lap2['LapTime'])
        st.metric(f"{st.session_state.driver2_name} Lap Time", lap2_time)

    st.markdown("---")

    # KPI Cards
    render_kpi_cards(
        comparison_summary=st.session_state.comparison_summary,
        driver1_name=st.session_state.driver1_name,
        driver2_name=st.session_state.driver2_name,
        minisector_data=st.session_state.minisector_data,
    )

    st.markdown("---")

    # Insight Summary
    render_insight_summary(
        comparison_summary=st.session_state.comparison_summary,
        minisector_data=st.session_state.minisector_data,
        corners1=st.session_state.corners1,
        corners2=st.session_state.corners2,
        decompositions=st.session_state.decompositions,
        driver1_name=st.session_state.driver1_name,
        driver2_name=st.session_state.driver2_name,
    )

    # Quick stats
    st.markdown("---")
    st.subheader("Quick Statistics")

    col1, col2 = st.columns(2)

    with col1:
        if st.session_state.corners1:
            st.metric("Corners Detected", len(st.session_state.corners1))

    with col2:
        if st.session_state.braking_zones1:
            st.metric("Braking Zones", len(st.session_state.braking_zones1))


def page_lap_compare():
    """Enhanced lap comparison page."""
    st.header("Lap Comparison")

    if not st.session_state.data_loaded:
        st.info("Load data using the sidebar to begin analysis")
        return

    # Car animation on track
    if "X" in st.session_state.telemetry1.columns and "Y" in st.session_state.telemetry1.columns:
        st.subheader("Track Animation")

        try:
            import plotly.graph_objects as go

            # Create animation frames
            tel1 = st.session_state.telemetry1
            tel2 = st.session_state.telemetry2

            # Downsample for smoother animation
            step = max(1, len(tel1) // 200)  # Target ~200 frames

            fig_anim = go.Figure()

            # Add track outline
            fig_anim.add_trace(go.Scatter(
                x=tel1["X"],
                y=tel1["Y"],
                mode="lines",
                line=dict(color="gray", width=2),
                name="Track",
                showlegend=True,
            ))

            # Add both cars as initial points
            fig_anim.add_trace(go.Scatter(
                x=[tel1["X"].iloc[0]],
                y=[tel1["Y"].iloc[0]],
                mode="markers",
                marker=dict(size=15, color=st.session_state.config.primary_color),
                name=st.session_state.driver1_name,
            ))

            fig_anim.add_trace(go.Scatter(
                x=[tel2["X"].iloc[0]],
                y=[tel2["Y"].iloc[0]],
                mode="markers",
                marker=dict(size=15, color=st.session_state.config.secondary_color),
                name=st.session_state.driver2_name,
            ))

            # Create frames for animation
            frames = []
            for i in range(0, len(tel1), step):
                frames.append(go.Frame(
                    data=[
                        go.Scatter(x=tel1["X"], y=tel1["Y"]),  # Track
                        go.Scatter(x=[tel1["X"].iloc[i]], y=[tel1["Y"].iloc[i]]),  # Driver 1
                        go.Scatter(x=[tel2["X"].iloc[i]], y=[tel2["Y"].iloc[i]]),  # Driver 2
                    ],
                    name=str(i)
                ))

            fig_anim.frames = frames

            # Add play/pause buttons
            fig_anim.update_layout(
                updatemenus=[{
                    "type": "buttons",
                    "showactive": False,
                    "buttons": [
                        {"label": "Play", "method": "animate", "args": [None, {"frame": {"duration": 50}}]},
                        {"label": "Pause", "method": "animate", "args": [[None], {"frame": {"duration": 0}, "mode": "immediate"}]}
                    ]
                }],
                xaxis=dict(scaleanchor="y", scaleratio=1, showgrid=False),
                yaxis=dict(showgrid=False),
                plot_bgcolor="rgba(0,0,0,0)",
                height=400,
            )

            st.plotly_chart(fig_anim, use_container_width=True)
        except Exception as e:
            st.warning(f"Could not create track animation: {e}")

    st.markdown("---")

    # Region focus selector
    st.subheader("Focus Region")

    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        focus_mode = st.selectbox(
            "View Mode", options=["Full Lap", "Sector", "Corner"], key="lap_compare_focus_mode"
        )

    distance_range = None

    if focus_mode == "Sector":
        with col2:
            # Define 3 sectors
            total_distance = st.session_state.telemetry1["Distance"].max()
            sector_size = total_distance / 3

            sectors = {
                "Sector 1": (0, sector_size),
                "Sector 2": (sector_size, 2 * sector_size),
                "Sector 3": (2 * sector_size, total_distance),
            }

            selected_sector = st.selectbox(
                "Select Sector",
                options=list(sectors.keys()),
                key="lap_compare_sector",
            )

            distance_range = sectors[selected_sector]

            # Calculate sector delta
            tel1_delta = st.session_state.comparison_summary["delta_time"]
            start_idx = int(distance_range[0] / total_distance * len(tel1_delta))
            end_idx = int(distance_range[1] / total_distance * len(tel1_delta))
            sector_delta = tel1_delta[end_idx - 1] - tel1_delta[start_idx] if end_idx > start_idx else 0

            with col3:
                st.metric("Delta", f"{sector_delta:+.3f}s")

    elif focus_mode == "Corner":
        with col2:
            if st.session_state.corners1:
                # Show ALL corners
                corner_options = [f"Corner {i+1}" for i in range(len(st.session_state.corners1))]
                selected_corner = st.selectbox(
                    "Select Corner", options=corner_options, key="lap_compare_corner"
                )

                corner_idx = int(selected_corner.split()[-1]) - 1
                corner = st.session_state.corners1[corner_idx]

                # Define window around corner (e.g., ±100m)
                window = 100
                distance_range = (
                    max(0, corner.apex_distance - window),
                    corner.apex_distance + window,
                )

                with col3:
                    st.metric("Apex Dist", f"{corner.apex_distance:.0f}m")

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

    # Apply zoom if region selected
    if distance_range:
        fig_speed.update_xaxes(range=distance_range)

    st.plotly_chart(fig_speed, use_container_width=True)

    # Delta time
    st.subheader("Delta Time Analysis")
    fig_delta = viz.create_delta_time_plot(
        st.session_state.comparison_summary["delta_time"],
        st.session_state.telemetry1["Distance"].values,
        st.session_state.driver1_name,
        st.session_state.driver2_name,
        st.session_state.config,
    )

    # Apply zoom if region selected
    if distance_range:
        fig_delta.update_xaxes(range=distance_range)

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

    # Apply zoom if region selected
    if distance_range:
        fig_tb.update_xaxes(range=distance_range)

    st.plotly_chart(fig_tb, use_container_width=True)

    # Gear comparison (nGear)
    if "nGear" in st.session_state.telemetry1.columns and "nGear" in st.session_state.telemetry2.columns:
        st.subheader("Gear Comparison")

        try:
            import plotly.graph_objects as go

            fig_gear = go.Figure()

            # Driver 1 gear
            fig_gear.add_trace(go.Scatter(
                x=st.session_state.telemetry1["Distance"],
                y=st.session_state.telemetry1["nGear"],
                mode="lines",
                name=st.session_state.driver1_name,
                line=dict(color=st.session_state.config.primary_color, width=2),
            ))

            # Driver 2 gear
            fig_gear.add_trace(go.Scatter(
                x=st.session_state.telemetry2["Distance"],
                y=st.session_state.telemetry2["nGear"],
                mode="lines",
                name=st.session_state.driver2_name,
                line=dict(color=st.session_state.config.secondary_color, width=2),
            ))

            fig_gear.update_layout(
                xaxis_title="Distance (m)",
                yaxis_title="Gear",
                yaxis=dict(dtick=1),
                height=400,
                hovermode="x unified",
                plot_bgcolor="rgba(0,0,0,0)",
            )

            # Apply zoom if region selected
            if distance_range:
                fig_gear.update_xaxes(range=distance_range)

            st.plotly_chart(fig_gear, use_container_width=True)
        except Exception as e:
            st.warning(f"Could not create gear plot: {e}")
    else:
        st.info("Gear data (nGear) not available for this session")


def page_minisectors():
    """Corner delta decomposition and braking zones analysis page."""
    st.header("Delta Decomposition Analysis")

    if not st.session_state.data_loaded:
        st.info("Load data using the sidebar to begin analysis")
        return

    # Braking zones analysis
    st.subheader("Braking Zones Analysis")

    if not st.session_state.braking_comparison.empty:
        st.markdown("**Zone-by-Zone Comparison**")
        st.dataframe(
            st.session_state.braking_comparison[
                [
                    "Zone_ID",
                    "Start_Dist_Driver1",
                    "Start_Dist_Driver2",
                    "Brake_Start_Delta_m",
                    "Entry_Speed_Driver1",
                    "Entry_Speed_Driver2",
                    "Entry_Speed_Delta",
                    "Min_Speed_Driver1",
                    "Min_Speed_Driver2",
                    "Min_Speed_Delta",
                    "Max_Decel_Driver1",
                    "Max_Decel_Driver2",
                    "Max_Decel_Delta",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

        # Top differences
        st.markdown("**Top 3 Most Different Braking Zones**")
        top_gains, top_losses = braking_zones.get_top_braking_differences(
            st.session_state.braking_comparison, n=3, sort_by="Brake_Start_Delta_m"
        )

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Later Braking ({st.session_state.driver1_name})**")
            if not top_gains.empty:
                st.dataframe(
                    top_gains[
                        [
                            "Zone_ID",
                            "Brake_Start_Delta_m",
                            "Entry_Speed_Delta",
                            "Approx_Time_Delta_s",
                        ]
                    ],
                    hide_index=True,
                )
        with col2:
            st.markdown(f"**Earlier Braking ({st.session_state.driver1_name})**")
            if not top_losses.empty:
                st.dataframe(
                    top_losses[
                        [
                            "Zone_ID",
                            "Brake_Start_Delta_m",
                            "Entry_Speed_Delta",
                            "Approx_Time_Delta_s",
                        ]
                    ],
                    hide_index=True,
                )
    else:
        st.warning("⚠️ Brake telemetry data is not available for this session. Braking zones analysis cannot be performed.")

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
            for phase, pct in pattern["phase_percentages"].items():
                st.markdown(f"- {phase.replace('_', ' ').title()}: {pct:.1f}%")

        with col2:
            st.markdown(
                f"**Primary Weakness:** {pattern['primary_weakness'].replace('_', ' ').title()}"
            )
            st.markdown("**Total Delta by Phase:**")
            for phase, delta in pattern["phase_total_deltas"].items():
                st.markdown(f"- {phase.replace('_', ' ').title()}: {delta:+.3f}s")


def page_track_map():
    """Track map with corner markers and fastest driver comparison."""
    st.header("Track Map & Corner Catalog")

    if not st.session_state.data_loaded:
        st.info("Load data using the sidebar to begin analysis")
        return

    # Check for position data
    if "X" not in st.session_state.telemetry1.columns:
        st.warning(
            "Position data (X, Y) not available for this session. Track maps cannot be displayed."
        )
        return

    # Fastest driver comparison map
    st.subheader("Fastest Driver by Track Region")

    try:
        import plotly.graph_objects as go
        import numpy as np

        tel1 = st.session_state.telemetry1
        tel2 = st.session_state.telemetry2

        # Calculate who is faster at each point (based on cumulative delta)
        delta_time = st.session_state.comparison_summary["delta_time"]

        # Create color array (driver 1 faster = primary color, driver 2 faster = secondary color)
        colors = np.where(
            delta_time < 0,
            st.session_state.config.primary_color,
            st.session_state.config.secondary_color
        )

        # Create scatter plot with colored segments
        fig_fastest = go.Figure()

        # Add track colored by fastest driver
        fig_fastest.add_trace(go.Scatter(
            x=tel1["X"],
            y=tel1["Y"],
            mode="markers",
            marker=dict(
                size=8,
                color=colors,
                colorscale=[
                    [0, st.session_state.config.primary_color],
                    [1, st.session_state.config.secondary_color]
                ],
                showscale=False,
            ),
            showlegend=False,  # Don't show track in legend
            hovertemplate="Distance: %{text}<br>X: %{x}<br>Y: %{y}<extra></extra>",
            text=[f"{d:.0f}m" for d in tel1["Distance"]],
        ))

        fig_fastest.update_layout(
            xaxis=dict(scaleanchor="y", scaleratio=1, showgrid=False, title=""),
            yaxis=dict(showgrid=False, title=""),
            plot_bgcolor="rgba(0,0,0,0)",
            height=600,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )

        # Add legend manually
        fig_fastest.add_trace(go.Scatter(
            x=[None], y=[None],
            mode='markers',
            marker=dict(size=10, color=st.session_state.config.primary_color),
            showlegend=True,
            name=f"{st.session_state.driver1_name} faster"
        ))

        fig_fastest.add_trace(go.Scatter(
            x=[None], y=[None],
            mode='markers',
            marker=dict(size=10, color=st.session_state.config.secondary_color),
            showlegend=True,
            name=f"{st.session_state.driver2_name} faster"
        ))

        st.plotly_chart(fig_fastest, use_container_width=True)
    except Exception as e:
        st.error(f"Error creating fastest driver map: {e}")

    # Corner markers map
    st.markdown("---")
    st.subheader("Corner Catalog Map")

    driver_choice = st.radio(
        "View corners from:",
        [st.session_state.driver1_name, st.session_state.driver2_name],
        horizontal=True,
        key="corner_map_driver_choice",
    )

    # Make sure telemetry matches driver choice
    tel_choice = (
        st.session_state.telemetry1
        if driver_choice == st.session_state.driver1_name
        else st.session_state.telemetry2
    )

    corners_choice = (
        st.session_state.corners1
        if driver_choice == st.session_state.driver1_name
        else st.session_state.corners2
    )

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

        # Sort options
        col1, col2 = st.columns([3, 1])
        with col1:
            sort_by = st.selectbox(
                "Sort by",
                options=["Corner ID", "Min Speed Delta", "Apex Distance"],
                key="corner_sort",
            )
        with col2:
            sort_ascending = st.checkbox("Ascending", value=True, key="corner_sort_asc")

        corner_table = corners_module.create_corner_report_table(
            st.session_state.corners1,
            st.session_state.corners2,
            st.session_state.driver1_name,
            st.session_state.driver2_name,
        )

        # Sort table
        if not corner_table.empty:
            if sort_by == "Corner ID":
                corner_table = corner_table.sort_values("Corner", ascending=sort_ascending)
            elif sort_by == "Min Speed Delta":
                if "Min_Speed_Delta" in corner_table.columns:
                    corner_table = corner_table.sort_values(
                        "Min_Speed_Delta", ascending=sort_ascending
                    )
            elif sort_by == "Apex Distance":
                if "Apex_Distance" in corner_table.columns:
                    corner_table = corner_table.sort_values(
                        "Apex_Distance", ascending=sort_ascending
                    )

        st.dataframe(corner_table, use_container_width=True, hide_index=True)

        # Highlight top gains/losses
        if not corner_table.empty and "Min_Speed_Delta" in corner_table.columns:
            st.markdown("**Top 3 Corners**")
            col1, col2 = st.columns(2)

            with col1:
                st.markdown(f"**Fastest ({st.session_state.driver1_name})**")
                top_fastest = corner_table.nsmallest(3, "Min_Speed_Delta")[
                    ["Corner", "Min_Speed_Delta", "Apex_Distance"]
                ]
                st.dataframe(top_fastest, hide_index=True)

            with col2:
                st.markdown(f"**Slowest ({st.session_state.driver1_name})**")
                top_slowest = corner_table.nlargest(3, "Min_Speed_Delta")[
                    ["Corner", "Min_Speed_Delta", "Apex_Distance"]
                ]
                st.dataframe(top_slowest, hide_index=True)
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

    st.markdown(
        """
    **Physics Note:** The g-g diagram shows longitudinal vs lateral acceleration.
    - Longitudinal: computed from speed change (braking = negative, traction = positive)
    - Lateral: approximated from track curvature and speed (requires X,Y position data)
    - Approximations do not account for: downforce, banking, elevation, tire degradation
    """
    )

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
        accel1 = gg_diagram.compute_accelerations(
            st.session_state.telemetry1, st.session_state.config
        )
        accel2 = gg_diagram.compute_accelerations(
            st.session_state.telemetry2, st.session_state.config
        )

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

    # Data availability matrix
    st.subheader("Telemetry Channel Availability Matrix")

    # Get all unique channels
    all_channels = set(st.session_state.telemetry1.columns) | set(
        st.session_state.telemetry2.columns
    )

    # Build availability matrix
    availability_data = []
    for channel in sorted(all_channels):
        driver1_has = channel in st.session_state.telemetry1.columns
        driver2_has = channel in st.session_state.telemetry2.columns

        # Calculate missing percentage
        driver1_missing = 0
        driver2_missing = 0

        if driver1_has:
            driver1_missing = (
                st.session_state.telemetry1[channel].isna().sum() / len(st.session_state.telemetry1)
            ) * 100

        if driver2_has:
            driver2_missing = (
                st.session_state.telemetry2[channel].isna().sum() / len(st.session_state.telemetry2)
            ) * 100

        availability_data.append(
            {
                "Channel": channel,
                f"{st.session_state.driver1_name} Available": "✓" if driver1_has else "✗",
                f"{st.session_state.driver1_name} % Missing": f"{driver1_missing:.1f}%"
                if driver1_has
                else "N/A",
                f"{st.session_state.driver2_name} Available": "✓" if driver2_has else "✗",
                f"{st.session_state.driver2_name} % Missing": f"{driver2_missing:.1f}%"
                if driver2_has
                else "N/A",
            }
        )

    availability_df = pd.DataFrame(availability_data)
    st.dataframe(availability_df, use_container_width=True, hide_index=True)

    # Warning banners
    st.subheader("Data Warnings")

    warnings_found = False

    # Check for X/Y position data
    if (
        "X" not in st.session_state.telemetry1.columns
        or "Y" not in st.session_state.telemetry1.columns
    ):
        st.warning("⚠️ No X/Y position data: Track maps and lateral g analysis disabled")
        warnings_found = True

    # Check for brake channel
    if "Brake" not in st.session_state.telemetry1.columns:
        st.warning("⚠️ Brake channel missing: Braking zones analysis disabled")
        warnings_found = True

    # Check for gear channel
    if "nGear" not in st.session_state.telemetry1.columns:
        st.warning("⚠️ Gear channel missing: Gear analysis disabled")
        warnings_found = True

    if not warnings_found:
        st.success("✓ All critical channels available!")

    # Lap validity stats
    st.markdown("---")
    st.subheader("Lap Validity Statistics")

    if st.session_state.session:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"**{st.session_state.driver1_name}**")
            driver1_all_laps = st.session_state.session.laps.pick_driver(
                st.session_state.driver1_name
            )
            if not driver1_all_laps.empty:
                total_laps = len(driver1_all_laps)
                if "IsAccurate" in driver1_all_laps.columns:
                    valid_laps = driver1_all_laps["IsAccurate"].sum()
                    invalid_laps = total_laps - valid_laps
                    st.metric("Total Laps", total_laps)
                    st.metric("Valid Laps", valid_laps)
                    st.metric("Invalid Laps", invalid_laps)
                else:
                    st.metric("Total Laps", total_laps)
                    st.caption("Validity information not available")

        with col2:
            st.markdown(f"**{st.session_state.driver2_name}**")
            driver2_all_laps = st.session_state.session.laps.pick_driver(
                st.session_state.driver2_name
            )
            if not driver2_all_laps.empty:
                total_laps = len(driver2_all_laps)
                if "IsAccurate" in driver2_all_laps.columns:
                    valid_laps = driver2_all_laps["IsAccurate"].sum()
                    invalid_laps = total_laps - valid_laps
                    st.metric("Total Laps", total_laps)
                    st.metric("Valid Laps", valid_laps)
                    st.metric("Invalid Laps", invalid_laps)
                else:
                    st.metric("Total Laps", total_laps)
                    st.caption("Validity information not available")

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
    config_df.columns = ["Value"]
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

    if params["load_button"]:
        load_data(params)

    # Page navigation
    page = st.sidebar.radio(
        "Navigation",
        options=[
            "Overview",
            "Lap Compare",
            "Delta Decomposition",
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
    elif page == "Delta Decomposition":
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
