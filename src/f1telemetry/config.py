"""
Configuration module for F1 Telemetry Physics Lab.

Defines default settings, validation, and configuration management.

Author: João Pedro Cunha
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)

SessionType = Literal["FP1", "FP2", "FP3", "Q", "S", "R"]


@dataclass
class Config:
    """Configuration settings for F1 telemetry analysis."""

    # Cache settings
    cache_dir: Path = field(default_factory=lambda: Path("cache"))
    enable_cache: bool = True

    # Analysis settings
    distance_resolution: float = 5.0  # meters
    smoothing_window: int = 11  # points for Savitzky-Golay filter
    smoothing_polyorder: int = 3  # polynomial order for Savitzky-Golay
    brake_threshold: float = 10.0  # percentage, threshold to detect braking
    speed_threshold_corner: float = 200.0  # km/h, below this might be a corner

    # Segment analysis
    num_segments: int = 10  # number of segments for lap division

    # Minisector analysis
    num_minisectors: int = 50  # number of minisectors for fine-grained delta analysis
    minisector_variance_threshold: float = 0.05  # seconds, threshold for identifying mistake zones

    # Corner detection
    corner_min_speed_threshold: float = (
        250.0  # km/h, maximum speed to consider as corner (increased to detect fast corners)
    )
    corner_prominence: float = (
        10.0  # km/h, minimum speed drop to detect corner (decreased to detect more corners)
    )
    corner_min_distance: int = (
        20  # samples, minimum distance between corners (decreased to allow closer corners)
    )

    # G-G diagram and acceleration
    max_lateral_g: float = 6.0  # maximum lateral g-force for clipping
    max_longitudinal_g: float = 5.0  # maximum longitudinal g-force for clipping
    brake_g_threshold: float = 1.0  # g-force threshold for braking zone detection
    traction_g_threshold: float = 0.5  # g-force threshold for traction zone detection
    cornering_g_threshold: float = 1.0  # lateral g threshold for cornering zone detection

    # Multi-lap analysis
    consistency_threshold_sigma: float = 2.0  # sigma multiplier for outlier detection

    # Plotting settings
    plot_dpi: int = 150
    plot_width: int = 1200
    plot_height: int = 600
    plot_theme: str = "plotly_dark"
    primary_color: str = "#FF1E1E"  # F1 red
    secondary_color: str = "#1E90FF"  # Blue

    # Report settings
    report_dir: Path = field(default_factory=lambda: Path("reports"))
    output_format: Literal["html", "png", "both"] = "both"

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        self.cache_dir = Path(self.cache_dir)
        self.report_dir = Path(self.report_dir)

        # Create directories if they don't exist
        if self.enable_cache:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.report_dir.mkdir(parents=True, exist_ok=True)

        # Validate numeric settings
        if self.distance_resolution <= 0:
            raise ValueError("distance_resolution must be positive")
        if self.smoothing_window < 3:
            raise ValueError("smoothing_window must be at least 3")
        if self.smoothing_polyorder >= self.smoothing_window:
            raise ValueError("smoothing_polyorder must be less than smoothing_window")
        if self.num_segments < 1:
            raise ValueError("num_segments must be at least 1")

        logger.info("Configuration initialized successfully")

    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        return {
            "cache_dir": str(self.cache_dir),
            "enable_cache": self.enable_cache,
            "distance_resolution": self.distance_resolution,
            "smoothing_window": self.smoothing_window,
            "smoothing_polyorder": self.smoothing_polyorder,
            "brake_threshold": self.brake_threshold,
            "speed_threshold_corner": self.speed_threshold_corner,
            "num_segments": self.num_segments,
            "num_minisectors": self.num_minisectors,
            "minisector_variance_threshold": self.minisector_variance_threshold,
            "corner_min_speed_threshold": self.corner_min_speed_threshold,
            "corner_prominence": self.corner_prominence,
            "corner_min_distance": self.corner_min_distance,
            "max_lateral_g": self.max_lateral_g,
            "max_longitudinal_g": self.max_longitudinal_g,
            "brake_g_threshold": self.brake_g_threshold,
            "traction_g_threshold": self.traction_g_threshold,
            "cornering_g_threshold": self.cornering_g_threshold,
            "consistency_threshold_sigma": self.consistency_threshold_sigma,
            "plot_dpi": self.plot_dpi,
            "plot_width": self.plot_width,
            "plot_height": self.plot_height,
            "plot_theme": self.plot_theme,
            "primary_color": self.primary_color,
            "secondary_color": self.secondary_color,
            "report_dir": str(self.report_dir),
            "output_format": self.output_format,
        }


# Default configuration instance
DEFAULT_CONFIG = Config()


def validate_session_type(session: str) -> SessionType:
    """
    Validate and normalize session type.

    Args:
        session: Session type string (case-insensitive)

    Returns:
        Validated session type

    Raises:
        ValueError: If session type is invalid
    """
    session_upper = session.upper()
    valid_sessions: list[SessionType] = ["FP1", "FP2", "FP3", "Q", "S", "R"]

    if session_upper not in valid_sessions:
        raise ValueError(f"Invalid session type: {session}. Must be one of {valid_sessions}")

    return session_upper  # type: ignore


def validate_driver_code(driver: str) -> str:
    """
    Validate driver code format.

    Args:
        driver: Three-letter driver code

    Returns:
        Validated driver code in uppercase

    Raises:
        ValueError: If driver code format is invalid
    """
    driver_upper = driver.upper()

    if len(driver_upper) != 3:
        raise ValueError(f"Driver code must be 3 letters, got: {driver}")

    if not driver_upper.isalpha():
        raise ValueError(f"Driver code must be alphabetic, got: {driver}")

    return driver_upper


def validate_year(year: int) -> int:
    """
    Validate year for F1 data availability.

    Args:
        year: Year to validate

    Returns:
        Validated year

    Raises:
        ValueError: If year is outside valid range
    """
    if year < 2018 or year > 2025:
        logger.warning(
            f"Year {year} may not have data available. FastF1 typically supports 2018-2025."
        )

    return year
