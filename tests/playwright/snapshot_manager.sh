#!/bin/bash

# =============================================================================
# Database Snapshot Manager for E2E Tests
# =============================================================================
# Allows saving and restoring database state at different test stages
# This enables running individual tests without rerunning entire suite
#
# Usage:
#   ./snapshot_manager.sh save <snapshot_name>     # Save current DB state
#   ./snapshot_manager.sh restore <snapshot_name>  # Restore DB state
#   ./snapshot_manager.sh list                     # List all snapshots
#   ./snapshot_manager.sh delete <snapshot_name>   # Delete a snapshot
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SNAPSHOT_DIR="tests/playwright/snapshots"
DB_NAME="lfa_intern_system"
DB_USER="postgres"
DB_HOST="localhost"
DB_PORT="5432"

# Create snapshot directory if it doesn't exist
mkdir -p "$SNAPSHOT_DIR"

# Function to save database snapshot
save_snapshot() {
    local snapshot_name=$1
    local snapshot_file="$SNAPSHOT_DIR/${snapshot_name}.sql"

    echo -e "${BLUE}📸 Saving database snapshot: ${snapshot_name}${NC}"

    # Export database to SQL file
    pg_dump -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" "$DB_NAME" > "$snapshot_file"

    if [ $? -eq 0 ]; then
        # Get file size
        local size=$(du -h "$snapshot_file" | cut -f1)
        echo -e "${GREEN}✅ Snapshot saved: ${snapshot_file} (${size})${NC}"

        # Save metadata
        local metadata_file="$SNAPSHOT_DIR/${snapshot_name}.meta"
        echo "snapshot_name: $snapshot_name" > "$metadata_file"
        echo "created_at: $(date '+%Y-%m-%d %H:%M:%S')" >> "$metadata_file"
        echo "db_name: $DB_NAME" >> "$metadata_file"
        echo "file_size: $size" >> "$metadata_file"

        # Count records in key tables
        local user_count=$(psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM users;" | xargs)
        local tournament_count=$(psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM semesters WHERE tournament_status IS NOT NULL;" | xargs)
        local enrollment_count=$(psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM semester_enrollments;" | xargs)

        echo "users: $user_count" >> "$metadata_file"
        echo "tournaments: $tournament_count" >> "$metadata_file"
        echo "enrollments: $enrollment_count" >> "$metadata_file"

        echo -e "${GREEN}   Users: $user_count | Tournaments: $tournament_count | Enrollments: $enrollment_count${NC}"
    else
        echo -e "${RED}❌ Failed to save snapshot${NC}"
        exit 1
    fi
}

# Function to restore database snapshot
restore_snapshot() {
    local snapshot_name=$1
    local snapshot_file="$SNAPSHOT_DIR/${snapshot_name}.sql"

    if [ ! -f "$snapshot_file" ]; then
        echo -e "${RED}❌ Snapshot not found: ${snapshot_name}${NC}"
        echo -e "${YELLOW}Available snapshots:${NC}"
        list_snapshots
        exit 1
    fi

    echo -e "${BLUE}🔄 Restoring database snapshot: ${snapshot_name}${NC}"

    # Drop and recreate database
    echo -e "${YELLOW}   Dropping existing database...${NC}"
    psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -d postgres -c "DROP DATABASE IF EXISTS $DB_NAME;" 2>/dev/null

    echo -e "${YELLOW}   Creating fresh database...${NC}"
    psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -d postgres -c "CREATE DATABASE $DB_NAME;" 2>/dev/null

    echo -e "${YELLOW}   Restoring data from snapshot...${NC}"
    psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -d "$DB_NAME" < "$snapshot_file" > /dev/null 2>&1

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Snapshot restored successfully${NC}"

        # Show metadata if exists
        local metadata_file="$SNAPSHOT_DIR/${snapshot_name}.meta"
        if [ -f "$metadata_file" ]; then
            echo -e "${BLUE}📋 Snapshot metadata:${NC}"
            cat "$metadata_file" | while read line; do
                echo -e "   ${line}"
            done
        fi

        # Restart Streamlit to clear Python module cache
        echo -e "${YELLOW}   Restarting Streamlit to clear module cache...${NC}"
        pkill -f "streamlit run" 2>/dev/null
        sleep 2

        cd "$(dirname "$SNAPSHOT_DIR")/../.." 2>/dev/null || cd .
        if [ -f "venv/bin/activate" ]; then
            source venv/bin/activate
            DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" \
            streamlit run streamlit_app/🏠_Home.py --server.port 8501 > /dev/null 2>&1 &
            sleep 3
            echo -e "${GREEN}   ✅ Streamlit restarted with fresh code${NC}"
        else
            echo -e "${YELLOW}   ⚠️  Streamlit not restarted (venv not found)${NC}"
        fi
    else
        echo -e "${RED}❌ Failed to restore snapshot${NC}"
        exit 1
    fi
}

# Function to list all snapshots
list_snapshots() {
    echo -e "${BLUE}📋 Available snapshots:${NC}"
    echo ""

    if [ ! -d "$SNAPSHOT_DIR" ] || [ -z "$(ls -A $SNAPSHOT_DIR/*.sql 2>/dev/null)" ]; then
        echo -e "${YELLOW}   No snapshots found${NC}"
        return
    fi

    for snapshot_file in "$SNAPSHOT_DIR"/*.sql; do
        local snapshot_name=$(basename "$snapshot_file" .sql)
        local metadata_file="$SNAPSHOT_DIR/${snapshot_name}.meta"

        echo -e "${GREEN}• ${snapshot_name}${NC}"

        if [ -f "$metadata_file" ]; then
            cat "$metadata_file" | while read line; do
                echo -e "    ${line}"
            done
        fi
        echo ""
    done
}

# Function to delete a snapshot
delete_snapshot() {
    local snapshot_name=$1
    local snapshot_file="$SNAPSHOT_DIR/${snapshot_name}.sql"
    local metadata_file="$SNAPSHOT_DIR/${snapshot_name}.meta"

    if [ ! -f "$snapshot_file" ]; then
        echo -e "${RED}❌ Snapshot not found: ${snapshot_name}${NC}"
        exit 1
    fi

    echo -e "${YELLOW}⚠️  Deleting snapshot: ${snapshot_name}${NC}"
    rm -f "$snapshot_file"
    rm -f "$metadata_file"

    echo -e "${GREEN}✅ Snapshot deleted${NC}"
}

# Main command handler
case "$1" in
    save)
        if [ -z "$2" ]; then
            echo -e "${RED}❌ Error: snapshot name required${NC}"
            echo "Usage: $0 save <snapshot_name>"
            exit 1
        fi
        save_snapshot "$2"
        ;;

    restore)
        if [ -z "$2" ]; then
            echo -e "${RED}❌ Error: snapshot name required${NC}"
            echo "Usage: $0 restore <snapshot_name>"
            exit 1
        fi
        restore_snapshot "$2"
        ;;

    list)
        list_snapshots
        ;;

    delete)
        if [ -z "$2" ]; then
            echo -e "${RED}❌ Error: snapshot name required${NC}"
            echo "Usage: $0 delete <snapshot_name>"
            exit 1
        fi
        delete_snapshot "$2"
        ;;

    *)
        echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${BLUE}║           Database Snapshot Manager for E2E Tests                 ║${NC}"
        echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════╝${NC}"
        echo ""
        echo "Usage:"
        echo -e "  ${GREEN}$0 save <name>${NC}      Save current database state"
        echo -e "  ${GREEN}$0 restore <name>${NC}   Restore database to saved state"
        echo -e "  ${GREEN}$0 list${NC}             List all saved snapshots"
        echo -e "  ${GREEN}$0 delete <name>${NC}    Delete a snapshot"
        echo ""
        echo "Examples:"
        echo -e "  ${BLUE}$0 save after_registration${NC}"
        echo -e "  ${BLUE}$0 save after_onboarding${NC}"
        echo -e "  ${BLUE}$0 save after_instructor_workflow${NC}"
        echo -e "  ${BLUE}$0 restore after_onboarding${NC}"
        echo ""
        exit 1
        ;;
esac
