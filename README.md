# F1 Telemetry Physics Lab: Driver & Car Behavior Explorer

A comprehensive telemetry analysis toolkit and interactive dashboard for comparing Formula 1 laps with physics-grounded insights. Built with Python, FastF1, and Streamlit.

**Author:** João Pedro Cunha
**License:** MIT

---

## Overview

F1 Telemetry Physics Lab is a production-quality analysis tool that:

- **Compares two F1 laps** from the same session with distance-based alignment
- **Translates telemetry into physics insights**: braking zones, cornering behavior, acceleration profiles, and delta time analysis
- **Provides engineering-quality visualizations**: interactive plots with Plotly showing speed traces, throttle/brake application, gear selection, and track maps
- **Identifies where laps are won/lost**: segment-by-segment comparison with detailed insights
- **Offers both CLI and web interfaces**: generate batch reports via command line or explore interactively in a Streamlit dashboard

All functionality uses **100% free and open-source** tools and data sources (FastF1 API). No paid APIs or services required.

---

## Features

### Core Analysis
- Distance-based lap alignment and interpolation
- Physics-derived metrics (longitudinal acceleration, braking zones, corner detection)
- Cumulative delta time calculation
- Segment-by-segment performance comparison

### Visualizations
- Speed vs distance overlay
- Throttle and brake application comparison
- Gear selection analysis
- Delta time progression
- Track map colored by speed/throttle/brake
- Longitudinal acceleration profiles
- Segment winners bar chart

### Interfaces
1. **Streamlit Dashboard**: Interactive web app with 4 pages
   - Lap Compare
   - Track Map
   - Braking & Cornering
   - Session Explorer / Data QA

2. **CLI Tool**: Batch report generation
   - HTML reports with embedded interactive plots
   - PNG image export option
   - Configurable analysis parameters

---

## Installation

### Prerequisites
- Python 3.9 or higher
- Poetry (recommended) or pip

### Using Poetry (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/f1telemetry.git
cd f1telemetry

# Install dependencies
poetry install

# Activate virtual environment
poetry shell
```

### Using pip

```bash
# Clone the repository
git clone https://github.com/yourusername/f1telemetry.git
cd f1telemetry

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
1. Enter session details in the sidebar (year, event, session type)
2. Select two drivers and lap selection (fastest or specific lap number)
3. Click "Load Data"
4. Explore the analysis across different pages
5. Download HTML reports from the Session Explorer page

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
f1telemetry/
├── src/
│   └── f1telemetry/
│       ├── __init__.py
│       ├── config.py              # Configuration and validation
│       ├── data_loader.py         # FastF1 data loading with caching
│       ├── alignment.py           # Distance-based lap alignment
│       ├── physics.py             # Physics computations (accel, braking, corners)
│       ├── metrics.py             # Lap comparison metrics
│       ├── viz.py                 # Plotly visualizations
│       ├── report.py              # HTML report generation
│       └── cli.py                 # Command-line interface
├── app/
│   └── streamlit_app.py           # Streamlit dashboard
├── tests/
│   ├── test_alignment.py
│   ├── test_physics.py
│   └── test_metrics.py
├── .github/workflows/
│   └── ci.yml                     # GitHub Actions CI/CD
├── pyproject.toml                 # Poetry dependencies and config
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

## Roadmap

Future enhancements:
- [ ] Multi-lap analysis (race stint comparison)
- [ ] Tire compound and degradation tracking
- [ ] Weather impact visualization
- [ ] Comparison across different sessions/weekends
- [ ] Export to CSV/JSON for external analysis
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
- Email: [your-email@example.com]

---

**Built with Claude Code** | Data powered by FastF1
