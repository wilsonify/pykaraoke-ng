#!/usr/bin/env bash
# Post-scan guard for the SonarQube CI job (called from .github/workflows/ci-cd.yml).
#
# The quality-gate action reads .scannerwork/report-task.txt produced by the
# scan step. If the scan did not complete, fail here with a clear pointer to
# the scan logs instead of the generic "does not exist" error from
# check-quality-gate.sh. Must run from the repository root.
set -uo pipefail

if [[ ! -f .scannerwork/report-task.txt ]]; then
  echo "::error::.scannerwork/report-task.txt not found — SonarQube Scan did not complete successfully. Check the 'SonarQube Scan' step logs above." >&2
  ls -la .scannerwork/ || true
  exit 1
fi
cat .scannerwork/report-task.txt
