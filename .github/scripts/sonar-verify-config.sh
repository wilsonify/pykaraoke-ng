#!/usr/bin/env bash
# Pre-scan guard for the SonarQube CI job (called from .github/workflows/ci-cd.yml).
#
# Fails fast with a clear message when auth/server config is missing or the
# token is rejected, instead of letting the scan fail obscurely (e.g. HTTP 403
# on JRE provisioning) and the quality-gate step report a confusing
# ".scannerwork/report-task.txt does not exist".
#
# Prints only non-secret facts (lengths, host type, valid:true/false) — never
# the token or host values. Expects SONAR_TOKEN and SONAR_HOST_URL in the
# environment (wired from GitHub secrets in the workflow step). Must run from
# the repository root.
set -uo pipefail

token="${SONAR_TOKEN:-}"
host_url="${SONAR_HOST_URL:-}"

echo "SONAR_TOKEN length: ${#token} (0 means the secret is missing)"
echo "SONAR_HOST_URL length: ${#host_url} (0 means the secret is missing)"

# Classify the host without printing its (secret-stored) value — echoing the
# URL itself only renders as *** in logs because GitHub masks secrets.
if [[ ${host_url} == "https://sonarcloud.io" || ${host_url} == "https://sonarcloud.io/" ]]; then
  echo "Sonar host type: SonarQube Cloud"
elif [[ -n ${host_url} ]]; then
  echo "Sonar host type: self-hosted SonarQube Server (value hidden)"
else
  echo "::warning::SONAR_HOST_URL is empty."
fi
host_base="$(printf '%s' "${host_url}" | sed -nE 's#^[a-zA-Z]+://[^/]+#&#p')"

echo "--- Effective sonar config (comments stripped) ---"
grep -v '^[[:space:]]*#' sonar-project.properties | grep -v '^[[:space:]]*$' || true

echo "--- Coverage inputs expected by sonar-project.properties ---"
if ! ls -la coverage.xml pytest-junit.xml; then
  echo "::warning::coverage inputs missing (scan may warn/fail on coverage)."
fi

failed=0
if [[ -z ${token} ]]; then
  echo "::error::SONAR_TOKEN is empty. Set the SONAR_TOKEN secret."
  failed=1
fi
if [[ -z ${host_url} ]]; then
  echo "::error::Sonar host URL is empty. Set the SONARQUBE_HOST_URL secret."
  failed=1
fi
if [[ ${failed} -ne 0 ]]; then
  exit 1
fi

# A pasted secret with a stray space/newline authenticates as garbage and the
# scanner fails with HTTP 403. Catch that here with a clear message.
if printf '%s' "${token}" | grep -q '[[:space:]]'; then
  echo "::error::SONAR_TOKEN contains whitespace (often a stray space/newline from copy-paste). Re-paste the secret with no extra characters."
  exit 1
fi

# Authenticated probe: asks the server whether the token is valid. Only the
# boolean answer is printed; the token itself never appears in logs (GitHub
# also masks secret values automatically).
if [[ -n ${host_base} ]]; then
  echo "--- Token validation (authenticated probe, answer only) ---"
  validate_out="$(curl -sS --max-time 15 -u "${token}:" "${host_base}/api/authentication/validate" 2>&1 || true)"
  if printf '%s' "${validate_out}" | grep -q '"valid":true'; then
    echo "Token check: server reports the token is valid."
  elif printf '%s' "${validate_out}" | grep -q '"valid":false'; then
    echo "::error::Sonar server rejected SONAR_TOKEN (api/authentication/validate returned valid:false). Generate a new token with Execute Analysis permission and update the SONAR_TOKEN secret."
    exit 1
  else
    echo "::warning::Token validation inconclusive (no valid:true/false in response). Continuing; the scan step will surface auth errors."
  fi
fi

echo "SonarQube configuration present (values hidden)."
