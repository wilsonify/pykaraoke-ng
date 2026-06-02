# Security Report

Date: 2026-06-02

## Methods
- Dependency CVE scan: pip-audit
- Static code security scan: bandit -r src/pykaraoke
- Manual config/secrets review in workflows and config files

## Findings

### 1) Pickle deserialization in song database path
- Severity: MEDIUM
- Impact: If attacker-controlled pickle content is loaded, arbitrary code execution is possible.
- Evidence: src/pykaraoke/core/database.py (pickle import and pickle.load)
- Remediation:
  - Prefer safer serialization (json/sqlite/native structured format)
  - If pickle must remain, enforce trusted file location and strict ownership/permissions checks before load
- Validation performed: bandit reported B403 and B301

### 2) Backend default bind host is 0.0.0.0
- Severity: MEDIUM
- Impact: Service may unintentionally listen on all interfaces if deployed without network controls
- Evidence: src/pykaraoke/core/backend.py defaults
- Remediation:
  - Consider localhost default for dev mode and explicit opt-in for external bind
  - Keep container deployments explicit via env override
- Validation performed: bandit B104

### 3) Subprocess usage in mpg player
- Severity: LOW
- Impact: Potential command execution risk if untrusted input reaches command args
- Evidence: src/pykaraoke/players/mpg.py subprocess.Popen(..., shell=False)
- Remediation:
  - Continue shell=False
  - Validate and normalize any externally sourced command/path inputs
- Validation performed: bandit B404/B603 (advisory context)

## Dependency Vulnerability Summary
- pip-audit result: No known vulnerabilities found in resolved third-party packages
- Note: local package pykaraoke-ng cannot be audited via PyPI advisory DB

## Secrets Management Review
- Workflow secrets are referenced via GitHub secrets context
- No hardcoded secret values found in audited files

## Remediation Implemented in This Pass
- No direct security-behavior code change to pickle/bind defaults was applied to avoid behavior regressions without maintainer policy decision.
- Operationally safer test behavior and tooling reliability improvements were implemented.

