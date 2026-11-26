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

# One timestamp definition, shared by line tags, .elrc entries and enhanced
# word tags: [mm:ss], [mm:ss.xx], [mm:ss:xx] or [mmm:ss.xxx].  Minutes are 1-3
# digits (long compilations), seconds 1-2, the fraction 1-3 digits and optional.
_TIMESTAMP = r"\[(\d{1,3}):(\d{1,2})(?:[.:](\d{1,3}))?\]"
_LINE_RE = re.compile("^" + _TIMESTAMP + "(.*)$")
# Any [key:value] ID tag.  Keys must start with a letter so timestamps
# like [00:12.34] are never mistaken for metadata.
_META_KEY_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_-]*\Z")


def _parse_meta(stripped: str) -> tuple[str, str] | None:
    """Key and value of a ``[key:value]`` tag (None when not one).

    Plain string slicing replaces ``^\\[([a-zA-Z][...]*):([^\\]]*)\\]$``:
    the trailing ``[^\\]]*\\]$`` backtracks on long bracket-less tails.
    """
    if not stripped.startswith("[") or not stripped.endswith("]"):
        return None
    key, sep, value = stripped[1:-1].partition(":")
    if not sep or "]" in value or _META_KEY_RE.match(key) is None:
        return None
    return key.lower(), value.strip()


# Enhanced-LRC word tag: <mm:ss.xx> inside the line text (fraction optional).
_WORD_RE = re.compile(r"<(\d{1,3}):(\d{1,2})(?:[.:](\d{1,3}))?>")
# .elrc word entry: [mm:ss.xx] text (same timestamp shape as a line tag).
# Only the fixed-width timestamp is a regex; the trailing ``\\s*(.+)$``
# backtracked on long whitespace tails, so the text is sliced by hand.
_ELRC_TS_RE = re.compile("^" + _TIMESTAMP)
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


def _fraction_ms(frac: str | None) -> int:
    """'9' -> 900 ms, '22' -> 220 ms, '225' -> 225 ms, None -> 0 ms."""
    if not frac:
        return 0
    if len(frac) == 1:
        return int(frac) * 100
    if len(frac) == 2:
        return int(frac) * 10
    return int(frac)


def _tag_ms(minutes: str, seconds: str, frac: str | None = None) -> int:
    """'12', '00', '50' -> 720050 ms (12:00.50); a missing fraction is 0 ms."""
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


def _collect_line_timestamps(rest: str) -> tuple[list[int], str]:
    """Every leading ``[mm:ss.xx]`` timestamp and the text after them."""
    timestamps: list[int] = []
    while True:
        line_match = _LINE_RE.match(rest)
        if not line_match:
            break
        timestamps.append(_tag_ms(line_match.group(1), line_match.group(2), line_match.group(3)))
        rest = line_match.group(4)
    return timestamps, rest


def _unparsed_warning(stripped: str, file_line: int) -> dict | None:
    """Warning for a line that looks timed but produced no lyric, else None.

    Covers the shapes a broken timestamp takes in the wild (`[00:6x.00]text`,
    `[0x:12]text`) while leaving ordinary untimed text, comments, blank lines
    and bare clear-line markers (`[00:05.00]` with no text) unreported.
    """
    if not stripped.startswith("["):
        return None
    close = stripped.find("]")
    if close == -1:
        return None
    inner = stripped[1:close]
    if ":" not in inner or not any(ch.isdigit() for ch in inner):
        return None
    if not _strip_bracket_tags(stripped[close + 1 :]).strip():
        return None
    return {"kind": "skipped-line", "line": file_line, "text": stripped}


def _parse_timed_entry(stripped: str) -> tuple[list[int], str | None, str] | None:
    """Timestamps, duet part and lyric text of one line (None if unusable)."""
    timestamps, rest = _collect_line_timestamps(stripped)
    if not timestamps:
        # Untimed, blank, malformed and comment lines are ignored.
        return None

    # Optional duet tag after the timestamps: [00:12.00][a]lyric.
    # Consumed before bracket stripping so the tag never reaches text.
    part: str | None = None
    part_match = _PART_RE.match(rest)
    if part_match:
        part = normalize_part(part_match.group(1))
        rest = rest[part_match.end() :]

    lyric_text = _strip_bracket_tags(rest).strip()
    if not lyric_text:
        return None
    return timestamps, part, lyric_text


def _append_word_syllables(
    syllables: list, segments: list, timestamps: list[int], current_line: int, part: str | None
) -> int:
    """Append word-level syllables for every line timestamp; returns the max."""
    line_max = 0
    for line_ms in timestamps:
        for seg_ms, seg_text in segments:
            word = seg_text.strip()
            if not word:
                continue
            ms = seg_ms if seg_ms is not None else line_ms
            syllables.append((ms, word, current_line, part))
            line_max = max(line_max, ms)
    return line_max


def _append_plain_syllables(
    syllables: list, timestamps: list[int], lyric_text: str, current_line: int, part: str | None
) -> int:
    """Append one syllable per line timestamp; returns the max timestamp."""
    line_max = 0
    for ms in timestamps:
        syllables.append((ms, lyric_text, current_line, part))
        line_max = max(line_max, ms)
    return line_max


def _accumulate_syllables(
    syllables: list, timestamps: list[int], lyric_text: str, current_line: int, part: str | None
) -> int:
    """Append one line's syllables; returns the largest timestamp added."""
    # Enhanced LRC: word-level <mm:ss.xx> tags inside the line text.
    segments = _split_word_segments(lyric_text)
    if any(seg_ms is not None for seg_ms, _seg in segments):
        return _append_word_syllables(syllables, segments, timestamps, current_line, part)
    # Simple LRC: one syllable per line timestamp.
    return _append_plain_syllables(syllables, timestamps, lyric_text, current_line, part)


def _consume_meta(stripped: str, meta: dict[str, str]) -> bool:
    """Record a ``[key:value]`` metadata tag; True when the line was one."""
    parsed = _parse_meta(stripped)
    if parsed is None:
        return False
    key, value = parsed
    meta[key] = value
    return True


def _apply_offset(syllables: list, offset_ms: int) -> tuple[list, int]:
    """Shift every timestamp sooner by *offset_ms* (never negative)."""
    if not offset_ms:
        max_ms = max((ms for ms, _text, _line, _part in syllables), default=0)
        return syllables, max_ms
    adjusted = [(max(0, ms - offset_ms), text, line, part) for ms, text, line, part in syllables]
    return adjusted, max(ms for ms, _text, _line, _part in adjusted)


def _resolve_duration(meta: dict[str, str], max_ms: int) -> int:
    """Duration from the ``[length:]`` tag, else the last timestamp."""
    length = meta.get("length")
    if not length:
        return max_ms
    parts = length.split(":")
    if len(parts) != 2 or not parts[0].isdigit():
        return max_ms
    seconds_part = parts[1]
    frac = ""
    if "." in seconds_part:
        seconds_part, frac = seconds_part.split(".", 1)
    if not seconds_part.isdigit() or (frac and not frac.isdigit()):
        return max_ms
    duration_ms = int(parts[0]) * 60_000 + int(seconds_part) * 1000
    if frac:
        duration_ms += _fraction_ms(frac)
    return duration_ms


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
    warnings: list[dict] = []
    max_ms = 0
    line_number = 0

    for file_line, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if _consume_meta(stripped, meta):
            continue

        # A line may carry several leading timestamps: [t1][t2]text means
        # the text occurs at both times (a repeated line).
        entry = _parse_timed_entry(stripped)
        if entry is None:
            # Untimed, blank and comment lines are ignored; a line that does
            # look timed is reported instead of disappearing silently.
            warning = _unparsed_warning(stripped, file_line)
            if warning is not None:
                warnings.append(warning)
            continue
        timestamps, part, lyric_text = entry

        current_line = line_number
        line_number += 1

        max_ms = max(
            max_ms, _accumulate_syllables(syllables, timestamps, lyric_text, current_line, part)
        )

    if not syllables:
        return None

    # [offset:] shifts every timestamp; positive makes lyrics appear
    # sooner (per the LRC spec), so subtract the offset.  Never negative.
    offset_ms = parse_offset(meta)
    adjusted, max_ms = _apply_offset(syllables, offset_ms)

    # [length:] is "mm:ss" or "mm:ss.xx"; fall back to the last timestamp.
    duration_ms = _resolve_duration(meta, max_ms)

    result = {
        "lyrics": [_event(ms, text, line, part) for ms, text, line, part in adjusted],
        "meta": meta,
        "duration_ms": duration_ms,
    }
    if warnings:
        result["warnings"] = warnings
    song_parts = parse_parts(meta)
    if song_parts:
        result["parts"] = song_parts
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
    groups.sort(key=lambda group: group["ms"] if isinstance(group["ms"], int) else 0)
    return groups


def _read_elrc_entries(elrc_text: str, offset_ms: int) -> list[tuple[int, str]]:
    """All ``[mm:ss.xx] word`` entries, shifted by *offset_ms*, by time."""
    entries: list[tuple[int, str]] = []
    for line in str(elrc_text).lstrip("\ufeff").splitlines():
        stripped = line.strip()
        match = _ELRC_TS_RE.match(stripped)
        if not match:
            continue  # metadata, comments, blanks and bare timestamps
        text = stripped[match.end() :].strip()
        if not text:
            continue  # timestamp with no words is not an entry
        ms = _tag_ms(match.group(1), match.group(2), match.group(3))
        if offset_ms:
            ms = max(0, ms - offset_ms)
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


def _token_letter_bounds(tokens: list[str]) -> tuple[list[tuple[int, int]], str]:
    """Per-token letter spans and the line's letters concatenated."""
    bounds = []
    flat = ""
    for token in tokens:
        letters = _normalize_letters(token)
        bounds.append((len(flat), len(flat) + len(letters)))
        flat += letters
    return bounds, flat


def _apply_entry_to_tokens(
    times: list, bounds: list[tuple[int, int]], cursor: int, word: str, ms: int
) -> int:
    """Stamp overlapped tokens with *ms*; returns how many were newly timed."""
    newly_timed = 0
    for idx, (start, end) in enumerate(bounds):
        if times[idx] is None and end > cursor and start < cursor + len(word):
            times[idx] = ms
            newly_timed += 1
    return newly_timed


def _align_entry_times(
    bounds: list[tuple[int, int]], flat: str, entries: list[tuple[int, str]]
) -> tuple[list, int]:
    """Match .elrc entries to token slots, walking a cursor over letters.

    An entry counts only when its letters really are the next letters of
    the line, which skips the line header and stray entries without
    shifting timings onto the wrong word.  Returns ``(times, unmatched)``:
    the per-token times and how many entries found no home in this line.
    """
    times: list[int | None] = [None] * len(bounds)
    cursor = 0
    header_skipped = False
    unmatched = 0
    for ms, text in entries:
        word = _normalize_letters(text)
        if not word:
            continue
        if word == flat and not header_skipped:
            header_skipped = True  # the first whole-line entry is the header
            continue
        if not flat.startswith(word, cursor):
            unmatched += 1  # not the letters the cursor expects: skip it
            continue
        _apply_entry_to_tokens(times, bounds, cursor, word, ms)
        cursor += len(word)
        if cursor >= len(flat):
            break
    return times, unmatched


def _match_line_words(
    group: dict, entries: list[tuple[int, str]]
) -> tuple[list[dict], int, int]:
    """Time *group*'s tokens against the .elrc *entries* assigned to it.

    Returns ``(words, timed, unmatched)``: every token of the line (so no
    word is ever dropped from the display), how many carry an .elrc time,
    and how many entries could not be matched anywhere in the line.
    """
    tokens = group["text"].split()
    if not tokens:
        return [], 0, len(entries)
    bounds, flat = _token_letter_bounds(tokens)
    if not flat:
        return [], 0, len(entries)

    times, unmatched = _align_entry_times(bounds, flat, entries)
    timed = sum(1 for ms in times if ms is not None)
    return _fill_missing_times(group, tokens, times), timed, unmatched


def parse_elrc(
    elrc_text: str,
    lyrics: list[dict],
    offset_ms: int = 0,
    warnings: list | None = None,
) -> list[dict] | None:
    """Merge word-level timings from a companion ``.elrc`` into *lyrics*.

    *lyrics* is the ``lyrics`` list returned by :func:`parse_lrc` and
    *offset_ms* the ``[offset:]`` already applied to it, so .elrc
    timestamps are shifted identically before matching.

    Returns the merged syllable list — lines the .elrc could not time keep
    their original syllables — or None when no word could be matched, in
    which case callers keep the plain line timings.  When *warnings* is a
    list, it receives one ``unmatched-elrc`` entry per line whose .elrc
    timings found no word; nothing is added when the merge itself fails,
    because the file's own timings are then unused.
    """
    if not elrc_text or not lyrics:
        return None
    entries = _read_elrc_entries(elrc_text, offset_ms)
    groups = _line_groups(lyrics)
    if not entries or not groups:
        return None

    assigned = _assign_entries(groups, entries)
    merged: list[dict] = []
    unmatched_warnings: list[dict] = []
    timed_total = 0
    for index, group in enumerate(groups):
        words, timed, unmatched = _match_line_words(group, assigned.get(index, []))
        if timed:
            timed_total += timed
            merged.extend(words)
            if unmatched:
                unmatched_warnings.append(
                    {"kind": "unmatched-elrc", "line": group["line"], "count": unmatched}
                )
        else:
            merged.extend(group["syllables"])
    if not timed_total:
        return None
    if warnings is not None:
        warnings.extend(unmatched_warnings)
    return merged


# ---------------------------------------------------------------------------
# .elrc on its own — the chord-vault dialect
# ---------------------------------------------------------------------------


def _elrc_entries_with_meta(text: str) -> tuple[dict[str, str], list[tuple[int, str]]]:
    """Metadata and timed entries of an ``.elrc``, in file order."""
    meta: dict[str, str] = {}
    entries: list[tuple[int, str]] = []
    for line in str(text).lstrip("\ufeff").splitlines():
        stripped = line.strip()
        if _consume_meta(stripped, meta):
            continue
        match = _ELRC_TS_RE.match(stripped)
        if not match:
            continue
        body = stripped[match.end() :].strip()
        if body:
            entries.append((_tag_ms(match.group(1), match.group(2), match.group(3)), body))
    return meta, entries


def _header_word_span(entries: list[tuple[int, str]], index: int) -> int:
    """How many entries after *index* spell entry *index*'s letters (0 if none).

    The first entry of a chord-vault line is the whole line; the entries
    after it are its words.  A header is real only when those words spell it
    exactly, which is the same rule :func:`_align_entry_times` applies.
    """
    header = _normalize_letters(entries[index][1])
    if not header:
        return 0
    consumed = ""
    cursor = index + 1
    while cursor < len(entries):
        word = _normalize_letters(entries[cursor][1])
        if not word:
            cursor += 1
            continue
        if not header.startswith(consumed + word):
            return 0
        consumed += word
        cursor += 1
        if consumed == header:
            return cursor - index - 1
    return 0


def parse_elrc_lines(text: str) -> dict | None:
    """Read an ``.elrc`` on its own, using its line headers for the text.

    Returns the same payload shape as :func:`parse_lrc`, or None when the
    text describes no lines.  Used when a song's ``.lrc`` carries no timed
    lines but its companion ``.elrc`` does describe them.
    """
    if not text:
        return None
    meta, entries = _elrc_entries_with_meta(text)
    if not entries:
        return None

    offset_ms = parse_offset(meta)
    lyrics: list[dict] = []
    line_number = 0
    index = 0
    while index < len(entries):
        ms, line_text = entries[index]
        span = _header_word_span(entries, index)
        if span:
            # A header: the line's words are the entries after it.  Each word
            # shadows one syllable; a word holding spaces keeps them together.
            for word_ms, word_text in entries[index + 1 : index + 1 + span]:
                lyrics.append(
                    _event(max(0, word_ms - offset_ms), word_text, line_number)
                )
            index += span + 1
        else:
            lyrics.append(_event(max(0, ms - offset_ms), line_text, line_number))
            index += 1
        line_number += 1

    if not lyrics:
        return None
    max_ms = max(event["ms"] for event in lyrics)
    result = {
        "lyrics": lyrics,
        "meta": meta,
        "duration_ms": _resolve_duration(meta, max_ms),
        "inferred": True,
    }
    return result
