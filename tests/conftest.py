"""
SAT Centre Updater - Pytest Configuration

Shared fixtures and configuration for the test suite.
"""

import sys
from pathlib import Path

# Ensure sat_updater package is importable
sys.path.insert(0, str(Path(__file__).parent.parent))
