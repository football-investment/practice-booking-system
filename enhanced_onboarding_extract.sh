#!/bin/bash

# 🎓 ENHANCED ONBOARDING EXTRACT SCRIPT
# Specialized extract for onboarding infrastructure analysis
# Target: Complete onboarding system documentation

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Configuration
OUTPUT_FILE="ONBOARDING_INFRASTRUCTURE_$(date +%Y%m%d_%H%M%S).txt"
PROJECT_ROOT="$(pwd)"
MAX_FILE_SIZE=75000      # 75KB per file max (larger for onboarding files)
MAX_TOTAL_SIZE=3000000   # 3MB total limit (larger for comprehensive analysis)
CURRENT_SIZE=0
FILES_INCLUDED=0
FILES_EXCLUDED=0

log_info() { echo -e "${BLUE}ℹ️ $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️ $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

# Smart file inclusion with size checks
add_file_smart() {
    local file="$1"
    local priority="$2"
    
    # Skip if file doesn't exist
    [[ ! -f "$file" ]] && return
    
    # Get file size
    local file_size=$(stat -c%s "$file" 2>/dev/null || stat -f%z "$file" 2>/dev/null || echo 0)
    
    # Skip oversized files
    if [[ $file_size -gt $MAX_FILE_SIZE ]]; then
        log_warning "Túl nagy: $file ($(($file_size/1024))KB) - kihagyva"
        FILES_EXCLUDED=$((FILES_EXCLUDED + 1))
        return
    fi
    
    # Check total size limit
    if [[ $((CURRENT_SIZE + file_size)) -gt $MAX_TOTAL_SIZE ]]; then
        log_warning "Méretlimit elérve - további fájlok kihagyása"
        FILES_EXCLUDED=$((FILES_EXCLUDED + 1))
        return
    fi
    
    # Add file content
    echo "" >> "$OUTPUT_FILE"
    echo "================================================================================" >> "$OUTPUT_FILE"
    echo "FILE: $file [$priority]" >> "$OUTPUT_FILE"
    echo "SIZE: $(($file_size/1024))KB | TYPE: $(file -b "$file" | cut -d',' -f1)" >> "$OUTPUT_FILE"
    echo "================================================================================" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
    
    # Add content based on file type
    case "$file" in
        *.py)
            # Keep essential comments for onboarding understanding
            cat "$file" >> "$OUTPUT_FILE"
            ;;
        *.js|*.jsx|*.ts|*.tsx)
            # Keep onboarding-related comments
            cat "$file" >> "$OUTPUT_FILE"
            ;;
        *.json)
            # Pretty print JSON for better readability
            if command -v jq > /dev/null; then
                jq . "$file" >> "$OUTPUT_FILE" 2>/dev/null || cat "$file" >> "$OUTPUT_FILE"
            else
                cat "$file" >> "$OUTPUT_FILE"
            fi
            ;;
        *)
            cat "$file" >> "$OUTPUT_FILE"
            ;;
    esac
    
    CURRENT_SIZE=$((CURRENT_SIZE + file_size))
    FILES_INCLUDED=$((FILES_INCLUDED + 1))
    
    echo -ne "\r${PURPLE}📁 Feldolgozva: $FILES_INCLUDED fájl | Méret: $(($CURRENT_SIZE/1024))KB${NC}"
}

# Print banner
echo -e "${BLUE}🎓 ONBOARDING INFRASTRUCTURE - SPECIALIZED EXTRACT${NC}"
echo -e "${BLUE}=================================================${NC}"
echo ""

# Check project root
if [[ ! -f "app/main.py" ]] && [[ ! -d "app" ]]; then
    log_error "Nem a Practice Booking System projekt gyökérében vagyunk!"
    exit 1
fi

# Create header
cat > "$OUTPUT_FILE" << EOF
# 🎓 ONBOARDING INFRASTRUCTURE - COMPREHENSIVE ANALYSIS
# ====================================================
# Generálva: $(date)
# Projekt: Practice Booking System - Onboarding Specialized Extract
# Célcsoport: Onboarding fejlesztés és architektúra

## 📋 ONBOARDING RENDSZER ÁTTEKINTÉS
Ez a dokumentum a Practice Booking System teljes onboarding infrastruktúráját tartalmazza,
beleértve a backend API-kat, frontend komponenseket, adatbázis modelleket és tesztelési keretrendszert.

## 🎯 SZAKMAI FÓKUSZ TERÜLETEK
- 🔐 Authentication & Authorization
- 👤 User Profile Management  
- 🎓 Specialization System
- 💳 Payment Verification
- 🧪 Testing Infrastructure
- 🎨 UI/UX Components
- 📱 Mobile Compatibility

## 📁 FÁJL KATEGÓRIÁK

EOF

log_info "🔐 AUTHENTICATION & USER MANAGEMENT"

# 1. AUTHENTICATION & USER CORE (Priority 1)
AUTH_FILES=(
    "app/models/user.py"
    "app/api/api_v1/endpoints/auth.py"
    "app/api/api_v1/endpoints/users.py"
    "app/core/security.py"
    "app/core/auth.py"
    "app/dependencies.py"
    "app/schemas/user.py"
    "frontend/src/contexts/AuthContext.js"
    "frontend/src/hooks/useAuth.js"
    "frontend/src/services/authService.js"
)

for file in "${AUTH_FILES[@]}"; do
    add_file_smart "$file" "AUTHENTICATION"
done

log_info "🎓 ONBOARDING WORKFLOW"

# 2. ONBOARDING WORKFLOW (Priority 1)
ONBOARDING_FILES=(
    "frontend/src/pages/student/StudentOnboarding.js"
    "frontend/src/components/student/ProtectedStudentRoute.js"
    "frontend/src/components/student/StudentRouter.js"
    "frontend/src/components/onboarding/ParallelSpecializationSelector.js"
    "frontend/src/components/onboarding/CurrentSpecializationStatus.js"
    "frontend/src/components/onboarding/SpecializationSelector.js"
    "app/api/api_v1/endpoints/specializations.py"
    "app/models/specialization.py"
    "app/services/parallel_specialization_service.py"
)

for file in "${ONBOARDING_FILES[@]}"; do
    add_file_smart "$file" "ONBOARDING-CORE"
done

log_info "💳 PAYMENT VERIFICATION SYSTEM"

# 3. PAYMENT VERIFICATION (Priority 1)
PAYMENT_FILES=(
    "app/api/api_v1/endpoints/payment_verification.py"
    "frontend/src/components/student/PaymentStatusBanner.js"
    "frontend/src/components/student/PaymentVerificationModal.js"
)

for file in "${PAYMENT_FILES[@]}"; do
    add_file_smart "$file" "PAYMENT-VERIFICATION"
done

log_info "🧪 TESTING INFRASTRUCTURE"

# 4. TESTING INFRASTRUCTURE (Priority 2)
TESTING_FILES=(
    "app/tests/test_onboarding_api.py"
    "e2e-tests/tests/student-onboarding.spec.js"
    "e2e-tests/cross-platform-stability-validation.js"
)

for file in "${TESTING_FILES[@]}"; do
    add_file_smart "$file" "TESTING"
done

log_info "🗄️ DATABASE & MIGRATIONS"

# 5. DATABASE SCHEMA (Priority 2)
DATABASE_FILES=(
    "app/database.py"
    "alembic/env.py"
    "alembic.ini"
)

# Find onboarding-related migration files
find alembic/versions -name "*onboarding*" -type f | head -3 | while read -r file; do
    add_file_smart "$file" "MIGRATION"
done

find alembic/versions -name "*profile*" -type f | head -2 | while read -r file; do
    add_file_smart "$file" "MIGRATION"
done

for file in "${DATABASE_FILES[@]}"; do
    add_file_smart "$file" "DATABASE"
done

log_info "🎨 UI/UX STYLING"

# 6. STYLING & UI COMPONENTS (Priority 2)
STYLING_FILES=(
    "frontend/src/pages/student/StudentOnboarding.css"
    "frontend/src/components/onboarding/CurrentSpecializationStatus.css"
    "frontend/src/components/onboarding/ParallelSpecializationSelector.css"
    "frontend/src/components/student/PaymentStatusBanner.css"
    "frontend/src/index.css"
    "frontend/src/App.css"
)

for file in "${STYLING_FILES[@]}"; do
    add_file_smart "$file" "STYLING"
done

log_info "📱 MOBILE & COMPATIBILITY"

# 7. MOBILE COMPATIBILITY (Priority 2)
MOBILE_FILES=(
    "frontend/src/utils/iosOptimizations.js"
    "frontend/src/styles/ios-responsive.css"
    "frontend/src/styles/chrome-ios-optimizations.css"
    "frontend/src/components/common/BrowserWarning.js"
)

for file in "${MOBILE_FILES[@]}"; do
    add_file_smart "$file" "MOBILE-COMPAT"
done

log_info "⚙️ CONFIGURATION & SERVICES"

# 8. CONFIGURATION & API SERVICES (Priority 3)
CONFIG_FILES=(
    "app/main.py"
    "app/core/config.py"
    "frontend/src/services/apiService.js"
    "requirements.txt"
    "frontend/package.json"
    ".env.example"
)

for file in "${CONFIG_FILES[@]}"; do
    add_file_smart "$file" "CONFIG"
done

log_info "📚 DOCUMENTATION & SCRIPTS"

# 9. DOCUMENTATION & UTILITY SCRIPTS (Priority 3)
DOC_FILES=(
    "README.md"
    "start_backend.sh"
    "start_frontend.sh"
)

for file in "${DOC_FILES[@]}"; do
    add_file_smart "$file" "DOCS"
done

echo -e "\n"

# Add comprehensive analysis
cat >> "$OUTPUT_FILE" << EOF

================================================================================
🎓 ONBOARDING INFRASTRUCTURE ANALYSIS
================================================================================

## 📊 ARCHITECTURE OVERVIEW

### 🔐 AUTHENTICATION FLOW
- JWT-based authentication with refresh tokens
- Automatic onboarding completion detection
- Protected route guards for incomplete profiles

### 👤 USER PROFILE SYSTEM
- Comprehensive user model with onboarding fields
- Nickname, phone, emergency contact validation
- Specialization tracking (Player/Coach/Internship)
- Payment verification workflow

### 🎯 SPECIALIZATION SYSTEM  
- Multi-track education platform
- Parallel specialization support (semester-based)
- Age requirement validation
- Payment verification integration

### 💳 PAYMENT VERIFICATION
- Admin-controlled payment approval
- Semester-specific payment logic
- Integration with specialization selection

### 🎨 USER EXPERIENCE
- 6-step guided onboarding process
- Mobile-first responsive design
- iOS/Safari optimizations
- Real-time form validation

### 🧪 TESTING COVERAGE
- Comprehensive backend API tests
- E2E frontend testing with Playwright
- Cross-platform compatibility validation

================================================================================
📊 EXTRACTION STATISTICS  
================================================================================

📁 Befoglalt fájlok: $FILES_INCLUDED
🗑️ Kihagyott fájlok: $FILES_EXCLUDED  
📦 Végső méret: $(du -h "$OUTPUT_FILE" | cut -f1)
🎯 Fókusz: Onboarding infrastruktúra
💾 Speciális extract: Teljes onboarding rendszer dokumentáció

⚡ EXTRACT SPECIALITÁSOK:
- 🎓 Onboarding-specifikus fájlok prioritizálva
- 📱 Mobile compatibility komponensek befoglalva
- 🧪 Teljes tesztelési infrastruktúra dokumentálva
- 💳 Payment verification rendszer feltárva
- 🎨 UI/UX komponensek részletesen

🎯 Ez a specialized extract a teljes onboarding infrastruktúrát tartalmazza
   a fejlesztési és karbantartási munkálatokhoz.

EOF

# Final report
FINAL_SIZE=$(du -h "$OUTPUT_FILE" | cut -f1)
echo ""
log_success "ONBOARDING INFRASTRUCTURE EXTRACT KÉSZ!"
echo -e "${GREEN}📊 EREDMÉNY:${NC}"
echo -e "   📁 Befoglalt fájlok: $FILES_INCLUDED"
echo -e "   🗑️ Kihagyott fájlok: $FILES_EXCLUDED"
echo -e "   📦 Végső méret: $FINAL_SIZE"
echo -e "   🎓 Specializáció: Onboarding infrastruktúra"
echo ""
echo -e "${BLUE}📤 Onboarding analysis ready: $OUTPUT_FILE${NC}"
echo -e "${YELLOW}💡 Ez a fájl a teljes onboarding rendszer architektúráját tartalmazza${NC}"