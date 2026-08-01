#!/usr/bin/env python3
"""Verify generated .kar files using pykaraoke-ng's own parser."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pykaraoke.players.kar import KaraokeParser

karaoke_dir = os.path.join(
    os.path.dirname(__file__), "..",
    "tests", "fixtures", "ultrastar-deluxe",
    "Creative Commons", "karaoke"
)

files = sorted(f for f in os.listdir(karaoke_dir) if f.endswith('.kar'))
print(f"Verifying {len(files)} .kar files in {karaoke_dir}\n")

ok = 0
err = 0
for f in files:
    path = os.path.join(karaoke_dir, f)
    try:
        parser = KaraokeParser()
        result = parser.parse(path)
        # Check basic structure
        tracks = getattr(result, 'midi_tracks', None) or getattr(result, 'tracks', None) or []
        ok += 1
    except Exception as e:
        err += 1

print(f"\nOK: {ok}, ERR: {err}, Total: {len(files)}")
