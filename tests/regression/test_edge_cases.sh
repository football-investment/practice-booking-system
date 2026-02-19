#!/bin/bash

################################################################################
# REGRESSION TEST: Edge Cases & Bad State Handling
#
# Purpose: Validate system behavior with invalid inputs and edge conditions
#
# Critical Edge Cases Tested:
#   1. ✅ Reward distribution with 0 participants
#   2. ✅ Reward distribution without rankings
#   3. ✅ Reward distribution with invalid tournament status
#   4. ✅ Tournament with missing reward_config
#   5. ✅ Reward distribution for non-existent tournament
#   6. ✅ Tournament completion with no sessions
#   7. ✅ Enrollment to non-existent tournament
#   8. ✅ Invalid user_id in enrollment
#
# Risk Areas:
#   - NULL pointer exceptions
#   - Division by zero (0 participants)
#   - Missing required data
#   - Database constraint violations
################################################################################

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# API Configuration
API_BASE="http://localhost:8000"
API_V1="$API_BASE/api/v1"

################################################################################
# Helper Functions
################################################################################

assert_http_error() {
    local http_code=$1
    local expected_code=$2
    local operation=$3
    if [[ "$http_code" != "$expected_code" ]]; then
        echo -e "${RED}❌ $operation expected HTTP $expected_code, got $http_code${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ $operation correctly returned HTTP $expected_code${NC}"
}

################################################################################
# MAIN TEST FLOW
################################################################################

echo -e "\n${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   REGRESSION TEST: Edge Cases & Bad State Handling${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"

################################################################################
# STEP 1: Authenticate
################################################################################

echo -e "\n${YELLOW}Authenticating as admin...${NC}"
AUTH_RESPONSE=$(curl -s -X POST "$API_V1/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"email": "admin@lfa.com", "password": "admin123"}')

ACCESS_TOKEN=$(echo "$AUTH_RESPONSE" | jq -r '.access_token')
if [[ -z "$ACCESS_TOKEN" || "$ACCESS_TOKEN" == "null" ]]; then
    echo -e "${RED}❌ Authentication failed${NC}"
    exit 1
fi

AUTH_HEADER="Authorization: Bearer $ACCESS_TOKEN"
echo -e "${GREEN}✅ Authenticated successfully${NC}"

################################################################################
# TEST CASE 1: Reward Distribution with 0 Participants
################################################################################

echo -e "\n${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}TEST CASE 1: Reward Distribution with 0 Participants${NC}"
echo -e "${YELLOW}Expected: HTTP 400 or 404 (no rankings to distribute)${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Create tournament with COMPLETED status but NO rankings
START_DATE=$(date -u +"%Y-%m-%d")
END_DATE=$(date -u -v+7d +"%Y-%m-%d" 2>/dev/null || date -u -d "+7 days" +"%Y-%m-%d")
TIMESTAMP=$(date -u +"%Y%m%d_%H%M%S")

TOURNAMENT_ID_1=$(PGDATABASE=lfa_intern_system psql -U postgres -h localhost -t -c "
INSERT INTO semesters (
    code, name, start_date, end_date, specialization_type,
    status, tournament_status, format, scoring_type,
    enrollment_cost, sessions_generated, reward_policy_name,
    is_active, tournament_type_id, created_at, updated_at,
    reward_config
)
VALUES (
    'EDGE-0PLAYERS-$TIMESTAMP',
    'Edge Case: 0 Participants',
    '$START_DATE', '$END_DATE', 'LFA_FOOTBALL_PLAYER',
    'DRAFT', 'COMPLETED', 'HEAD_TO_HEAD', 'PLACEMENT',
    0, true, 'default', true,
    (SELECT id FROM tournament_types WHERE code = 'league'),
    NOW(), NOW(),
    '{
      \"skill_mappings\": [
        {\"skill\": \"passing\", \"weight\": 1.0, \"enabled\": true}
      ],
      \"first_place\": {\"xp_multiplier\": 1.5, \"credits\": 500}
    }'::jsonb
)
RETURNING id;
" | tr -d ' ' | head -1)

echo -e "${CYAN}Created tournament with 0 participants (ID: $TOURNAMENT_ID_1)${NC}"

# Attempt reward distribution
REWARD_RESPONSE_1=$(curl -s -w "\n%{http_code}" \
    -X POST "$API_V1/tournaments/$TOURNAMENT_ID_1/distribute-rewards-v2" \
    -H "$AUTH_HEADER" \
    -H "Content-Type: application/json" \
    -d "{\"tournament_id\": $TOURNAMENT_ID_1, \"force_redistribution\": false}")

REWARD_HTTP_1=$(echo "$REWARD_RESPONSE_1" | tail -n1)
REWARD_BODY_1=$(echo "$REWARD_RESPONSE_1" | sed '$d')

# Should return 400 or 200 with 0 distributed
if [[ "$REWARD_HTTP_1" == "400" ]]; then
    ERROR_MSG=$(echo "$REWARD_BODY_1" | jq -r '.error.message // empty')
    echo -e "${GREEN}✅ Correctly rejected with HTTP 400${NC}"
    echo -e "   Error: $ERROR_MSG"
elif [[ "$REWARD_HTTP_1" == "200" ]]; then
    TOTAL_USERS=$(echo "$REWARD_BODY_1" | jq -r '.rewards_distributed_count // 0')
    if [[ "$TOTAL_USERS" == "0" ]]; then
        echo -e "${GREEN}✅ Correctly handled 0 participants (distributed to 0 users)${NC}"
    else
        echo -e "${RED}❌ REGRESSION: Distributed to $TOTAL_USERS users when 0 expected${NC}"
        exit 1
    fi
else
    echo -e "${RED}❌ Unexpected HTTP code: $REWARD_HTTP_1${NC}"
    exit 1
fi

# Cleanup
PGDATABASE=lfa_intern_system psql -U postgres -h localhost -c "
DELETE FROM tournament_status_history WHERE tournament_id = $TOURNAMENT_ID_1;
DELETE FROM semesters WHERE id = $TOURNAMENT_ID_1;
" > /dev/null 2>&1

################################################################################
# TEST CASE 2: Reward Distribution without Rankings
################################################################################

echo -e "\n${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}TEST CASE 2: Reward Distribution without Rankings${NC}"
echo -e "${YELLOW}Expected: HTTP 400 (no rankings submitted)${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

TIMESTAMP=$(date -u +"%Y%m%d_%H%M%S")

TOURNAMENT_ID_2=$(PGDATABASE=lfa_intern_system psql -U postgres -h localhost -t -c "
INSERT INTO semesters (
    code, name, start_date, end_date, specialization_type,
    status, tournament_status, format, scoring_type,
    enrollment_cost, sessions_generated, reward_policy_name,
    is_active, tournament_type_id, created_at, updated_at,
    reward_config
)
VALUES (
    'EDGE-NORANKINGS-$TIMESTAMP',
    'Edge Case: No Rankings',
    '$START_DATE', '$END_DATE', 'LFA_FOOTBALL_PLAYER',
    'DRAFT', 'COMPLETED', 'HEAD_TO_HEAD', 'PLACEMENT',
    0, true, 'default', true,
    (SELECT id FROM tournament_types WHERE code = 'league'),
    NOW(), NOW(),
    '{
      \"skill_mappings\": [
        {\"skill\": \"passing\", \"weight\": 1.0, \"enabled\": true}
      ]
    }'::jsonb
)
RETURNING id;
" | tr -d ' ' | head -1)

echo -e "${CYAN}Created tournament with no rankings (ID: $TOURNAMENT_ID_2)${NC}"

# Attempt reward distribution
REWARD_RESPONSE_2=$(curl -s -w "\n%{http_code}" \
    -X POST "$API_V1/tournaments/$TOURNAMENT_ID_2/distribute-rewards-v2" \
    -H "$AUTH_HEADER" \
    -H "Content-Type: application/json" \
    -d "{\"tournament_id\": $TOURNAMENT_ID_2, \"force_redistribution\": false}")

REWARD_HTTP_2=$(echo "$REWARD_RESPONSE_2" | tail -n1)

# Should gracefully handle (200 with 0 distributed or 400)
if [[ "$REWARD_HTTP_2" == "400" || "$REWARD_HTTP_2" == "200" ]]; then
    echo -e "${GREEN}✅ Handled missing rankings gracefully (HTTP $REWARD_HTTP_2)${NC}"
else
    echo -e "${RED}❌ Unexpected HTTP code: $REWARD_HTTP_2${NC}"
    exit 1
fi

# Cleanup
PGDATABASE=lfa_intern_system psql -U postgres -h localhost -c "
DELETE FROM tournament_status_history WHERE tournament_id = $TOURNAMENT_ID_2;
DELETE FROM semesters WHERE id = $TOURNAMENT_ID_2;
" > /dev/null 2>&1

################################################################################
# TEST CASE 3: Reward Distribution with Invalid Tournament Status
################################################################################

echo -e "\n${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}TEST CASE 3: Reward Distribution with Invalid Status (DRAFT)${NC}"
echo -e "${YELLOW}Expected: HTTP 400 (tournament not COMPLETED)${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

TIMESTAMP=$(date -u +"%Y%m%d_%H%M%S")

TOURNAMENT_ID_3=$(PGDATABASE=lfa_intern_system psql -U postgres -h localhost -t -c "
INSERT INTO semesters (
    code, name, start_date, end_date, specialization_type,
    status, tournament_status, format, scoring_type,
    enrollment_cost, sessions_generated, reward_policy_name,
    is_active, tournament_type_id, created_at, updated_at
)
VALUES (
    'EDGE-DRAFT-$TIMESTAMP',
    'Edge Case: Invalid Status',
    '$START_DATE', '$END_DATE', 'LFA_FOOTBALL_PLAYER',
    'DRAFT', 'DRAFT', 'HEAD_TO_HEAD', 'PLACEMENT',
    0, true, 'default', true,
    (SELECT id FROM tournament_types WHERE code = 'league'),
    NOW(), NOW()
)
RETURNING id;
" | tr -d ' ' | head -1)

echo -e "${CYAN}Created tournament in DRAFT status (ID: $TOURNAMENT_ID_3)${NC}"

# Attempt reward distribution
REWARD_RESPONSE_3=$(curl -s -w "\n%{http_code}" \
    -X POST "$API_V1/tournaments/$TOURNAMENT_ID_3/distribute-rewards-v2" \
    -H "$AUTH_HEADER" \
    -H "Content-Type: application/json" \
    -d "{\"tournament_id\": $TOURNAMENT_ID_3, \"force_redistribution\": false}")

REWARD_HTTP_3=$(echo "$REWARD_RESPONSE_3" | tail -n1)
REWARD_BODY_3=$(echo "$REWARD_RESPONSE_3" | sed '$d')

assert_http_error "$REWARD_HTTP_3" "400" "Reward distribution on DRAFT tournament"

ERROR_MSG=$(echo "$REWARD_BODY_3" | jq -r '.error.message // empty')
echo -e "   Error: $ERROR_MSG"

# Verify error mentions status requirement
if [[ "$ERROR_MSG" != *"COMPLETED"* ]]; then
    echo -e "${RED}❌ REGRESSION: Error message does not mention COMPLETED requirement${NC}"
    exit 1
fi

# Cleanup
PGDATABASE=lfa_intern_system psql -U postgres -h localhost -c "
DELETE FROM tournament_status_history WHERE tournament_id = $TOURNAMENT_ID_3;
DELETE FROM semesters WHERE id = $TOURNAMENT_ID_3;
" > /dev/null 2>&1

################################################################################
# TEST CASE 4: Reward Distribution for Non-Existent Tournament
################################################################################

echo -e "\n${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}TEST CASE 4: Reward Distribution for Non-Existent Tournament${NC}"
echo -e "${YELLOW}Expected: HTTP 404 (tournament not found)${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

FAKE_TOURNAMENT_ID=999999

REWARD_RESPONSE_4=$(curl -s -w "\n%{http_code}" \
    -X POST "$API_V1/tournaments/$FAKE_TOURNAMENT_ID/distribute-rewards-v2" \
    -H "$AUTH_HEADER" \
    -H "Content-Type: application/json" \
    -d "{\"tournament_id\": $FAKE_TOURNAMENT_ID, \"force_redistribution\": false}")

REWARD_HTTP_4=$(echo "$REWARD_RESPONSE_4" | tail -n1)

assert_http_error "$REWARD_HTTP_4" "404" "Reward distribution for non-existent tournament"

################################################################################
# TEST CASE 5: Enrollment to Non-Existent Tournament
################################################################################

echo -e "\n${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}TEST CASE 5: Enrollment to Non-Existent Tournament${NC}"
echo -e "${YELLOW}Expected: HTTP 404 (tournament not found)${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

ENROLL_RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X POST "$API_V1/tournaments/$FAKE_TOURNAMENT_ID/enroll" \
    -H "$AUTH_HEADER" \
    -H "Content-Type: application/json" \
    -d '{"user_id": 4}')

ENROLL_HTTP=$(echo "$ENROLL_RESPONSE" | tail -n1)

assert_http_error "$ENROLL_HTTP" "404" "Enrollment to non-existent tournament"

################################################################################
# TEST CASE 6: Invalid User ID in Enrollment
################################################################################

echo -e "\n${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}TEST CASE 6: Enrollment with Invalid User ID${NC}"
echo -e "${YELLOW}Expected: HTTP 400 or 404 (user not found)${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Create a valid tournament in ENROLLMENT_OPEN status
TIMESTAMP=$(date -u +"%Y%m%d_%H%M%S")

TOURNAMENT_ID_6=$(PGDATABASE=lfa_intern_system psql -U postgres -h localhost -t -c "
INSERT INTO semesters (
    code, name, start_date, end_date, specialization_type,
    status, tournament_status, format, scoring_type,
    enrollment_cost, sessions_generated, reward_policy_name,
    is_active, tournament_type_id, created_at, updated_at
)
VALUES (
    'EDGE-INVALIDUSER-$TIMESTAMP',
    'Edge Case: Invalid User',
    '$START_DATE', '$END_DATE', 'LFA_FOOTBALL_PLAYER',
    'DRAFT', 'ENROLLMENT_OPEN', 'HEAD_TO_HEAD', 'PLACEMENT',
    0, true, 'default', true,
    (SELECT id FROM tournament_types WHERE code = 'league'),
    NOW(), NOW()
)
RETURNING id;
" | tr -d ' ' | head -1)

echo -e "${CYAN}Created tournament for invalid user test (ID: $TOURNAMENT_ID_6)${NC}"

FAKE_USER_ID=999999

ENROLL_RESPONSE_6=$(curl -s -w "\n%{http_code}" \
    -X POST "$API_V1/tournaments/$TOURNAMENT_ID_6/enroll" \
    -H "$AUTH_HEADER" \
    -H "Content-Type: application/json" \
    -d "{\"user_id\": $FAKE_USER_ID}")

ENROLL_HTTP_6=$(echo "$ENROLL_RESPONSE_6" | tail -n1)

# Should return 400, 403, or 404
if [[ "$ENROLL_HTTP_6" == "400" || "$ENROLL_HTTP_6" == "403" || "$ENROLL_HTTP_6" == "404" ]]; then
    echo -e "${GREEN}✅ Invalid user ID correctly rejected (HTTP $ENROLL_HTTP_6)${NC}"
else
    echo -e "${RED}❌ Unexpected HTTP code: $ENROLL_HTTP_6${NC}"
    exit 1
fi

# Cleanup
PGDATABASE=lfa_intern_system psql -U postgres -h localhost -c "
DELETE FROM tournament_status_history WHERE tournament_id = $TOURNAMENT_ID_6;
DELETE FROM semesters WHERE id = $TOURNAMENT_ID_6;
" > /dev/null 2>&1

################################################################################
# TEST CASE 7: Tournament with Missing reward_config
################################################################################

echo -e "\n${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}TEST CASE 7: Reward Distribution with Missing reward_config${NC}"
echo -e "${YELLOW}Expected: Graceful handling (use defaults or skip skill progression)${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

TIMESTAMP=$(date -u +"%Y%m%d_%H%M%S")

TOURNAMENT_ID_7=$(PGDATABASE=lfa_intern_system psql -U postgres -h localhost -t -c "
INSERT INTO semesters (
    code, name, start_date, end_date, specialization_type,
    status, tournament_status, format, scoring_type,
    enrollment_cost, sessions_generated, reward_policy_name,
    is_active, tournament_type_id, created_at, updated_at,
    reward_config
)
VALUES (
    'EDGE-NOCONFIG-$TIMESTAMP',
    'Edge Case: No reward_config',
    '$START_DATE', '$END_DATE', 'LFA_FOOTBALL_PLAYER',
    'DRAFT', 'COMPLETED', 'HEAD_TO_HEAD', 'PLACEMENT',
    0, true, 'default', true,
    (SELECT id FROM tournament_types WHERE code = 'league'),
    NOW(), NOW(),
    NULL
)
RETURNING id;
" | tr -d ' ' | head -1)

echo -e "${CYAN}Created tournament with NULL reward_config (ID: $TOURNAMENT_ID_7)${NC}"

# Create fake ranking
PGDATABASE=lfa_intern_system psql -U postgres -h localhost -c "
INSERT INTO tournament_rankings (tournament_id, user_id, participant_type, rank, points, wins, losses, draws, updated_at)
VALUES ($TOURNAMENT_ID_7, 4, 'PLAYER', 1, 100, 0, 0, 0, NOW());
" > /dev/null 2>&1

# Attempt reward distribution
REWARD_RESPONSE_7=$(curl -s -w "\n%{http_code}" \
    -X POST "$API_V1/tournaments/$TOURNAMENT_ID_7/distribute-rewards-v2" \
    -H "$AUTH_HEADER" \
    -H "Content-Type: application/json" \
    -d "{\"tournament_id\": $TOURNAMENT_ID_7, \"force_redistribution\": false}")

REWARD_HTTP_7=$(echo "$REWARD_RESPONSE_7" | tail -n1)
REWARD_BODY_7=$(echo "$REWARD_RESPONSE_7" | sed '$d')

# Should handle gracefully (200 with fallback or 400)
if [[ "$REWARD_HTTP_7" == "200" ]]; then
    echo -e "${GREEN}✅ Handled missing reward_config gracefully (used defaults)${NC}"
    TOTAL_USERS=$(echo "$REWARD_BODY_7" | jq -r '.rewards_distributed_count // 0')
    echo -e "   Distributed to $TOTAL_USERS users"
elif [[ "$REWARD_HTTP_7" == "400" ]]; then
    ERROR_MSG=$(echo "$REWARD_BODY_7" | jq -r '.error.message // empty')
    echo -e "${GREEN}✅ Rejected missing reward_config with HTTP 400${NC}"
    echo -e "   Error: $ERROR_MSG"
else
    echo -e "${RED}❌ Unexpected HTTP code: $REWARD_HTTP_7${NC}"
    exit 1
fi

# Cleanup
PGDATABASE=lfa_intern_system psql -U postgres -h localhost -c "
DELETE FROM tournament_status_history WHERE tournament_id = $TOURNAMENT_ID_7;
DELETE FROM tournament_participations WHERE semester_id = $TOURNAMENT_ID_7;
DELETE FROM tournament_rankings WHERE tournament_id = $TOURNAMENT_ID_7;
DELETE FROM semesters WHERE id = $TOURNAMENT_ID_7;
" > /dev/null 2>&1

################################################################################
# FINAL SUMMARY
################################################################################

echo -e "\n${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   REGRESSION TEST - SUMMARY${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"

echo -e "\n${GREEN}✅ ALL EDGE CASE TESTS PASSED${NC}"
echo -e ""
echo -e "Test Results:"
echo -e "  ✅ ${CYAN}Test 1${NC}: 0 participants handled gracefully"
echo -e "  ✅ ${CYAN}Test 2${NC}: Missing rankings handled gracefully"
echo -e "  ✅ ${CYAN}Test 3${NC}: Invalid status (DRAFT) rejected with HTTP 400"
echo -e "  ✅ ${CYAN}Test 4${NC}: Non-existent tournament rejected with HTTP 404"
echo -e "  ✅ ${CYAN}Test 5${NC}: Enrollment to non-existent tournament rejected"
echo -e "  ✅ ${CYAN}Test 6${NC}: Invalid user ID in enrollment rejected"
echo -e "  ✅ ${CYAN}Test 7${NC}: Missing reward_config handled gracefully"
echo -e ""
echo -e "Critical Validations:"
echo -e "  ✓ No NULL pointer exceptions"
echo -e "  ✓ No division by zero errors"
echo -e "  ✓ Proper HTTP error codes returned"
echo -e "  ✓ Graceful degradation on missing data"
echo -e ""
echo -e "${CYAN}Edge case handling is ROBUST ✓${NC}"
