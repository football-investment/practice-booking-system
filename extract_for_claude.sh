#!/bin/bash

# Extract all source files content for Claude AI Knowledge Base

# Script: extract_for_claude.sh
# Purpose: Create a single comprehensive file with all source code content
# Project: Practice Booking System (React + Python/FastAPI)

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
OUTPUT_FILE="CLAUDE_AINAK.txt"
PROJECT_ROOT="$(pwd)"

# Print banner
echo -e "${BLUE}🤖 Claude AI Knowledge Extractor - Practice Booking System${NC}"
echo -e "${BLUE}=======================================================${NC}"
echo ""

# Check if we're in project root
if [[ ! -f "app/main.py" ]] && [[ ! -d "frontend" ]]; then
    echo -e "${RED}❌ Error: This script must be run from the Practice Booking System project root${NC}"
    echo -e "   Make sure you have app/main.py (backend) and frontend/ directory"
    exit 1
fi

# Remove existing output file
if [[ -f "${OUTPUT_FILE}" ]]; then
    rm "${OUTPUT_FILE}"
fi

# Function to add file content to output
add_file_content() {
    local file_path="$1"
    local relative_path="${file_path#./}"
    
    if [[ -f "$file_path" ]]; then
        echo -e "${YELLOW}📄 Processing: ${relative_path}${NC}"
        
        # Add separator and file header
        echo "" >> "${OUTPUT_FILE}"
        echo "================================================================================" >> "${OUTPUT_FILE}"
        echo "FILE: ${relative_path}" >> "${OUTPUT_FILE}"
        echo "================================================================================" >> "${OUTPUT_FILE}"
        echo "" >> "${OUTPUT_FILE}"
        
        # Add file content
        cat "$file_path" >> "${OUTPUT_FILE}"
        echo "" >> "${OUTPUT_FILE}"
    else
        echo -e "${YELLOW}   ⚠️  File ${relative_path} not found, skipping${NC}"
    fi
}

# Create initial header
echo "# Claude AI Knowledge Base - Practice Booking System" > "${OUTPUT_FILE}"
echo "# Generálva: $(date)" >> "${OUTPUT_FILE}"
echo "# Projekt: Practice Booking System (React + Python/FastAPI)" >> "${OUTPUT_FILE}"
echo "" >> "${OUTPUT_FILE}"

# Add project overview
echo -e "${YELLOW}📋 Adding project overview...${NC}"
echo "================================================================================" >> "${OUTPUT_FILE}"
echo "PROJEKT ÁTTEKINTÉS" >> "${OUTPUT_FILE}"
echo "================================================================================" >> "${OUTPUT_FILE}"
echo "" >> "${OUTPUT_FILE}"
echo "Ez egy Practice Booking System projekt Python/FastAPI backend + React frontend architektúrával." >> "${OUTPUT_FILE}"
echo "Tartalmazza a teljes forráskódot és konfigurációs fájlokat." >> "${OUTPUT_FILE}"
echo "" >> "${OUTPUT_FILE}"
echo "KOMPONENSEK:" >> "${OUTPUT_FILE}"
echo "- Backend: Python/FastAPI (app/ mappa)" >> "${OUTPUT_FILE}"
echo "- Frontend: React (frontend/ és src/ mappák)" >> "${OUTPUT_FILE}"
echo "- Database: SQLite/PostgreSQL (Alembic migrations)" >> "${OUTPUT_FILE}"
echo "- Admin panel: React komponensek" >> "${OUTPUT_FILE}"
echo "- Student dashboard: React komponensek" >> "${OUTPUT_FILE}"
echo "" >> "${OUTPUT_FILE}"

# Python Backend Files
echo -e "${YELLOW}🐍 Adding Python backend files...${NC}"

# Main application files
find app/ -name "*.py" -type f 2>/dev/null | sort | while read -r file; do
    add_file_content "$file"
done

# Alembic migration files
if [[ -d "alembic" ]]; then
    echo -e "${YELLOW}🗄️  Adding Alembic migration files...${NC}"
    find alembic/ -name "*.py" -type f | sort | while read -r file; do
        add_file_content "$file"
    done
    add_file_content "alembic.ini"
fi

# Backend configuration files
BACKEND_CONFIG_FILES=(
    "requirements.txt"
    ".env.example"
    ".env.development"
    ".env.production"
    "pytest.ini"
    "pyproject.toml"
    "setup.py"
)

for file in "${BACKEND_CONFIG_FILES[@]}"; do
    if [[ -f "$file" ]]; then
        add_file_content "$file"
    fi
done

# React Frontend Files - Package and Config
echo -e "${YELLOW}⚙️  Adding React frontend configuration...${NC}"
FRONTEND_CONFIG_FILES=(
    "frontend/package.json"
    "frontend/package-lock.json"
    "package.json"
    "package-lock.json"
    ".gitignore"
)

for file in "${FRONTEND_CONFIG_FILES[@]}"; do
    if [[ -f "$file" ]]; then
        add_file_content "$file"
    fi
done

# React Source Files
echo -e "${YELLOW}💻 Adding React source code files...${NC}"

# Main src directory
if [[ -d "src" ]]; then
    find src/ -type f \( -name "*.js" -o -name "*.jsx" -o -name "*.ts" -o -name "*.tsx" -o -name "*.css" \) | sort | while read -r file; do
        add_file_content "$file"
    done
fi

# Frontend src directory (if exists)
if [[ -d "frontend/src" ]]; then
    find frontend/src/ -type f \( -name "*.js" -o -name "*.jsx" -o -name "*.ts" -o -name "*.tsx" -o -name "*.css" \) | sort | while read -r file; do
        add_file_content "$file"
    done
fi

# Frontend public files
echo -e "${YELLOW}🌐 Adding React public files...${NC}"
if [[ -d "frontend/public" ]]; then
    find frontend/public/ -type f \( -name "*.html" -o -name "*.json" -o -name "*.txt" -o -name "*.xml" \) | sort | while read -r file; do
        add_file_content "$file"
    done
fi

if [[ -d "public" ]]; then
    find public/ -type f \( -name "*.html" -o -name "*.json" -o -name "*.txt" -o -name "*.xml" \) | sort | while read -r file; do
        add_file_content "$file"
    done
fi

# Shell Scripts and Configuration
echo -e "${YELLOW}🔧 Adding utility scripts...${NC}"
SCRIPT_FILES=(
    "frontend_setup.sh"
    "frontend_testing.sh"
    "verify_frontend_setup.sh"
    "run_backend.sh"
    "deploy.sh"
    "test.sh"
)

for file in "${SCRIPT_FILES[@]}"; do
    if [[ -f "$file" ]]; then
        add_file_content "$file"
    fi
done

# Find any additional shell scripts
find . -maxdepth 2 -name "*.sh" -type f | while read -r file; do
    add_file_content "$file"
done

# Documentation Files
echo -e "${YELLOW}📚 Adding documentation...${NC}"
DOC_FILES=(
    "README.md"
    "frontend/README.md"
    "DEPLOYMENT.md"
    "API_DOCUMENTATION.md"
    "TESTING.md"
    "ARCHITECTURE.md"
    "SETUP.md"
    "testing_report.md"
    "CHANGELOG.md"
)

for file in "${DOC_FILES[@]}"; do
    if [[ -f "$file" ]]; then
        add_file_content "$file"
    fi
done

# Test Files
echo -e "${YELLOW}🧪 Adding test files...${NC}"

# Python tests
if [[ -d "tests" ]]; then
    find tests/ -name "*.py" -type f | sort | while read -r file; do
        add_file_content "$file"
    done
fi

# React tests
find . -name "*.test.js" -o -name "*.test.jsx" -o -name "*.spec.js" -o -name "*.spec.jsx" | sort | while read -r file; do
    add_file_content "$file"
done

# Database Files (if not too large)
echo -e "${YELLOW}💾 Adding database and data files...${NC}"
if [[ -f "practice_booking.db" ]] && [[ $(wc -c <"practice_booking.db" 2>/dev/null || echo "0") -lt 100000 ]]; then
    echo -e "${YELLOW}   Note: SQLite database found but skipped (binary file)${NC}"
fi

# SQL files
find . -name "*.sql" -type f | while read -r file; do
    if [[ $(wc -c <"$file") -lt 1000000 ]]; then  # Only if smaller than 1MB
        add_file_content "$file"
    fi
done

# Environment and Config Files
ENV_FILES=(
    ".env.backup.*"
    "config.py"
    "settings.py"
    "config.json"
)

for pattern in "${ENV_FILES[@]}"; do
    for file in $pattern; do
        if [[ -f "$file" ]] && [[ $(wc -c <"$file") -lt 10000 ]]; then
            add_file_content "$file"
        fi
    done 2>/dev/null
done

# Docker files (if present)
DOCKER_FILES=(
    "Dockerfile"
    "docker-compose.yml"
    "docker-compose.yaml"
    ".dockerignore"
)

for file in "${DOCKER_FILES[@]}"; do
    if [[ -f "$file" ]]; then
        add_file_content "$file"
    fi
done

# Add final summary
echo "" >> "${OUTPUT_FILE}"
echo "================================================================================" >> "${OUTPUT_FILE}"
echo "ÖSSZEFOGLALÓ" >> "${OUTPUT_FILE}"
echo "================================================================================" >> "${OUTPUT_FILE}"
echo "" >> "${OUTPUT_FILE}"
echo "Ez a fájl tartalmazza a teljes Practice Booking System projekt forráskódját." >> "${OUTPUT_FILE}"
echo "Generálva: $(date)" >> "${OUTPUT_FILE}"
echo "Projekt gyökér: ${PROJECT_ROOT}" >> "${OUTPUT_FILE}"
echo "" >> "${OUTPUT_FILE}"
echo "TARTALMAZOTT KOMPONENSEK:" >> "${OUTPUT_FILE}"
echo "- Python/FastAPI backend (app/ mappa)" >> "${OUTPUT_FILE}"
echo "- React frontend (src/ és frontend/ mappák)" >> "${OUTPUT_FILE}"
echo "- Alembic database migrations" >> "${OUTPUT_FILE}"
echo "- Konfigurációs fájlok (package.json, requirements.txt, stb.)" >> "${OUTPUT_FILE}"
echo "- Utility script-ek" >> "${OUTPUT_FILE}"
echo "- Dokumentáció és tesztek" >> "${OUTPUT_FILE}"
echo "" >> "${OUTPUT_FILE}"

# Calculate statistics
FILE_SIZE=$(du -sh "${OUTPUT_FILE}" | cut -f1)
LINE_COUNT=$(wc -l < "${OUTPUT_FILE}" | tr -d ' ')
CHAR_COUNT=$(wc -c < "${OUTPUT_FILE}" | tr -d ' ')

echo "Fájl méret: ${FILE_SIZE}" >> "${OUTPUT_FILE}"
echo "Sorok száma: ${LINE_COUNT}" >> "${OUTPUT_FILE}"
echo "Karakterek száma: ${CHAR_COUNT}" >> "${OUTPUT_FILE}"
echo "" >> "${OUTPUT_FILE}"

# Success message
echo ""
echo -e "${GREEN}🎉 Practice Booking System extraction completed successfully!${NC}"
echo -e "${GREEN}============================================================${NC}"
echo -e "📁 Output file: ${OUTPUT_FILE}"
echo -e "📏 Size: ${FILE_SIZE}"
echo -e "📄 Lines: ${LINE_COUNT}"
echo -e "🔤 Characters: ${CHAR_COUNT}"
echo ""
echo -e "${BLUE}🤖 This file contains complete Practice Booking System codebase for Claude AI${NC}"
echo -e "${BLUE}   Upload this single file to your Claude project knowledge base.${NC}"
echo ""
echo -e "${YELLOW}💡 Included:${NC}"
echo -e "${YELLOW}   ✅ Python/FastAPI backend code${NC}"
echo -e "${YELLOW}   ✅ React frontend components${NC}"
echo -e "${YELLOW}   ✅ Database migrations${NC}"
echo -e "${YELLOW}   ✅ Configuration files${NC}"
echo -e "${YELLOW}   ✅ Shell scripts${NC}"
echo -e "${YELLOW}   ✅ Documentation${NC}"
echo -e "${YELLOW}   ✅ Test files${NC}"
echo ""
echo -e "${YELLOW}💡 Excluded: Binary files, images, large databases, node_modules${NC}"