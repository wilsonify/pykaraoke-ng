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
- Second-pass hardening implemented:
  - Added `SongDB._is_safe_database_file` guard to reject unsafe db paths/files before load.
  - Added size/ownership/permission checks (platform-appropriate).
  - Added regression tests validating unsafe-file rejection path.

### 2) Backend default bind host behavior
- Severity: RESOLVED (from MEDIUM)
- Previous Impact: Service could listen on all interfaces by default.
- Evidence: src/pykaraoke/core/backend.py defaults.
- Remediation implemented:
  - Default host changed from `0.0.0.0` to `127.0.0.1` in backend runtime and CLI defaults.
  - Container deployment remains explicit via `PYKARAOKE_API_HOST=0.0.0.0` where external bind is intended.
- Validation performed:
  - Targeted backend regression tests passed.
  - bandit no longer reports B104 for backend default bind host.

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
- Applied backend default-host hardening (`127.0.0.1` default).
- Applied guarded pickle-load path for song database cache.
- Added targeted regression tests for both security fixes.
- Re-ran bandit to confirm removal of bind-host finding and capture residual pickle/subprocess advisories.

## Current Security Posture
- High/Critical: none observed in this pass.
- Medium: pickle deserialization remains a known residual risk by design (mitigated by file safety checks).
- Low: subprocess advisory remains, with `shell=False` and expected command invocation pattern.

