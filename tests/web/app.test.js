import { describe, expect, it } from 'vitest';

import {
  buildLyricLines,
  CDG_HEIGHT,
  CDG_WIDTH,
  computeNoteTimeline,
  debounce,
  escapeHtml,
  findSyllableAt,
  formatTime,
  noteToFrequency,
  SongQueue,
  songLabel,
  writeTileRgba,
  ZOOM_SCALES,
} from '../../web/app.js';

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

describe('SongQueue', () => {
  it('pushes, removes and clears', () => {
    const q = new SongQueue();
    q.push({ id: 'a' });
    q.push({ id: 'b' });
    q.push({ id: 'c' });
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

  it('handles empty input', () => {
    expect(buildLyricLines([])).toEqual([]);
    expect(buildLyricLines(null)).toEqual([]);
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

describe('zoom scales', () => {
  it('covers the legacy CDG zoom modes', () => {
    expect(ZOOM_SCALES.quick).toBe(0.75);
    expect(ZOOM_SCALES.int).toBe(1);
    expect(ZOOM_SCALES.full).toBe(1.5);
    expect(ZOOM_SCALES.soft).toBe(2);
  });
});