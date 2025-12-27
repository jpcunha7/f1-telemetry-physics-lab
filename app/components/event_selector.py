"""
Event selector component with season schedule integration.

Provides robust event selection using FastF1 schedule data.

Author: João Pedro Cunha
"""

import streamlit as st
from typing import Tuple, Dict, Any
import pandas as pd
import fastf1
import logging

logger = logging.getLogger(__name__)


@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_season_schedule(year: int) -> pd.DataFrame:
    """
    Get season schedule from FastF1.

    Args:
        year: Season year

    Returns:
        DataFrame with event schedule
    """
    try:
        schedule = fastf1.get_event_schedule(year)
        return schedule
    except Exception as e:
        logger.error(f"Failed to load season schedule for {year}: {e}")
        return pd.DataFrame()


def render_event_selector(
    year: int,
    key_prefix: str = "event",
) -> Tuple[str, Dict[str, Any]]:
    """
    Render event selector with season schedule dropdown.

    Args:
        year: Selected year
        key_prefix: Unique key prefix for widgets

    Returns:
        Tuple of (event_identifier, event_metadata)
        event_identifier: Either event name or round number as string
        event_metadata: Dict with event information
    """
    # Load season schedule
    schedule = get_season_schedule(year)

    if schedule.empty:
        # Fallback to text input
        event_identifier = st.text_input(
            "Event",
            value="Monaco",
            key=f"{key_prefix}_fallback_input",
            help="Enter event name (e.g., 'Monaco', 'Monza')",
        )
        event_metadata = {"event_name": event_identifier, "round": None}
    else:
        # Create event options
        event_options = []
        event_map = {}

        for idx, row in schedule.iterrows():
            # Build label: "Round X - Event Name (Location)"
            round_num = row["RoundNumber"]
            event_name = row["EventName"]
            location = row["Location"] if "Location" in row else row.get("Country", "")

            label = f"Round {round_num} - {event_name}"
            if location and location != event_name:
                label += f" ({location})"

            event_options.append(label)
            event_map[label] = {
                "event_name": event_name,
                "round": int(round_num),
                "location": location,
                "country": row.get("Country", ""),
                "date": str(row.get("EventDate", "")),
            }

        # Dropdown selector
        selected_label = st.selectbox(
            "Event",
            options=event_options,
            key=f"{key_prefix}_dropdown",
        )

        event_metadata = event_map[selected_label]
        event_identifier = event_metadata["event_name"]

    return event_identifier, event_metadata
