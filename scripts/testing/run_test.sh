#!/bin/bash
cd "/Users/lovas.zoltan/Seafile/Football Investment/Projects/Football Investment Internship/practice_booking_system"
source venv/bin/activate
export PYTHONPATH="${PWD}:${PYTHONPATH}"
pytest tests/e2e/test_complete_registration_flow.py::TestCompleteRegistrationFlow::test_02_admin_creates_coupon -v --headed --browser firefox --slowmo 1000 -s
