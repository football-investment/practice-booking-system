#!/bin/bash
cd "/Users/lovas.zoltan/Seafile/Football Investment/Projects/Football Investment Internship/practice_booking_system"
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system"
source implementation/venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
