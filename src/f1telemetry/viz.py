"""
Visualization module for F1 Telemetry Physics Lab.

Creates high-quality interactive plots for lap comparison analysis.

Author: João Pedro Cunha
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from f1telemetry.config import Config, DEFAULT_CONFIG
from f1telemetry.metrics import SegmentComparison

logger = logging.getLogger(__name__)


def create_speed_comparison_plot(
    telemetry1: pd.DataFrame,
    telemetry2: pd.DataFrame,
    driver1_name: str,
    driver2_name: str,
    config: Config = DEFAULT_CONFIG,
) -> go.Figure:
    """
    Create speed vs distance comparison plot.

    Args:
        telemetry1: Aligned telemetry for driver 1
        telemetry2: Aligned telemetry for driver 2
        driver1_name: Name/code for driver 1
        driver2_name: Name/code for driver 2
        config: Configuration

    Returns:
        Plotly figure
    """
    fig = go.Figure()

    # Driver 1
    fig.add_trace(go.Scatter(
        x=telemetry1['Distance'],
        y=telemetry1['Speed'],
        mode='lines',
        name=driver1_name,
        line=dict(color='#FF1E1E', width=2),
    ))

    # Driver 2
    fig.add_trace(go.Scatter(
        x=telemetry2['Distance'],
        y=telemetry2['Speed'],
        mode='lines',
        name=driver2_name,
        line=dict(color='#1E90FF', width=2),
    ))

    fig.update_layout(
        title='Speed Comparison',
        xaxis_title='Distance (m)',
        yaxis_title='Speed (km/h)',
        template=config.plot_theme,
        width=config.plot_width,
        height=config.plot_height,
        hovermode='x unified',
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
    )

    return fig


def create_throttle_brake_plot(
    telemetry1: pd.DataFrame,
    telemetry2: pd.DataFrame,
    driver1_name: str,
    driver2_name: str,
    config: Config = DEFAULT_CONFIG,
) -> go.Figure:
    """
    Create throttle and brake comparison plot.

    Args:
        telemetry1: Aligned telemetry for driver 1
        telemetry2: Aligned telemetry for driver 2
        driver1_name: Name/code for driver 1
        driver2_name: Name/code for driver 2
        config: Configuration

    Returns:
        Plotly figure with subplots
    """
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Throttle Application', 'Brake Pressure'),
        vertical_spacing=0.12,
    )

    # Throttle - Driver 1
    if 'Throttle' in telemetry1.columns:
        fig.add_trace(go.Scatter(
            x=telemetry1['Distance'],
            y=telemetry1['Throttle'],
            mode='lines',
            name=f'{driver1_name} Throttle',
            line=dict(color='#FF1E1E', width=2),
        ), row=1, col=1)

    # Throttle - Driver 2
    if 'Throttle' in telemetry2.columns:
        fig.add_trace(go.Scatter(
            x=telemetry2['Distance'],
            y=telemetry2['Throttle'],
            mode='lines',
            name=f'{driver2_name} Throttle',
            line=dict(color='#1E90FF', width=2),
        ), row=1, col=1)

    # Brake - Driver 1
    if 'Brake' in telemetry1.columns:
        fig.add_trace(go.Scatter(
            x=telemetry1['Distance'],
            y=telemetry1['Brake'],
            mode='lines',
            name=f'{driver1_name} Brake',
            line=dict(color='#FF1E1E', width=2),
            showlegend=False,
        ), row=2, col=1)

    # Brake - Driver 2
    if 'Brake' in telemetry2.columns:
        fig.add_trace(go.Scatter(
            x=telemetry2['Distance'],
            y=telemetry2['Brake'],
            mode='lines',
            name=f'{driver2_name} Brake',
            line=dict(color='#1E90FF', width=2),
            showlegend=False,
        ), row=2, col=1)

    fig.update_xaxes(title_text="Distance (m)", row=2, col=1)
    fig.update_yaxes(title_text="Throttle (%)", row=1, col=1)
    fig.update_yaxes(title_text="Brake (%)", row=2, col=1)

    fig.update_layout(
        template=config.plot_theme,
        width=config.plot_width,
        height=config.plot_height * 1.2,
        hovermode='x unified',
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
    )

    return fig


def create_gear_plot(
    telemetry1: pd.DataFrame,
    telemetry2: pd.DataFrame,
    driver1_name: str,
    driver2_name: str,
    config: Config = DEFAULT_CONFIG,
) -> go.Figure:
    """
    Create gear selection comparison plot.

    Args:
        telemetry1: Aligned telemetry for driver 1
        telemetry2: Aligned telemetry for driver 2
        driver1_name: Name/code for driver 1
        driver2_name: Name/code for driver 2
        config: Configuration

    Returns:
        Plotly figure
    """
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=(f'{driver1_name} Gear', f'{driver2_name} Gear'),
        vertical_spacing=0.12,
    )

    # Driver 1
    if 'nGear' in telemetry1.columns:
        fig.add_trace(go.Scatter(
            x=telemetry1['Distance'],
            y=telemetry1['nGear'],
            mode='lines',
            name=driver1_name,
            line=dict(color='#FF1E1E', width=2),
            fill='tozeroy',
        ), row=1, col=1)

    # Driver 2
    if 'nGear' in telemetry2.columns:
        fig.add_trace(go.Scatter(
            x=telemetry2['Distance'],
            y=telemetry2['nGear'],
            mode='lines',
            name=driver2_name,
            line=dict(color='#1E90FF', width=2),
            fill='tozeroy',
        ), row=2, col=1)

    fig.update_xaxes(title_text="Distance (m)", row=2, col=1)
    fig.update_yaxes(title_text="Gear", row=1, col=1)
    fig.update_yaxes(title_text="Gear", row=2, col=1)

    fig.update_layout(
        template=config.plot_theme,
        width=config.plot_width,
        height=config.plot_height * 1.2,
        showlegend=False,
    )

    return fig


def create_delta_time_plot(
    delta_time: np.ndarray,
    distance: np.ndarray,
    driver1_name: str,
    driver2_name: str,
    config: Config = DEFAULT_CONFIG,
) -> go.Figure:
    """
    Create cumulative delta time plot.

    Args:
        delta_time: Delta time array (positive = driver1 slower)
        distance: Distance array
        driver1_name: Name/code for driver 1
        driver2_name: Name/code for driver 2
        config: Configuration

    Returns:
        Plotly figure
    """
    fig = go.Figure()

    # Color based on who's ahead
    colors = ['#FF1E1E' if dt > 0 else '#1E90FF' for dt in delta_time]

    fig.add_trace(go.Scatter(
        x=distance,
        y=delta_time,
        mode='lines',
        name='Delta Time',
        line=dict(color='#00FF00', width=2),
        fill='tozeroy',
    ))

    # Add zero line
    fig.add_hline(y=0, line_dash="dash", line_color="gray")

    fig.update_layout(
        title=f'Cumulative Delta Time ({driver2_name} - {driver1_name})',
        xaxis_title='Distance (m)',
        yaxis_title='Delta Time (s)',
        template=config.plot_theme,
        width=config.plot_width,
        height=config.plot_height,
        hovermode='x unified',
        annotations=[
            dict(
                x=0.02, y=0.98,
                xref='paper', yref='paper',
                text=f'Positive = {driver1_name} slower<br>Negative = {driver1_name} faster',
                showarrow=False,
                bgcolor='rgba(0,0,0,0.5)',
                font=dict(size=10),
            )
        ],
    )

    return fig


def create_segment_comparison_plot(
    segment_comparisons: list[SegmentComparison],
    driver1_name: str,
    driver2_name: str,
    config: Config = DEFAULT_CONFIG,
) -> go.Figure:
    """
    Create segment comparison bar chart.

    Args:
        segment_comparisons: List of SegmentComparison objects
        driver1_name: Name/code for driver 1
        driver2_name: Name/code for driver 2
        config: Configuration

    Returns:
        Plotly figure
    """
    segments = [f"Seg {s.segment_num}" for s in segment_comparisons]
    deltas = [s.time_delta for s in segment_comparisons]

    # Color based on winner
    colors = ['#1E90FF' if d < 0 else '#FF1E1E' for d in deltas]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=segments,
        y=deltas,
        marker_color=colors,
        name='Time Delta',
    ))

    fig.add_hline(y=0, line_dash="dash", line_color="gray")

    fig.update_layout(
        title='Segment-by-Segment Comparison',
        xaxis_title='Segment',
        yaxis_title='Time Delta (s)',
        template=config.plot_theme,
        width=config.plot_width,
        height=config.plot_height,
        showlegend=False,
        annotations=[
            dict(
                x=0.02, y=0.98,
                xref='paper', yref='paper',
                text=f'Red = {driver1_name} slower<br>Blue = {driver1_name} faster',
                showarrow=False,
                bgcolor='rgba(0,0,0,0.5)',
                font=dict(size=10),
            )
        ],
    )

    return fig


def create_track_map(
    telemetry1: pd.DataFrame,
    telemetry2: pd.DataFrame,
    driver1_name: str,
    driver2_name: str,
    color_by: str = 'Speed',
    config: Config = DEFAULT_CONFIG,
) -> go.Figure:
    """
    Create track map visualization colored by a telemetry channel.

    Args:
        telemetry1: Aligned telemetry for driver 1
        telemetry2: Aligned telemetry for driver 2
        driver1_name: Name/code for driver 1
        driver2_name: Name/code for driver 2
        color_by: Column name to color by (default: Speed)
        config: Configuration

    Returns:
        Plotly figure
    """
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=(f'{driver1_name}', f'{driver2_name}'),
        specs=[[{'type': 'scatter'}, {'type': 'scatter'}]],
    )

    # Check if position data is available
    if 'X' not in telemetry1.columns or 'Y' not in telemetry1.columns:
        logger.warning("Position data (X, Y) not available for track map")
        fig.add_annotation(
            text="Position data not available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
        )
        return fig

    # Driver 1 track map
    if color_by in telemetry1.columns:
        fig.add_trace(go.Scatter(
            x=telemetry1['X'],
            y=telemetry1['Y'],
            mode='markers',
            marker=dict(
                size=3,
                color=telemetry1[color_by],
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(x=0.45, len=0.5),
            ),
            name=driver1_name,
            showlegend=False,
        ), row=1, col=1)

    # Driver 2 track map
    if color_by in telemetry2.columns:
        fig.add_trace(go.Scatter(
            x=telemetry2['X'],
            y=telemetry2['Y'],
            mode='markers',
            marker=dict(
                size=3,
                color=telemetry2[color_by],
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(x=1.02, len=0.5),
            ),
            name=driver2_name,
            showlegend=False,
        ), row=1, col=2)

    fig.update_xaxes(showgrid=False, showticklabels=False)
    fig.update_yaxes(showgrid=False, showticklabels=False)

    fig.update_layout(
        title=f'Track Map (colored by {color_by})',
        template=config.plot_theme,
        width=config.plot_width * 1.5,
        height=config.plot_height,
    )

    return fig


def create_acceleration_plot(
    telemetry1: pd.DataFrame,
    telemetry2: pd.DataFrame,
    driver1_name: str,
    driver2_name: str,
    config: Config = DEFAULT_CONFIG,
) -> go.Figure:
    """
    Create acceleration comparison plot.

    Args:
        telemetry1: Aligned telemetry for driver 1 (with Acceleration column)
        telemetry2: Aligned telemetry for driver 2 (with Acceleration column)
        driver1_name: Name/code for driver 1
        driver2_name: Name/code for driver 2
        config: Configuration

    Returns:
        Plotly figure
    """
    fig = go.Figure()

    # Driver 1
    if 'Acceleration' in telemetry1.columns:
        fig.add_trace(go.Scatter(
            x=telemetry1['Distance'],
            y=telemetry1['Acceleration'],
            mode='lines',
            name=driver1_name,
            line=dict(color='#FF1E1E', width=2),
        ))

    # Driver 2
    if 'Acceleration' in telemetry2.columns:
        fig.add_trace(go.Scatter(
            x=telemetry2['Distance'],
            y=telemetry2['Acceleration'],
            mode='lines',
            name=driver2_name,
            line=dict(color='#1E90FF', width=2),
        ))

    fig.add_hline(y=0, line_dash="dash", line_color="gray")

    fig.update_layout(
        title='Longitudinal Acceleration',
        xaxis_title='Distance (m)',
        yaxis_title='Acceleration (m/s²)',
        template=config.plot_theme,
        width=config.plot_width,
        height=config.plot_height,
        hovermode='x unified',
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
    )

    return fig
