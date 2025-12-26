"""
Tests for metrics module.

Author: João Pedro Cunha
"""

import numpy as np
import pandas as pd
import pytest

from f1telemetry.metrics import (
    divide_lap_into_segments,
    compute_segment_times,
    compare_segments,
)
from f1telemetry.config import Config


def create_mock_telemetry(speed_multiplier: float = 1.0) -> pd.DataFrame:
    """Create mock aligned telemetry."""
    distance = np.linspace(0, 1000, 200)
    speed = (200 + 50 * np.sin(distance / 100)) * speed_multiplier

    return pd.DataFrame({
        'Distance': distance,
        'Speed': speed,
    })


class TestDivideLapIntoSegments:
    """Tests for lap segmentation."""

    def test_correct_number_of_segments(self):
        """Test correct number of segments are created."""
        distance = np.linspace(0, 1000, 100)
        segments = divide_lap_into_segments(distance, num_segments=10)

        assert len(segments) == 10

    def test_segments_cover_full_range(self):
        """Test segments cover the full distance range."""
        distance = np.linspace(0, 1000, 100)
        segments = divide_lap_into_segments(distance, num_segments=5)

        first_start = segments[0][0]
        last_end = segments[-1][1]

        assert first_start == pytest.approx(0, abs=1)
        assert last_end == pytest.approx(1000, abs=1)

    def test_segments_are_contiguous(self):
        """Test segments are contiguous (no gaps)."""
        distance = np.linspace(0, 1000, 100)
        segments = divide_lap_into_segments(distance, num_segments=8)

        for i in range(len(segments) - 1):
            assert segments[i][1] == pytest.approx(segments[i + 1][0], abs=1e-6)


class TestComputeSegmentTimes:
    """Tests for segment time computation."""

    def test_number_of_times_matches_segments(self):
        """Test number of times matches number of segments."""
        telemetry = create_mock_telemetry()
        distance = telemetry['Distance'].values
        segments = divide_lap_into_segments(distance, num_segments=10)

        times = compute_segment_times(telemetry, segments)

        assert len(times) == len(segments)

    def test_times_are_positive(self):
        """Test all segment times are positive."""
        telemetry = create_mock_telemetry()
        distance = telemetry['Distance'].values
        segments = divide_lap_into_segments(distance, num_segments=5)

        times = compute_segment_times(telemetry, segments)

        assert all(t >= 0 for t in times)

    def test_faster_speed_shorter_time(self):
        """Test faster speed results in shorter segment time."""
        tel_slow = create_mock_telemetry(speed_multiplier=0.8)
        tel_fast = create_mock_telemetry(speed_multiplier=1.2)

        distance = tel_slow['Distance'].values
        segments = divide_lap_into_segments(distance, num_segments=5)

        times_slow = compute_segment_times(tel_slow, segments)
        times_fast = compute_segment_times(tel_fast, segments)

        # Fast lap should have shorter times
        assert sum(times_fast) < sum(times_slow)


class TestCompareSegments:
    """Tests for segment comparison."""

    def test_comparison_output_length(self):
        """Test comparison produces correct number of segments."""
        tel1 = create_mock_telemetry()
        tel2 = create_mock_telemetry()
        config = Config(num_segments=10)

        comparisons = compare_segments(tel1, tel2, config)

        assert len(comparisons) == 10

    def test_comparison_attributes(self):
        """Test comparison objects have expected attributes."""
        tel1 = create_mock_telemetry()
        tel2 = create_mock_telemetry()
        config = Config(num_segments=5)

        comparisons = compare_segments(tel1, tel2, config)

        comp = comparisons[0]
        assert hasattr(comp, 'segment_num')
        assert hasattr(comp, 'driver1_time')
        assert hasattr(comp, 'driver2_time')
        assert hasattr(comp, 'time_delta')
        assert hasattr(comp, 'winner')

    def test_winner_determination(self):
        """Test winner is correctly determined."""
        tel1 = create_mock_telemetry(speed_multiplier=1.2)  # Faster
        tel2 = create_mock_telemetry(speed_multiplier=0.8)  # Slower
        config = Config(num_segments=5)

        comparisons = compare_segments(tel1, tel2, config)

        # Driver 1 should win most/all segments
        driver1_wins = sum(1 for c in comparisons if c.winner == "driver1")
        assert driver1_wins > 0

    def test_identical_laps_tie(self):
        """Test identical laps result in ties."""
        tel1 = create_mock_telemetry()
        tel2 = tel1.copy()
        config = Config(num_segments=5)

        comparisons = compare_segments(tel1, tel2, config)

        # All segments should be ties or very close
        ties = sum(1 for c in comparisons if c.winner == "tie")
        assert ties == len(comparisons)

    def test_time_delta_sign(self):
        """Test time delta has correct sign."""
        tel1 = create_mock_telemetry(speed_multiplier=0.9)  # Slower
        tel2 = create_mock_telemetry(speed_multiplier=1.1)  # Faster
        config = Config(num_segments=5)

        comparisons = compare_segments(tel1, tel2, config)

        # Delta should be positive (driver1 slower)
        for comp in comparisons:
            # Allow small numerical errors
            if comp.winner == "driver2":
                assert comp.time_delta > -0.01
