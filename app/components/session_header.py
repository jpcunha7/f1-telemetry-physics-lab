"""
Session header component.

Displays session and lap information in a clean banner.

Author: João Pedro Cunha
"""

import streamlit as st
from typing import Dict, Any


def render_session_header(
    session_info: Dict[str, Any],
    driver1_name: str,
    driver2_name: str,
    lap1_info: Dict[str, Any],
    lap2_info: Dict[str, Any],
) -> None:
    """
    Render session header with session and lap information.

    Args:
        session_info: Session metadata dict
        driver1_name: Driver 1 name
        driver2_name: Driver 2 name
        lap1_info: Lap 1 metadata (lap_number, lap_time, compound, etc.)
        lap2_info: Lap 2 metadata
    """
    st.markdown("---")

    # Session badge
    col1, col2, col3 = st.columns([2, 3, 2])

    with col1:
        st.markdown(f"**Session:** {session_info['event_name']} - {session_info['session_type']}")
        st.markdown(f"**Date:** {session_info['date']}")

    with col2:
        st.markdown(
            f"<h3 style='text-align: center;'>{driver1_name} vs {driver2_name}</h3>",
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(f"**Location:** {session_info['location']}, {session_info['country']}")

    st.markdown("---")

    # Lap selection summary
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"**{driver1_name}**")
        st.markdown(f"- Lap: {lap1_info['lap_number']}")
        st.markdown(f"- Time: {lap1_info['lap_time']}")
        if "compound" in lap1_info and lap1_info["compound"]:
            st.markdown(f"- Compound: {lap1_info['compound']}")

    with col2:
        st.markdown(f"**{driver2_name}**")
        st.markdown(f"- Lap: {lap2_info['lap_number']}")
        st.markdown(f"- Time: {lap2_info['lap_time']}")
        if "compound" in lap2_info and lap2_info["compound"]:
            st.markdown(f"- Compound: {lap2_info['compound']}")

    st.markdown("---")
