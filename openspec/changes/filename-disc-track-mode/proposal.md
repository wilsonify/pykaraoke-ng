# Proposal: Disc-track spaced naming mode (issue #14)

> Status: proposed — not implemented.
> Capabilities: `filename-parsing`, `song-library`
> Legacy issue: kelvinlawson/pykaraoke#14 (artist-title parsing fails when a
> disc/track prefix is spaced).

## Intent

Issue #14's reporter wanted libraries named like
`CB30055-15 - Switchfoot - Stars.zip` and
`SC3448-03 - All-American Rejects - Dirty Little Secret.zip` to parse
correctly. Today the first `" - "` is always the artist split, so the whole
disc-track prefix lands in the artist field and the real artist leaks into
the title. The reporter's requested convention was explicit: spaces are
**required** around the separating dashes, the **last** dash inside the
disc-track prefix separates disc from track, and the **first** `" - "` in
the remainder separates artist from title. That mode does not exist in the
parser (`FileNameType` has only modes 0–3).

## Scope

In scope:

* A new naming mode `DISC_TRACK_SPACED = 4` in `FileNameType` implementing
  the algorithm above, with these behaviours:
  * `CB30055-15 - Switchfoot - Stars` → disc `CB30055`, track `15`,
    artist `Switchfoot`, title `Stars`;
  * `CB5056-03-06 - Al Green - Let's Stay Together` → disc `CB5056-03`,
    track `06`, artist `Al Green`, title `Let's Stay Together` (last dash
    in the prefix wins);
  * inner `" - "` segments stay in the title (`… - Dirty Little Secret -
    Radio Edit`);
  * a stem that does not match the pattern (no spaced separator, or a
    prefix with no dash) falls back to the existing space-dash or
    best-effort legacy parsing so a mixed library still loads under one
    setting;
  * zip members parse under the same mode (`parse_zip_path` benefits for
    free), so `PHM - Pop/PHM0512/PHM0512-08 - Switchfoot - Stars` yields
    artist `Switchfoot`.
* `file_name_type` accepts `4`; settings round-trip already persists the
  integer unchanged.
* A settings-panel control exposing `file_name_type` (0–4) — the gap that
  issues #5/#14 also flagged as "still open"; without it the new mode is
  unreachable for non-technical users.
* Unit tests (pytest) for every scenario above plus non-regression for
  modes 0–3.
* Documentation: configuration reference and issue #14 coverage update.

Out of scope:

* Arbitrary user-supplied patterns (issue #5's regex filter) — a different
  feature.
* Unicode dash normalisation and other parser edge cases, owned by the
  existing `filename-parser-edge-cases` change.
* Fully resolving unspaced ambiguous legacy names such as
  `SC3448-03-All-American Rejects-…` (inherently ambiguous without spaces;
  the spaced mode is the supported answer).

## Approach

In `FilenameParser.parse()`, when the configured type is
`DISC_TRACK_SPACED`, the space-dash route calls a new helper
`_parse_disc_track_spaced(stem)` instead of `_parse_space_dash`. The helper
splits at the first `_SPACE_DASH_RE` match, requires a dash inside the
prefix (splitting disc/track at `rfind("-")`), then splits the remainder at
its first `" - "` for artist/title. Any mismatch falls back to
`_parse_space_dash`. Stems with no spaced separator fall back to
`_parse_legacy`, where mode 4 is handled by the `ARTIST_TITLE` branch
(best-effort; a title-only result is acceptable for unspaced names).
