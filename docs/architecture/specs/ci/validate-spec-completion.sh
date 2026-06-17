#!/usr/bin/env bash
# specs/ci/validate-spec-completion.sh
#
# CI gate script: Validates that a feature branch has completed all
# Spec Kit workflow steps before merge is permitted.
#
# Usage:
#   ./specs/ci/validate-spec-completion.sh [branch-name]
#
# If branch-name is omitted, uses the current Git branch.
#
# Exit codes:
#   0 — All validations pass
#   1 — Validation failure (blocks merge)

set -euo pipefail

BRANCH="${1:-$(git rev-parse --abbrev-ref HEAD)}"
SPEC_DIR="specs/features"

# ─── Step 1: Validate branch naming convention ───────────────────────────

if [[ "$BRANCH" == "main" || "$BRANCH" == "master" ]]; then
    echo "✅ Branch is main/master — spec validation not required."
    exit 0
fi

# Automated tooling branches (copilot, dependabot, renovate, etc.) are exempt
# from spec validation because they are generated without a Spec Kit workflow.
if [[ "$BRANCH" =~ ^(copilot|dependabot|renovate)/ ]]; then
    echo "✅ Branch '$BRANCH' is an automated tooling branch — spec validation not required."
    exit 0
fi

if [[ ! "$BRANCH" =~ ^[0-9]{3}-.+ ]]; then
    echo "❌ FAIL: Branch name '$BRANCH' does not match required format: NNN-feature-name"
    echo "   Example: 001-filename-parser-edge-cases"
    exit 1
fi

echo "✅ Branch name '$BRANCH' follows NNN-feature-name convention."

# Extract the feature directory name (same as branch name)
FEATURE_DIR="${SPEC_DIR}/${BRANCH}"

# ─── Step 2: Check that spec artifacts exist ─────────────────────────────

REQUIRED_FILES=(
    "spec.md"
    "clarify.md"
    "plan.md"
    "tasks.md"
    "checklist.md"
)

MISSING=0
for file in "${REQUIRED_FILES[@]}"; do
    if [[ ! -f "${FEATURE_DIR}/${file}" ]]; then
        echo "❌ FAIL: Missing ${FEATURE_DIR}/${file}"
        MISSING=1
    else
        echo "✅ Found ${FEATURE_DIR}/${file}"
    fi
done

if [[ $MISSING -eq 1 ]]; then
    echo ""
    echo "❌ BLOCKED: Spec artifacts are incomplete. Complete the Spec Kit workflow:"
    echo "   1. /speckit.specify  → spec.md"
    echo "   2. /speckit.clarify  → clarify.md"
    echo "   3. /speckit.plan     → plan.md"
    echo "   4. /speckit.tasks    → tasks.md"
    echo "   5. /speckit.checklist → checklist.md"
    exit 1
fi

# ─── Step 3: Validate checklist completion ───────────────────────────────

CHECKLIST="${FEATURE_DIR}/checklist.md"
UNCHECKED=$(grep -c '^\- \[ \]' "$CHECKLIST" || true)
CHECKED=$(grep -c '^\- \[x\]' "$CHECKLIST" || true)
TOTAL=$((UNCHECKED + CHECKED))

if [[ $TOTAL -eq 0 ]]; then
    echo "❌ FAIL: Checklist has no checkable items. Was it filled out?"
    exit 1
fi

if [[ $UNCHECKED -gt 0 ]]; then
    echo "❌ FAIL: Checklist has ${UNCHECKED} incomplete items out of ${TOTAL}."
    echo "   All checklist items must be checked before merge."
    grep '^\- \[ \]' "$CHECKLIST" | head -10
    exit 1
fi

echo "✅ Checklist complete: ${CHECKED}/${TOTAL} items checked."

# ─── Step 4: Validate commit message convention ─────────────────────────

# Check that at least the most recent commit follows Conventional Commits
LAST_COMMIT=$(git log -1 --pretty=format:"%s")
CONVENTIONAL_RE='^(feat|fix|chore|docs|style|refactor|perf|test|build|ci|revert|constitution)(\(.+\))?!?: .+'

if [[ ! "$LAST_COMMIT" =~ $CONVENTIONAL_RE ]]; then
    echo "⚠️  WARNING: Last commit message does not follow Conventional Commits format:"
    echo "   \"$LAST_COMMIT\""
    echo "   Expected: type(scope): description"
    # Warning only — don't block for this
fi

echo ""
echo "═══════════════════════════════════════════════════════"
echo "✅ ALL SPEC VALIDATIONS PASSED for branch: ${BRANCH}"
echo "═══════════════════════════════════════════════════════"
exit 0
