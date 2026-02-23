#!/bin/bash
# Clean restart — always clears pycache before starting
PROJECT="$(cd "$(dirname "$0")" && pwd)"
echo "Clearing __pycache__..."
find "$PROJECT/streamlit_app" -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find "$PROJECT/streamlit_app" -name "*.pyc" -delete 2>/dev/null
echo "Starting Streamlit..."
source "$PROJECT/.venv/bin/activate"
# PYTHONDONTWRITEBYTECODE=1 prevents Python from writing .pyc files
# so stale pyc files can never accumulate during the session
export PYTHONDONTWRITEBYTECODE=1
# Ensure streamlit_app/ is always in Python's module search path
# so 'components' is always found as a regular package, regardless of
# any sys.path.insert calls in individual component files
export PYTHONPATH="$PROJECT/streamlit_app:${PYTHONPATH:-}"
streamlit run "$PROJECT/streamlit_app/🏠_Home.py" --server.port 8501
