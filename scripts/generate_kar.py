#!/usr/bin/env python3
"""Generate .kar (MIDI karaoke) files from chord-vault album data."""

import os
import re
import math
from mido import MidiFile, MidiTrack, MetaMessage, Message, bpm2tempo

# ── Chord mappings ──────────────────────────────────────────────────────────

# Roman numeral → scale degrees for major keys
MAJOR_DEGREES = {
    'I': 0, 'II': 2, 'III': 4, 'IV': 5, 'V': 7, 'VI': 9, 'VII': 11,
    'i': 0, 'ii': 2, 'iii': 4, 'iv': 5, 'v': 7, 'vi': 9, 'vii': 11,
}

# Roman numeral → scale degrees for minor keys (natural minor)
MINOR_DEGREES = {
    'i': 0, 'ii': 2, 'III': 3, 'iv': 5, 'v': 7, 'VI': 8, 'VII': 10,
    'I': 0, 'II': 2, 'iii': 3, 'IV': 5, 'V': 7, 'vi': 8, 'vii': 10,
}

# Root note for each key (MIDI note numbers, C4=60)
KEY_ROOTS = {
    'C': 60, 'C#': 61, 'Db': 61, 'D': 62, 'D#': 63, 'Eb': 63,
    'E': 64, 'F': 65, 'F#': 66, 'Gb': 66, 'G': 67, 'G#': 68,
    'Ab': 68, 'A': 69, 'A#': 70, 'Bb': 70, 'B': 71,
    'Cm': 60, 'C#m': 61, 'Dm': 62, 'D#m': 63, 'Em': 64, 'Fm': 65,
    'F#m': 66, 'Gm': 67, 'G#m': 68, 'Am': 69, 'A#m': 70, 'Bm': 71,
}

def parse_key(key_str):
    """Parse a key string like 'A', 'Dm', 'Bb', 'F#m' into (root_note, is_minor)."""
    key_str = key_str.strip()
    is_minor = key_str.endswith('m') and not key_str.endswith('M')
    root = key_str.replace('m', '')
    root_note = KEY_ROOTS.get(root)
    if root_note is None:
        # Try full key string
        root_note = KEY_ROOTS.get(key_str)
    if root_note is None:
        print(f"  WARNING: Unknown key '{key_str}', defaulting to C")
        root_note = 60
        is_minor = False
    return root_note, is_minor

def roman_to_chord(roman, key_root, is_minor):
    """Convert a Roman numeral like 'I', 'IV', 'vi' to a MIDI root note."""
    roman = roman.strip()
    # Handle chords like 'V7' or 'IVmaj7' - strip extensions
    bare = re.sub(r'[^IViv]+.*', '', roman)
    if not bare:
        bare = roman[0] if roman else 'I'

    degrees = MINOR_DEGREES if is_minor else MAJOR_DEGREES
    semitone = degrees.get(bare)
    if semitone is None:
        print(f"  WARNING: Unknown roman numeral '{bare}', defaulting to I")
        semitone = 0
    return key_root + semitone

def chord_to_notes(root_midi):
    """Return MIDI notes for a simple triad based on root note."""
    major_third = root_midi + 4
    perfect_fifth = root_midi + 7
    # Return root, third, fifth in different octaves for a nice pad
    return [
        root_midi - 12,       # bass
        root_midi,            # root
        major_third,          # third
        perfect_fifth,        # fifth
    ]

# ── Song data ───────────────────────────────────────────────────────────────

# Song definitions extracted from chord-vault albums
SONGS = [
    # Automatic Static
    dict(album="Automatic Static", title="Automatic", key="A", bpm=140,
         progression="A5 G5 D5 A5", capo=0, is_minor=False,
         lyrics_dir="01-automatic"),
    dict(album="Automatic Static", title="Concrete and Canvas", key="E", bpm=145,
         progression="E5 A5 B5", capo=0, is_minor=False,
         lyrics_dir="02-concrete-and-canvas"),

    # Between Tides
    dict(album="Between Tides", title="Breaking the Surface", key="Dm", bpm=92,
         progression="Dm C Bb F C", capo=0, is_minor=True,
         lyrics_dir="01-breaking-the-surface"),
    dict(album="Between Tides", title="Porch Light Rebellion", key="A", bpm=120,
         progression="A D E A", capo=0, is_minor=False,
         lyrics_dir="07-porch-light-rebellion"),

    # Heavy Weather
    dict(album="Heavy Weather", title="Burning the Blueprint", key="E", bpm=140,
         progression="E5 A5 B5 E5", capo=0, is_minor=False,
         lyrics_dir="01-burning-the-blueprint"),
    dict(album="Heavy Weather", title="Waking Slow", key="Db", bpm=76,
         progression="A D A E F#m D A E", capo=4, is_minor=False,
         lyrics_dir="12-waking-slow"),

    # Late Blooming
    dict(album="Late Blooming", title="Late Blooming", key="A", bpm=98,
         progression="A D E D F#m D E A", capo=0, is_minor=False,
         lyrics_dir="11-late-blooming"),
    dict(album="Late Blooming", title="Habit by Habit", key="G", bpm=110,
         progression="G C D Em C G D G", capo=0, is_minor=False,
         lyrics_dir="07-habit-by-habit"),

    # Quiet Evidence
    dict(album="Quiet Evidence", title="Possibility Survives", key="D", bpm=98,
         progression="D G D A G A D G D A Em G D", capo=0, is_minor=False,
         lyrics_dir="12-possibility-survives"),
    dict(album="Quiet Evidence", title="Maintenance", key="G", bpm=96,
         progression="G C D G C G D G", capo=0, is_minor=False,
         lyrics_dir="02-maintenance"),

    # Secondhand Static
    dict(album="Secondhand Static", title="High Volt Blitz", key="F", bpm=165,
         progression="F Am Dm Gm C F F7 Bb Gm7 D7", capo=0, is_minor=False,
         lyrics_dir="01-high-volt-blitz"),
    dict(album="Secondhand Static", title="What Remains Is Love", key="A", bpm=100,
         progression="A D E F#m D E A", capo=0, is_minor=False,
         lyrics_dir="09-what-remains-is-love"),
]

# ── Lyric loading ───────────────────────────────────────────────────────────

CHORD_VAULT = r"C:\Users\toman\repos\music\chord-vault\album"

def load_lyrics(album, lyrics_dir):
    """Load lyrics from a chord-vault lyrics.md file."""
    base = os.path.join(CHORD_VAULT, album, "songs", lyrics_dir)
    candidates = []

    def find_lyric_file(directory, filename):
        for root, dirs, files in os.walk(directory):
            if filename in files:
                return os.path.join(root, filename)
        return None

    # Try lyrics.md first
    result = find_lyric_file(base, "lyrics.md")
    if result:
        candidates.append(result)
    else:
        # Try lyrics.txt
        result = find_lyric_file(base, "lyrics.txt")
        if result:
            candidates.append(result)
        else:
            # Try parent with fuzzy match
            parent = os.path.dirname(base.rstrip("\\/"))
            for root, dirs, files in os.walk(parent):
                if "lyrics.md" in files or "lyrics.txt" in files:
                    lf = "lyrics.md" if "lyrics.md" in files else "lyrics.txt"
                    if lyrics_dir.replace("-", "").replace(" ", "") in os.path.basename(root):
                        candidates.append(os.path.join(root, lf))

    if not candidates:
        print(f"  WARNING: Lyrics not found in {base}")
        return []

    path = candidates[0]
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = []
    for line in content.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("["):
            continue
        if re.match(r'^[A-G][#b]?\d?\s', line):
            continue
        if line.startswith(("Key:", "Tempo:", "Time Signature:", "Feel:",
                           "Capo:", "Beats Per Chord:", "Funk groove:",
                           "Suggested", "Tuning:")):
            continue
        if line.startswith("(") and line.endswith(")"):
            continue
        # Sanitize unicode characters for MIDI latin-1
        line = line.replace('\u2014', '--').replace('\u2013', '-')
        line = line.replace('\u2018', "'").replace('\u2019', "'")
        line = line.replace('\u201c', '"').replace('\u201d', '"')
        line = line.replace('\u2026', '...')
        # Only include actual lyric lines (skip chord-only lines)
        if re.match(r'^[\sA-G#bmM\d\(\)/,]+\s*$', line) and len(line) > 3:
            tokens = line.split()
            chord_count = sum(1 for t in tokens if re.match(r'^[A-G][#b]?\d*[mM]?\d*[/]?\w*$', t))
            if chord_count == len(tokens) and chord_count > 1:
                continue
        lines.append(line)

    return lines

# ── Generation ──────────────────────────────────────────────────────────────

def parse_progression(prog_str, key_root, is_minor):
    """Parse a space-separated progression into MIDI note lists."""
    chords = prog_str.split()
    result = []
    for c in chords:
        # Handle chords with extensions like A5, G5, D5
        bare = c.rstrip("0123456789mM#b")
        if not bare:
            bare = c[0]
        roman = None
        # Try to interpret as roman numeral
        if bare in MAJOR_DEGREES or bare in MINOR_DEGREES:
            roman = bare
        if roman:
            root = roman_to_chord(roman, key_root, is_minor)
        else:
            # Try direct chord name
            root_note, _ = parse_key(bare)
            if root_note:
                root = root_note
            else:
                print(f"  WARNING: Cannot parse chord '{c}', skipping")
                continue
        # Determine if major or minor based on chord name
        is_minor_chord = 'm' in c and not c.startswith('M')
        if is_minor_chord:
            third = root + 3
        else:
            third = root + 4
        fifth = root + 7
        result.append([root - 12, root, third, fifth])
    return result

def generate_kar(song, output_dir):
    """Generate a .kar file for a single song."""
    album = song["album"]
    title = song["title"]
    key_str = song["key"]
    bpm = song["bpm"]
    progression_str = song["progression"]
    capo = song.get("capo", 0)
    lyrics_dir = song["lyrics_dir"]

    # Parse key
    key_root, is_minor = parse_key(key_str)
    if capo:
        key_root += capo

    print(f"\n{'='*60}")
    print(f"Generating: {title}")
    print(f"  Album: {album}, Key: {key_str}, BPM: {bpm}")
    print(f"  Progression: {progression_str}")

    # Parse progression
    chord_notes = parse_progression(progression_str, key_root, is_minor)
    if not chord_notes:
        print(f"  ERROR: No valid chords in progression")
        return

    # Load lyrics
    lyric_lines = load_lyrics(album, lyrics_dir)
    if not lyric_lines:
        print(f"  WARNING: No lyrics found, using placeholder")
        lyric_lines = ["[No lyrics found for " + title + "]"]

    print(f"  Lyrics lines: {len(lyric_lines)}")

    # Create MIDI file
    midi = MidiFile(type=1)
    midi.ticks_per_beat = 480

    # ── Track 0: Tempo map ──
    track0 = MidiTrack()
    midi.tracks.append(track0)
    track0.append(MetaMessage('track_name', name='Tempo Map', time=0))
    track0.append(MetaMessage('time_signature',
                               numerator=4, denominator=2, clocks_per_click=24,
                               notated_32nd_notes_per_beat=8, time=0))
    track0.append(MetaMessage('set_tempo', tempo=bpm2tempo(bpm), time=0))
    # Use proper MIDI key format (e.g., 'Dm', 'A', 'F#m')
    midi_key = key_str
    track0.append(MetaMessage('key_signature', key=midi_key, time=0))

    # ── Track 1: Karaoke (chords + lyrics) ──
    track1 = MidiTrack()
    midi.tracks.append(track1)
    track1.append(MetaMessage('track_name', name='Karaoke', time=0))
    track1.append(Message('program_change', program=4, time=0))  # Electric Piano 1

    # Build accompaniment patterns
    beats_per_chord = 4  # 4 beats per chord change
    chord_duration_ticks = beats_per_chord * midi.ticks_per_beat
    ticks_per_beat = midi.ticks_per_beat

    # Place lyrics on the beat grid
    # Each beat gets one syllable, but we distribute lyrics across the chord grid
    total_syllables = 0
    for line in lyric_lines:
        words = line.split()
        for word in words:
            word = word.strip(".,!?;:'\"")
            if word:
                # Count syllables (rough estimate)
                syl_count = max(1, len(re.findall(r'[aeiouy]+', word, re.I)))
                total_syllables += syl_count

    # Calculate timing: distribute syllables across the song duration
    # Assume ~90 seconds average duration at the given BPM
    # At BPM X, 90 seconds = 90 * X / 60 = 1.5 * X beats
    available_beats = max(total_syllables * 2, int(1.5 * bpm))
    beats_per_syllable = available_beats / max(total_syllables, 1)

    current_beat = 0
    chord_cycle = chord_notes
    chord_idx = 0

    # Track active notes so we can turn them off properly
    active_notes = []

    for line_idx, line in enumerate(lyric_lines):
        words = line.split()
        if not words:
            current_beat += 2 * beats_per_syllable
            continue

        for word_idx, word_str in enumerate(words):
            word = word_str.strip(".,!?;:'\"")
            if not word:
                continue

            # Simple syllable split
            syllables = re.findall(r'[^aeiouy]*[aeiouy]+[^aeiouy]*|[^aeiouy]+',
                                   word, re.I)
            if not syllables:
                syllables = [word]

            for syl_idx, syl in enumerate(syllables):
                # Get chord for this syllable
                chord = chord_cycle[chord_idx % len(chord_cycle)]

                # Calculate ticks for this syllable
                syl_ticks = int(beats_per_syllable * ticks_per_beat)
                if syl_ticks < 60:
                    syl_ticks = 60

                # Turn off previous chord notes
                if active_notes:
                    for note in active_notes:
                        track1.append(Message('note_off', note=note, velocity=64,
                                              time=0))
                    active_notes = []

                # Turn on new chord notes
                first = True
                for note in chord:
                    time = 0 if not first else int(current_beat * ticks_per_beat)
                    track1.append(Message('note_on', note=note, velocity=65,
                                          time=time))
                    active_notes.append(note)
                    first = False

                # Syllable prefix (space between words in lyrics display)
                prefix = ""
                if syl_idx == 0 and word_idx > 0:
                    prefix = " "
                # Handle contractions
                if syl_idx == 0 and word_str.startswith("'"):
                    prefix = ""

                # Sanitize syllable text for MIDI (latin-1)
                syl_clean = syl.encode('ascii', errors='replace').decode('ascii')
                syl_text = prefix + syl_clean

                # Place lyric event (must be text, not empty)
                if syl_text.strip():
                    track1.append(MetaMessage('lyrics', text=syl_text,
                                              time=0))

                current_beat += beats_per_syllable
                chord_idx += 1

            # Small gap between words
            syllable_ticks = int(beats_per_syllable * ticks_per_beat)
            current_beat += 0.5

        # Line break - slight pause
        current_beat += 1.5

    # Turn off final notes
    if active_notes:
        for note in active_notes:
            track1.append(Message('note_off', note=note, velocity=64,
                                  time=int(beats_per_syllable * 2 * ticks_per_beat)))
        active_notes = []

    # End of track
    track1.append(MetaMessage('end_of_track', time=0))

    # Write file
    safe_title = re.sub(r'[^\w\s-]', '', title).strip()
    output_path = os.path.join(output_dir, f"{safe_title}.kar")
    midi.save(output_path)
    print(f"  -> {output_path}")
    return output_path

# ── Main ────────────────────────────────────────────────────────────────────

def main():
    output_dir = os.path.join(
        r"C:\Users\toman\repos\music\pykaraoke-ng",
        "tests", "fixtures", "ultrastar-deluxe",
        "Creative Commons", "karaoke"
    )
    os.makedirs(output_dir, exist_ok=True)
    print(f"Output directory: {output_dir}")
    print(f"Generating {len(SONGS)} karaoke files...")

    for song in SONGS:
        try:
            generate_kar(song, output_dir)
        except Exception as e:
            print(f"  ERROR generating {song['title']}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\nDone! Generated {len(SONGS)} .kar files in {output_dir}")

if __name__ == "__main__":
    main()
