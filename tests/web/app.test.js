import { describe, expect, it } from 'vitest';

import { loadApp } from './load-app.mjs';

const {
  buildLyricLines,
  CDG_HEIGHT,
  CDG_WIDTH,
  companionBaseName,
  companionMember,
  computeNoteTimeline,
  debounce,
  ELRC_EXT,
  escapeHtml,
  findSyllableAt,
  formatTime,
  highlightState,
  noteToFrequency,
  PART_IDS,
  partClass,
  partLabel,
  SongQueue,
  songLabel,
  writeTileRgba,
  ZOOM_SCALES,
} = await loadApp();

describe('formatTime', () => {
  it('formats minutes and seconds', () => {
    expect(formatTime(0)).toBe('0:00');
    expect(formatTime(5000)).toBe('0:05');
    expect(formatTime(125000)).toBe('2:05');
    expect(formatTime(60000 * 9 + 59999)).toBe('9:59');
  });

  it('clamps negative input', () => {
    expect(formatTime(-100)).toBe('0:00');
  });
});

describe('escapeHtml', () => {
  it('escapes dangerous characters', () => {
    expect(escapeHtml('<b>&"\'')).toBe('&lt;b&gt;&amp;&quot;&#39;');
  });
});

describe('songLabel', () => {
  it('uses parsed title and artist', () => {
    expect(songLabel({ title: 'Rhapsody', artist: 'Queen', filename: 'q.cdg' })).toBe('Rhapsody — Queen');
  });

  it('falls back to the filename stem', () => {
    expect(songLabel({ title: '', artist: '', filename: 'Some Song.kar' })).toBe('Some Song');
  });
});

describe('companion files (.elrc)', () => {
  it('derives the loose-file companion key from the filename', () => {
    expect(companionBaseName({ filename: 'Song.lrc' }, ELRC_EXT)).toBe('song.elrc');
    expect(companionBaseName({ filename: 'Artist - Song.lcr' }, ELRC_EXT)).toBe(
      'artist - song.elrc',
    );
    expect(companionBaseName({ filename: 'No Extension' }, ELRC_EXT)).toBe(
      'no extension.elrc',
    );
  });

  it('returns null when there is no filename', () => {
    expect(companionBaseName({ filename: '' }, ELRC_EXT)).toBeNull();
    expect(companionBaseName(null, ELRC_EXT)).toBeNull();
  });

  it('derives the zip member companion name', () => {
    const song = { zip_name: 'pack.zip', id: 'pack.zip!Artist/Song.lrc', filename: 'Song.lrc' };
    expect(companionMember(song, ELRC_EXT)).toBe('Artist/Song.elrc');
    expect(companionMember({ zip_name: 'pack.zip', id: 'pack.zip!' }, ELRC_EXT)).toBeNull();
  });

  it('is null for songs that are not inside a zip', () => {
    expect(companionMember({ id: 'Folder/Song.lrc', filename: 'Song.lrc' }, ELRC_EXT)).toBeNull();
    expect(companionMember(undefined, ELRC_EXT)).toBeNull();
  });
});

describe('SongQueue', () => {
  it('pushes, removes and clears', () => {
    const q = new SongQueue([{ id: 'a' }, { id: 'b' }, { id: 'c' }]);
    expect(q.length).toBe(3);
    expect(q.removeAt(1).id).toBe('b');
    expect(q.length).toBe(2);
    q.clear();
    expect(q.length).toBe(0);
  });

  it('moves items and guards bounds', () => {
    const q = new SongQueue([{ id: 'a' }, { id: 'b' }, { id: 'c' }]);
    q.move(0, 2);
    expect(q.items.map((s) => s.id)).toEqual(['b', 'c', 'a']);
    q.move(2, 5); // no-op, out of bounds
    expect(q.items.map((s) => s.id)).toEqual(['b', 'c', 'a']);
    q.move(0, 0); // no-op
    expect(q.length).toBe(3);
  });

  it('shifts the next song', () => {
    const q = new SongQueue([{ id: 'a' }, { id: 'b' }]);
    expect(q.next().id).toBe('a');
    expect(q.next().id).toBe('b');
    expect(q.next()).toBeNull();
  });
});

describe('debounce', () => {
  it('fires once after the wait window', async () => {
    let calls = 0;
    const fn = debounce(() => calls++, 30);
    fn();
    fn();
    fn();
    await new Promise((r) => setTimeout(r, 60));
    expect(calls).toBe(1);
  });
});

describe('buildLyricLines', () => {
  it('groups sung syllables by line and sorts by time', () => {
    const lines = buildLyricLines([
      { ms: 0, text: 'Hel', type: 0, line: 1 },
      { ms: 300, text: 'lo', type: 0, line: 1 },
      { ms: 200, text: 'Some', type: 0, line: 0 },
      { ms: 50, text: '@TTitle', type: 2, line: 0 },
    ]);
    expect(lines).toHaveLength(2);
    // Lines are ordered by the time of their first syllable.
    expect(lines[0].line).toBe(1);
    expect(lines[0].syllables.map((s) => s.text)).toEqual(['Hel', 'lo']);
    expect(lines[1].line).toBe(0);
    expect(lines[1].syllables.map((s) => s.text)).toEqual(['Some']);
  });

  it('sorts out-of-order word timestamps within a line', () => {
    // Enhanced-LRC word times in file order: a, c, b.
    const lines = buildLyricLines([
      { ms: 12000, text: 'c', type: 0, line: 0 },
      { ms: 10000, text: 'a', type: 0, line: 0 },
      { ms: 11000, text: 'b', type: 0, line: 0 },
    ]);
    expect(lines[0].syllables.map((s) => s.text)).toEqual(['a', 'b', 'c']);
    expect(lines[0].syllables.map((s) => s.ms)).toEqual([10000, 11000, 12000]);
  });

  it('handles empty input', () => {
    expect(buildLyricLines([])).toEqual([]);
    expect(buildLyricLines(null)).toEqual([]);
  });

  it('carries a duet part onto each grouped line', () => {
    const lines = buildLyricLines([
      { ms: 0, text: 'Hel', type: 0, line: 0, part: 'a' },
      { ms: 100, text: 'lo', type: 0, line: 0, part: 'a' },
      { ms: 2000, text: 'Yes', type: 0, line: 1, part: 'b' },
      { ms: 4000, text: 'Us', type: 0, line: 2, part: 'ab' },
      { ms: 6000, text: 'Solo', type: 0, line: 3 },
    ]);
    expect(lines.map((l) => l.part)).toEqual(['a', 'b', 'ab', null]);
    expect(lines[0].syllables.map((s) => s.text)).toEqual(['Hel', 'lo']);
  });

  it('treats unknown and missing parts as solo', () => {
    const unknown = buildLyricLines([{ ms: 0, text: 'x', type: 0, line: 0, part: 'zzz' }]);
    expect(unknown[0].part).toBeNull();
    const solo = buildLyricLines([{ ms: 0, text: 'x', type: 0, line: 0 }]);
    expect(solo[0].part).toBeNull();
  });
});

describe('partClass', () => {
  it('maps the generic part ids to CSS modifiers', () => {
    expect(PART_IDS).toEqual(['a', 'b', 'ab']);
    expect(partClass('a')).toBe('part-a');
    expect(partClass('B')).toBe('part-b');
    expect(partClass('ab')).toBe('part-ab');
  });

  it('returns an empty class for solo or unknown parts', () => {
    expect(partClass(null)).toBe('');
    expect(partClass(undefined)).toBe('');
    expect(partClass('')).toBe('');
    expect(partClass('c')).toBe('');
  });
});

describe('partLabel', () => {
  it('falls back to generic A / B / A+B labels', () => {
    expect(partLabel(null, 'a')).toBe('A');
    expect(partLabel(undefined, 'b')).toBe('B');
    expect(partLabel({}, 'ab')).toBe('A+B');
  });

  it('uses the song singer names when defined', () => {
    expect(partLabel({ a: 'Alice', b: 'Bob' }, 'a')).toBe('Alice');
    expect(partLabel({ a: 'Alice', b: 'Bob' }, 'b')).toBe('Bob');
    expect(partLabel({ a: 'Alice', b: 'Bob' }, 'ab')).toBe('Alice + Bob');
    // Only one singer named: the shared line falls back to A+B.
    expect(partLabel({ a: 'Alice' }, 'ab')).toBe('A+B');
  });

  it('returns an empty label for solo and unknown parts', () => {
    expect(partLabel({ a: 'Alice' }, null)).toBe('');
    expect(partLabel({ a: 'Alice' }, 'zzz')).toBe('');
  });
});

describe('findSyllableAt', () => {
  it('finds the first syllable at or after ms', () => {
    const lines = buildLyricLines([
      { ms: 0, text: 'a', type: 0, line: 0 },
      { ms: 500, text: 'b', type: 0, line: 0 },
    ]);
    // Returns the first syllable strictly after ms (the upcoming one).
    expect(findSyllableAt(lines, 0).text).toBe('b');
    expect(findSyllableAt(lines, 499).text).toBe('b');
    expect(findSyllableAt(lines, 500)).toBeNull();
  });
});

describe('noteToFrequency', () => {
  it('maps MIDI notes to frequencies', () => {
    expect(noteToFrequency(69)).toBeCloseTo(440, 5);
    expect(noteToFrequency(81)).toBeCloseTo(880, 5);
  });
});

describe('computeNoteTimeline', () => {
  it('sorts events and maps voices', () => {
    const timeline = computeNoteTimeline(
      [
        [500, 0, 60, 100, 200],
        [0, 0, 72, 100, 100],
      ],
      { '0': 0 },
    );
    expect(timeline).toHaveLength(2);
    expect(timeline[0].startMs).toBe(0);
    expect(timeline[1].startMs).toBe(500);
    expect(timeline[0].freq).toBeCloseTo(noteToFrequency(72), 5);
    expect(timeline[0].type).toBe('triangle'); // GM piano
  });

  it('uses the drum channel for channel 9', () => {
    const timeline = computeNoteTimeline([[0, 9, 42, 100, 100]], {});
    expect(timeline[0].drum).toBe(true);
    expect(timeline[0].freq).toBe(0);
  });

  it('scales gain by velocity', () => {
    const loud = computeNoteTimeline([[0, 0, 60, 127, 100]], { '0': 0 })[0];
    const soft = computeNoteTimeline([[0, 0, 60, 10, 100]], { '0': 0 })[0];
    expect(loud.gain).toBeGreaterThan(soft.gain);
  });

  it('enforces a minimum note duration', () => {
    const timeline = computeNoteTimeline([[0, 0, 60, 80, 5]], {});
    expect(timeline[0].endMs - timeline[0].startMs).toBeGreaterThanOrEqual(40);
  });
});

describe('writeTileRgba', () => {
  it('writes tile RGB bytes into the RGBA frame', () => {
    const rgba = new Uint8ClampedArray(CDG_WIDTH * CDG_HEIGHT * 4);
    const tile = new Uint8Array(48 * 48 * 3);
    tile[0] = 255; // top-left pixel red
    tile[1] = 0;
    tile[2] = 128;
    // The tile's top-left pixel lands at frame position (1*48, 2*48)
    // when the tile is placed at grid position (1, 2).
    writeTileRgba(tile, rgba, CDG_WIDTH, 1, 2);
    const idx = ((2 * 48) * CDG_WIDTH + 1 * 48) * 4;
    expect(rgba[idx]).toBe(255);
    expect(rgba[idx + 1]).toBe(0);
    expect(rgba[idx + 2]).toBe(128);
    expect(rgba[idx + 3]).toBe(255); // alpha
    // Pixels outside the tile stay untouched.
    expect(rgba[0]).toBe(0);
  });
});

describe('highlightState', () => {
  const lines = buildLyricLines([
    { ms: 1000, text: 'a', type: 0, line: 0 },
    { ms: 1500, text: 'b', type: 0, line: 0 },
    { ms: 2000, text: 'c', type: 0, line: 0 },
    { ms: 5000, text: 'd', type: 0, line: 1 },
  ]);

  it('selects the active line and lit syllable count', () => {
    expect(highlightState(lines, 0)).toEqual({ lineIdx: 0, litCount: 0 });
    expect(highlightState(lines, 1000)).toEqual({ lineIdx: 0, litCount: 1 });
    expect(highlightState(lines, 1499)).toEqual({ lineIdx: 0, litCount: 1 });
    expect(highlightState(lines, 1500)).toEqual({ lineIdx: 0, litCount: 2 });
    expect(highlightState(lines, 2000)).toEqual({ lineIdx: 0, litCount: 3 });
    expect(highlightState(lines, 4999)).toEqual({ lineIdx: 0, litCount: 3 });
    expect(highlightState(lines, 5000)).toEqual({ lineIdx: 1, litCount: 1 });
  });

  it('clears highlights when seeking backward', () => {
    expect(highlightState(lines, 2000).litCount).toBe(3);
    expect(highlightState(lines, 1000).litCount).toBe(1);
    expect(highlightState(lines, 0).litCount).toBe(0);
    // Backward across a line boundary.
    expect(highlightState(lines, 5000).lineIdx).toBe(1);
    expect(highlightState(lines, 2500).lineIdx).toBe(0);
    expect(highlightState(lines, 2500).litCount).toBe(3);
  });

  it('handles empty input', () => {
    expect(highlightState([], 0)).toEqual({ lineIdx: -1, litCount: 0 });
    expect(highlightState(null, 0)).toEqual({ lineIdx: -1, litCount: 0 });
  });
});

describe('lyric sync timeline (deterministic fake clock)', () => {
  // A realistic enhanced-LRC timeline: three lines, words every ~250 ms.
  const timeline = buildLyricLines([
    { ms: 0, text: 'a', type: 0, line: 0 },
    { ms: 250, text: 'b', type: 0, line: 0 },
    { ms: 500, text: 'c', type: 0, line: 0 },
    { ms: 1000, text: 'd', type: 0, line: 1 },
    { ms: 1250, text: 'e', type: 0, line: 1 },
    { ms: 2000, text: 'f', type: 0, line: 2 },
  ]);

  it('highlights monotonically during forward playback without drift', () => {
    let last = { lineIdx: -1, litCount: -1 };
    for (let ms = 0; ms <= 2500; ms += 50) {
      const state = highlightState(timeline, ms);
      // No backward movement in (lineIdx, litCount) while playing forward.
      const progress = state.lineIdx * 1000 + state.litCount;
      const lastProgress = last.lineIdx * 1000 + last.litCount;
      expect(progress).toBeGreaterThanOrEqual(lastProgress);
      last = state;
    }
  });

  it('lights words exactly at their timestamp', () => {
    expect(highlightState(timeline, 249).litCount).toBe(1); // 'a' only
    expect(highlightState(timeline, 250).litCount).toBe(2); // 'b' starts
  });

  it('responds instantly to seeks on a fake audio clock', () => {
    // Simulate the app reading audio.currentTime: seek 2000 -> 400 -> 1600.
    const clock = { ms: 0 };
    const read = () => highlightState(timeline, clock.ms);
    clock.ms = 2000;
    expect(read().litCount).toBe(1); // line 2, one word lit
    clock.ms = 400;
    expect(read().lineIdx).toBe(0);
    expect(read().litCount).toBe(2); // 'a' + 'b' lit (b starts at 250)
    clock.ms = 1600;
    expect(read().lineIdx).toBe(1);
    expect(read().litCount).toBe(2); // 'd' + 'e' lit
  });

  it('keeps state stable across pause (frozen clock)', () => {
    const frozen = highlightState(timeline, 1300);
    for (let i = 0; i < 10; i++) {
      // Paused: the clock does not advance, the highlight must not either.
      expect(highlightState(timeline, 1300)).toEqual(frozen);
    }
  });
});

describe('zoom scales', () => {
  it('covers the legacy CDG zoom modes', () => {
    expect(ZOOM_SCALES.quick).toBe(0.75);
    expect(ZOOM_SCALES.int).toBe(1);
    expect(ZOOM_SCALES.full).toBe(1.5);
    expect(ZOOM_SCALES.soft).toBe(2);
  });
});