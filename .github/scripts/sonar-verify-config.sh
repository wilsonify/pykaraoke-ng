#!/usr/bin/env bash
# Pre-scan guard for the SonarQube CI job (called from .github/workflows/ci-cd.yml).
#
# Fails fast with a clear message when auth/server config is missing, instead
# of letting the scan fail obscurely and the quality-gate step report a
# confusing ".scannerwork/report-task.txt does not exist".
#
# Prints only non-secret facts (lengths, scheme+host) — never the token.
# Expects SONAR_TOKEN and SONAR_HOST_URL in the environment (wired from
# GitHub secrets in the workflow step). Must run from the repository root.
set -uo pipefail

token="${SONAR_TOKEN:-}"
host_url="${SONAR_HOST_URL:-}"

echo "SONAR_TOKEN length: ${#token} (0 means the secret is missing)"
echo "SONAR_HOST_URL length: ${#host_url} (0 means the secret is missing)"

host_base="$(printf '%s' "${host_url}" | sed -nE 's#^[a-zA-Z]+://[^/]+#&#p')"
if [ -n "${host_base}" ]; then
  echo "Sonar host: ${host_base}"
else
  echo "::warning::SONAR_HOST_URL is empty or not a URL."
fi

echo "--- Effective sonar config (comments stripped) ---"
grep -v '^[[:space:]]*#' sonar-project.properties | grep -v '^[[:space:]]*$' || true

echo "--- Coverage inputs expected by sonar-project.properties ---"
if ! ls -la coverage.xml pytest-junit.xml; then
  echo "::warning::coverage inputs missing (scan may warn/fail on coverage)."
fi

failed=0
if [ -z "${token}" ]; then
  echo "::error::SONAR_TOKEN is empty. Set the SONAR_TOKEN secret."
  failed=1
fi
if [ -z "${host_url}" ]; then
  echo "::error::Sonar host URL is empty. Set the SONARQUBE_HOST_URL secret."
  failed=1
fi
if [ "${failed}" -ne 0 ]; then
  exit 1
fi
echo "SonarQube configuration present (values hidden)."
