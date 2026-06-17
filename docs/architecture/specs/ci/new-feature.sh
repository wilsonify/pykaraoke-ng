#!/usr/bin/env bash
# specs/ci/new-feature.sh
#
# Helper script to bootstrap a new feature branch with Spec Kit artifacts.
#
# Usage:
#   ./specs/ci/new-feature.sh "short description of feature"
#
# This will:
#   1. Read and increment the next feature ID from specs/features/.next-id
#   2. Create the branch NNN-kebab-case-description
#   3. Scaffold the spec artifact directory from templates
#   4. Print next steps

set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 \"short description of feature\""
    exit 1
fi

DESCRIPTION="$1"
KEBAB=$(echo "$DESCRIPTION" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-//;s/-$//')

# Read next ID
NEXT_ID_FILE="specs/features/.next-id"
if [[ ! -f "$NEXT_ID_FILE" ]]; then
    echo "1" > "$NEXT_ID_FILE"
fi

NEXT_ID=$(cat "$NEXT_ID_FILE")
PADDED_ID=$(printf "%03d" "$NEXT_ID")
BRANCH_NAME="${PADDED_ID}-${KEBAB}"
FEATURE_DIR="specs/features/${BRANCH_NAME}"

echo "═══════════════════════════════════════════════════════"
echo "  Creating feature: ${BRANCH_NAME}"
echo "═══════════════════════════════════════════════════════"

# Increment the ID for next time
echo $((NEXT_ID + 1)) > "$NEXT_ID_FILE"

# Create branch
git checkout -b "$BRANCH_NAME"

# Scaffold spec directory
mkdir -p "$FEATURE_DIR"

for template in spec.md clarify.md plan.md tasks.md; do
    TEMPLATE_MAP=("spec.md:feature-spec.md" "clarify.md:clarification.md" "plan.md:technical-plan.md" "tasks.md:task-breakdown.md")
    for mapping in "${TEMPLATE_MAP[@]}"; do
        target="${mapping%%:*}"
        source="${mapping##*:}"
        if [[ "$template" == "$target" ]]; then
            if [[ -f "specs/templates/${source}" ]]; then
                cp "specs/templates/${source}" "${FEATURE_DIR}/${target}"
            else
                touch "${FEATURE_DIR}/${target}"
            fi
        fi
    done
done

# Create empty checklist placeholder
cat > "${FEATURE_DIR}/checklist.md" << 'EOF'
# Completion Checklist

> Complete this checklist before requesting merge.
> Run: `/speckit.checklist`

- [ ] All spec artifacts reviewed
- [ ] All tasks completed
- [ ] All tests pass
- [ ] CI pipeline passes
- [ ] SonarQube quality gate passes
- [ ] Code reviewed and approved
EOF

echo ""
echo "✅ Branch created: ${BRANCH_NAME}"
echo "✅ Spec directory: ${FEATURE_DIR}/"
echo ""
echo "Next steps:"
echo "  1. Edit ${FEATURE_DIR}/spec.md     — /speckit.specify"
echo "  2. Edit ${FEATURE_DIR}/clarify.md  — /speckit.clarify"
echo "  3. Edit ${FEATURE_DIR}/plan.md     — /speckit.plan"
echo "  4. Edit ${FEATURE_DIR}/tasks.md    — /speckit.tasks"
echo "  5. Implement (TDD: red → green → refactor)"
echo "  6. Edit ${FEATURE_DIR}/checklist.md — /speckit.checklist"
echo "  7. Push and open PR"
