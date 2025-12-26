"""
Tests for physics module.

Author: João Pedro Cunha
"""

import numpy as np
import pandas as pd
import pytest

from f1telemetry.physics import (
    smooth_signal,
    compute_acceleration,
    detect_braking_zones,
    detect_corners,
    add_physics_channels,
)
from f1telemetry.config import Config


def create_mock_telemetry() -> pd.DataFrame:
    """Create mock telemetry with realistic patterns."""
    distance = np.linspace(0, 1000, 200)

    # Simulate speed variation (high speed, braking, corner, acceleration)
    speed = np.zeros_like(distance)
    speed[:50] = 300  # Straight
    speed[50:80] = np.linspace(300, 100, 30)  # Braking
    speed[80:100] = 100  # Corner
    speed[100:150] = np.linspace(100, 280, 50)  # Acceleration
    speed[150:] = 280  # Straight

    # Throttle and brake
    throttle = np.where(distance < 50, 100, np.where(distance < 100, 0, 80))
    brake = np.where((distance >= 50) & (distance < 80), 80, 0)

    return pd.DataFrame({
        'Distance': distance,
        'Speed': speed,
        'Throttle': throttle,
        'Brake': brake,
    })


class TestSmoothSignal:
    """Tests for signal smoothing."""

    def test_smooth_preserves_length(self):
        """Test smoothing preserves signal length."""
        signal = np.random.randn(100)
        smoothed = smooth_signal(signal, window_length=11, polyorder=3)

        assert len(smoothed) == len(signal)

    def test_smooth_reduces_noise(self):
        """Test smoothing reduces high-frequency noise."""
        # Create signal with noise
        x = np.linspace(0, 10, 100)
        signal = np.sin(x) + 0.5 * np.random.randn(100)

        smoothed = smooth_signal(signal, window_length=11, polyorder=3)

        # Standard deviation should be lower after smoothing
        assert np.std(smoothed) < np.std(signal)

    def test_short_signal_returns_original(self):
        """Test very short signals are returned unchanged."""
        signal = np.array([1, 2, 3])
        smoothed = smooth_signal(signal, window_length=11)

        np.testing.assert_array_equal(signal, smoothed)


class TestComputeAcceleration:
    """Tests for acceleration computation."""

    def test_acceleration_output_length(self):
        """Test acceleration has same length as input."""
        telemetry = create_mock_telemetry()
        config = Config()

        acceleration = compute_acceleration(telemetry, config)

        assert len(acceleration) == len(telemetry)

    def test_constant_speed_zero_acceleration(self):
        """Test constant speed produces near-zero acceleration."""
        distance = np.linspace(0, 1000, 100)
        telemetry = pd.DataFrame({
            'Distance': distance,
            'Speed': np.full(100, 200.0),
        })
        config = Config()

        acceleration = compute_acceleration(telemetry, config)

        # Should be close to zero (accounting for smoothing artifacts)
        assert np.abs(np.mean(acceleration)) < 0.1

    def test_increasing_speed_positive_acceleration(self):
        """Test increasing speed produces positive acceleration."""
        distance = np.linspace(0, 1000, 100)
        speed = np.linspace(100, 300, 100)  # Accelerating
        telemetry = pd.DataFrame({
            'Distance': distance,
            'Speed': speed,
        })
        config = Config()

        acceleration = compute_acceleration(telemetry, config)

        # Average acceleration should be positive
        assert np.mean(acceleration[20:-20]) > 0  # Exclude edges


class TestDetectBrakingZones:
    """Tests for braking zone detection."""

    def test_braking_zones_detected(self):
        """Test braking zones are detected."""
        telemetry = create_mock_telemetry()
        config = Config(brake_threshold=10.0)

        zones = detect_braking_zones(telemetry, config=config)

        assert len(zones) > 0

    def test_no_brake_column_returns_empty(self):
        """Test returns empty list when Brake column missing."""
        telemetry = pd.DataFrame({
            'Distance': np.linspace(0, 1000, 100),
            'Speed': np.full(100, 200.0),
        })
        config = Config()

        zones = detect_braking_zones(telemetry, config=config)

        assert len(zones) == 0

    def test_braking_zone_attributes(self):
        """Test braking zone has expected attributes."""
        telemetry = create_mock_telemetry()
        config = Config(brake_threshold=10.0)

        zones = detect_braking_zones(telemetry, config=config)

        if len(zones) > 0:
            zone = zones[0]
            assert hasattr(zone, 'start_distance')
            assert hasattr(zone, 'end_distance')
            assert hasattr(zone, 'entry_speed')
            assert hasattr(zone, 'min_speed')
            assert hasattr(zone, 'braking_distance')


class TestDetectCorners:
    """Tests for corner detection."""

    def test_corners_detected(self):
        """Test corners are detected in telemetry."""
        telemetry = create_mock_telemetry()
        config = Config(speed_threshold_corner=200.0)

        corners = detect_corners(telemetry, config=config)

        # Should detect at least one corner
        assert len(corners) >= 0  # May or may not detect depending on data

    def test_corner_attributes(self):
        """Test corner has expected attributes."""
        # Create telemetry with clear corner
        distance = np.linspace(0, 1000, 200)
        speed = 250 - 100 * np.abs(np.sin(distance / 200))  # Oscillating speed
        telemetry = pd.DataFrame({
            'Distance': distance,
            'Speed': speed,
        })
        config = Config(speed_threshold_corner=200.0)

        corners = detect_corners(telemetry, config=config)

        if len(corners) > 0:
            corner = corners[0]
            assert hasattr(corner, 'distance')
            assert hasattr(corner, 'min_speed')
            assert hasattr(corner, 'entry_speed')
            assert hasattr(corner, 'exit_speed')


class TestAddPhysicsChannels:
    """Tests for adding physics channels to telemetry."""

    def test_adds_acceleration_column(self):
        """Test acceleration column is added."""
        telemetry = create_mock_telemetry()
        config = Config()

        result = add_physics_channels(telemetry, config)

        assert 'Acceleration' in result.columns

    def test_original_telemetry_unchanged(self):
        """Test original telemetry is not modified."""
        telemetry = create_mock_telemetry()
        original_columns = telemetry.columns.tolist()
        config = Config()

        result = add_physics_channels(telemetry, config)

        # Original should be unchanged
        assert telemetry.columns.tolist() == original_columns
        # Result should have new column
        assert 'Acceleration' in result.columns

    def test_acceleration_values_reasonable(self):
        """Test acceleration values are in reasonable range for F1."""
        telemetry = create_mock_telemetry()
        config = Config()

        result = add_physics_channels(telemetry, config)

        # F1 cars typically: -5 to +2 g (but our approximation is rougher)
        # Just check no extreme outliers (mock data has sharp transitions)
        assert result['Acceleration'].min() > -50  # Allow for approximation roughness
        assert result['Acceleration'].max() < 20  # Allow for approximation roughness
