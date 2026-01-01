#!/usr/bin/env python3
"""Test script to verify render_smart_matrix import"""

import sys
from pathlib import Path

# Add streamlit_app to path
sys.path.insert(0, str(Path(__file__).parent / "streamlit_app"))

try:
    from components.semesters import render_smart_matrix
    print(f"✅ Successfully imported render_smart_matrix")
    print(f"   Function: {render_smart_matrix}")
    print(f"   Module: {render_smart_matrix.__module__}")
    print(f"   File: {render_smart_matrix.__code__.co_filename}")

    # Check signature
    import inspect
    sig = inspect.signature(render_smart_matrix)
    print(f"   Signature: {sig}")

    if len(sig.parameters) == 2 and 'token' in sig.parameters:
        print("✅ Correct signature! (token, user_role)")
    else:
        print(f"❌ Wrong signature! Expected (token, user_role), got {sig}")

except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
