# Technical Plan Template

> **Command:** `/speckit.plan`
> **Purpose:** Define HOW the feature will be implemented.
> **Input:** Completed `spec.md` and `clarify.md`.
> **Rule:** NOW you specify tech stack, libraries, patterns.

---

## Feature Reference

_[Link to `spec.md` or feature name]_

## Implementation Language / Stack

_[Python 3.13+, Rust, etc.]_

## Architecture

_[Which modules/layers are affected? What's the data flow?]_

## Files to Create / Modify

| File | Action | Purpose |
|------|--------|---------|
| _[path]_ | Create / Modify | _[What changes]_ |

## Key Design Decisions

1. _[Decision]_ — _[Rationale]_

## Data Structures

```
[Describe key data structures, classes, or types]
```

## Algorithm / Strategy

_[Step-by-step description of the core logic]_

## Dependencies

- _[Library name]_ — _[Version]_ — _[Justification]_

## Testing Strategy

- **Framework:** _[pytest, cargo test, node --test]_
- **Approach:** _[Parameterized, property-based, snapshot]_
- **Coverage target:** _[≥ N%]_

## Error Handling

_[How errors are surfaced, logged, and recovered from]_

## Performance Considerations

_[Complexity analysis, benchmarks if needed]_
