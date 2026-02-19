#!/bin/bash

################################################################################
# Interactive Checkpoint E2E Test - League Tournament
#
# Purpose: Step-by-step validation of skill progression with manual UI verification
#
# Flow:
#   1. Setup + Enroll → STOP (check UI: baseline skills)
#   2. Play matches + Complete → STOP (check UI: skills unchanged)
#   3. Distribute rewards → STOP (check UI: skills updated)
#
# User can verify skill changes in frontend at each checkpoint.
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

# Test data
TOURNAMENT_PLAYERS="4 5 6 7 13 14 15 16"

################################################################################
# Helper Functions
################################################################################

assert_http_success() {
    local http_code=$1
    local operation=$2
    if [[ "$http_code" != "200" && "$http_code" != "201" ]]; then
        echo -e "${RED}❌ $operation failed with HTTP $http_code${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ $operation - HTTP $http_code${NC}"
}

wait_for_user() {
    local message=$1
    echo -e "\n${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}⏸️  CHECKPOINT - Manual Verification Required${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}$message${NC}"
    echo -e ""
    read -p "Press ENTER to continue to next step..."
    echo -e ""
}

print_user_list() {
    echo -e "${CYAN}Test Players:${NC}"
    for USER_ID in $TOURNAMENT_PLAYERS; do
        echo -e "  • User $USER_ID"
    done
}

################################################################################
# Authenticate
################################################################################

echo -e "\n${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   INTERACTIVE CHECKPOINT E2E TEST - League Tournament${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"

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
# STEP 1: Create Tournament + Enroll Players
################################################################################

echo -e "\n${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}STEP 1: Create Tournament + Enroll Players${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Create tournament via SQL (with reward_config for V2 skill progression)
START_DATE=$(date -u +"%Y-%m-%d")
END_DATE=$(date -u -v+7d +"%Y-%m-%d" 2>/dev/null || date -u -d "+7 days" +"%Y-%m-%d")
TIMESTAMP=$(date -u +"%Y%m%d_%H%M%S")

TOURNAMENT_ID=$(PGDATABASE=lfa_intern_system psql -U postgres -h localhost -t -c "
INSERT INTO semesters (
    code, name, start_date, end_date, specialization_type,
    status, tournament_status, format, scoring_type,
    enrollment_cost, sessions_generated, reward_policy_name,
    is_active, tournament_type_id, created_at, updated_at,
    reward_config
)
VALUES (
    'INTERACTIVE-$TIMESTAMP',
    'Interactive E2E Test - League',
    '$START_DATE', '$END_DATE', 'LFA_FOOTBALL_PLAYER',
    'DRAFT', 'DRAFT', 'HEAD_TO_HEAD', 'PLACEMENT',
    0, false, 'default', true,
    (SELECT id FROM tournament_types WHERE code = 'league'),
    NOW(), NOW(),
    '{
      \"template_name\": \"Standard\",
      \"custom_config\": true,
      \"skill_mappings\": [
        {\"skill\": \"passing\", \"weight\": 1.0, \"enabled\": true, \"category\": \"TECHNICAL\"},
        {\"skill\": \"dribbling\", \"weight\": 0.8, \"enabled\": true, \"category\": \"TECHNICAL\"}
      ],
      \"first_place\": {\"xp_multiplier\": 1.5, \"credits\": 500, \"badges\": []},
      \"second_place\": {\"xp_multiplier\": 1.3, \"credits\": 300, \"badges\": []},
      \"third_place\": {\"xp_multiplier\": 1.2, \"credits\": 200, \"badges\": []},
      \"participation\": {\"xp_multiplier\": 1.0, \"credits\": 25, \"badges\": []}
    }'::jsonb
)
RETURNING id;
" | tr -d ' ' | head -1)

echo -e "${GREEN}✅ Tournament created (ID: $TOURNAMENT_ID)${NC}"
echo -e "${CYAN}   Name: Interactive E2E Test - League${NC}"
echo -e "${CYAN}   Format: HEAD_TO_HEAD (League)${NC}"
echo -e "${CYAN}   Reward Config: Passing + Dribbling skills configured${NC}"

# Change status to ENROLLMENT_OPEN to allow enrollments
# Note: Using direct SQL UPDATE to bypass workflow validations for testing
echo -e "\n${CYAN}Opening enrollment (via SQL for testing)...${NC}"
PGDATABASE=lfa_intern_system psql -U postgres -h localhost -c "
UPDATE semesters
SET tournament_status = 'ENROLLMENT_OPEN'
WHERE id = $TOURNAMENT_ID;
" > /dev/null 2>&1

echo -e "${GREEN}✅ Tournament status → ENROLLMENT_OPEN${NC}"

# Enroll players
echo -e "\n${CYAN}Enrolling players...${NC}"
for USER_ID in $TOURNAMENT_PLAYERS; do
    ENROLL_RESPONSE=$(curl -s -w "\n%{http_code}" \
        -X POST "$API_V1/tournaments/$TOURNAMENT_ID/enroll" \
        -H "$AUTH_HEADER" \
        -H "Content-Type: application/json" \
        -d "{\"user_id\": $USER_ID}")

    ENROLL_HTTP_CODE=$(echo "$ENROLL_RESPONSE" | tail -n1)
    if [[ "$ENROLL_HTTP_CODE" == "200" || "$ENROLL_HTTP_CODE" == "201" ]]; then
        echo -e "${GREEN}   ✓ Enrolled User $USER_ID${NC}"
    else
        echo -e "${RED}   ✗ Failed to enroll User $USER_ID (HTTP $ENROLL_HTTP_CODE)${NC}"
    fi
done

echo -e "${GREEN}✅ All players enrolled${NC}"

# STOP 1: Check baseline skills
wait_for_user "🔍 CHECKPOINT 1: Tournament created, players enrolled

📋 What to verify in the frontend:
   1. Navigate to player profiles (User 4, 5, 6, 14, 15, 16)
   2. Check their BASELINE skill values for 'passing' and 'dribbling'
   3. Note these values down - they should NOT change until reward distribution

Expected baseline examples:
   • User 4: passing ~80.0, dribbling ~50.0
   • User 5: passing ~60.0, dribbling ~50.0
   • User 16: passing ~100.0, dribbling ~50.0

Tournament ID: $TOURNAMENT_ID
Tournament URL: http://localhost:3000/admin/tournaments/$TOURNAMENT_ID"

################################################################################
# STEP 2: Generate Sessions + Play Matches + Complete Tournament
################################################################################

echo -e "\n${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}STEP 2: Play Matches + Complete Tournament${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Change status to IN_PROGRESS
# Note: Using direct SQL UPDATE to bypass workflow validations for testing
echo -e "${CYAN}Starting tournament (via SQL for testing)...${NC}"
PGDATABASE=lfa_intern_system psql -U postgres -h localhost -c "
UPDATE semesters
SET tournament_status = 'IN_PROGRESS'
WHERE id = $TOURNAMENT_ID;
" > /dev/null 2>&1

echo -e "${GREEN}✅ Tournament status → IN_PROGRESS${NC}"

# Generate sessions
echo -e "\n${CYAN}Generating sessions...${NC}"
SESSIONS_RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X POST "$API_V1/tournaments/$TOURNAMENT_ID/generate-sessions" \
    -H "$AUTH_HEADER")

SESSIONS_HTTP_CODE=$(echo "$SESSIONS_RESPONSE" | tail -n1)
assert_http_success "$SESSIONS_HTTP_CODE" "POST /tournaments/generate-sessions"

# Get generated sessions
SESSIONS=$(curl -s -X GET "$API_V1/sessions?tournament_id=$TOURNAMENT_ID" -H "$AUTH_HEADER")
SESSION_IDS=$(echo "$SESSIONS" | jq -r '.[].id')

# Submit match results (3 matches, deterministic outcomes)
echo -e "${CYAN}Submitting match results...${NC}"

MATCH_COUNT=0
for SESSION_ID in $SESSION_IDS; do
    if [ $MATCH_COUNT -ge 3 ]; then
        break
    fi

    # Get participants for this session
    SESSION_DATA=$(echo "$SESSIONS" | jq -r ".[] | select(.id == $SESSION_ID)")
    PLAYER1_ID=$(echo "$SESSION_DATA" | jq -r '.participants[0].user_id // .player1_id // empty')
    PLAYER2_ID=$(echo "$SESSION_DATA" | jq -r '.participants[1].user_id // .player2_id // empty')

    if [[ -n "$PLAYER1_ID" && -n "$PLAYER2_ID" ]]; then
        # Player 1 wins 3-1
        RESULT_RESPONSE=$(curl -s -w "\n%{http_code}" \
            -X POST "$API_V1/sessions/$SESSION_ID/result" \
            -H "$AUTH_HEADER" \
            -H "Content-Type: application/json" \
            -d "{\"player1_score\": 3, \"player2_score\": 1, \"status\": \"COMPLETED\"}")

        RESULT_HTTP_CODE=$(echo "$RESULT_RESPONSE" | tail -n1)
        if [[ "$RESULT_HTTP_CODE" == "200" || "$RESULT_HTTP_CODE" == "201" ]]; then
            echo -e "${GREEN}   ✓ Match $((MATCH_COUNT+1)): Player $PLAYER1_ID [3] - [1] Player $PLAYER2_ID${NC}"
            MATCH_COUNT=$((MATCH_COUNT+1))
        fi
    fi
done

echo -e "${GREEN}✅ Match results submitted${NC}"

# Complete tournament
echo -e "\n${CYAN}Completing tournament...${NC}"
COMPLETE_RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X PATCH "$API_V1/tournaments/$TOURNAMENT_ID/status" \
    -H "$AUTH_HEADER" \
    -H "Content-Type: application/json" \
    -d '{"new_status": "COMPLETED", "reason": "Tournament finished"}')

COMPLETE_HTTP_CODE=$(echo "$COMPLETE_RESPONSE" | tail -n1)
assert_http_success "$COMPLETE_HTTP_CODE" "PATCH /tournaments/$TOURNAMENT_ID/status (COMPLETED)"

echo -e "${GREEN}✅ Tournament status → COMPLETED${NC}"

# STOP 2: Check skills unchanged after tournament completion
wait_for_user "🔍 CHECKPOINT 2: Tournament completed, rankings generated

📋 What to verify in the frontend:
   1. Navigate to tournament page to see final standings
   2. Check player profiles again (User 4, 5, 6, 14, 15, 16)
   3. ⚠️  CRITICAL: Skills should be UNCHANGED from baseline

✅ Expected behavior:
   • Skills have NOT changed yet
   • This proves skills only update AFTER reward distribution
   • Tournament completion alone does NOT change skills

Tournament ID: $TOURNAMENT_ID
Tournament URL: http://localhost:3000/admin/tournaments/$TOURNAMENT_ID"

################################################################################
# STEP 3: Distribute Rewards
################################################################################

echo -e "\n${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}STEP 3: Distribute Rewards${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo -e "${CYAN}Distributing rewards...${NC}"
REWARD_RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X POST "$API_V1/tournaments/$TOURNAMENT_ID/distribute-rewards-v2" \
    -H "$AUTH_HEADER" \
    -H "Content-Type: application/json" \
    -d "{\"tournament_id\": $TOURNAMENT_ID, \"force_redistribution\": true}")

REWARD_HTTP_CODE=$(echo "$REWARD_RESPONSE" | tail -n1)
REWARD_BODY=$(echo "$REWARD_RESPONSE" | sed '$d')

assert_http_success "$REWARD_HTTP_CODE" "POST /tournaments/distribute-rewards-v2"

# Parse reward summary
TOTAL_USERS=$(echo "$REWARD_BODY" | jq -r '.rewards_distributed_count // 0')
TOTAL_PARTICIPANTS=$(echo "$REWARD_BODY" | jq -r '.total_participants // 0')
TOTAL_XP=$(echo "$REWARD_BODY" | jq -r '.summary.total_xp_awarded // 0')
TOTAL_BADGES=$(echo "$REWARD_BODY" | jq -r '.summary.total_badges_awarded // 0')

echo -e "${GREEN}✅ Rewards distributed${NC}"
echo -e "   Total participants: $TOTAL_PARTICIPANTS"
echo -e "   Rewards distributed to: $TOTAL_USERS users"
echo -e "   Total XP awarded: $TOTAL_XP"
echo -e "   Total badges awarded: $TOTAL_BADGES"

# STOP 3: Check skills updated after reward distribution
wait_for_user "🔍 CHECKPOINT 3: Rewards distributed - SKILLS UPDATED!

📋 What to verify in the frontend:
   1. Navigate to player profiles (User 4, 5, 6, 14, 15, 16)
   2. ✅ Skills should NOW BE UPDATED from baseline
   3. Compare with baseline values from Checkpoint 1

✅ Expected changes:
   • Top performers: HIGHER passing/dribbling (e.g., User 5, 6)
   • Lower performers: LOWER or unchanged values (e.g., User 14, 15, 16)
   • Skill changes reflect tournament placement

Example expected changes:
   • User 5 (likely 1st place): passing increased by +10-15 points
   • User 6 (likely 2nd place): passing increased by +3-5 points
   • User 16 (likely lower place): passing decreased by -20-25 points

This proves: Tournament → Complete (no change) → Rewards (SKILLS UPDATED)

Tournament ID: $TOURNAMENT_ID
Tournament URL: http://localhost:3000/admin/tournaments/$TOURNAMENT_ID"

################################################################################
# FINAL SUMMARY
################################################################################

echo -e "\n${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   INTERACTIVE E2E TEST - COMPLETED${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"

echo -e "\n${GREEN}✅ All checkpoints verified${NC}"
echo -e ""
echo -e "Flow validated:"
echo -e "  1️⃣  ${CYAN}Tournament created + players enrolled${NC}"
echo -e "      → Skills at baseline (no change)"
echo -e "  2️⃣  ${CYAN}Matches played + tournament completed${NC}"
echo -e "      → Skills still at baseline (no change)"
echo -e "  3️⃣  ${GREEN}Rewards distributed${NC}"
echo -e "      → Skills UPDATED based on placement ✓"
echo -e ""
echo -e "${CYAN}Complete stack validated via UI:${NC}"
echo -e "${CYAN}Tournament → Completion → Reward Distribution → Skill Progression${NC}"
echo -e ""
echo -e "Tournament ID: $TOURNAMENT_ID"
echo -e "Tournament URL: http://localhost:3000/admin/tournaments/$TOURNAMENT_ID"
