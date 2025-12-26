# F1 Telemetry Physics Lab: Methodology

**Author:** João Pedro Cunha

---

## Overview

This document describes the technical methodology, physics approximations, and engineering approach used in the F1 Telemetry Physics Lab.

## 1. Data Source and Preprocessing

### FastF1 Data Loading
- **Source:** FastF1 Python package (free, open-source)
- **Data types:** Position (X, Y), Speed, Throttle, Brake, Gear, DRS, Distance
- **Caching:** Local cache to avoid repeated downloads
- **Sessions supported:** Practice, Qualifying, Sprint, Race (2018-2025)

### Lap Selection
- **Fastest lap mode:** Automatically selects each driver's fastest lap
- **Manual mode:** Specify exact lap numbers
- **Filtering:** Excludes in/out laps, pit laps, and incomplete laps

## 2. Distance-Based Alignment

### Why Distance Alignment?
Time-based comparison is misleading when drivers are at different speeds. Distance-based alignment ensures we compare the same physical location on track.

### Alignment Process
1. **Common distance grid:** Create uniform distance points (default: 5m resolution)
2. **Interpolation:** Use linear interpolation to map telemetry to common grid
3. **Monotonicity check:** Ensure distance increases monotonically
4. **Validation:** Check for data quality issues

### Mathematical Formulation
```
For each telemetry channel (Speed, Throttle, Brake, etc.):
  Interpolated_value(d) = interp1d(Distance_original, Value_original)(d)
  where d ∈ [0, max_distance] with step = resolution
```

## 3. Minisector Analysis

### Segmentation Method
- **Definition:** Track divided into N equal-distance segments (minisectors)
- **Default:** 50 minisectors (varies by track length)
- **Time delta:** Computed by integrating speed over distance for each minisector

### Delta Calculation
```
For minisector i:
  time_driver1 = ∫ (1 / speed1(d)) dd over minisector distance
  time_driver2 = ∫ (1 / speed2(d)) dd over minisector distance
  delta_i = time_driver1 - time_driver2
```

### Top Gains Analysis
Identifies minisectors with largest time differences and correlates with:
- Brake application difference
- Throttle difference
- Minimum speed difference

## 4. Corner Detection and Analysis

### Detection Algorithm
Corners detected as local minima in speed profile with additional criteria:
- Minimum speed drop threshold
- Minimum corner duration
- Heading change (if position data available)

### Corner Metrics
For each detected corner:
- **Entry speed:** Speed at brake onset
- **Minimum speed:** Lowest speed in corner
- **Exit speed:** Speed at throttle reapplication
- **Brake start distance:** Where brake pressure exceeds threshold
- **Peak deceleration:** Maximum negative acceleration in braking zone

### Delta Decomposition
Each corner's time delta categorized into three phases:
1. **Braking:** Compare brake onset and entry speed
2. **Mid-corner:** Compare minimum speed
3. **Traction/Exit:** Compare throttle reapply point and exit acceleration

**Dominant cause assignment:**
- If |braking_delta| > |mid_corner_delta| and |exit_delta|: "Braking"
- Else if |mid_corner_delta| > others: "Mid-corner"
- Else: "Traction/Exit"

## 5. Physics Approximations

### Longitudinal Acceleration
```
ax = dv/dt ≈ Δv / Δt
```
- Computed from speed and time telemetry
- Smoothed to reduce noise
- Approximate only (ignores air resistance, mass, fuel load)

### Lateral Acceleration (GG Diagram)
```
ay ≈ v² * κ
where κ = curvature = d(heading)/d(distance)
```
- Heading computed from position (X, Y) data via arctangent
- Requires position data availability
- Highly approximate (ignores banking, aero, tire slip angle)

### GG Diagram Regions
- **Braking zone:** ax < -1.0g
- **Cornering zone:** |ay| > 1.0g
- **Traction zone:** ax > 0.5g
- **Combined:** High |ax| and |ay|

## 6. Multi-Lap Consistency Analysis

### Driver Fingerprint Metrics
- **Brake consistency:** Standard deviation of brake onset points across laps
- **Corner speed consistency:** Variance in minimum corner speeds
- **Throttle aggressiveness:** Average throttle application rate

### Outlier Detection
Laps with minisector deltas > 2 standard deviations from mean flagged as inconsistent.

## 7. Limitations and Caveats

### What We DON'T Model
- **Aerodynamics:** Downforce, drag, DRS effect on cornering
- **Tire physics:** Grip levels, temperature, degradation, compounds
- **Track elevation:** Uphill/downhill effects on acceleration
- **Fuel load:** Mass changes over race distance
- **Traffic:** Following another car in dirty air
- **Weather:** Temperature, wind, rain effects

### Interpretation Guidelines
- Use for **relative comparison** between laps
- Treat acceleration values as **approximate indicators**, not absolute measurements
- Consider context (tire age, fuel load, traffic) when interpreting differences
- Physics calculations are **simplified models** for comparative insight

## 8. Visualization Standards

### Plotly Dark Theme
- Template: `plotly_dark`
- Primary color: F1 Red (#FF1E1E)
- Background: #0E1117
- Grid: Subtle gray

### Plot Types
1. **Speed vs Distance:** Overlaid line plots
2. **Delta Time:** Cumulative difference over distance
3. **Throttle/Brake:** Filled area plots (0-100%)
4. **Track Map:** 2D position colored by metric (speed, throttle, delta)
5. **Minisector Bar Chart:** Horizontal bars showing gains/losses
6. **GG Diagram:** Scatter plot of ax vs ay
7. **Corner Catalog:** Table with sortable columns

## 9. Quality Assurance

### Data Validation
- Check for monotonic distance
- Verify telemetry channel availability
- Detect missing position data
- Flag potential outliers (e.g., SC laps, pit laps)

### Reproducibility
- All computations deterministic
- Configuration saved with outputs
- FastF1 cache versioning

---

## References

1. **FastF1 Documentation:** https://docs.fastf1.dev/
2. **Race Engineering Principles:** Various F1 technical publications
3. **Telemetry Analysis:** Industry standard practices

---

**Document Version:** 1.0
**Last Updated:** 2025-12-26
**Author:** João Pedro Cunha
