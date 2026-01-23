#!/bin/bash
# Tournament Snapshot Helper Script
# Quick access to snapshot commands

cd "$(dirname "$0")/.."
source venv/bin/activate

export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system"

# Run the snapshot script with all arguments
python3 scripts/tournament_snapshot.py "$@"
