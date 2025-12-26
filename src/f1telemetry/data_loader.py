"""
Data loading module for F1 Telemetry Physics Lab.

Handles loading sessions, laps, and telemetry data from FastF1 with caching.

Author: João Pedro Cunha
"""

import logging
from typing import Optional, Union

import fastf1
import pandas as pd
from fastf1.core import Lap, Session

from f1telemetry.config import Config, DEFAULT_CONFIG, SessionType

logger = logging.getLogger(__name__)


def enable_cache(cache_dir: str = "cache") -> None:
    """
    Enable FastF1 caching to avoid re-downloading data.

    Args:
        cache_dir: Directory to store cached data
    """
    try:
        fastf1.Cache.enable_cache(cache_dir)
        logger.info(f"FastF1 cache enabled at: {cache_dir}")
    except Exception as e:
        logger.warning(f"Failed to enable cache: {e}")


def load_session(
    year: int,
    event: Union[int, str],
    session_type: SessionType,
    config: Config = DEFAULT_CONFIG,
) -> Session:
    """
    Load an F1 session with error handling.

    Args:
        year: Season year (e.g., 2024)
        event: Event name (e.g., "Monaco") or round number
        session_type: Session type (FP1, FP2, FP3, Q, S, R)
        config: Configuration instance

    Returns:
        Loaded FastF1 Session object

    Raises:
        ValueError: If session cannot be loaded
    """
    try:
        # Enable cache if configured
        if config.enable_cache:
            enable_cache(str(config.cache_dir))

        logger.info(f"Loading session: {year} {event} {session_type}")
        session = fastf1.get_session(year, event, session_type)
        session.load()
        logger.info(f"Session loaded successfully: {session.event['EventName']}")

        return session

    except Exception as e:
        error_msg = (
            f"Failed to load session {year} {event} {session_type}. "
            f"Error: {str(e)}. "
            f"Ensure the event name/round and session type are correct."
        )
        logger.error(error_msg)
        raise ValueError(error_msg) from e


def get_lap(
    session: Session,
    driver: str,
    lap_selection: Union[int, str] = "fastest",
) -> Lap:
    """
    Get a specific lap for a driver.

    Args:
        session: FastF1 Session object
        driver: Three-letter driver code (e.g., "VER")
        lap_selection: Either "fastest" or a lap number

    Returns:
        Selected lap

    Raises:
        ValueError: If lap cannot be found
    """
    try:
        driver_laps = session.laps.pick_driver(driver)

        if driver_laps.empty:
            raise ValueError(f"No laps found for driver {driver}")

        if lap_selection == "fastest":
            lap = driver_laps.pick_fastest()
            logger.info(f"Selected fastest lap for {driver}: Lap {lap['LapNumber']}")
        else:
            lap_number = int(lap_selection)
            lap = driver_laps[driver_laps["LapNumber"] == lap_number].iloc[0]
            logger.info(f"Selected lap {lap_number} for {driver}")

        return lap

    except Exception as e:
        error_msg = (
            f"Failed to get lap for driver {driver} (selection: {lap_selection}). "
            f"Error: {str(e)}"
        )
        logger.error(error_msg)
        raise ValueError(error_msg) from e


def get_telemetry(lap: Lap) -> pd.DataFrame:
    """
    Get telemetry data for a lap.

    Args:
        lap: FastF1 Lap object

    Returns:
        DataFrame with telemetry data (Speed, Throttle, Brake, nGear, Distance, etc.)

    Raises:
        ValueError: If telemetry cannot be loaded
    """
    try:
        telemetry = lap.get_telemetry()

        if telemetry.empty:
            raise ValueError("Telemetry data is empty")

        # Ensure required columns exist
        required_columns = ["Distance", "Speed", "Throttle", "Brake"]
        missing_columns = [col for col in required_columns if col not in telemetry.columns]

        if missing_columns:
            raise ValueError(f"Missing required telemetry columns: {missing_columns}")

        logger.info(f"Loaded telemetry with {len(telemetry)} samples")

        return telemetry

    except Exception as e:
        error_msg = f"Failed to load telemetry: {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg) from e


def get_weather(session: Session) -> Optional[pd.DataFrame]:
    """
    Get weather data for a session.

    Args:
        session: FastF1 Session object

    Returns:
        Weather data DataFrame or None if not available
    """
    try:
        weather = session.weather_data
        if weather is not None and not weather.empty:
            logger.info("Weather data loaded")
            return weather
        else:
            logger.warning("Weather data not available for this session")
            return None
    except Exception as e:
        logger.warning(f"Could not load weather data: {e}")
        return None


def load_lap_comparison_data(
    year: int,
    event: Union[int, str],
    session_type: SessionType,
    driver1: str,
    driver2: str,
    lap1_selection: Union[int, str] = "fastest",
    lap2_selection: Union[int, str] = "fastest",
    config: Config = DEFAULT_CONFIG,
) -> tuple[Lap, Lap, pd.DataFrame, pd.DataFrame, Session]:
    """
    Load all data needed for lap comparison.

    Args:
        year: Season year
        event: Event name or round number
        session_type: Session type
        driver1: First driver code
        driver2: Second driver code
        lap1_selection: Lap selection for driver 1
        lap2_selection: Lap selection for driver 2
        config: Configuration instance

    Returns:
        Tuple of (lap1, lap2, telemetry1, telemetry2, session)

    Raises:
        ValueError: If data cannot be loaded
    """
    # Load session
    session = load_session(year, event, session_type, config)

    # Get laps
    lap1 = get_lap(session, driver1, lap1_selection)
    lap2 = get_lap(session, driver2, lap2_selection)

    # Get telemetry
    telemetry1 = get_telemetry(lap1)
    telemetry2 = get_telemetry(lap2)

    logger.info(
        f"Comparison data loaded: {driver1} ({lap1_selection}) vs " f"{driver2} ({lap2_selection})"
    )

    return lap1, lap2, telemetry1, telemetry2, session


def get_session_info(session: Session) -> dict:
    """
    Extract session information as a dictionary.

    Args:
        session: FastF1 Session object

    Returns:
        Dictionary with session metadata
    """
    return {
        "event_name": session.event.get("EventName", "Unknown"),
        "location": session.event.get("Location", "Unknown"),
        "country": session.event.get("Country", "Unknown"),
        "circuit": session.event.get("OfficialEventName", "Unknown"),
        "session_type": session.name,
        "date": str(session.date) if session.date else "Unknown",
    }
