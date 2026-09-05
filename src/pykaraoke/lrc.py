"""Pure-Python LRC lyrics parser (Pyodide-compatible).

Parses the LRC timed-lyrics format (also seen with the ``.lcr``
extension): lines of ``[mm:ss.xx]text`` plus metadata tags such as
``[ar:artist]``, ``[ti:title]``, ``[al:album]`` and ``[length:mm:ss]``.

The output uses the same lyric shape as :mod:`pykaraoke.midi` (``ms``,
``text``, ``type``, ``line``) so the web UI can reuse its existing
karaoke-style lyric renderer.
"""

from __future__ import annotations

import re

# [mm:ss.xx] or [mm:ss.xxx] — fraction is hundredths or milliseconds.
_LINE_RE = re.compile(r"^\[(\d{1,2}):(\d{2})\.(\d{2,3})\](.*)$")
_META_RE = re.compile(r"^\[(ar|ti|al|length):([^\]]*)\]$", re.IGNORECASE)

TEXT_LYRIC = 0


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
    """'22' -> 220 ms, '225' -> 225 ms."""
    if len(frac) == 2:
        return int(frac) * 10
    return int(frac)


def parse_lrc(text: str) -> dict | None:
    """Parse LRC *text* into timed lyrics, or None when unusable.

    Returns::

        {
          "lyrics": [{"ms": int, "text": str, "type": 0, "line": int}, ...],
          "meta": {"ar": str, "ti": str, "al": str, "length": str},
          "duration_ms": int,   # from [length:] meta or the last timestamp
        }
    """
    if not text:
        return None

    meta: dict[str, str] = {}
    syllables: list[tuple[int, str, int]] = []  # (ms, text, line)
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
            minutes = int(line_match.group(1))
            seconds = int(line_match.group(2))
            timestamps.append(minutes * 60_000 + seconds * 1000 + _fraction_ms(line_match.group(3)))
            rest = line_match.group(4)

        if not timestamps:
            continue

        lyric_text = _strip_bracket_tags(rest).strip()
        if not lyric_text:
            continue

        current_line = line_number
        line_number += 1
        for ms in timestamps:
            syllables.append((ms, lyric_text, current_line))
            max_ms = max(max_ms, ms)

    if not syllables:
        return None

    # [length:] is "mm:ss" or "mm:ss.xx"; fall back to the last timestamp.
    duration_ms = max_ms
    length = meta.get("length")
    if length:
        parts = length.split(":")
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            duration_ms = int(parts[0]) * 60_000 + int(parts[1]) * 1000

    return {
        "lyrics": [
            {"ms": ms, "text": text, "type": TEXT_LYRIC, "line": line}
            for ms, text, line in syllables
        ],
        "meta": meta,
        "duration_ms": duration_ms,
    }
