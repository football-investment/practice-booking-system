# API Smoke Test Generation Summary

**Total Endpoints:** 579
**Total Tests Generated:** 1737
**Domains:** 69

## Tests per Domain

| Domain | Endpoints | Tests Generated |
|--------|-----------|-----------------|
| _semesters_main | 6 | 18 |
| adaptive_learning | 7 | 21 |
| admin | 13 | 39 |
| analytics | 5 | 15 |
| attendance | 8 | 24 |
| audit | 6 | 18 |
| auth | 13 | 39 |
| bookings | 9 | 27 |
| campuses | 7 | 21 |
| certificates | 6 | 18 |
| coach | 9 | 27 |
| competency | 6 | 18 |
| coupons | 9 | 27 |
| curriculum | 16 | 48 |
| curriculum_adaptive | 6 | 18 |
| dashboard | 3 | 9 |
| debug | 3 | 9 |
| enrollments | 3 | 9 |
| feedback | 8 | 24 |
| game_presets | 6 | 18 |
| gamification | 3 | 9 |
| gancuju | 8 | 24 |
| gancuju_routes | 2 | 6 |
| groups | 7 | 21 |
| health | 5 | 15 |
| instructor | 8 | 24 |
| instructor_assignments | 11 | 33 |
| instructor_availability | 6 | 18 |
| instructor_dashboard | 3 | 9 |
| instructor_management | 27 | 81 |
| internship | 9 | 27 |
| internship_routes | 2 | 6 |
| invitation_codes | 5 | 15 |
| invoices | 8 | 24 |
| lfa_coach_routes | 3 | 9 |
| lfa_player | 8 | 24 |
| lfa_player_routes | 2 | 6 |
| license_renewal | 4 | 12 |
| licenses | 29 | 87 |
| locations | 6 | 18 |
| messages | 9 | 27 |
| motivation | 2 | 6 |
| notifications | 5 | 15 |
| onboarding | 7 | 21 |
| parallel_specializations | 8 | 24 |
| payment_verification | 6 | 18 |
| periods | 4 | 12 |
| profile | 3 | 9 |
| progression | 6 | 18 |
| projects | 22 | 66 |
| public_profile | 3 | 9 |
| quiz | 16 | 48 |
| reports | 7 | 21 |
| sandbox | 4 | 12 |
| semester_enrollments | 12 | 36 |
| semester_generator | 2 | 6 |
| semesters | 2 | 6 |
| session_groups | 4 | 12 |
| sessions | 19 | 57 |
| spec_info | 5 | 15 |
| specialization | 6 | 18 |
| specializations | 13 | 39 |
| student_features | 4 | 12 |
| students | 3 | 9 |
| system_events | 3 | 9 |
| tournament_types | 3 | 9 |
| tournaments | 72 | 216 |
| tracks | 8 | 24 |
| users | 16 | 48 |

## Test Types

Each endpoint has 3 tests:
1. **Happy Path** - Validates 200/201 response with admin auth
2. **Auth Required** - Validates 401/403 without authentication
3. **Input Validation** - Validates 422 with invalid payload (SKIPPED - needs manual implementation)

## Running Tests

```bash
# Run all smoke tests
pytest tests/integration/api_smoke -v

# Run specific domain
pytest tests/integration/api_smoke/test_tournaments_smoke.py -v

# Parallel execution
pytest tests/integration/api_smoke -n auto -v
```

## Next Steps

1. Review generated tests
2. Add realistic payloads for POST/PUT/PATCH endpoints
3. Implement input validation tests (currently skipped)
4. Add to CI pipeline as BLOCKING gate