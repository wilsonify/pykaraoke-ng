"""Pure-Python LRC lyrics parser (Pyodide-compatible).

Parses the LRC timed-lyrics format (also seen with the ``.lcr``
extension): lines of ``[mm:ss.xx]text`` plus metadata tags such as
``[ar:artist]``, ``[ti:title]``, ``[al:album]``, ``[by:creator]``,
``[length:mm:ss]`` and ``[offset:±ms]``.

Also supports *extended/enhanced LRC* (A2 extension): word-level
timestamps inside a line, e.g. ``[00:12.00]Word <00:12.50> by <00:12.80>
word`` — text before the first tag takes the line time, each tag times
the word that follows it.

Word timing can also arrive in a *companion* ``.elrc`` file next to the
``.lrc``: entries of ``[mm:ss.xx] word`` that must be aligned with the
lines of the LRC (see :func:`parse_elrc`).

Duet songs tag each lyric line with the singer/part that performs it,
immediately after the timestamps: ``[00:12.00][a]first line``,
``[00:16.00][b]answer``, ``[00:20.00][ab]shared line``.  The ids are
generic (never gendered): ``a`` and ``b`` for the two singers, ``ab``
for a line they sing together (``ba`` is normalised to ``ab``).  Lines
without a tag are solo/untagged.  The song may optionally name the two
singers with ``[pa:Name]``/``[pb:Name]`` metadata.

Timestamps accept ``[m:ss.xx]``/``[mm:ss.x]`` (1-2 digit minutes and
seconds, 1-3 digit fraction).  ``[offset:]`` is a global millisecond
adjustment applied to every timestamp: per the LRC spec a positive value
makes lyrics appear *sooner*, so ``effective_ms = ms - offset`` (clamped
at 0).

The output uses the same lyric shape as :mod:`pykaraoke.midi` (``ms``,
``text``, ``type``, ``line``) so the web UI can reuse its existing
karaoke-style lyric renderer (which highlights per-syllable).
"""

from __future__ import annotations

import re

# [mm:ss.xx] or [mm:ss.xxx] — minutes/seconds 1-2 digits, fraction 1-3.
_LINE_RE = re.compile(r"^\[(\d{1,2}):(\d{1,2})\.(\d{1,3})\](.*)$")
# Any [key:value] ID tag.  Keys must start with a letter so timestamps
# like [00:12.34] are never mistaken for metadata.
_META_RE = re.compile(r"^\[([a-zA-Z][a-zA-Z0-9_-]*):([^\]]*)\]$")
# Enhanced-LRC word tag: <mm:ss.xx> inside the line text.
_WORD_RE = re.compile(r"<(\d{1,2}):(\d{1,2})\.(\d{1,3})>")
# .elrc word entry: [mm:ss.xx] text (same timestamp shape as a line tag).
_ELRC_RE = re.compile(r"^\[(\d{1,2}):(\d{1,2})\.(\d{1,3})\]\s*(.+)$")
# Duet part tag sitting right after the timestamps: [00:12.00][a]line.
# Longer alternatives first so [ab]/[ba] are never read as a bare part.
_PART_RE = re.compile(r"^\[(ab|ba|a|b)\]", re.IGNORECASE)

TEXT_LYRIC = 0

# Generic singer/part ids (never gendered); "ab" is a shared line.
PART_IDS = ("a", "b", "ab")


def normalize_part(tag: str) -> str | None:
    """Map a raw part tag to a :data:`PART_IDS` id, else None.

    ``"ba"`` is the mirror of ``"ab"``, so both normalise to ``"ab"``.
    """
    part = str(tag or "").strip().lower()
    if part in ("a", "b"):
        return part
    if part in ("ab", "ba"):
        return "ab"
    return None


def parse_parts(meta: dict[str, str]) -> dict[str, str] | None:
    """Song-level singer names from ``[pa:Name]``/``[pb:Name]`` metadata.

    Returns ``{"a": name, "b": name}`` with only the names actually
    defined, or None when the song names no singers.
    """
    parts = {}
    for tag, part in (("pa", "a"), ("pb", "b")):
        name = str(meta.get(tag, "") or "").strip()
        if name:
            parts[part] = name
    return parts or None


def _event(ms: int, text: str, line: int, part: str | None = None) -> dict:
    """One lyric event in the UI's shape, carrying *part* when tagged."""
    event = {"ms": ms, "text": text, "type": TEXT_LYRIC, "line": line}
    if part:
        event["part"] = part
    return event


def _strip_bracket_tags(text: str) -> str:
    """Replace ``[...]`` groups (extra timestamps) with a single space."""
    out = []
    i = 0
    while i < len(text):
        if text[i] == "[":
            close = text.find("]", i + 1)
            if close == -1:
                out.append(text[i:])
                break
            out.append(" ")
            i = close + 1
            while i < len(text) and text[i].isspace():
                i += 1
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def _fraction_ms(frac: str) -> int:
    """'9' -> 900 ms, '22' -> 220 ms, '225' -> 225 ms."""
    if len(frac) == 1:
        return int(frac) * 100
    if len(frac) == 2:
        return int(frac) * 10
    return int(frac)


def _tag_ms(minutes: str, seconds: str, frac: str) -> int:
    """'12', '00', '50' -> 720050 ms (12:00.50)."""
    return int(minutes) * 60_000 + int(seconds) * 1000 + _fraction_ms(frac)


def _split_word_segments(text: str) -> list[tuple[int | None, str]]:
    """Split *text* on ``<mm:ss.xx>`` tags into (ms, segment) pairs.

    ``ms`` is None for the segment before the first tag (it inherits the
    line time); each tag times the text that follows it.
    """
    segments: list[tuple[int | None, str]] = []
    current_ms: int | None = None
    buffer: list[str] = []
    pos = 0
    for match in _WORD_RE.finditer(text):
        if text[pos : match.start()]:
            buffer.append(text[pos : match.start()])
        pos = match.end()
        if buffer:
            segments.append((current_ms, "".join(buffer)))
            buffer = []
        current_ms = _tag_ms(match.group(1), match.group(2), match.group(3))
    if text[pos:]:
        buffer.append(text[pos:])
    if buffer:
        segments.append((current_ms, "".join(buffer)))
    return segments


def parse_offset(meta: dict[str, str]) -> int:
    """Millisecond offset from ``[offset:±ms]``; malformed values are 0."""
    raw = meta.get("offset", "")
    try:
        return int(raw.strip())
    except (TypeError, ValueError):
        return 0


def parse_lrc(text: str) -> dict | None:
    """Parse LRC *text* into timed lyrics, or None when unusable.

    Returns::

        {
          "lyrics": [{"ms": int, "text": str, "type": 0, "line": int,
                      "part": "a"|"b"|"ab"}, ...],
          "meta": {"ar": str, "ti": str, "al": str, "length": str, ...},
          "duration_ms": int,   # from [length:] meta or the last timestamp
          "parts": {"a": str, "b": str},   # only when [pa:]/[pb:] given
        }

    ``part`` is present only on tagged duet lines and ``parts`` only when
    the song names its singers, so solo songs keep their exact payload.

    Timestamps are sorted deterministically: lines in file order, words
    within a line in file order (the UI sorts per line for rendering).
    """
    if not text:
        return None

    # Drop a UTF-8 byte-order mark if present.
    text = text.lstrip("\ufeff")

    meta: dict[str, str] = {}
    syllables: list[tuple[int, str, int, str | None]] = []  # (ms, text, line, part)
    max_ms = 0
    line_number = 0

    for line in text.splitlines():
        stripped = line.strip()
        meta_match = _META_RE.match(stripped)
        if meta_match:
            meta[meta_match.group(1).lower()] = meta_match.group(2).strip()
            continue

        # Collect every leading [mm:ss.xx] timestamp: [t1][t2]text means
        # the text occurs at both times (a repeated line).
        timestamps: list[int] = []
        rest = stripped
        while True:
            line_match = _LINE_RE.match(rest)
            if not line_match:
                break
            timestamps.append(
                _tag_ms(line_match.group(1), line_match.group(2), line_match.group(3))
            )
            rest = line_match.group(4)

        if not timestamps:
            # Untimed, blank, malformed and comment lines are ignored.
            continue

        # Optional duet tag after the timestamps: [00:12.00][a]lyric.
        # Consumed before bracket stripping so the tag never reaches text.
        part: str | None = None
        part_match = _PART_RE.match(rest)
        if part_match:
            part = normalize_part(part_match.group(1))
            rest = rest[part_match.end() :]

        lyric_text = _strip_bracket_tags(rest).strip()
        if not lyric_text:
            continue

        current_line = line_number
        line_number += 1

        # Enhanced LRC: word-level <mm:ss.xx> tags inside the line text.
        segments = _split_word_segments(lyric_text)
        if any(seg_ms is not None for seg_ms, _seg in segments):
            for line_ms in timestamps:
                for seg_ms, seg_text in segments:
                    text = seg_text.strip()
                    if not text:
                        continue
                    ms = seg_ms if seg_ms is not None else line_ms
                    syllables.append((ms, text, current_line, part))
                    max_ms = max(max_ms, ms)
        else:
            # Simple LRC: one syllable per line timestamp.
            for ms in timestamps:
                syllables.append((ms, lyric_text, current_line, part))
                max_ms = max(max_ms, ms)

    if not syllables:
        return None

    # [offset:] shifts every timestamp; positive makes lyrics appear
    # sooner (per the LRC spec), so subtract the offset.  Never negative.
    offset_ms = parse_offset(meta)
    adjusted = syllables
    if offset_ms:
        adjusted = [
            (max(0, ms - offset_ms), text, line, part) for ms, text, line, part in syllables
        ]
        max_ms = max(ms for ms, _text, _line, _part in adjusted)

    # [length:] is "mm:ss" or "mm:ss.xx"; fall back to the last timestamp.
    duration_ms = max_ms
    length = meta.get("length")
    if length:
        parts = length.split(":")
        if len(parts) == 2 and parts[0].isdigit():
            seconds_part = parts[1]
            frac = ""
            if "." in seconds_part:
                seconds_part, frac = seconds_part.split(".", 1)
            if seconds_part.isdigit() and (not frac or frac.isdigit()):
                duration_ms = int(parts[0]) * 60_000 + int(seconds_part) * 1000
                if frac:
                    duration_ms += _fraction_ms(frac)

    result = {
        "lyrics": [_event(ms, text, line, part) for ms, text, line, part in adjusted],
        "meta": meta,
        "duration_ms": duration_ms,
    }
    parts = parse_parts(meta)
    if parts:
        result["parts"] = parts
    return result


# ---------------------------------------------------------------------------
# .elrc — companion file with word-level timing
# ---------------------------------------------------------------------------


def _normalize_letters(text: str) -> str:
    """Lowercase *text* keeping only alphanumerics (unicode-aware).

    Matching on letters alone makes punctuation, spacing and case
    differences between the ``.lrc`` and the ``.elrc`` irrelevant.
    """
    return "".join(ch.lower() for ch in text if ch.isalnum())


def _line_groups(lyrics: list[dict]) -> list[dict]:
    """Group *lyrics* into display lines ordered by their start time.

    Each group is ``{"line", "ms", "text", "part", "syllables"}`` where
    *text* is the line rebuilt from its own syllables (a line stamped at
    several times collapses to one copy, so its letters are not counted
    twice) and *part* is the duet part tag shared by its syllables (or
    None for a solo line).
    """
    order: list[int] = []
    by_line: dict[int, list[dict]] = {}
    for syllable in lyrics:
        key = int(syllable.get("line") or 0)
        if key not in by_line:
            by_line[key] = []
            order.append(key)
        by_line[key].append(syllable)

    groups = []
    for key in order:
        syllables = sorted(by_line[key], key=lambda s: int(s.get("ms") or 0))
        texts = dict.fromkeys(str(s.get("text") or "") for s in syllables)
        part = next((s.get("part") for s in syllables if s.get("part")), None)
        groups.append(
            {
                "line": key,
                "ms": int(syllables[0].get("ms") or 0),
                "text": " ".join(t for t in texts if t),
                "part": part,
                "syllables": syllables,
            }
        )
    groups.sort(key=lambda group: group["ms"])
    return groups


def _read_elrc_entries(elrc_text: str, offset_ms: int) -> list[tuple[int, str]]:
    """All ``[mm:ss.xx] word`` entries, shifted by *offset_ms*, by time."""
    entries: list[tuple[int, str]] = []
    for line in str(elrc_text).lstrip("\ufeff").splitlines():
        match = _ELRC_RE.match(line.strip())
        if not match:
            continue  # metadata, comments, blanks and bare timestamps
        ms = _tag_ms(match.group(1), match.group(2), match.group(3))
        if offset_ms:
            ms = max(0, ms - offset_ms)
        text = match.group(4).strip()
        if text:
            entries.append((ms, text))
    entries.sort(key=lambda entry: entry[0])
    return entries


def _assign_entries(groups: list[dict], entries: list[tuple[int, str]]) -> dict:
    """Bucket *entries* under the line whose start time precedes them."""
    assigned: dict[int, list[tuple[int, str]]] = {}
    index = 0
    for ms, text in entries:
        while index < len(groups) - 1 and groups[index + 1]["ms"] <= ms:
            index += 1
        assigned.setdefault(index, []).append((ms, text))
    return assigned


def _fill_missing_times(group: dict, tokens: list[str], times: list) -> list[dict]:
    """Every token as a syllable; unmatched ones inherit a neighbour's time.

    Times are forced non-decreasing so the renderer's "lit so far" walk
    never stops early on a word stamped earlier than its predecessor.
    The line's duet part tag is carried onto every rebuilt syllable.
    """
    words = []
    previous = int(group["ms"])
    for token, ms in zip(tokens, times, strict=False):
        current = previous if ms is None else max(int(ms), previous)
        words.append(_event(current, token, group["line"], group.get("part")))
        previous = current
    return words


def _match_line_words(group: dict, entries: list[tuple[int, str]]) -> tuple[list[dict], int]:
    """Time *group*'s tokens against the .elrc *entries* assigned to it.

    Walks a cursor over the line's letters: an entry counts only when its
    letters really are the next letters of the line, which skips the line
    header and stray entries without shifting timings onto the wrong word.

    Returns ``(words, timed)``: every token of the line (so no word is
    ever dropped from the display) and how many carry an .elrc time.
    """
    tokens = group["text"].split()
    if not tokens:
        return [], 0
    bounds = []
    flat = ""
    for token in tokens:
        letters = _normalize_letters(token)
        bounds.append((len(flat), len(flat) + len(letters)))
        flat += letters
    if not flat:
        return [], 0

    times: list[int | None] = [None] * len(tokens)
    cursor = 0
    header_skipped = False
    timed = 0
    for ms, text in entries:
        word = _normalize_letters(text)
        if not word:
            continue
        if word == flat and not header_skipped:
            header_skipped = True  # the first whole-line entry is the header
            continue
        if not flat.startswith(word, cursor):
            continue  # not the letters the cursor expects: skip, don't shift
        for idx, (start, end) in enumerate(bounds):
            if times[idx] is None and end > cursor and start < cursor + len(word):
                times[idx] = ms
                timed += 1
        cursor += len(word)
        if cursor >= len(flat):
            break

    return _fill_missing_times(group, tokens, times), timed


def parse_elrc(elrc_text: str, lyrics: list[dict], offset_ms: int = 0) -> list[dict] | None:
    """Merge word-level timings from a companion ``.elrc`` into *lyrics*.

    *lyrics* is the ``lyrics`` list returned by :func:`parse_lrc` and
    *offset_ms* the ``[offset:]`` already applied to it, so .elrc
    timestamps are shifted identically before matching.

    Returns the merged syllable list — lines the .elrc could not time keep
    their original syllables — or None when no word could be matched, in
    which case callers keep the plain line timings.
    """
    if not elrc_text or not lyrics:
        return None
    entries = _read_elrc_entries(elrc_text, offset_ms)
    groups = _line_groups(lyrics)
    if not entries or not groups:
        return None

    assigned = _assign_entries(groups, entries)
    merged: list[dict] = []
    timed_total = 0
    for index, group in enumerate(groups):
        words, timed = _match_line_words(group, assigned.get(index, []))
        if timed:
            timed_total += timed
            merged.extend(words)
        else:
            merged.extend(group["syllables"])
    return merged if timed_total else None
