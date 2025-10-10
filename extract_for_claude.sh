#!/bin/bash

# ================================================================
# LFA EDUCATION CENTER - CLAUDE AI OPTIMALIZÁLT EXTRACT SCRIPT
# ================================================================
# Projekt: Practice Booking System (LFA Education Center)
# Cél: Max 2-3 MB méretű fájl létrehozása Claude AI számára
# Minden kritikus forráskód tartalom optimalizált formátumban

set -e

# Színes output konfigurálás
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Konfigurációs változók
OUTPUT_FILE="CLAUDE_AINAK.txt"
PROJECT_ROOT="$(pwd)"
MAX_SIZE_MB=3
MAX_SIZE_BYTES=$((MAX_SIZE_MB * 1024 * 1024))

# Banner megjelenítés
echo -e "${BLUE}🎓 LFA EDUCATION CENTER - CLAUDE AI EXTRACT${NC}"
echo -e "${BLUE}=============================================${NC}"
echo -e "${CYAN}🎯 Target: Max ${MAX_SIZE_MB}MB → CLAUDE_AINAK.txt${NC}"
echo -e "${CYAN}📚 Projekt: Practice Booking System${NC}"
echo ""

# Projekt gyökér ellenőrzés
if [[ ! -f "app/main.py" ]] && [[ ! -d "frontend" ]] && [[ ! -f "requirements.txt" ]]; then
    echo -e "${RED}❌ HIBA: Nem a Practice Booking System projekt gyökerében vagy!${NC}"
    echo -e "${RED}   Navigálj a project root-ba és futtasd újra.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Projekt gyökér OK: $(basename "$PROJECT_ROOT")${NC}"

# Korábbi fájl törlése
[[ -f "${OUTPUT_FILE}" ]] && rm "${OUTPUT_FILE}"

# Fájlméret ellenőrző függvény (macOS + Linux kompatibilis)
get_file_size() {
    if [[ -f "$1" ]]; then
        if command -v stat >/dev/null 2>&1; then
            # macOS és Linux kompatibilitás
            stat -f%z "$1" 2>/dev/null || stat -c%s "$1" 2>/dev/null || echo 0
        else
            wc -c < "$1" 2>/dev/null || echo 0
        fi
    else
        echo 0
    fi
}

# Intelligens fájl hozzáadás méretkorláttal
add_file_smart() {
    local file_path="$1"
    local category="$2"
    local relative_path="${file_path#./}"
    
    # Fájl létezés ellenőrzés
    if [[ ! -f "$file_path" ]]; then
        return
    fi
    
    # Méret ellenőrzés
    local current_size=$(get_file_size "${OUTPUT_FILE}")
    local file_size=$(get_file_size "$file_path")
    
    # Skip ha túllépné a limitet
    if (( current_size + file_size > MAX_SIZE_BYTES )); then
        echo -e "${YELLOW}⏭️  Méretkorlát: ${relative_path} (${category})${NC}"
        return
    fi
    
    # Nagy fájlok kiszűrése (>200KB)
    if (( file_size > 204800 )); then
        echo -e "${YELLOW}📦 Nagy fájl skip: ${relative_path} ($(( file_size / 1024 ))KB)${NC}"
        return
    fi
    
    echo -e "${GREEN}📄 Hozzáadás: ${relative_path} [${category}]${NC}"
    
    # Fájl header és tartalom hozzáadása
    cat >> "${OUTPUT_FILE}" << EOF

================================================================================
FILE: ${relative_path} [${category}]
================================================================================

EOF
    
    cat "$file_path" >> "${OUTPUT_FILE}"
    echo "" >> "${OUTPUT_FILE}"
}

# Projekt header létrehozás
cat > "${OUTPUT_FILE}" << EOF
# ========================================================================
# CLAUDE AI KNOWLEDGE BASE - LFA EDUCATION CENTER (OPTIMIZED)
# ========================================================================
# Generated: $(date)
# Project: Practice Booking System (LFA Education Center)
# Output: CLAUDE_AINAK.txt (Max ${MAX_SIZE_MB}MB for optimal Claude AI processing)
# Root: $(basename "$PROJECT_ROOT")

## 🎓 PROJECT OVERVIEW - LFA EDUCATION CENTER

**Full-Stack Educational Platform:**
- **Backend**: FastAPI + PostgreSQL + Alembic migrations
- **Frontend**: React + TypeScript + Material-UI
- **Features**: User management, booking system, onboarding, specializations
- **Architecture**: RESTful API + JWT authentication + Role-based access

**Development URLs:**
- Backend API: http://localhost:8000
- Frontend App: http://localhost:3000
- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

**Key Features:**
- 🔐 JWT Authentication & Role Management
- 👤 Advanced User Onboarding System
- 🎯 Specialization Tracks (Player/Coach/Internship)
- 📚 Session Booking & Attendance Tracking
- 💳 Payment Verification System
- 🎨 Mobile-Responsive UI (iOS Safari optimized)
- 🧪 Comprehensive Testing Suite

**Test Accounts:**
- Admin: admin@company.com / admin123
- Instructor: sarah.johnson@instructor.com / instructor123
- Student: alex.newcomer@student.com / student123

## 🗂️ CRITICAL FILES BY PRIORITY

EOF

echo -e "${YELLOW}📋 PHASE 1: Core Configuration Files${NC}"

# PRIORITY 1: Core configuration
add_file_smart "requirements.txt" "CONFIG"
add_file_smart "alembic.ini" "CONFIG"
add_file_smart "app/config.py" "CONFIG"
add_file_smart ".env.example" "CONFIG"
add_file_smart "README.md" "DOCS"

echo -e "${YELLOW}📋 PHASE 2: Critical Backend Core${NC}"

# PRIORITY 2: Backend alapok
add_file_smart "app/main.py" "CRITICAL-BACKEND"
add_file_smart "app/database.py" "CRITICAL-BACKEND"
add_file_smart "app/dependencies.py" "CRITICAL-BACKEND"

echo -e "${YELLOW}📋 PHASE 3: Authentication & User Models${NC}"

# PRIORITY 3: Authentication rendszer
add_file_smart "app/models/user.py" "AUTHENTICATION"
add_file_smart "app/schemas/user.py" "AUTHENTICATION"
add_file_smart "app/api/auth.py" "AUTHENTICATION"
add_file_smart "app/api/users.py" "AUTHENTICATION"
add_file_smart "app/core/auth.py" "AUTHENTICATION"
add_file_smart "app/core/security.py" "AUTHENTICATION"

echo -e "${YELLOW}📋 PHASE 4: Business Logic Models & Schemas${NC}"

# PRIORITY 4: Core business models
for model in "session" "booking" "attendance" "feedback" "group" "semester"; do
    add_file_smart "app/models/${model}.py" "MODEL"
    add_file_smart "app/schemas/${model}.py" "SCHEMA"
done

# Specialization rendszer
add_file_smart "app/models/specialization.py" "MODEL"
add_file_smart "app/schemas/specialization.py" "SCHEMA"

echo -e "${YELLOW}📋 PHASE 5: API Routes${NC}"

# PRIORITY 5: API endpoints
for route in "sessions" "bookings" "groups" "admin" "students" "analytics"; do
    add_file_smart "app/api/${route}.py" "API"
done

echo -e "${YELLOW}📋 PHASE 6: Services & Business Logic${NC}"

# PRIORITY 6: Services
find app/services -name "*.py" -type f | head -8 | while read service_file; do
    add_file_smart "$service_file" "SERVICE"
done

echo -e "${YELLOW}📋 PHASE 7: Database Migrations${NC}"

# PRIORITY 7: Legfrissebb migrációk
find alembic/versions -name "*.py" -type f | sort -r | head -5 | while read migration; do
    add_file_smart "$migration" "MIGRATION"
done

echo -e "${YELLOW}📋 PHASE 8: Frontend Core${NC}"

# PRIORITY 8: Frontend core (ha létezik)
if [[ -d "frontend" ]]; then
    add_file_smart "frontend/package.json" "FRONTEND-CONFIG"
    add_file_smart "frontend/src/index.tsx" "FRONTEND-CORE"
    add_file_smart "frontend/src/App.tsx" "FRONTEND-CORE"
    add_file_smart "frontend/src/index.css" "FRONTEND-STYLE"
    
    # React components (legfontosabbak)
    for component in "Layout" "Auth/LoginForm" "Auth/RegisterForm" "Dashboard" "Onboarding"; do
        find frontend/src -name "${component}.tsx" -o -name "${component}.ts" | head -1 | while read comp_file; do
            if [[ -n "$comp_file" ]]; then
                add_file_smart "$comp_file" "FRONTEND-COMPONENT"
            fi
        done
    done
    
    # API services
    find frontend/src -name "*api*" -o -name "*service*" | grep -E "\.(ts|tsx)$" | head -3 | while read api_file; do
        add_file_smart "$api_file" "FRONTEND-API"
    done
fi

echo -e "${YELLOW}📋 PHASE 9: Testing Infrastructure${NC}"

# PRIORITY 9: Tesztek (ha marad hely)
find . -name "test_*.py" -o -name "*_test.py" | head -5 | while read test_file; do
    add_file_smart "$test_file" "TEST"
done

echo -e "${YELLOW}📋 PHASE 10: Utility Scripts${NC}"

# PRIORITY 10: Fontos szkriptek
for script in "start_backend.sh" "start_both.sh" "automated_test.sh"; do
    if [[ -f "$script" ]]; then
        add_file_smart "$script" "UTILITY"
    fi
done

# Végső statisztikák
final_size=$(get_file_size "${OUTPUT_FILE}")
final_size_mb=$(echo "scale=2; $final_size / 1024 / 1024" | bc -l 2>/dev/null || python3 -c "print(f'{$final_size / 1024 / 1024:.2f}')" 2>/dev/null || echo "~$((final_size / 1024 / 1024))")
line_count=$(wc -l < "${OUTPUT_FILE}" | tr -d ' ')
char_count=$(wc -c < "${OUTPUT_FILE}" | tr -d ' ')

# Statisztika hozzáadása a fájlhoz
cat >> "${OUTPUT_FILE}" << EOF

================================================================================
📊 EXTRACTION STATISTICS & PROJECT SUMMARY
================================================================================

## 📈 File Statistics
- **Final Size**: ${final_size_mb} MB (${final_size} bytes)
- **Line Count**: ${line_count}
- **Character Count**: ${char_count}
- **Target Limit**: ${MAX_SIZE_MB} MB
- **Status**: $(if (( final_size <= MAX_SIZE_BYTES )); then echo "✅ WITHIN LIMIT"; else echo "⚠️ EXCEEDED LIMIT"; fi)

## 🎓 LFA Education Center Architecture Summary

### 🔧 Backend Technology Stack
- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Authentication**: JWT tokens with role-based access
- **Migration**: Alembic database migrations
- **Testing**: pytest with comprehensive coverage

### 🎨 Frontend Technology Stack  
- **Framework**: React 18 with TypeScript
- **UI Library**: Material-UI (MUI)
- **State Management**: React hooks + Context API
- **Build Tool**: Create React App (CRA)
- **Testing**: Jest + React Testing Library

### 🏗️ Key System Components
- **User Management**: Multi-role authentication system
- **Onboarding**: Guided user profile completion
- **Specializations**: Player/Coach/Internship tracks
- **Booking System**: Session scheduling and attendance
- **Payment Verification**: Admin-controlled payment approval
- **Analytics**: Comprehensive reporting dashboard

### 🔐 Security Features
- JWT token authentication with refresh tokens
- Role-based access control (Admin/Instructor/Student)
- Password hashing with bcrypt
- Rate limiting and CORS protection
- Input validation and SQL injection prevention

### 📱 Mobile Compatibility
- iOS Safari optimized
- Responsive design patterns
- Touch-friendly UI components
- Cross-browser compatibility

## 🚀 Development Workflow
1. **Backend Start**: \`./start_backend.sh\`
2. **Frontend Start**: \`cd frontend && npm start\`
3. **Full Stack**: \`./start_both.sh\`
4. **Testing**: \`./automated_test.sh\`
5. **Database Reset**: \`python scripts/fresh_database_reset.py\`

## 🎯 API Endpoints Summary
- **Authentication**: /auth/login, /auth/register, /auth/refresh
- **Users**: /users/profile, /users/onboarding, /users/specialization
- **Sessions**: /sessions/create, /sessions/book, /sessions/attend
- **Admin**: /admin/users, /admin/payments, /admin/analytics
- **Health**: /health, /health/detailed, /health/ready

Generated: $(date)
Project Root: ${PROJECT_ROOT}
Optimized for Claude AI knowledge base processing.

EOF

# Befejezés üzenet
echo ""
echo -e "${GREEN}🎉 EXTRACTION COMPLETED SUCCESSFULLY!${NC}"
echo -e "${GREEN}====================================${NC}"
echo -e "${CYAN}📁 Output File: ${OUTPUT_FILE}${NC}"
echo -e "${CYAN}📏 Final Size: ${final_size_mb} MB${NC}"
echo -e "${CYAN}📄 Lines: ${line_count}${NC}"
echo -e "${CYAN}🎯 Target: ${MAX_SIZE_MB} MB${NC}"

if (( final_size <= MAX_SIZE_BYTES )); then
    echo -e "${GREEN}✅ SUCCESS: File within ${MAX_SIZE_MB}MB limit!${NC}"
    echo -e "${BLUE}🤖 Perfect for Claude AI project knowledge upload${NC}"
else
    echo -e "${YELLOW}⚠️ WARNING: File exceeds ${MAX_SIZE_MB}MB limit${NC}"
    echo -e "${YELLOW}   Consider running again or removing less critical files${NC}"
fi

echo ""
echo -e "${PURPLE}💡 NEXT STEPS:${NC}"
echo -e "${PURPLE}1. Upload ${OUTPUT_FILE} to your Claude project knowledge base${NC}"
echo -e "${PURPLE}2. This optimized extract contains all critical LFA Education Center code${NC}"
echo -e "${PURPLE}3. Claude will understand the full project architecture & implementation${NC}"
echo ""
echo -e "${BLUE}🎓 LFA Education Center extraction complete! 🚀${NC}"