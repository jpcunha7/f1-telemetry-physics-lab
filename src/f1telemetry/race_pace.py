"""
Race pace and stint analysis module.

Analyzes race pace, stint strategies, and lap-by-lap performance.

Author: João Pedro Cunha
"""

import logging
from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from f1telemetry.config import Config, DEFAULT_CONFIG

logger = logging.getLogger(__name__)


class Stint:
    """Represents a single stint in a race."""

    def __init__(
        self,
        stint_number: int,
        start_lap: int,
        end_lap: int,
        compound: Optional[str] = None,
    ):
        self.stint_number = stint_number
        self.start_lap = start_lap
        self.end_lap = end_lap
        self.compound = compound
        self.lap_times: List[float] = []
        self.lap_numbers: List[int] = []

    @property
    def num_laps(self) -> int:
        """Number of laps in stint."""
        return len(self.lap_times)

    @property
    def median_lap_time(self) -> Optional[float]:
        """Median lap time in stint."""
        return np.median(self.lap_times) if self.lap_times else None

    @property
    def best_lap_time(self) -> Optional[float]:
        """Best lap time in stint."""
        return min(self.lap_times) if self.lap_times else None

    @property
    def consistency(self) -> Optional[float]:
        """Lap time consistency (standard deviation)."""
        return np.std(self.lap_times) if len(self.lap_times) > 1 else None

    @property
    def pace_drop(self) -> Optional[float]:
        """Pace degradation: difference between first 3 and last 3 laps."""
        if len(self.lap_times) < 6:
            return None

        first_3_avg = np.mean(self.lap_times[:3])
        last_3_avg = np.mean(self.lap_times[-3:])
        return last_3_avg - first_3_avg

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "stint_number": self.stint_number,
            "start_lap": self.start_lap,
            "end_lap": self.end_lap,
            "compound": self.compound,
            "num_laps": self.num_laps,
            "median_lap_time": self.median_lap_time,
            "best_lap_time": self.best_lap_time,
            "consistency_std": self.consistency,
            "pace_drop_s": self.pace_drop,
        }


def detect_stints(laps_df: pd.DataFrame, pit_detection_method: str = "pit_duration") -> List[Stint]:
    """
    Detect stints from race laps.

    Args:
        laps_df: DataFrame with lap data (must have LapNumber, LapTime)
        pit_detection_method: Method to detect pit stops
            - 'pit_duration': Use PitInTime/PitOutTime if available
            - 'lap_time': Detect anomalously slow laps
            - 'compound': Detect compound changes

    Returns:
        List of Stint objects
    """
    if laps_df.empty:
        return []

    stints = []
    current_stint = Stint(stint_number=1, start_lap=int(laps_df.iloc[0]["LapNumber"]), end_lap=0)

    # Track compound if available
    current_compound = None
    if "Compound" in laps_df.columns:
        current_compound = laps_df.iloc[0]["Compound"]
        current_stint.compound = current_compound

    for idx, row in laps_df.iterrows():
        lap_number = int(row["LapNumber"])
        lap_time = row["LapTime"]

        # Convert lap time to seconds if it's a timedelta
        if hasattr(lap_time, "total_seconds"):
            lap_time_seconds = lap_time.total_seconds()
        else:
            lap_time_seconds = float(lap_time)

        # Check for pit stop (compound change)
        is_pit_lap = False
        if "Compound" in laps_df.columns and pd.notna(row["Compound"]):
            if current_compound and row["Compound"] != current_compound:
                is_pit_lap = True
                current_compound = row["Compound"]

        # Alternative: detect by pit out time
        if not is_pit_lap and "PitOutTime" in laps_df.columns:
            if pd.notna(row["PitOutTime"]):
                is_pit_lap = True

        if is_pit_lap and current_stint.num_laps > 0:
            # End current stint
            current_stint.end_lap = lap_number - 1
            stints.append(current_stint)

            # Start new stint
            stint_number = current_stint.stint_number + 1
            current_stint = Stint(
                stint_number=stint_number,
                start_lap=lap_number,
                end_lap=0,
                compound=current_compound if "Compound" in laps_df.columns else None,
            )

        # Add lap to current stint
        current_stint.lap_numbers.append(lap_number)
        current_stint.lap_times.append(lap_time_seconds)

    # Close final stint
    if current_stint.num_laps > 0:
        current_stint.end_lap = int(laps_df.iloc[-1]["LapNumber"])
        stints.append(current_stint)

    logger.info(f"Detected {len(stints)} stints")
    return stints


def filter_valid_laps(
    laps_df: pd.DataFrame,
    exclude_outliers: bool = True,
    outlier_threshold: float = 1.3,
) -> pd.DataFrame:
    """
    Filter laps to include only valid racing laps.

    Args:
        laps_df: DataFrame with lap data
        exclude_outliers: Remove laps with anomalous lap times
        outlier_threshold: Lap times > median * threshold are outliers

    Returns:
        Filtered DataFrame
    """
    filtered = laps_df.copy()

    # Filter by IsAccurate if available
    if "IsAccurate" in filtered.columns:
        filtered = filtered[filtered["IsAccurate"]]

    # Exclude in/out laps if TrackStatus available
    if "TrackStatus" in filtered.columns:
        # TrackStatus codes: 1 = normal, 2 = yellow, 4 = SC, 6 = VSC
        # We might want to exclude SC/VSC laps
        pass  # User can decide via UI

    # Exclude outliers
    if exclude_outliers and not filtered.empty:
        lap_times = []
        for lt in filtered["LapTime"]:
            if hasattr(lt, "total_seconds"):
                lap_times.append(lt.total_seconds())
            else:
                lap_times.append(float(lt))

        median_time = np.median(lap_times)
        threshold_time = median_time * outlier_threshold

        filtered["LapTimeSeconds"] = lap_times
        filtered = filtered[filtered["LapTimeSeconds"] < threshold_time]

    return filtered


def create_stint_summary_table(
    stints: List[Stint],
    driver_name: str,
) -> pd.DataFrame:
    """
    Create summary table for stints.

    Args:
        stints: List of Stint objects
        driver_name: Driver name

    Returns:
        DataFrame with stint summaries
    """
    rows = []
    for stint in stints:
        row = stint.to_dict()
        row["driver"] = driver_name

        # Format lap times
        if row["median_lap_time"]:
            row["median_lap_time_str"] = f"{row['median_lap_time']:.3f}s"
        if row["best_lap_time"]:
            row["best_lap_time_str"] = f"{row['best_lap_time']:.3f}s"
        if row["consistency_std"]:
            row["consistency_std_str"] = f"{row['consistency_std']:.3f}s"
        if row["pace_drop_s"]:
            row["pace_drop_s_str"] = f"{row['pace_drop_s']:+.3f}s"

        rows.append(row)

    return pd.DataFrame(rows)


def create_race_pace_plot(
    laps_df: pd.DataFrame,
    driver_name: str,
    stints: Optional[List[Stint]] = None,
    config: Config = DEFAULT_CONFIG,
) -> go.Figure:
    """
    Create race pace plot with lap times vs lap number.

    Args:
        laps_df: DataFrame with lap data
        driver_name: Driver name for title
        stints: Optional list of stints to color-code
        config: Configuration instance

    Returns:
        Plotly figure
    """
    fig = go.Figure()

    # Convert lap times to seconds
    lap_times = []
    for lt in laps_df["LapTime"]:
        if hasattr(lt, "total_seconds"):
            lap_times.append(lt.total_seconds())
        else:
            lap_times.append(float(lt))

    lap_numbers = laps_df["LapNumber"].values

    # Plot lap times
    fig.add_trace(
        go.Scatter(
            x=lap_numbers,
            y=lap_times,
            mode="lines+markers",
            name=f"{driver_name} Lap Time",
            line=dict(color="#1e90ff", width=2),
            marker=dict(size=6),
        )
    )

    # Mark pit stops
    if "PitOutTime" in laps_df.columns:
        pit_laps = laps_df[pd.notna(laps_df["PitOutTime"])]["LapNumber"].values
        pit_lap_times = [lap_times[i] for i, ln in enumerate(lap_numbers) if ln in pit_laps]

        if len(pit_laps) > 0:
            fig.add_trace(
                go.Scatter(
                    x=pit_laps,
                    y=pit_lap_times,
                    mode="markers",
                    name="Pit Stop",
                    marker=dict(color="red", size=12, symbol="diamond"),
                )
            )

    # Stint shading
    if stints:
        colors = [
            "rgba(255, 0, 0, 0.1)",
            "rgba(0, 255, 0, 0.1)",
            "rgba(0, 0, 255, 0.1)",
            "rgba(255, 255, 0, 0.1)",
            "rgba(255, 0, 255, 0.1)",
        ]

        for i, stint in enumerate(stints):
            color = colors[i % len(colors)]
            fig.add_vrect(
                x0=stint.start_lap - 0.5,
                x1=stint.end_lap + 0.5,
                fillcolor=color,
                layer="below",
                line_width=0,
                annotation_text=f"Stint {stint.stint_number}",
                annotation_position="top left",
            )

    fig.update_layout(
        title=f"Race Pace - {driver_name}",
        xaxis_title="Lap Number",
        yaxis_title="Lap Time (s)",
        template="plotly_dark",
        hovermode="x unified",
        height=500,
    )

    return fig


def compare_race_pace(
    laps_df1: pd.DataFrame,
    laps_df2: pd.DataFrame,
    driver1_name: str,
    driver2_name: str,
    config: Config = DEFAULT_CONFIG,
) -> go.Figure:
    """
    Compare race pace between two drivers.

    Args:
        laps_df1: Laps for driver 1
        laps_df2: Laps for driver 2
        driver1_name: Name of driver 1
        driver2_name: Name of driver 2
        config: Configuration instance

    Returns:
        Plotly figure with comparison
    """
    fig = go.Figure()

    # Driver 1
    lap_times1 = []
    for lt in laps_df1["LapTime"]:
        if hasattr(lt, "total_seconds"):
            lap_times1.append(lt.total_seconds())
        else:
            lap_times1.append(float(lt))

    fig.add_trace(
        go.Scatter(
            x=laps_df1["LapNumber"].values,
            y=lap_times1,
            mode="lines+markers",
            name=driver1_name,
            line=dict(color="#ff1e1e", width=2),
            marker=dict(size=5),
        )
    )

    # Driver 2
    lap_times2 = []
    for lt in laps_df2["LapTime"]:
        if hasattr(lt, "total_seconds"):
            lap_times2.append(lt.total_seconds())
        else:
            lap_times2.append(float(lt))

    fig.add_trace(
        go.Scatter(
            x=laps_df2["LapNumber"].values,
            y=lap_times2,
            mode="lines+markers",
            name=driver2_name,
            line=dict(color="#1e90ff", width=2),
            marker=dict(size=5),
        )
    )

    fig.update_layout(
        title=f"Race Pace Comparison - {driver1_name} vs {driver2_name}",
        xaxis_title="Lap Number",
        yaxis_title="Lap Time (s)",
        template="plotly_dark",
        hovermode="x unified",
        height=500,
    )

    return fig
