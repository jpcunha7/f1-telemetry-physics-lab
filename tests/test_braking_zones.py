"""
Tests for braking_zones module.

Author: João Pedro Cunha
"""

import pytest
import pandas as pd
import numpy as np
from f1telemetry import braking_zones, config


@pytest.fixture
def sample_telemetry():
    """Create sample telemetry data with braking zones."""
    # Create telemetry with 2 clear braking zones
    distance = np.linspace(0, 1000, 500)

    # Speed: high speed (200), braking zone 1 (250-350m), high speed, braking zone 2 (600-700m)
    speed = np.ones(500) * 200
    speed[125:175] = np.linspace(200, 100, 50)  # Braking zone 1: 250-350m
    speed[300:350] = np.linspace(200, 120, 50)  # Braking zone 2: 600-700m

    # Brake: 0 normally, >10 in braking zones
    brake = np.zeros(500)
    brake[125:175] = 80  # Braking zone 1
    brake[300:350] = 90  # Braking zone 2

    df = pd.DataFrame(
        {
            "Distance": distance,
            "Speed": speed,
            "Brake": brake,
            "Throttle": np.ones(500) * 100,
        }
    )

    return df


@pytest.fixture
def sample_telemetry_no_brake():
    """Create sample telemetry without brake channel."""
    df = pd.DataFrame(
        {
            "Distance": np.linspace(0, 1000, 500),
            "Speed": np.ones(500) * 200,
            "Throttle": np.ones(500) * 100,
        }
    )
    return df


def test_detect_braking_zones_basic(sample_telemetry):
    """Test basic braking zone detection."""
    cfg = config.Config()
    zones = braking_zones.detect_braking_zones(sample_telemetry, cfg)

    # Should detect 2 braking zones
    assert len(zones) == 2

    # Check first zone
    assert zones[0].zone_id == 1
    assert 200 < zones[0].start_distance < 300
    assert 300 < zones[0].end_distance < 400
    assert zones[0].entry_speed > zones[0].min_speed

    # Check second zone
    assert zones[1].zone_id == 2
    assert 550 < zones[1].start_distance < 650
    assert 650 < zones[1].end_distance < 750


def test_detect_braking_zones_no_brake_channel(sample_telemetry_no_brake):
    """Test braking zone detection without brake channel."""
    cfg = config.Config()
    zones = braking_zones.detect_braking_zones(sample_telemetry_no_brake, cfg)

    # Should return empty list when brake channel missing
    assert len(zones) == 0


def test_detect_braking_zones_custom_threshold(sample_telemetry):
    """Test braking zone detection with custom thresholds."""
    cfg = config.Config()

    # Very high threshold - should detect fewer zones
    zones_high = braking_zones.detect_braking_zones(sample_telemetry, cfg, brake_threshold=95.0)

    # Lower threshold - should detect more zones
    zones_low = braking_zones.detect_braking_zones(sample_telemetry, cfg, brake_threshold=5.0)

    assert len(zones_low) >= len(zones_high)


def test_braking_zone_to_dict():
    """Test BrakingZone to_dict conversion."""
    zone = braking_zones.BrakingZone(
        zone_id=1,
        start_distance=250.0,
        end_distance=350.0,
        entry_speed=200.0,
        min_speed=100.0,
        exit_speed=120.0,
        max_decel=2.5,
        duration=1.5,
    )

    zone_dict = zone.to_dict()

    assert zone_dict["zone_id"] == 1
    assert zone_dict["start_distance"] == 250.0
    assert zone_dict["end_distance"] == 350.0
    assert zone_dict["entry_speed"] == 200.0
    assert zone_dict["min_speed"] == 100.0
    assert zone_dict["max_decel"] == 2.5


def test_compare_braking_zones():
    """Test braking zone comparison."""
    # Create zones for driver 1
    zones1 = [
        braking_zones.BrakingZone(1, 250.0, 350.0, 200.0, 100.0, 120.0, 2.5, 1.5),
        braking_zones.BrakingZone(2, 600.0, 700.0, 200.0, 120.0, 140.0, 2.0, 1.2),
    ]

    # Create zones for driver 2 (slightly different)
    zones2 = [
        braking_zones.BrakingZone(1, 240.0, 340.0, 195.0, 98.0, 118.0, 2.6, 1.6),
        braking_zones.BrakingZone(2, 610.0, 710.0, 198.0, 122.0, 142.0, 1.9, 1.1),
    ]

    comparison = braking_zones.compare_braking_zones(zones1, zones2)

    # Should match both zones
    assert len(comparison) == 2

    # Check first zone comparison
    row1 = comparison.iloc[0]
    assert row1["Zone_ID"] == 1
    assert row1["Brake_Start_Delta_m"] == pytest.approx(10.0)  # 250 - 240
    assert row1["Entry_Speed_Delta"] == pytest.approx(5.0)  # 200 - 195
    assert row1["Min_Speed_Delta"] == pytest.approx(2.0)  # 100 - 98


def test_compare_braking_zones_no_match():
    """Test braking zone comparison with no matches."""
    zones1 = [
        braking_zones.BrakingZone(1, 250.0, 350.0, 200.0, 100.0, 120.0, 2.5, 1.5),
    ]

    # Zone at completely different location
    zones2 = [
        braking_zones.BrakingZone(1, 1500.0, 1600.0, 195.0, 98.0, 118.0, 2.6, 1.6),
    ]

    comparison = braking_zones.compare_braking_zones(zones1, zones2, distance_tolerance=50.0)

    # Should not match any zones
    assert len(comparison) == 0


def test_get_top_braking_differences():
    """Test getting top braking differences."""
    # Create comparison DataFrame
    comparison_df = pd.DataFrame(
        {
            "Zone_ID": [1, 2, 3, 4, 5],
            "Brake_Start_Delta_m": [10.0, -5.0, 15.0, -20.0, 8.0],
            "Entry_Speed_Delta": [5.0, -2.0, 8.0, -10.0, 3.0],
            "Approx_Time_Delta_s": [0.05, -0.02, 0.08, -0.15, 0.04],
        }
    )

    top_gains, top_losses = braking_zones.get_top_braking_differences(
        comparison_df, n=2, sort_by="Brake_Start_Delta_m"
    )

    # Top gains (positive deltas - driver 1 brakes later)
    assert len(top_gains) == 2
    assert top_gains.iloc[0]["Brake_Start_Delta_m"] == 15.0  # Zone 3
    assert top_gains.iloc[1]["Brake_Start_Delta_m"] == 10.0  # Zone 1

    # Top losses (negative deltas - driver 1 brakes earlier)
    assert len(top_losses) == 2
    assert top_losses.iloc[0]["Brake_Start_Delta_m"] == -20.0  # Zone 4
    assert top_losses.iloc[1]["Brake_Start_Delta_m"] == -5.0  # Zone 2


def test_create_braking_zones_summary():
    """Test braking zones summary creation."""
    zones1 = [
        braking_zones.BrakingZone(1, 250.0, 350.0, 200.0, 100.0, 120.0, 2.5, 1.5),
        braking_zones.BrakingZone(2, 600.0, 700.0, 200.0, 120.0, 140.0, 2.0, 1.2),
    ]

    zones2 = [
        braking_zones.BrakingZone(1, 240.0, 340.0, 195.0, 98.0, 118.0, 2.6, 1.6),
    ]

    summary = braking_zones.create_braking_zones_summary(zones1, zones2, "VER", "LEC")

    assert summary["num_zones_driver1"] == 2
    assert summary["num_zones_driver2"] == 1
    assert summary["driver1_name"] == "VER"
    assert summary["driver2_name"] == "LEC"
    assert "avg_max_decel_driver1" in summary
    assert "total_braking_distance_driver1" in summary


def test_braking_zone_validation():
    """Test that short zones or small speed drops are filtered."""
    # Create telemetry with a very short braking zone
    distance = np.linspace(0, 1000, 500)
    speed = np.ones(500) * 200
    speed[125:130] = 190  # Only 10m zone with small speed drop
    brake = np.zeros(500)
    brake[125:130] = 50

    df = pd.DataFrame(
        {
            "Distance": distance,
            "Speed": speed,
            "Brake": brake,
        }
    )

    cfg = config.Config()
    zones = braking_zones.detect_braking_zones(df, cfg, min_zone_length=20.0, min_speed_drop=20.0)

    # Should not detect zone (too short and speed drop too small)
    assert len(zones) == 0
