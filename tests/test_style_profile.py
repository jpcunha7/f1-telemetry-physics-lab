"""
Tests for style_profile module.

Author: João Pedro Cunha
"""

import pytest
import pandas as pd
import numpy as np
from f1telemetry import style_profile


@pytest.fixture
def sample_telemetry_list():
    """Create list of sample telemetry DataFrames."""
    telemetry_list = []

    for lap_idx in range(3):
        # Create telemetry for one lap
        n_samples = 200
        df = pd.DataFrame(
            {
                "Distance": np.linspace(0, 5000, n_samples),
                "Speed": np.random.uniform(100, 300, n_samples),
                "Throttle": np.random.uniform(0, 100, n_samples),
                "Brake": np.random.uniform(0, 100, n_samples),
                "nGear": np.random.randint(1, 8, n_samples),
                "LongAccel": np.random.uniform(-3, 2, n_samples),
                "LatAccel": np.random.uniform(-3, 3, n_samples),
            }
        )
        telemetry_list.append(df)

    return telemetry_list


@pytest.fixture
def sample_telemetry_full_throttle():
    """Create telemetry with high full-throttle percentage."""
    n_samples = 200
    throttle = np.ones(n_samples) * 100  # Full throttle
    throttle[50:60] = 50  # Small lift in one section

    df = pd.DataFrame(
        {
            "Distance": np.linspace(0, 5000, n_samples),
            "Speed": np.ones(n_samples) * 200,
            "Throttle": throttle,
            "Brake": np.zeros(n_samples),
            "nGear": np.ones(n_samples) * 7,
            "LongAccel": np.ones(n_samples) * 1.5,
            "LatAccel": np.zeros(n_samples),
        }
    )

    return [df]


def test_aggregate_telemetry_stats_basic(sample_telemetry_list):
    """Test basic aggregated statistics calculation."""
    stats = style_profile.aggregate_telemetry_stats(sample_telemetry_list, "VER")

    assert stats["driver_name"] == "VER"
    assert stats["num_laps"] == 3

    # Should have speed statistics
    assert "avg_speed" in stats
    assert "max_speed" in stats
    assert "min_speed" in stats
    assert "speed_std" in stats

    # Should have throttle statistics
    assert "avg_throttle" in stats
    assert "percent_full_throttle" in stats
    assert "percent_partial_throttle" in stats

    # Should have brake statistics
    assert "avg_brake" in stats
    assert "percent_braking" in stats

    # Should have gear statistics
    assert "most_common_gear" in stats
    assert "avg_gear" in stats

    # Should have acceleration statistics
    assert "avg_long_accel" in stats
    assert "max_accel" in stats
    assert "max_decel" in stats
    assert "percent_accelerating" in stats
    assert "percent_decelerating" in stats


def test_aggregate_telemetry_stats_values(sample_telemetry_full_throttle):
    """Test that aggregated statistics have reasonable values."""
    stats = style_profile.aggregate_telemetry_stats(sample_telemetry_full_throttle, "VER")

    # Should have high full throttle percentage
    assert stats["percent_full_throttle"] > 90

    # Should have low braking percentage
    assert stats["percent_braking"] < 5

    # Average speed should be reasonable
    assert 100 < stats["avg_speed"] < 400


def test_aggregate_empty_list():
    """Test aggregation with empty telemetry list."""
    stats = style_profile.aggregate_telemetry_stats([], "VER")

    assert stats["driver_name"] == "VER"
    assert stats["num_laps"] == 0


def test_aggregate_missing_channels():
    """Test aggregation with missing channels."""
    # Telemetry without some channels
    df = pd.DataFrame(
        {
            "Distance": np.linspace(0, 5000, 200),
            "Speed": np.ones(200) * 200,
            # Missing: Throttle, Brake, Gear, Accel channels
        }
    )

    stats = style_profile.aggregate_telemetry_stats([df], "VER")

    # Should still work but some stats won't be present
    assert "avg_speed" in stats
    assert "max_speed" in stats


def test_compare_driver_styles():
    """Test driver style comparison."""
    stats1 = {
        "driver_name": "VER",
        "avg_speed": 200.0,
        "max_speed": 320.0,
        "percent_full_throttle": 65.0,
        "percent_braking": 15.0,
        "avg_long_accel": 0.5,
        "max_accel": 2.0,
        "max_decel": -3.5,
        "avg_lat_accel": 1.2,
        "max_lat_accel": 4.0,
    }

    stats2 = {
        "driver_name": "LEC",
        "avg_speed": 198.0,
        "max_speed": 315.0,
        "percent_full_throttle": 62.0,
        "percent_braking": 16.0,
        "avg_long_accel": 0.4,
        "max_accel": 1.9,
        "max_decel": -3.4,
        "avg_lat_accel": 1.3,
        "max_lat_accel": 4.1,
    }

    comparison = style_profile.compare_driver_styles(stats1, stats2)

    assert not comparison.empty
    assert "Metric" in comparison.columns
    assert "VER" in comparison.columns
    assert "LEC" in comparison.columns
    assert "Delta" in comparison.columns

    # Check that all metrics are present
    metrics = comparison["Metric"].tolist()
    assert "Avg Speed" in metrics
    assert "Max Speed" in metrics
    assert "Percent Full Throttle" in metrics


def test_compare_driver_styles_deltas():
    """Test that comparison deltas are calculated correctly."""
    stats1 = {
        "driver_name": "VER",
        "avg_speed": 200.0,
        "max_speed": 320.0,
    }

    stats2 = {
        "driver_name": "LEC",
        "avg_speed": 195.0,
        "max_speed": 315.0,
    }

    comparison = style_profile.compare_driver_styles(stats1, stats2)

    # Find avg_speed row
    avg_speed_row = comparison[comparison["Metric"] == "Avg Speed"].iloc[0]

    # Delta should be +5.0 (VER - LEC)
    delta_str = avg_speed_row["Delta"]
    assert "+5.00" in delta_str


def test_percent_calculations():
    """Test percentage calculations for throttle/brake."""
    # Create telemetry with known percentages
    n = 100
    throttle = np.zeros(n)
    throttle[:65] = 100  # 65% full throttle

    brake = np.zeros(n)
    brake[80:95] = 50  # 15% braking

    df = pd.DataFrame(
        {
            "Distance": np.linspace(0, 5000, n),
            "Speed": np.ones(n) * 200,
            "Throttle": throttle,
            "Brake": brake,
        }
    )

    stats = style_profile.aggregate_telemetry_stats([df], "VER")

    assert stats["percent_full_throttle"] == pytest.approx(65.0)
    assert stats["percent_braking"] == pytest.approx(15.0)


def test_acceleration_percentages():
    """Test acceleration/deceleration percentage calculations."""
    n = 100
    long_accel = np.zeros(n)
    long_accel[:60] = 1.0  # 60% accelerating (>0.5)
    long_accel[60:80] = -1.0  # 20% decelerating (<-0.5)
    long_accel[80:] = 0.0  # 20% coasting

    df = pd.DataFrame(
        {
            "Distance": np.linspace(0, 5000, n),
            "Speed": np.ones(n) * 200,
            "LongAccel": long_accel,
        }
    )

    stats = style_profile.aggregate_telemetry_stats([df], "VER")

    assert stats["percent_accelerating"] == pytest.approx(60.0)
    assert stats["percent_decelerating"] == pytest.approx(20.0)


def test_gear_statistics():
    """Test gear usage statistics."""
    n = 100
    # Mostly in gear 7, sometimes in gear 6
    gears = np.ones(n) * 7
    gears[20:30] = 6

    df = pd.DataFrame(
        {
            "Distance": np.linspace(0, 5000, n),
            "Speed": np.ones(n) * 200,
            "nGear": gears,
        }
    )

    stats = style_profile.aggregate_telemetry_stats([df], "VER")

    assert stats["most_common_gear"] == 7
    assert 6.0 < stats["avg_gear"] <= 7.0


def test_multiple_laps_aggregation():
    """Test that statistics are properly aggregated across multiple laps."""
    # Create 3 laps with different characteristics
    lap1 = pd.DataFrame(
        {
            "Speed": [100, 150, 200],
            "Throttle": [50, 75, 100],
            "Brake": [0, 0, 0],
        }
    )

    lap2 = pd.DataFrame(
        {
            "Speed": [110, 160, 210],
            "Throttle": [60, 80, 100],
            "Brake": [0, 0, 0],
        }
    )

    lap3 = pd.DataFrame(
        {
            "Speed": [105, 155, 205],
            "Throttle": [55, 78, 100],
            "Brake": [0, 0, 0],
        }
    )

    telemetry_list = [lap1, lap2, lap3]
    stats = style_profile.aggregate_telemetry_stats(telemetry_list, "VER")

    # Average speed should be around (105+155+205)/3 ≈ 155 for middle values
    # But actually it pools all values: (100+150+200+110+160+210+105+155+205)/9 ≈ 155
    assert 100 < stats["avg_speed"] < 220
    assert stats["num_laps"] == 3


def test_lateral_acceleration_stats():
    """Test lateral acceleration statistics."""
    df = pd.DataFrame(
        {
            "Distance": np.linspace(0, 5000, 100),
            "Speed": np.ones(100) * 200,
            "LatAccel": np.concatenate(
                [
                    np.ones(50) * 2.0,  # Right corners
                    np.ones(50) * -2.0,  # Left corners
                ]
            ),
        }
    )

    stats = style_profile.aggregate_telemetry_stats([df], "VER")

    # Average absolute lateral should be 2.0
    assert stats["avg_lat_accel"] == pytest.approx(2.0)
    assert stats["max_lat_accel"] == pytest.approx(2.0)
