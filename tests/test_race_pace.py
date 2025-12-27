"""
Tests for race_pace module.

Author: João Pedro Cunha
"""

import pytest
import pandas as pd
import numpy as np
from datetime import timedelta
from f1telemetry import race_pace


@pytest.fixture
def sample_race_laps():
    """Create sample race lap data with stints."""
    # Simulate 20 laps with 2 stints
    laps = []

    for i in range(1, 21):
        # Pit stop after lap 10
        compound = "SOFT" if i <= 10 else "MEDIUM"

        lap_data = {
            "LapNumber": i,
            "LapTime": timedelta(seconds=90 + np.random.uniform(-2, 2)),
            "Compound": compound,
            "IsAccurate": True,
            "PitOutTime": pd.NaT if i != 11 else pd.Timestamp("2024-01-01 14:30:00"),
        }
        laps.append(lap_data)

    return pd.DataFrame(laps)


@pytest.fixture
def sample_race_laps_degradation():
    """Create sample race lap data with clear degradation pattern."""
    laps = []

    # Stint 1: Laps 1-10, degrading from 90s to 92s
    for i in range(1, 11):
        lap_time = 90.0 + (i - 1) * 0.2  # Linear degradation
        laps.append(
            {
                "LapNumber": i,
                "LapTime": timedelta(seconds=lap_time),
                "Compound": "SOFT",
                "IsAccurate": True,
                "PitOutTime": pd.NaT,
            }
        )

    # Stint 2: Laps 11-20, fresh tires then degrading
    for i in range(11, 21):
        lap_time = 89.0 + (i - 11) * 0.15
        laps.append(
            {
                "LapNumber": i,
                "LapTime": timedelta(seconds=lap_time),
                "Compound": "MEDIUM",
                "IsAccurate": True,
                "PitOutTime": pd.Timestamp("2024-01-01 14:30:00") if i == 11 else pd.NaT,
            }
        )

    return pd.DataFrame(laps)


def test_detect_stints_basic(sample_race_laps):
    """Test basic stint detection."""
    stints = race_pace.detect_stints(sample_race_laps)

    # Should detect 2 stints
    assert len(stints) == 2

    # Check first stint
    assert stints[0].stint_number == 1
    assert stints[0].start_lap == 1
    assert stints[0].end_lap == 10
    assert stints[0].compound == "SOFT"
    assert stints[0].num_laps == 10

    # Check second stint
    assert stints[1].stint_number == 2
    assert stints[1].start_lap == 11
    assert stints[1].end_lap == 20
    assert stints[1].compound == "MEDIUM"
    assert stints[1].num_laps == 10


def test_detect_stints_no_compound():
    """Test stint detection without compound data."""
    laps = pd.DataFrame(
        {
            "LapNumber": range(1, 11),
            "LapTime": [timedelta(seconds=90)] * 10,
            "IsAccurate": [True] * 10,
        }
    )

    stints = race_pace.detect_stints(laps)

    # Should still create one stint
    assert len(stints) == 1
    assert stints[0].num_laps == 10


def test_stint_properties(sample_race_laps_degradation):
    """Test stint property calculations."""
    stints = race_pace.detect_stints(sample_race_laps_degradation)

    assert len(stints) == 2

    # First stint analysis
    stint1 = stints[0]
    assert stint1.median_lap_time is not None
    assert stint1.best_lap_time is not None
    assert stint1.consistency is not None
    assert stint1.pace_drop is not None

    # Best lap should be faster than median
    assert stint1.best_lap_time <= stint1.median_lap_time

    # Pace drop should be positive (degradation)
    assert stint1.pace_drop > 0


def test_stint_to_dict():
    """Test Stint to_dict conversion."""
    stint = race_pace.Stint(stint_number=1, start_lap=1, end_lap=10, compound="SOFT")

    stint.lap_numbers = [1, 2, 3, 4, 5]
    stint.lap_times = [90.0, 90.5, 91.0, 91.5, 92.0]

    stint_dict = stint.to_dict()

    assert stint_dict["stint_number"] == 1
    assert stint_dict["start_lap"] == 1
    assert stint_dict["end_lap"] == 10
    assert stint_dict["compound"] == "SOFT"
    assert stint_dict["num_laps"] == 5
    assert stint_dict["median_lap_time"] == 91.0
    assert stint_dict["best_lap_time"] == 90.0


def test_filter_valid_laps():
    """Test lap filtering."""
    laps = pd.DataFrame(
        {
            "LapNumber": range(1, 11),
            "LapTime": [
                timedelta(seconds=90),
                timedelta(seconds=91),
                timedelta(seconds=92),
                timedelta(
                    seconds=150
                ),  # Outlier - but marked as accurate to test outlier detection
                timedelta(seconds=91),
                timedelta(seconds=90),
                timedelta(seconds=92),
                timedelta(seconds=91),
                timedelta(seconds=90),
                timedelta(seconds=91),  # Invalid lap
            ],
            "IsAccurate": [True, True, True, True, True, True, True, True, True, False],
        }
    )

    # Filter valid only
    filtered = race_pace.filter_valid_laps(laps, exclude_outliers=False)
    assert len(filtered) == 9  # Excludes 1 invalid lap

    # Filter outliers
    filtered_outliers = race_pace.filter_valid_laps(
        laps, exclude_outliers=True, outlier_threshold=1.3
    )
    assert len(filtered_outliers) < len(filtered)  # Should exclude the 150s lap


def test_create_stint_summary_table():
    """Test stint summary table creation."""
    stint1 = race_pace.Stint(1, 1, 10, "SOFT")
    stint1.lap_numbers = list(range(1, 11))
    stint1.lap_times = [90.0 + i * 0.2 for i in range(10)]

    stint2 = race_pace.Stint(2, 11, 20, "MEDIUM")
    stint2.lap_numbers = list(range(11, 21))
    stint2.lap_times = [89.0 + i * 0.15 for i in range(10)]

    stints = [stint1, stint2]

    table = race_pace.create_stint_summary_table(stints, "VER")

    assert len(table) == 2
    assert "driver" in table.columns
    assert "stint_number" in table.columns
    assert "compound" in table.columns
    assert "num_laps" in table.columns

    assert table.iloc[0]["driver"] == "VER"
    assert table.iloc[0]["stint_number"] == 1
    assert table.iloc[0]["compound"] == "SOFT"


def test_pace_drop_calculation():
    """Test pace drop (degradation) calculation."""
    stint = race_pace.Stint(1, 1, 10, "SOFT")

    # Clear degradation: first 3 laps avg 90s, last 3 laps avg 92s
    stint.lap_times = [90.0, 90.0, 90.0, 91.0, 91.5, 91.5, 92.0, 92.0, 92.0, 92.5]

    pace_drop = stint.pace_drop

    assert pace_drop is not None
    assert pace_drop > 0  # Should show degradation
    assert pace_drop == pytest.approx(2.0, abs=0.5)  # ~2s degradation


def test_pace_drop_insufficient_laps():
    """Test pace drop with insufficient laps."""
    stint = race_pace.Stint(1, 1, 5, "SOFT")
    stint.lap_times = [90.0, 90.5, 91.0, 91.5, 92.0]

    # Not enough laps to calculate pace drop (need 6+)
    assert stint.pace_drop is None


def test_consistency_calculation():
    """Test consistency (std deviation) calculation."""
    stint = race_pace.Stint(1, 1, 10, "SOFT")

    # Very consistent laps
    stint.lap_times = [90.0] * 10
    assert stint.consistency == pytest.approx(0.0)

    # Variable laps
    stint.lap_times = [90.0, 91.0, 89.0, 92.0, 88.0, 91.5, 89.5, 90.5, 91.0, 90.0]
    assert stint.consistency > 0


def test_detect_stints_empty_dataframe():
    """Test stint detection with empty DataFrame."""
    empty_df = pd.DataFrame()
    stints = race_pace.detect_stints(empty_df)

    assert len(stints) == 0


def test_stint_detection_multiple_pit_stops():
    """Test stint detection with multiple pit stops."""
    laps = []

    # Stint 1: Laps 1-10
    for i in range(1, 11):
        laps.append(
            {
                "LapNumber": i,
                "LapTime": timedelta(seconds=90),
                "Compound": "SOFT",
                "PitOutTime": pd.NaT,
            }
        )

    # Stint 2: Laps 11-20
    for i in range(11, 21):
        laps.append(
            {
                "LapNumber": i,
                "LapTime": timedelta(seconds=90),
                "Compound": "MEDIUM",
                "PitOutTime": pd.Timestamp("2024-01-01 14:30:00") if i == 11 else pd.NaT,
            }
        )

    # Stint 3: Laps 21-30
    for i in range(21, 31):
        laps.append(
            {
                "LapNumber": i,
                "LapTime": timedelta(seconds=90),
                "Compound": "HARD",
                "PitOutTime": pd.Timestamp("2024-01-01 15:00:00") if i == 21 else pd.NaT,
            }
        )

    df = pd.DataFrame(laps)
    stints = race_pace.detect_stints(df)

    # Should detect 3 stints
    assert len(stints) == 3
    assert stints[0].compound == "SOFT"
    assert stints[1].compound == "MEDIUM"
    assert stints[2].compound == "HARD"
