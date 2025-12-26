"""
Tests for alignment module.

Author: João Pedro Cunha
"""

import numpy as np
import pandas as pd
import pytest

from f1telemetry.alignment import (
    create_distance_array,
    interpolate_telemetry,
    align_laps,
    compute_delta_time,
    validate_telemetry,
)
from f1telemetry.config import Config


def create_mock_telemetry(start_dist: float = 0, end_dist: float = 1000, num_points: int = 100) -> pd.DataFrame:
    """Create mock telemetry data for testing."""
    distance = np.linspace(start_dist, end_dist, num_points)
    speed = 200 + 50 * np.sin(distance / 100)  # Varying speed
    throttle = np.clip(50 + 40 * np.sin(distance / 80), 0, 100)
    brake = np.clip(20 * np.cos(distance / 90), 0, 100)

    return pd.DataFrame({
        'Distance': distance,
        'Speed': speed,
        'Throttle': throttle,
        'Brake': brake,
    })


class TestValidateTelemetry:
    """Tests for telemetry validation."""

    def test_valid_telemetry(self):
        """Test validation passes for valid telemetry."""
        telemetry = create_mock_telemetry()
        validate_telemetry(telemetry)  # Should not raise

    def test_empty_telemetry(self):
        """Test validation fails for empty telemetry."""
        telemetry = pd.DataFrame()
        with pytest.raises(ValueError, match="empty"):
            validate_telemetry(telemetry)

    def test_missing_columns(self):
        """Test validation fails for missing required columns."""
        telemetry = pd.DataFrame({'Distance': [1, 2, 3]})
        with pytest.raises(ValueError, match="missing required columns"):
            validate_telemetry(telemetry)


class TestCreateDistanceArray:
    """Tests for distance array creation."""

    def test_basic_array(self):
        """Test basic distance array creation."""
        arr = create_distance_array(0, 100, 10)
        assert len(arr) == 10
        assert arr[0] == 0
        assert np.allclose(np.diff(arr), 10)

    def test_monotonic_increasing(self):
        """Test array is monotonic increasing."""
        arr = create_distance_array(0, 500, 5)
        assert np.all(np.diff(arr) > 0)


class TestInterpolateTelemetry:
    """Tests for telemetry interpolation."""

    def test_interpolation_output_length(self):
        """Test interpolated telemetry has correct length."""
        telemetry = create_mock_telemetry()
        distance_array = create_distance_array(0, 1000, 5)

        interpolated = interpolate_telemetry(telemetry, distance_array)

        assert len(interpolated) == len(distance_array)

    def test_interpolation_columns(self):
        """Test interpolated telemetry contains expected columns."""
        telemetry = create_mock_telemetry()
        distance_array = create_distance_array(0, 1000, 5)

        interpolated = interpolate_telemetry(telemetry, distance_array)

        assert 'Distance' in interpolated.columns
        assert 'Speed' in interpolated.columns
        assert 'Throttle' in interpolated.columns

    def test_interpolation_preserves_distance(self):
        """Test interpolation uses provided distance array."""
        telemetry = create_mock_telemetry()
        distance_array = create_distance_array(100, 900, 10)

        interpolated = interpolate_telemetry(telemetry, distance_array)

        np.testing.assert_array_almost_equal(interpolated['Distance'].values, distance_array)


class TestAlignLaps:
    """Tests for lap alignment."""

    def test_align_same_length(self):
        """Test aligned laps have same length."""
        tel1 = create_mock_telemetry(0, 1000, 100)
        tel2 = create_mock_telemetry(0, 1000, 120)

        config = Config(distance_resolution=5.0)
        aligned1, aligned2 = align_laps(tel1, tel2, config)

        assert len(aligned1) == len(aligned2)

    def test_align_overlapping_range(self):
        """Test alignment uses overlapping distance range."""
        tel1 = create_mock_telemetry(0, 1000, 100)
        tel2 = create_mock_telemetry(100, 900, 100)

        config = Config(distance_resolution=5.0)
        aligned1, aligned2 = align_laps(tel1, tel2, config)

        assert aligned1['Distance'].min() >= 100
        assert aligned1['Distance'].max() <= 900

    def test_no_overlap_raises_error(self):
        """Test alignment fails when no overlap exists."""
        tel1 = create_mock_telemetry(0, 500, 100)
        tel2 = create_mock_telemetry(600, 1000, 100)

        config = Config(distance_resolution=5.0)

        with pytest.raises(ValueError, match="No overlapping distance range"):
            align_laps(tel1, tel2, config)


class TestComputeDeltaTime:
    """Tests for delta time computation."""

    def test_delta_time_length(self):
        """Test delta time array has correct length."""
        tel1 = create_mock_telemetry(0, 1000, 100)
        tel2 = create_mock_telemetry(0, 1000, 100)

        delta = compute_delta_time(tel1, tel2)

        assert len(delta) == len(tel1)

    def test_same_speed_zero_delta(self):
        """Test delta time is approximately zero for same speeds."""
        distance = np.linspace(0, 1000, 100)
        telemetry = pd.DataFrame({
            'Distance': distance,
            'Speed': np.full(100, 200.0),
        })

        delta = compute_delta_time(telemetry, telemetry)

        # Should be close to zero (numerical precision)
        assert np.allclose(delta, 0, atol=1e-6)

    def test_faster_driver_negative_delta(self):
        """Test faster driver has negative cumulative delta."""
        tel1 = create_mock_telemetry(0, 1000, 100)
        tel2 = tel1.copy()
        tel2['Speed'] = tel2['Speed'] * 0.95  # Driver 2 slower

        delta = compute_delta_time(tel1, tel2)

        # Driver 1 faster, so delta should be negative at end
        assert delta[-1] < 0

    def test_mismatched_length_raises(self):
        """Test error raised for mismatched telemetry lengths."""
        tel1 = create_mock_telemetry(0, 1000, 100)
        tel2 = create_mock_telemetry(0, 1000, 50)

        with pytest.raises(ValueError, match="must be aligned"):
            compute_delta_time(tel1, tel2)
