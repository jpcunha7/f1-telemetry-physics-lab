"""
Exports Page.

Provides download functionality for reports and data exports.

Author: João Pedro Cunha
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import streamlit as st
import logging
from io import StringIO

from f1telemetry import report as report_module

logger = logging.getLogger(__name__)


def render():
    """Render the Exports page."""
    st.header("Exports & Downloads")

    if not st.session_state.get("data_loaded", False):
        st.info("Load data using the sidebar on the main comparison pages to enable exports")
        return

    st.markdown(
        """
    Download analysis results and reports in various formats.
    """
    )

    # HTML Report Section
    st.subheader("HTML Report")
    st.markdown("Generate a comprehensive HTML report with all analysis and visualizations.")

    if st.button("Generate HTML Report", type="primary"):
        try:
            with st.spinner("Generating HTML report..."):
                # Generate report with enhanced insights
                html_content = report_module.generate_html_report(
                    session_info=st.session_state.session_info,
                    comparison_summary=st.session_state.comparison_summary,
                    driver1_name=st.session_state.driver1_name,
                    driver2_name=st.session_state.driver2_name,
                    telemetry1=st.session_state.telemetry1,
                    telemetry2=st.session_state.telemetry2,
                    config=st.session_state.config,
                    minisector_data=st.session_state.minisector_data,
                    corners1=st.session_state.corners1,
                    corners2=st.session_state.corners2,
                    decompositions=st.session_state.decompositions,
                )

                # Provide download button
                st.download_button(
                    label="Download HTML Report",
                    data=html_content,
                    file_name=f"f1_telemetry_report_{st.session_state.driver1_name}_vs_{st.session_state.driver2_name}.html",
                    mime="text/html",
                )

                st.success("HTML report generated successfully!")

        except Exception as e:
            st.error(f"Error generating HTML report: {str(e)}")
            logger.error(f"HTML report generation error: {e}", exc_info=True)

    st.markdown("---")

    # CSV Exports Section
    st.subheader("CSV Data Exports")
    st.markdown("Download raw analysis data as CSV files.")

    col1, col2 = st.columns(2)

    with col1:
        # Minisector deltas CSV
        st.markdown("**Minisector Deltas**")
        if st.button("Export Minisector Data"):
            try:
                csv_buffer = StringIO()
                st.session_state.minisector_data.to_csv(csv_buffer, index=False)
                csv_data = csv_buffer.getvalue()

                st.download_button(
                    label="Download Minisector CSV",
                    data=csv_data,
                    file_name=f"minisector_deltas_{st.session_state.driver1_name}_vs_{st.session_state.driver2_name}.csv",
                    mime="text/csv",
                )
                st.success("Minisector data ready for download!")
            except Exception as e:
                st.error(f"Error exporting minisector data: {str(e)}")

        # Corner comparison CSV
        st.markdown("**Corner Performance**")
        if st.button("Export Corner Data"):
            try:
                from f1telemetry import corners as corners_module

                corner_table = corners_module.create_corner_report_table(
                    st.session_state.corners1,
                    st.session_state.corners2,
                    st.session_state.driver1_name,
                    st.session_state.driver2_name,
                )

                csv_buffer = StringIO()
                corner_table.to_csv(csv_buffer, index=False)
                csv_data = csv_buffer.getvalue()

                st.download_button(
                    label="Download Corner CSV",
                    data=csv_data,
                    file_name=f"corner_performance_{st.session_state.driver1_name}_vs_{st.session_state.driver2_name}.csv",
                    mime="text/csv",
                )
                st.success("Corner data ready for download!")
            except Exception as e:
                st.error(f"Error exporting corner data: {str(e)}")

    with col2:
        # Braking zones CSV
        st.markdown("**Braking Zones**")
        if st.button("Export Braking Zones"):
            try:
                if not st.session_state.braking_comparison.empty:
                    csv_buffer = StringIO()
                    st.session_state.braking_comparison.to_csv(csv_buffer, index=False)
                    csv_data = csv_buffer.getvalue()

                    st.download_button(
                        label="Download Braking Zones CSV",
                        data=csv_data,
                        file_name=f"braking_zones_{st.session_state.driver1_name}_vs_{st.session_state.driver2_name}.csv",
                        mime="text/csv",
                    )
                    st.success("Braking zones data ready for download!")
                else:
                    st.warning("No braking zones data available")
            except Exception as e:
                st.error(f"Error exporting braking zones: {str(e)}")

        # Delta decomposition CSV
        st.markdown("**Delta Decomposition**")
        if st.button("Export Delta Decomposition"):
            try:
                from f1telemetry import delta_decomp

                decomp_table = delta_decomp.create_decomposition_table(
                    st.session_state.decompositions,
                    st.session_state.driver1_name,
                    st.session_state.driver2_name,
                )

                csv_buffer = StringIO()
                decomp_table.to_csv(csv_buffer, index=False)
                csv_data = csv_buffer.getvalue()

                st.download_button(
                    label="Download Decomposition CSV",
                    data=csv_data,
                    file_name=f"delta_decomposition_{st.session_state.driver1_name}_vs_{st.session_state.driver2_name}.csv",
                    mime="text/csv",
                )
                st.success("Delta decomposition data ready for download!")
            except Exception as e:
                st.error(f"Error exporting delta decomposition: {str(e)}")

    st.markdown("---")

    # Raw Telemetry Export
    st.subheader("Raw Telemetry Data")
    st.markdown("Download raw telemetry data with physics channels.")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"**{st.session_state.driver1_name} Telemetry**")
        if st.button(f"Export {st.session_state.driver1_name} Telemetry"):
            try:
                csv_buffer = StringIO()
                st.session_state.telemetry1.to_csv(csv_buffer, index=False)
                csv_data = csv_buffer.getvalue()

                st.download_button(
                    label=f"Download {st.session_state.driver1_name} Telemetry CSV",
                    data=csv_data,
                    file_name=f"telemetry_{st.session_state.driver1_name}.csv",
                    mime="text/csv",
                )
                st.success("Telemetry data ready for download!")
            except Exception as e:
                st.error(f"Error exporting telemetry: {str(e)}")

    with col2:
        st.markdown(f"**{st.session_state.driver2_name} Telemetry**")
        if st.button(f"Export {st.session_state.driver2_name} Telemetry"):
            try:
                csv_buffer = StringIO()
                st.session_state.telemetry2.to_csv(csv_buffer, index=False)
                csv_data = csv_buffer.getvalue()

                st.download_button(
                    label=f"Download {st.session_state.driver2_name} Telemetry CSV",
                    data=csv_data,
                    file_name=f"telemetry_{st.session_state.driver2_name}.csv",
                    mime="text/csv",
                )
                st.success("Telemetry data ready for download!")
            except Exception as e:
                st.error(f"Error exporting telemetry: {str(e)}")

    st.markdown("---")

    # Data Preview
    st.subheader("Data Preview")
    st.markdown("Preview available data before downloading.")

    data_type = st.selectbox(
        "Select data to preview",
        options=[
            "Minisector Deltas",
            "Braking Zones",
            "Corner Performance",
            "Delta Decomposition",
            f"{st.session_state.driver1_name} Telemetry",
            f"{st.session_state.driver2_name} Telemetry",
        ],
    )

    if data_type == "Minisector Deltas":
        st.dataframe(st.session_state.minisector_data, use_container_width=True)
    elif data_type == "Braking Zones":
        if not st.session_state.braking_comparison.empty:
            st.dataframe(st.session_state.braking_comparison, use_container_width=True)
        else:
            st.info("No braking zones data available")
    elif data_type == "Corner Performance":
        from f1telemetry import corners as corners_module

        corner_table = corners_module.create_corner_report_table(
            st.session_state.corners1,
            st.session_state.corners2,
            st.session_state.driver1_name,
            st.session_state.driver2_name,
        )
        st.dataframe(corner_table, use_container_width=True)
    elif data_type == "Delta Decomposition":
        from f1telemetry import delta_decomp

        decomp_table = delta_decomp.create_decomposition_table(
            st.session_state.decompositions,
            st.session_state.driver1_name,
            st.session_state.driver2_name,
        )
        st.dataframe(decomp_table, use_container_width=True)
    elif data_type == f"{st.session_state.driver1_name} Telemetry":
        st.dataframe(st.session_state.telemetry1.head(100), use_container_width=True)
        st.caption(f"Showing first 100 of {len(st.session_state.telemetry1)} rows")
    elif data_type == f"{st.session_state.driver2_name} Telemetry":
        st.dataframe(st.session_state.telemetry2.head(100), use_container_width=True)
        st.caption(f"Showing first 100 of {len(st.session_state.telemetry2)} rows")
