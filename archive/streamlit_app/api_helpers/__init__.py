"""
API Helpers Package
Modular API helper functions for Streamlit frontend
"""

# Re-export all general helper functions for backward compatibility
import sys
from pathlib import Path

# Add parent directory to path to import api_helpers_general
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from api_helpers_general import *

# Import instructors subpackage
from . import instructors

# Export all instructor functions
from .instructors import *

# Combine all exports
import api_helpers_general
__all__ = list(api_helpers_general.__dict__.keys()) + instructors.__all__
