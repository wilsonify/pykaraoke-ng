# Clarification Template

> **Command:** `/speckit.clarify`
> **Purpose:** Surface risks, ambiguities, and cross-cutting concerns.
> **Input:** A completed `spec.md` for the feature.

---

## Feature Reference

_[Link to `spec.md` or feature name]_

## Security Considerations

- _[Attack vectors, input validation, privilege boundaries]_

## Performance Considerations

- _[Latency budgets, throughput expectations, memory constraints]_

## Cross-Platform Considerations

- _[OS-specific behaviors, filesystem differences, path handling]_

## Backward Compatibility

- _[Public API changes, config format changes, migration needs]_

## CI/CD and Build-System Impact

- _[Does this change any CI workflow, build script, or packaging config?]_
- _[Will the change work on all three CI platforms (Linux, Windows, macOS)?]_
- _[Are there new relative-path assumptions?  What directory is the CWD?]_
- _[Do existing integration tests validate behaviour or literal strings?]_
- _[How will you test this locally before pushing? (act, cargo check, etc.)]_

## Dependency Impact

- _[New dependencies needed? License compatibility?]_

## Ambiguities Identified

1. _[Ambiguity]_ → **Resolution:** _[How to resolve]_

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| _[Risk]_ | _[H/M/L]_ | _[H/M/L]_ | _[Strategy]_ |

## Decisions Made

- **Decision:** _[What was decided]_ — **Rationale:** _[Why]_
