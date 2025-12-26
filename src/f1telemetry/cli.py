"""
Command-line interface for F1 Telemetry Physics Lab.

Provides CLI commands for batch report generation.

Author: João Pedro Cunha
"""

import argparse
import logging
import sys
from pathlib import Path

from f1telemetry import (
    config as cfg,
    data_loader,
    alignment,
    physics,
    metrics,
    report,
    minisectors,
    corners as corners_module,
)

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """
    Set up logging configuration.

    Args:
        verbose: Enable verbose (DEBUG) logging
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def generate_report_command(args: argparse.Namespace) -> int:
    """
    Generate comparison report from command line arguments.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        # Validate inputs
        year = cfg.validate_year(args.year)
        session_type = cfg.validate_session_type(args.session)
        driver1 = cfg.validate_driver_code(args.driver1)
        driver2 = cfg.validate_driver_code(args.driver2)

        # Create configuration
        config = cfg.Config(
            cache_dir=Path(args.cache_dir) if args.cache_dir else cfg.DEFAULT_CONFIG.cache_dir,
            enable_cache=not args.no_cache,
            distance_resolution=args.resolution,
            num_segments=args.segments,
        )

        logger.info(
            f"Loading data: {year} {args.event} {session_type} - " f"{driver1} vs {driver2}"
        )

        # Load data
        lap1, lap2, telemetry1_raw, telemetry2_raw, session = data_loader.load_lap_comparison_data(
            year=year,
            event=args.event,
            session_type=session_type,
            driver1=driver1,
            driver2=driver2,
            lap1_selection=args.lap1,
            lap2_selection=args.lap2,
            config=config,
        )

        # Align laps
        logger.info("Aligning laps...")
        telemetry1, telemetry2 = alignment.align_laps(
            telemetry1_raw,
            telemetry2_raw,
            config,
        )

        # Add physics channels
        logger.info("Computing physics channels...")
        telemetry1 = physics.add_physics_channels(telemetry1, config)
        telemetry2 = physics.add_physics_channels(telemetry2, config)

        # Get session info
        session_info = data_loader.get_session_info(session)

        # Determine output path
        if args.output:
            output_path = Path(args.output)
        else:
            # Generate default filename
            event_name = session_info["event_name"].replace(" ", "_")
            filename = f"report_{event_name}_{session_type}_{driver1}_vs_{driver2}.html"
            output_path = config.report_dir / filename

        # Generate report
        logger.info("Generating HTML report...")
        report.generate_html_report(
            lap1=lap1,
            lap2=lap2,
            telemetry1=telemetry1,
            telemetry2=telemetry2,
            session_info=session_info,
            driver1_name=driver1,
            driver2_name=driver2,
            config=config,
            output_path=output_path,
        )

        # Save plots as images if requested
        if args.save_plots:
            plots_dir = output_path.parent / f"{output_path.stem}_plots"
            logger.info(f"Saving plots to: {plots_dir}")

            # Create comparison summary for plots
            comparison_summary = metrics.create_comparison_summary(
                lap1,
                lap2,
                telemetry1,
                telemetry2,
                driver1,
                driver2,
                config,
            )

            report.save_plots_as_images(
                telemetry1,
                telemetry2,
                driver1,
                driver2,
                comparison_summary,
                plots_dir,
                config,
            )

        logger.info(f"✅ Report generated successfully: {output_path}")
        return 0

    except Exception as e:
        logger.error(f"Failed to generate report: {e}", exc_info=args.verbose)
        return 1


def minisectors_command(args: argparse.Namespace) -> int:
    """
    Generate minisector analysis CSV from command line arguments.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        # Validate inputs
        year = cfg.validate_year(args.year)
        session_type = cfg.validate_session_type(args.session)
        driver1 = cfg.validate_driver_code(args.driver1)
        driver2 = cfg.validate_driver_code(args.driver2)

        # Create configuration
        config = cfg.Config(
            cache_dir=Path(args.cache_dir) if args.cache_dir else cfg.DEFAULT_CONFIG.cache_dir,
            enable_cache=not args.no_cache,
            num_minisectors=args.n_minisectors,
        )

        logger.info(f"Loading data for minisector analysis: {year} {args.event} {session_type}")

        # Load data
        lap1, lap2, telemetry1_raw, telemetry2_raw, session = data_loader.load_lap_comparison_data(
            year=year,
            event=args.event,
            session_type=session_type,
            driver1=driver1,
            driver2=driver2,
            lap1_selection=args.lap1,
            lap2_selection=args.lap2,
            config=config,
        )

        # Align laps
        logger.info("Aligning laps...")
        telemetry1, telemetry2 = alignment.align_laps(telemetry1_raw, telemetry2_raw, config)

        # Compute minisectors
        logger.info("Computing minisector deltas...")
        minisector_data = minisectors.compute_minisector_deltas(
            telemetry1, telemetry2, args.n_minisectors, config
        )

        # Create table
        table = minisectors.create_minisector_comparison_table(
            minisector_data, driver1, driver2
        )

        # Save to CSV
        output_path = Path(args.output) if args.output else config.report_dir / "minisectors.csv"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        table.to_csv(output_path, index=False)

        logger.info(f"Minisector analysis saved to: {output_path}")
        return 0

    except Exception as e:
        logger.error(f"Failed to generate minisector analysis: {e}", exc_info=args.verbose)
        return 1


def corners_command(args: argparse.Namespace) -> int:
    """
    Generate corner catalog CSV from command line arguments.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        # Validate inputs
        year = cfg.validate_year(args.year)
        session_type = cfg.validate_session_type(args.session)
        driver1 = cfg.validate_driver_code(args.driver1)
        driver2 = cfg.validate_driver_code(args.driver2)

        # Create configuration
        config = cfg.Config(
            cache_dir=Path(args.cache_dir) if args.cache_dir else cfg.DEFAULT_CONFIG.cache_dir,
            enable_cache=not args.no_cache,
        )

        logger.info(f"Loading data for corner analysis: {year} {args.event} {session_type}")

        # Load data
        lap1, lap2, telemetry1_raw, telemetry2_raw, session = data_loader.load_lap_comparison_data(
            year=year,
            event=args.event,
            session_type=session_type,
            driver1=driver1,
            driver2=driver2,
            lap1_selection=args.lap1,
            lap2_selection=args.lap2,
            config=config,
        )

        # Align laps
        logger.info("Aligning laps...")
        telemetry1, telemetry2 = alignment.align_laps(telemetry1_raw, telemetry2_raw, config)

        # Add physics channels
        logger.info("Computing physics channels...")
        telemetry1 = physics.add_physics_channels(telemetry1, config)
        telemetry2 = physics.add_physics_channels(telemetry2, config)

        # Detect corners
        logger.info("Detecting corners...")
        corners1 = corners_module.detect_corners(telemetry1, config=config)
        corners2 = corners_module.detect_corners(telemetry2, config=config)

        # Create comparison table
        table = corners_module.create_corner_report_table(corners1, corners2, driver1, driver2)

        # Save to CSV
        output_path = Path(args.output) if args.output else config.report_dir / "corners.csv"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        table.to_csv(output_path, index=False)

        logger.info(f"Corner analysis saved to: {output_path}")
        return 0

    except Exception as e:
        logger.error(f"Failed to generate corner analysis: {e}", exc_info=args.verbose)
        return 1


def main() -> int:
    """
    Main CLI entry point.

    Returns:
        Exit code
    """
    parser = argparse.ArgumentParser(
        description="F1 Telemetry Physics Lab - Driver & Car Behavior Explorer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Compare fastest laps in Monaco qualifying
  f1telemetry report --year 2024 --event "Monaco" --session Q --driver1 VER --driver2 LEC

  # Compare specific lap numbers
  f1telemetry report --year 2024 --event "Monza" --session R --driver1 VER --driver2 HAM --lap1 15 --lap2 16

  # Save plots as PNG images
  f1telemetry report --year 2024 --event "Silverstone" --session Q --driver1 NOR --driver2 PIA --save-plots

Author: João Pedro Cunha
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Report command
    report_parser = subparsers.add_parser(
        "report",
        help="Generate lap comparison report",
    )

    # Required arguments
    report_parser.add_argument(
        "--year",
        type=int,
        required=True,
        help="Season year (e.g., 2024)",
    )
    report_parser.add_argument(
        "--event",
        type=str,
        required=True,
        help='Event name (e.g., "Monaco", "Monza") or round number',
    )
    report_parser.add_argument(
        "--session",
        type=str,
        required=True,
        help="Session type: FP1, FP2, FP3, Q, S, R",
    )
    report_parser.add_argument(
        "--driver1",
        type=str,
        required=True,
        help="First driver code (e.g., VER)",
    )
    report_parser.add_argument(
        "--driver2",
        type=str,
        required=True,
        help="Second driver code (e.g., LEC)",
    )

    # Optional arguments
    report_parser.add_argument(
        "--lap1",
        type=str,
        default="fastest",
        help='Lap selection for driver1: "fastest" or lap number (default: fastest)',
    )
    report_parser.add_argument(
        "--lap2",
        type=str,
        default="fastest",
        help='Lap selection for driver2: "fastest" or lap number (default: fastest)',
    )
    report_parser.add_argument(
        "--output",
        type=str,
        help="Output HTML file path (default: auto-generated in reports/)",
    )
    report_parser.add_argument(
        "--resolution",
        type=float,
        default=5.0,
        help="Distance resolution in meters (default: 5.0)",
    )
    report_parser.add_argument(
        "--segments",
        type=int,
        default=10,
        help="Number of segments for lap division (default: 10)",
    )
    report_parser.add_argument(
        "--cache-dir",
        type=str,
        help="FastF1 cache directory (default: cache/)",
    )
    report_parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable FastF1 caching",
    )
    report_parser.add_argument(
        "--save-plots",
        action="store_true",
        help="Save plots as PNG images",
    )
    report_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    # Minisectors command
    minisectors_parser = subparsers.add_parser(
        "minisectors",
        help="Generate minisector analysis CSV",
    )
    minisectors_parser.add_argument("--year", type=int, required=True, help="Season year")
    minisectors_parser.add_argument("--event", type=str, required=True, help="Event name or round")
    minisectors_parser.add_argument("--session", type=str, required=True, help="Session type")
    minisectors_parser.add_argument("--driver1", type=str, required=True, help="First driver code")
    minisectors_parser.add_argument("--driver2", type=str, required=True, help="Second driver code")
    minisectors_parser.add_argument("--lap1", type=str, default="fastest", help="Lap selection for driver1")
    minisectors_parser.add_argument("--lap2", type=str, default="fastest", help="Lap selection for driver2")
    minisectors_parser.add_argument("--n-minisectors", type=int, default=50, help="Number of minisectors")
    minisectors_parser.add_argument("--output", type=str, help="Output CSV file path")
    minisectors_parser.add_argument("--cache-dir", type=str, help="FastF1 cache directory")
    minisectors_parser.add_argument("--no-cache", action="store_true", help="Disable caching")
    minisectors_parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")

    # Corners command
    corners_parser = subparsers.add_parser(
        "corners",
        help="Generate corner catalog CSV",
    )
    corners_parser.add_argument("--year", type=int, required=True, help="Season year")
    corners_parser.add_argument("--event", type=str, required=True, help="Event name or round")
    corners_parser.add_argument("--session", type=str, required=True, help="Session type")
    corners_parser.add_argument("--driver1", type=str, required=True, help="First driver code")
    corners_parser.add_argument("--driver2", type=str, required=True, help="Second driver code")
    corners_parser.add_argument("--lap1", type=str, default="fastest", help="Lap selection for driver1")
    corners_parser.add_argument("--lap2", type=str, default="fastest", help="Lap selection for driver2")
    corners_parser.add_argument("--output", type=str, help="Output CSV file path")
    corners_parser.add_argument("--cache-dir", type=str, help="FastF1 cache directory")
    corners_parser.add_argument("--no-cache", action="store_true", help="Disable caching")
    corners_parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")

    # Parse arguments
    args = parser.parse_args()

    # Set up logging
    setup_logging(args.verbose if hasattr(args, "verbose") else False)

    # Execute command
    if args.command == "report":
        return generate_report_command(args)
    elif args.command == "minisectors":
        return minisectors_command(args)
    elif args.command == "corners":
        return corners_command(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
