#!/usr/bin/env bash
# Best-effort triage dump for SonarQube job failures
# (called from .github/workflows/ci-cd.yml with `if: failure()`).
#
# Never prints SONAR_TOKEN (lengths and scheme+host only). Every
# informational command is guarded so diagnostics can't mask the original
# failure. Always exits 0 — the job result is decided by the failed step.
#
# Environment (all optional except SONAR_HOST_URL for the reachability probe):
#   SONAR_HOST_URL          Sonar server URL (no token is ever sent; the probe
#                           hits the anonymous /api/server/version endpoint).
#   NEEDS_PYTHON_RESULT, NEEDS_RUST_RESULT, NEEDS_FRONTEND_RESULT,
#   NEEDS_OPENSPEC_RESULT  upstream job results, passed via the workflow's
#                           `needs.*.result` contexts.
# Runner context (ref/sha/event) is read from the standard GITHUB_* variables
# that GitHub Actions sets automatically. Must run from the repository root.
set -uo pipefail

host_url="${SONAR_HOST_URL:-}"

echo "===== SonarQube failure diagnostics (non-secret) ====="

echo "--- Runner / repo ---"
uname -a || true
echo "ref=${GITHUB_REF:-unknown} sha=${GITHUB_SHA:-unknown} event=${GITHUB_EVENT_NAME:-unknown}"
git rev-parse --short HEAD || true
git rev-parse --is-shallow-repository || true
echo "needs: python=${NEEDS_PYTHON_RESULT:-unknown} rust=${NEEDS_RUST_RESULT:-unknown} frontend=${NEEDS_FRONTEND_RESULT:-unknown} openspec=${NEEDS_OPENSPEC_RESULT:-unknown}"

echo "--- Workspace top level ---"
ls -la || true

echo "--- Coverage inputs ---"
ls -la coverage.xml pytest-junit.xml htmlcov/ || true

echo "--- Scanner workdir ---"
ls -la .scannerwork/ || echo "(no .scannerwork directory)"

echo "--- Any report-task.txt in workspace (maxdepth 4) ---"
find . -maxdepth 4 -name 'report-task.txt' -print || true
if [[ -f .scannerwork/report-task.txt ]]; then
  echo "--- .scannerwork/report-task.txt ---"
  cat .scannerwork/report-task.txt || true
fi

echo "--- Server reachability (no token sent) ---"
host_base="$(printf '%s' "${host_url}" | sed -nE 's#^[a-zA-Z]+://[^/]+#&#p')"
if [[ -n ${host_base} ]]; then
  code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 15 "${host_base}/api/server/version" 2>&1 || true)"
  echo "GET ${host_base}/api/server/version -> ${code}"
else
  echo "Skipped: SONAR_HOST_URL empty or not a URL."
fi

echo "--- Disk ---"
df -h . || true

echo "===== end diagnostics ====="
