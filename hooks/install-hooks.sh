#!/usr/bin/env bash
# =============================================================================
# install-hooks.sh — Install all project git hooks
# =============================================================================
#
# Run once after cloning or when hooks change:
#   ./hooks/install-hooks.sh
#
# What it installs:
#   pre-commit  — Champion badge static guard (fast, <1s)
#                 Blocks commits that remove the CHAMPION guard or introduce
#                 the hardcoded "No ranking data" string
#   pre-push    — Champion badge E2E regression guard (Playwright, ~20–60s)
#                 Self-starts a dedicated Streamlit, runs the golden-path test,
#                 shuts Streamlit down, blocks push on failure
#
# Idempotent: safe to run multiple times.
# =============================================================================

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOKS_SRC="${REPO_ROOT}/hooks"
HOOKS_DST="${REPO_ROOT}/.git/hooks"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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
    if [[ -f "${dst}" ]] && ! grep -q "Champion Badge" "${dst}" 2>/dev/null; then
        cp "${dst}" "${dst}.backup"
        echo -e "  ${YELLOW}ℹ️  ${name}: existing hook backed up to ${name}.backup${NC}"
    fi

    cp "${src}" "${dst}"
    chmod +x "${dst}"
    echo -e "  ${GREEN}✅ ${name} installed → .git/hooks/${name}${NC}"
}

install_hook "pre-commit"
install_hook "pre-push"

echo ""
echo -e "${GREEN}${BOLD}All hooks installed.${NC}"
echo ""
echo "Hooks installed:"
echo "  pre-commit  — Champion static guard (fast)"
echo "                Blocks commits that remove CHAMPION guard or add regression string"
echo "                Override: SKIP_CHAMPION_COMMIT_CHECK=1 git commit"
echo ""
echo "  pre-push    — Champion E2E regression guard (full Playwright test)"
echo "                Self-manages a dedicated Streamlit on port 8599"
echo "                Override: SKIP_CHAMPION_CHECK=1 SKIP_REASON=\"<reason>\" git push"
echo "                Note: SKIP_REASON is required; every skip is audit-logged"
echo ""
echo "Uninstall:"
echo "  rm .git/hooks/pre-commit .git/hooks/pre-push"
echo ""
