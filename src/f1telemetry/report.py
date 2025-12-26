"""
Report generation module for F1 Telemetry Physics Lab.

Generates HTML reports and saves visualizations.

Author: João Pedro Cunha
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
from jinja2 import Template

from f1telemetry.config import Config, DEFAULT_CONFIG
from f1telemetry import physics, metrics, viz

logger = logging.getLogger(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>F1 Telemetry Comparison Report - {{ session_info.event_name }}</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            background-color: #0f0f0f;
            color: #e0e0e0;
        }
        h1 {
            color: #ff1e1e;
            border-bottom: 3px solid #ff1e1e;
            padding-bottom: 10px;
        }
        h2 {
            color: #1e90ff;
            margin-top: 30px;
        }
        .header {
            background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }
        .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        .info-item {
            background-color: #1a1a1a;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #ff1e1e;
        }
        .info-label {
            font-size: 12px;
            color: #888;
            text-transform: uppercase;
        }
        .info-value {
            font-size: 18px;
            font-weight: bold;
            color: #fff;
        }
        .insights {
            background-color: #1a1a1a;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
            border-left: 5px solid #00ff00;
        }
        .insight-item {
            padding: 8px 0;
            font-size: 16px;
        }
        .plot {
            margin: 30px 0;
            text-align: center;
        }
        .footer {
            margin-top: 50px;
            padding: 20px;
            text-align: center;
            color: #666;
            border-top: 1px solid #333;
        }
        .assumption-box {
            background-color: #2d1a1a;
            border-left: 4px solid #ff6b6b;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
        }
        .assumption-box h3 {
            margin-top: 0;
            color: #ff6b6b;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🏎️ F1 Telemetry Physics Lab</h1>
        <h2>Lap Comparison Report</h2>
        <p><strong>Event:</strong> {{ session_info.event_name }} - {{ session_info.location }}, {{ session_info.country }}</p>
        <p><strong>Session:</strong> {{ session_info.session_type }}</p>
        <p><strong>Date:</strong> {{ session_info.date }}</p>
        <p><strong>Generated:</strong> {{ generation_time }}</p>
    </div>

    <div class="info-grid">
        <div class="info-item">
            <div class="info-label">Driver 1</div>
            <div class="info-value" style="color: #ff1e1e;">{{ driver1_name }}</div>
        </div>
        <div class="info-item">
            <div class="info-label">Driver 2</div>
            <div class="info-value" style="color: #1e90ff;">{{ driver2_name }}</div>
        </div>
        <div class="info-item">
            <div class="info-label">Final Delta</div>
            <div class="info-value">{{ "%.3f"|format(final_delta) }} s</div>
        </div>
    </div>

    <div class="insights">
        <h3>📊 Key Insights</h3>
        {% for insight in insights %}
        <div class="insight-item">{{ insight }}</div>
        {% endfor %}
    </div>

    <h2>Speed Comparison</h2>
    <div class="plot">{{ plot_speed }}</div>

    <h2>Delta Time Analysis</h2>
    <div class="plot">{{ plot_delta }}</div>

    <h2>Segment Comparison</h2>
    <div class="plot">{{ plot_segments }}</div>

    <h2>Throttle & Brake Application</h2>
    <div class="plot">{{ plot_throttle_brake }}</div>

    <h2>Gear Selection</h2>
    <div class="plot">{{ plot_gear }}</div>

    <h2>Acceleration Profile</h2>
    <div class="plot">{{ plot_acceleration }}</div>

    <h2>Track Map</h2>
    <div class="plot">{{ plot_track_map }}</div>

    <div class="assumption-box">
        <h3>⚠️ Physics Approximations & Limitations</h3>
        <ul>
            <li>Acceleration is computed from speed and distance data using kinematic approximations</li>
            <li>No vehicle mass, drag coefficient, or detailed aerodynamic model is used</li>
            <li>Track elevation changes are ignored</li>
            <li>Tire degradation and temperature effects are not modeled</li>
            <li>All calculations are approximate and intended for comparative analysis only</li>
        </ul>
    </div>

    <div class="footer">
        <p><strong>F1 Telemetry Physics Lab</strong></p>
        <p>Author: João Pedro Cunha | Data: FastF1</p>
    </div>
</body>
</html>
"""


def generate_html_report(
    lap1: object,
    lap2: object,
    telemetry1: pd.DataFrame,
    telemetry2: pd.DataFrame,
    session_info: dict,
    driver1_name: str,
    driver2_name: str,
    config: Config = DEFAULT_CONFIG,
    output_path: Optional[Path] = None,
) -> str:
    """
    Generate HTML report for lap comparison.

    Args:
        lap1: FastF1 Lap object for driver 1
        lap2: FastF1 Lap object for driver 2
        telemetry1: Aligned telemetry for driver 1
        telemetry2: Aligned telemetry for driver 2
        session_info: Session metadata dictionary
        driver1_name: Name/code for driver 1
        driver2_name: Name/code for driver 2
        config: Configuration
        output_path: Optional path to save report

    Returns:
        HTML report string
    """
    logger.info("Generating HTML report...")

    # Add physics channels
    telemetry1 = physics.add_physics_channels(telemetry1, config)
    telemetry2 = physics.add_physics_channels(telemetry2, config)

    # Compute metrics
    comparison_summary = metrics.create_comparison_summary(
        lap1,
        lap2,
        telemetry1,
        telemetry2,
        driver1_name,
        driver2_name,
        config,
    )

    # Create plots
    plot_speed = viz.create_speed_comparison_plot(
        telemetry1, telemetry2, driver1_name, driver2_name, config
    ).to_html(include_plotlyjs="cdn", div_id="speed_plot")

    plot_delta = viz.create_delta_time_plot(
        comparison_summary["delta_time"],
        telemetry1["Distance"].values,
        driver1_name,
        driver2_name,
        config,
    ).to_html(include_plotlyjs=False, div_id="delta_plot")

    plot_segments = viz.create_segment_comparison_plot(
        comparison_summary["segment_comparisons"],
        driver1_name,
        driver2_name,
        config,
    ).to_html(include_plotlyjs=False, div_id="segments_plot")

    plot_throttle_brake = viz.create_throttle_brake_plot(
        telemetry1, telemetry2, driver1_name, driver2_name, config
    ).to_html(include_plotlyjs=False, div_id="throttle_brake_plot")

    plot_gear = viz.create_gear_plot(
        telemetry1, telemetry2, driver1_name, driver2_name, config
    ).to_html(include_plotlyjs=False, div_id="gear_plot")

    plot_acceleration = viz.create_acceleration_plot(
        telemetry1, telemetry2, driver1_name, driver2_name, config
    ).to_html(include_plotlyjs=False, div_id="acceleration_plot")

    plot_track_map = viz.create_track_map(
        telemetry1, telemetry2, driver1_name, driver2_name, "Speed", config
    ).to_html(include_plotlyjs=False, div_id="track_map_plot")

    # Render template
    template = Template(HTML_TEMPLATE)
    html_content = template.render(
        session_info=session_info,
        driver1_name=driver1_name,
        driver2_name=driver2_name,
        final_delta=comparison_summary["final_delta"],
        insights=comparison_summary["insights"],
        plot_speed=plot_speed,
        plot_delta=plot_delta,
        plot_segments=plot_segments,
        plot_throttle_brake=plot_throttle_brake,
        plot_gear=plot_gear,
        plot_acceleration=plot_acceleration,
        plot_track_map=plot_track_map,
        generation_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )

    # Save if output path provided
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html_content, encoding="utf-8")
        logger.info(f"Report saved to: {output_path}")

    return html_content


def save_plots_as_images(
    telemetry1: pd.DataFrame,
    telemetry2: pd.DataFrame,
    driver1_name: str,
    driver2_name: str,
    comparison_summary: dict,
    output_dir: Path,
    config: Config = DEFAULT_CONFIG,
) -> None:
    """
    Save all plots as PNG images.

    Args:
        telemetry1: Aligned telemetry for driver 1
        telemetry2: Aligned telemetry for driver 2
        driver1_name: Name/code for driver 1
        driver2_name: Name/code for driver 2
        comparison_summary: Comparison summary from metrics
        output_dir: Directory to save images
        config: Configuration
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Saving plots to: {output_dir}")

    # Create and save each plot
    plots = {
        "speed_comparison": viz.create_speed_comparison_plot(
            telemetry1, telemetry2, driver1_name, driver2_name, config
        ),
        "delta_time": viz.create_delta_time_plot(
            comparison_summary["delta_time"],
            telemetry1["Distance"].values,
            driver1_name,
            driver2_name,
            config,
        ),
        "segment_comparison": viz.create_segment_comparison_plot(
            comparison_summary["segment_comparisons"],
            driver1_name,
            driver2_name,
            config,
        ),
        "throttle_brake": viz.create_throttle_brake_plot(
            telemetry1, telemetry2, driver1_name, driver2_name, config
        ),
        "gear": viz.create_gear_plot(telemetry1, telemetry2, driver1_name, driver2_name, config),
        "acceleration": viz.create_acceleration_plot(
            telemetry1, telemetry2, driver1_name, driver2_name, config
        ),
        "track_map": viz.create_track_map(
            telemetry1, telemetry2, driver1_name, driver2_name, "Speed", config
        ),
    }

    for name, fig in plots.items():
        output_path = output_dir / f"{name}.png"
        try:
            fig.write_image(str(output_path), width=config.plot_width, height=config.plot_height)
            logger.info(f"Saved: {output_path}")
        except Exception as e:
            logger.warning(f"Could not save {name}.png: {e}")
