"""
F1 Telemetry Physics Lab: Driver & Car Behavior Explorer

A telemetry analysis toolkit for comparing F1 laps with physics-grounded insights.

Author: João Pedro Cunha
License: MIT
"""

__version__ = "0.1.0"
__author__ = "João Pedro Cunha"

from f1telemetry import config, data_loader, alignment, physics, metrics, viz

__all__ = [
    "config",
    "data_loader",
    "alignment",
    "physics",
    "metrics",
    "viz",
]
