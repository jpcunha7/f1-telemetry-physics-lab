# F1 Telemetry Physics Lab: Driver & Car Behavior Explorer

A comprehensive telemetry analysis toolkit and interactive dashboard for comparing Formula 1 laps with physics-grounded insights. Built with Python, FastF1, and Streamlit.

**Author:** João Pedro Cunha
**License:** MIT

---

## Overview

F1 Telemetry Physics Lab is a **production-ready, portfolio-grade** analysis tool that transforms F1 telemetry data into actionable insights:

- **Compares two F1 laps** with distance-based alignment and physics-grounded analysis
- **Tells the "where and why" story**: Automated sector-based insight generation identifies where time is won/lost
- **Advanced corner detection**: Improved algorithm detects ALL corners on the track with configurable parameters
- **Comprehensive braking analysis**: Detects and compares braking zones with detailed metrics
- **Track visualization**: Animated car positions and fastest driver region comparison
- **Interactive dashboard**: Streamlit web interface with 6 focused, specialized pages
- **Professional visualizations**: Interactive Plotly charts with sector and corner focus capabilities
- **User-friendly interface**: Dropdown selectors for all inputs (year, event, session, drivers)

All functionality uses **100% free and open-source** tools (FastF1, Streamlit, Plotly). No paid APIs required.

### Why This Matters

**For Motorsport Fans:**
- Clear storytelling: "VER brakes 10m later into Turn 1"
- Race pace analysis: "HAM's pace dropped 0.5s in final stint"
- Driver comparisons: "VER uses 15% more full throttle than LEC"

**For Data Science Portfolio:**
- Production-quality code architecture (1600+ lines)
- Comprehensive test coverage
- Clean separation of concerns
- Professional UI components
- Reproducible analysis pipeline

---

## Features

### 🎯 Core Analysis
- **Lap Comparison**: Distance-based alignment with physics channels and gear analysis
- **Sector-Based Insights**: Data-driven analysis focusing on F1's standard 3-sector format
- **Braking Zones**: Automatic detection and driver-vs-driver comparison
- **Corner Analysis**: Enhanced detection algorithm finds ALL corners with apex, entry, and exit metrics
- **Delta Decomposition**: Corner-by-corner performance breakdown by phase (braking, mid-corner, traction)
- **Track Visualization**: Animated lap comparison and fastest driver region mapping

### 📊 Dashboard Pages (Streamlit)

1. **Overview** - Session summary with sector-focused insights and lap time comparison (MM:SS.mmm format)
2. **Lap Compare** - Speed, delta, throttle/brake, and gear plots with **sector and corner focus** + **animated track visualization**
3. **Delta Decomposition** - Corner decomposition + **braking zones analysis** with detailed metrics
4. **Track Map & Corners** - **Fastest driver region map** + corner catalog + sortable corner-by-corner comparison
5. **G-G Diagram** - Friction circle + combined g-force + grip utilization statistics
6. **Data QA** - Channel availability matrix, data quality warnings, and lap validity statistics

### 🎨 Visualizations
- Speed comparison with sector/corner zoom
- Delta time progression
- Throttle & brake application
- Gear selection analysis (nGear)
- Animated car positions on track
- Fastest driver region map (color-coded by driver performance)
- Track maps with corner markers
- Corner delta decomposition waterfall charts
- Phase contribution analysis
- G-G diagrams (friction circle)
- Combined g-force plots
- Braking zones comparison tables

### 🖥️ CLI Tool
Batch report generation with:
- Configurable analysis parameters
- HTML reports with embedded interactive plots
- Optional PNG image export

---

## Installation

### Prerequisites
- Python 3.9 or higher
- Poetry (recommended) or pip

### Using Poetry (Recommended)

```bash
# Clone the repository
git clone https://github.com/jpcunha7/f1-telemetry-physics-lab.git
cd f1-telemetry-physics-lab

# Install dependencies
poetry install

# Activate virtual environment
poetry shell
```

### Using pip

```bash
# Clone the repository
git clone https://github.com/jpcunha7/f1-telemetry-physics-lab.git
cd f1-telemetry-physics-lab

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
```

---

## Quick Start

### Running the Streamlit Dashboard

```bash
# With Poetry
poetry run streamlit run app/streamlit_app.py

# Or with activated venv
streamlit run app/streamlit_app.py
```

Then open your browser to `http://localhost:8501`

**Usage:**
1. Select session details from dropdown menus in the sidebar:
   - **Year** - Choose from 2024-2018
   - **Event** - Select from full season schedule with round numbers
   - **Session Type** - Full names (e.g., "Qualifying", "Practice 1", "Race")
2. Select drivers from dropdown menus with full names (e.g., "Max Verstappen (VER)")
3. Choose lap selection (fastest or specific lap number)
4. Click "Load Data"
5. Explore the analysis across 6 focused pages

### Using the CLI

```bash
# Compare fastest laps in Monaco qualifying
poetry run f1telemetry report \
  --year 2024 \
  --event "Monaco" \
  --session Q \
  --driver1 VER \
  --driver2 LEC

# Compare specific lap numbers in a race
poetry run f1telemetry report \
  --year 2024 \
  --event "Monza" \
  --session R \
  --driver1 VER \
  --driver2 HAM \
  --lap1 15 \
  --lap2 16

# Save plots as PNG images
poetry run f1telemetry report \
  --year 2024 \
  --event "Silverstone" \
  --session Q \
  --driver1 NOR \
  --driver2 PIA \
  --save-plots

# Custom resolution and segments
poetry run f1telemetry report \
  --year 2024 \
  --event "Spa" \
  --session Q \
  --driver1 VER \
  --driver2 LEC \
  --resolution 10.0 \
  --segments 15
```

**CLI Options:**
- `--year`: Season year (required)
- `--event`: Event name or round number (required)
- `--session`: Session type - FP1/FP2/FP3/Q/S/R (required)
- `--driver1`, `--driver2`: Three-letter driver codes (required)
- `--lap1`, `--lap2`: "fastest" or lap number (default: "fastest")
- `--output`: Custom output path for HTML report
- `--resolution`: Distance resolution in meters (default: 5.0)
- `--segments`: Number of segments for lap division (default: 10)
- `--cache-dir`: FastF1 cache directory (default: cache/)
- `--no-cache`: Disable caching
- `--save-plots`: Save plots as PNG images
- `--verbose`, `-v`: Enable verbose logging

---

## Examples

### Example 1: Monaco GP 2024 Qualifying

```bash
poetry run f1telemetry report \
  --year 2024 \
  --event "Monaco" \
  --session Q \
  --driver1 VER \
  --driver2 LEC
```

**Output:** HTML report showing lap comparison with insights like:
- "VER is 0.234s faster than LEC"
- "Maximum gap of 0.187s occurs at 2450m (favoring VER)"
- "Biggest segment gain: VER in segment 7 (0.089s)"

### Example 2: Interactive Dashboard Analysis

1. Launch: `streamlit run app/streamlit_app.py`
2. Select: Year=2024, Event="Spa", Session=Q, Driver1=VER, Driver2=PIA
3. Load data and explore:
   - **Lap Compare**: See where VER gains time on PIA
   - **Track Map**: Visualize speed differences around the circuit
   - **Braking & Cornering**: Compare braking points and corner minimum speeds
   - **Session Explorer**: Download full HTML report

---

## Project Structure

```
f1-telemetry-physics-lab/
├── src/f1telemetry/               # Core analytics modules
│   ├── __init__.py
│   ├── config.py                  # Configuration and validation
│   ├── data_loader.py             # FastF1 data loading with caching
│   ├── alignment.py               # Distance-based lap alignment
│   ├── physics.py                 # Physics computations (accel, forces)
│   ├── metrics.py                 # Lap comparison metrics
│   ├── minisectors.py             # Minisector analysis
│   ├── corners.py                 # Corner detection and analysis
│   ├── delta_decomp.py            # Delta decomposition by phase
│   ├── gg_diagram.py              # G-G diagram and grip analysis
│   ├── braking_zones.py           # NEW: Braking zone detection
│   ├── race_pace.py               # NEW: Stint and race analysis
│   ├── style_profile.py           # NEW: Driver style profiling
│   ├── viz.py                     # Plotly visualizations
│   ├── report.py                  # Enhanced HTML report generation
│   └── cli.py                     # Command-line interface
├── app/
│   ├── streamlit_app.py           # Main dashboard (single-page app with 6 tabs)
│   ├── components/                # Reusable UI components
│   │   ├── session_header.py
│   │   ├── kpi_cards.py
│   │   ├── insight_summary.py     # Sector-focused insight generation
│   │   ├── lap_selector.py
│   │   └── event_selector.py      # Event dropdown with season schedule
│   └── _archived_pages/           # Archived multi-page components
├── tests/                         # Comprehensive test suite
│   ├── test_alignment.py
│   ├── test_physics.py
│   ├── test_metrics.py
│   ├── test_braking_zones.py      # NEW
│   ├── test_race_pace.py          # NEW
│   └── test_style_profile.py      # NEW
├── .github/workflows/
│   └── ci.yml                     # GitHub Actions CI/CD
├── docs/
│   └── methodology.md             # Analysis methodology
├── assets/                        # Screenshots and resources
├── pyproject.toml                 # Poetry dependencies
├── README.md
└── LICENSE
```

---

## Physics Approximations & Limitations

This tool provides **approximate physics calculations** intended for comparative analysis, not absolute measurements:

### What We Calculate
- **Longitudinal acceleration**: Estimated from speed and distance using kinematic equations (a = dv/dt)
- **Braking zones**: Detected from brake pressure threshold and speed reduction
- **Corner detection**: Identified as local minima in speed profiles
- **Delta time**: Cumulative time difference computed from speed and distance

### What We Ignore
- Vehicle mass and inertia
- Aerodynamic drag and downforce
- Track elevation changes
- Tire degradation and temperature effects
- Fuel load variations
- Detailed powertrain modeling

### Interpretation Guidelines
- Use insights for **relative comparison** between laps (e.g., "Driver A brakes later into Turn 7")
- Do **not** treat acceleration values as absolute measurements
- Results are approximate and smoothed to reduce noise
- When uncertain, insights use language like "suggests" or "likely" rather than "proves"

---

## Data Source

All telemetry data is sourced from [FastF1](https://docs.fastf1.dev/), a free and open-source Python package that provides access to F1 timing and telemetry data.

- **Supported seasons**: 2018-2025 (check FastF1 docs for latest availability)
- **Data cached locally** to avoid re-downloading
- **Zero cost**: No API keys or paid services required

---

## Development

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=f1telemetry --cov-report=term-missing

# Run specific test file
poetry run pytest tests/test_alignment.py -v
```

### Code Quality

```bash
# Format code
poetry run black src/ tests/

# Lint
poetry run ruff check src/ tests/

# Type checking
poetry run mypy src/f1telemetry --ignore-missing-imports
```

### CI/CD

GitHub Actions automatically runs tests and linting on push/PR to `main` or `develop`:
- Tests on Python 3.9, 3.10, 3.11
- Black formatting check
- Ruff linting
- MyPy type checking
- Pytest with coverage

---

## Screenshots

<!-- Add screenshots here after running the application -->

### Streamlit Dashboard - Lap Compare
*Screenshot placeholder: Show speed comparison and delta time plots*

### Streamlit Dashboard - Track Map
*Screenshot placeholder: Show track map colored by speed*

### Streamlit Dashboard - Braking & Cornering
*Screenshot placeholder: Show throttle/brake and acceleration plots*

### HTML Report Example
*Screenshot placeholder: Show generated HTML report*

---

## Troubleshooting

### Issue: "Session not found"
- Verify the event name matches exactly (e.g., "Monaco" not "Monte Carlo")
- Try using the round number instead of event name (e.g., `--event 6`)
- Check that the session type exists for that event

### Issue: "No laps found for driver"
- Verify the driver code is correct (3 letters, e.g., "VER" not "VERSTAPPEN")
- Ensure the driver participated in that session

### Issue: "FastF1 cache errors"
- Delete the cache directory and try again: `rm -rf cache/`
- Or disable caching: `--no-cache`

### Issue: "Track map shows 'Position data not available'"
- Some older sessions may not have X/Y position data
- This is a FastF1 data limitation, not a bug

---

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Ensure CI passes (black, ruff, mypy, pytest)
5. Submit a pull request

---

## Example Scenarios

### Scenario 1: Qualifying Battle - Monaco 2024
**Goal:** Understand where VER gained time over LEC in Monaco qualifying

```bash
# Load 2024 Monaco Q session
# Select VER vs LEC, fastest laps
# Navigate to Overview page
```

**What you'll discover:**
- Insight Summary shows: "VER is 0.234s faster"
- Top 3 locations: Casino Square (+0.089s), Tunnel (+0.067s), Swimming Pool (+0.045s)
- Breakdown: VER gains in braking (+0.142s) and traction (+0.078s)
- Key finding: "VER brakes 12m later into Mirabeau"

**Use the dashboard:**
- **Lap Compare** → Select "Sector" view → Choose Sector 1 → See detailed zoom with gear analysis
- **Lap Compare** → Watch animated car positions to visualize the race
- **Delta Decomposition** → View braking zones table → VER brakes later in 8 of 12 zones
- **Track Map & Corners** → See fastest driver region map → VER faster through tunnel section
- **Track Map & Corners** → Sort corners by min speed delta → VER carries 3.2 km/h more through Portier

---

## Roadmap

**Recently Completed:**
- [x] Sector-focused insights (replacing mini-sectors)
- [x] Enhanced corner detection algorithm (detects ALL corners)
- [x] Animated track visualization with car positions
- [x] Fastest driver region comparison map
- [x] Gear analysis (nGear) plots
- [x] Improved UI with dropdown selectors
- [x] Better lap time formatting (MM:SS.mmm)
- [x] Streamlined dashboard (6 focused pages)

**Future enhancements:**
- [ ] Multi-lap analysis (race stint comparison)
- [ ] Tire compound tracking
- [ ] Weather impact visualization
- [ ] Comparison across different sessions/weekends
- [ ] Machine learning for lap time prediction

---

## Acknowledgments

- **FastF1**: For providing free access to F1 telemetry data
- **Plotly**: For interactive visualization capabilities
- **Streamlit**: For rapid dashboard development
- **F1 Community**: For inspiring this analysis tool

---

## License

MIT License - see [LICENSE](LICENSE) for details

Copyright (c) 2025 João Pedro Cunha

---

## Contact

For questions, issues, or suggestions:
- Open an issue on GitHub

