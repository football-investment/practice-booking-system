#!/bin/bash

# Student Reset Management Script
# This script provides easy access to student reset functionality

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

echo "🎓 STUDENT RESET MANAGEMENT TOOL"
echo "================================"
echo ""

# Function to show help
show_help() {
    echo "Usage: ./scripts/student_reset.sh [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  check      - Check current student state (verification)"
    echo "  preview    - Preview what would be reset (dry-run)"
    echo "  reset      - ACTUALLY reset all students (requires confirmation)"
    echo "  force      - Force reset without confirmation (DANGEROUS!)"
    echo "  help       - Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./scripts/student_reset.sh check      # Check current state"
    echo "  ./scripts/student_reset.sh preview    # See what would be deleted"
    echo "  ./scripts/student_reset.sh reset      # Reset with confirmation"
    echo ""
}

# Check if Python environment is available
check_environment() {
    if ! python -c "import app.database" 2>/dev/null; then
        echo "❌ ERROR: Cannot import app.database"
        echo "💡 Make sure you're in the project root and dependencies are installed"
        exit 1
    fi
}

case "${1:-help}" in
    "check")
        echo "🔍 Checking current student state..."
        echo ""
        check_environment
        python scripts/verify_student_clean_state.py
        ;;
    
    "preview")
        echo "👀 Preview mode - showing what would be reset..."
        echo ""
        check_environment
        python scripts/reset_students_to_newcomer.py --dry-run
        ;;
    
    "reset")
        echo "⚠️  RESET MODE - This will actually delete student data!"
        echo ""
        check_environment
        python scripts/reset_students_to_newcomer.py
        echo ""
        echo "🔍 Verifying reset was successful..."
        python scripts/verify_student_clean_state.py
        ;;
    
    "force")
        echo "💀 FORCE RESET MODE - No confirmation required!"
        echo "⚠️  This is DANGEROUS and will delete all student data!"
        echo ""
        check_environment
        python scripts/reset_students_to_newcomer.py --confirm
        echo ""
        echo "🔍 Verifying reset was successful..."
        python scripts/verify_student_clean_state.py
        ;;
    
    "help"|"--help"|"-h"|"")
        show_help
        ;;
    
    *)
        echo "❌ Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac