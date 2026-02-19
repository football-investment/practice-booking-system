"""
Semester Management Components
Modular components for LFA Education Center semester operations
Extracted from unified_workflow_dashboard.py
"""

from .location_management import render_location_management
from .semester_generation import render_semester_generation
from .semester_management import render_semester_management
from .semester_overview import render_semester_overview

# DON'T import from .smart_matrix because it's ambiguous (both a .py file and a directory exist)
# Instead, import directly from the file
import sys
from pathlib import Path
_parent = Path(__file__).parent
_spec_path = _parent / "smart_matrix.py"
if _spec_path.exists():
    import importlib.util
    spec = importlib.util.spec_from_file_location("_smart_matrix_file", _spec_path)
    _smart_matrix_file = importlib.util.module_from_spec(spec)
    sys.modules["_smart_matrix_file"] = _smart_matrix_file
    spec.loader.exec_module(_smart_matrix_file)
    render_smart_matrix = _smart_matrix_file.render_smart_matrix
else:
    # Fallback if file doesn't exist
    from .smart_matrix import render_smart_matrix

__all__ = [
    'render_location_management',
    'render_semester_generation',
    'render_semester_management',
    'render_semester_overview',
    'render_smart_matrix'
]
