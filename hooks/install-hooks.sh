#!/usr/bin/env bash
# =============================================================================
# install-hooks.sh — Install all project git hooks
# =============================================================================
#
# Run once after cloning or when hooks change:
#   ./hooks/install-hooks.sh
#
# What it does:
#   - Copies hooks/pre-push  → .git/hooks/pre-push  (Champion badge guard)
#   - Makes each hook executable
#   - Verifies installation
#
# Idempotent: safe to run multiple times.
# =============================================================================

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOKS_SRC="${REPO_ROOT}/hooks"
HOOKS_DST="${REPO_ROOT}/.git/hooks"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

echo ""
echo -e "${BOLD}Installing project git hooks...${NC}"
echo ""

install_hook() {
    local name="$1"
    local src="${HOOKS_SRC}/${name}"
    local dst="${HOOKS_DST}/${name}"

    if [[ ! -f "${src}" ]]; then
        echo -e "  ${YELLOW}⚠️  ${name}: source not found at ${src}, skipping${NC}"
        return
    fi

    # Backup existing hook if it's not already our version
    if [[ -f "${dst}" ]] && ! grep -q "Champion Badge Regression Guard" "${dst}" 2>/dev/null; then
        cp "${dst}" "${dst}.backup"
        echo -e "  ${YELLOW}ℹ️  ${name}: existing hook backed up to ${name}.backup${NC}"
    fi

    cp "${src}" "${dst}"
    chmod +x "${dst}"
    echo -e "  ${GREEN}✅ ${name} installed → .git/hooks/${name}${NC}"
}

install_hook "pre-push"

echo ""
echo -e "${GREEN}${BOLD}All hooks installed.${NC}"
echo ""
echo "What was installed:"
echo "  pre-push  — Champion badge regression guard"
echo "              Blocks push if CHAMPION badge shows 'No ranking data'"
echo ""
echo "Override (emergencies only):"
echo "  SKIP_CHAMPION_CHECK=1 git push"
echo ""
echo "Uninstall:"
echo "  rm .git/hooks/pre-push"
echo ""
