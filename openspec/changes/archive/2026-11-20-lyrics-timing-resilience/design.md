# Design: Lyrics timing resilience

## One timestamp pattern

```python
_TIMESTAMP = r"\[(\d{1,3}):(\d{1,2})(?:[.:](\d{1,3}))?\]"
_LINE_RE   = re.compile(r"^" + _TIMESTAMP + r"(.*)$")
_ELRC_TS   = re.compile(r"^" + _TIMESTAMP)
_WORD_RE   = re.compile(r"<(\d{1,3}):(\d{1,2})(?:[.:](\d{1,3}))?>")
```

Three forms share one definition, so a variant accepted by the line parser is
accepted by the `.elrc` reader and by enhanced word tags — the previous bug was
that each had its own copy of the pattern and each copy required a fraction.

Minutes go to three digits because compilations are long; seconds stay at two.
The fraction may be `.` or `:` because both appear in the wild, and 1–3 digits
so `[00:12.5]`, `[00:12.50]` and `[00:12.500]` all mean what they look like.

`_tag_ms(minutes, seconds, frac)` maps a missing fraction to 0 ms, keeping the
call sites branch-free.

## Warnings instead of silence

`parse_lrc()` returns `warnings` **only when non-empty**:

```python
{"kind": "skipped-line", "line": 7, "text": "[00:6x.00]Non-digit seconds"}
```

Omitting the key for clean files keeps every existing payload and test
identical, which is what lets this land without touching the dozens of tests
that compare lyric dicts.

A line is a candidate only when it starts with `[` and contains a digit-colon
digit sequence; metadata, comments, blanks and untimed text are not warned
about, because they are not lyric lines. That keeps the warning meaningful: it
names a line the user expected to see sung.

`parse_elrc(..., warnings=None)` appends:

```python
{"kind": "unmatched-elrc", "count": 3, "line": 4}
```

for a lyric line whose `.elrc` entries could not be aligned. Line headers are
deliberately consumed and never counted, so the warning is a real signal.

## Header inference

`parse_elrc_lines(text)` walks the entries and, for each one, asks whether the
letters of the following entries concatenate exactly to its own letters. If
they do, that entry is the line header and the rest are its words; otherwise
the entry is a standalone line with no word timing.

```
[00:11.560]I got my driver's license last week   <- header
[00:11.560] I                                    <- word
[00:12.440] got                                  <- word
```

This is the same rule `_align_entry_times()` already uses to skip a header
during a merge, so both paths agree on what a header is. The function returns
the same payload shape as `parse_lrc()` (`lyrics`, `meta`, `duration_ms`), and
`webapp.parse_lrc()` only calls it when the `.lrc` produced nothing usable —
a merge into existing lines is always preferred, because the `.lrc` is the
authoritative line text.

## UI: three-line window

```
past     (dimmed, 13px)   ← line just sung
current  (bright, part colour, syllable highlight)
next     (dimmed, 14px)   ← line coming up
```

`lyricWindow(lines, ms)` returns `{past, current, next, litCount}`; `-1` means
"no such line". A pure function keeps the rule testable and means the renderer
does no searching. The rows are rebuilt only when the current index changes;
each frame then toggles `lit` on the syllables between the previous and new
`litCount`, which is O(changed syllables) instead of O(all syllables + a DOM
query) per frame.

Click-to-seek is delegated on `#lyrics`: the clicked line carries
`data-ms`, and the handler seeks only when `state.seekDisabled` is false, so a
paused or MIDI song behaves consistently with the progress slider. The stage
stays `aria-live`-free (lyrics change at syllable rate); the buttons and the
slider remain the accessible route to seeking.

Lyric size is a `data-size` attribute on `#lyrics` with three CSS overrides
(`.lyrics[data-size="…"] .lyric-line`) rather than inline styles, so the
stylesheet stays the single place that defines typography and the existing
"one declaration per selector" test keeps guarding it.

## Alternatives rejected

* **Reject the whole file when a line is malformed.** The shipped behaviour
  for untimed lines is already "skip this line, keep the rest"; failing the
  file was an accident of the regex, not a decision.
* **Normalise timestamps in the UI.** The engine is the single source of truth
  for both CPython and Pyodide; a JS normaliser would be a second parser.
* **Scroll a long lyric list to the active line.** The panel is a slim strip;
  a three-row window is the scroll. A long list would push the CD+G canvas and
  the transport off-screen, which the UX spec forbids.
* **Store lyric size in `localStorage` only.** Settings already round-trip
  through the engine, and the Tauri and browser builds share that store.
