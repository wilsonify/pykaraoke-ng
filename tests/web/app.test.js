import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

import {
  BROWSE_LIMIT,
  buildLyricLines,
  CDG_HEIGHT,
  CDG_WIDTH,
  companionBaseName,
  companionMember,
  computeNoteTimeline,
  debounce,
  describeEngine,
  describePlayback,
  describePlaybackError,
  describeQueue,
  describeResults,
  describeScanReport,
  ELRC_EXT,
  escapeHtml,
  findSyllableAt,
  formatCount,
  formatTime,
  highlightState,
  needsRescan,
  noteToFrequency,
  PART_IDS,
  partClass,
  partLabel,
  queueBadgeFor,
  RESCAN_KEYS,
  scanCategoryLabel,
  SHORTCUTS,
  SongQueue,
  songLabel,
  writeTileRgba,
  ZOOM_SCALES,
} from '../../src/web/src/helpers.js';

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
    const timeline = computeNoteTimeline([[0, 0, 60, 80, 5]], {})[0];
    expect(timeline.endMs - timeline.startMs).toBeGreaterThanOrEqual(40);
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

describe('settings panel: naming convention select', () => {
  // The select's values must match the engine's FileNameType enum in
  // src/pykaraoke/filename_parser.py (0=DISC_TRACK_ARTIST_TITLE ...
  // 4=DISC_TRACK_SPACED); a previous revision shifted the labels by one.
  const htmlPath = resolve(
    dirname(fileURLToPath(import.meta.url)),
    '..',
    '..',
    'src',
    'web',
    'index.html',
  );
  const html = readFileSync(htmlPath, 'utf8');

  it('maps each option value to the correct convention label', () => {
    const select = /<select id="setting-naming">([\s\S]*?)<\/select>/.exec(html);
    expect(select).toBeTruthy();
    const options = [...select[1].matchAll(/<option value="(\d+)">([^<]+)<\/option>/g)].map(
      (m) => [m[1], m[2]],
    );
    expect(options).toEqual([
      ['0', 'Disc Track - Artist - Title'],
      ['1', 'DiscTrack - Artist - Title'],
      ['2', 'Disc - Artist - Title'],
      ['3', 'Artist - Title'],
      ['4', 'Disc-Track - Artist - Title (spaced)'],
    ]);
  });

  it('offers exactly the five engine conventions', () => {
    const namingBlock = /<select id="setting-naming">([\s\S]*?)<\/select>/.exec(html)[1];
    const namingValues = [...namingBlock.matchAll(/<option value="(\d+)">/g)].map((m) =>
      Number(m[1]),
    );
    expect(namingValues).toEqual([0, 1, 2, 3, 4]);
  });
});

describe('formatCount', () => {
  it('adds thousands separators to counts', () => {
    expect(formatCount(0)).toBe('0');
    expect(formatCount(999)).toBe('999');
    expect(formatCount(2382)).toBe('2,382');
    expect(formatCount(1234567)).toBe('1,234,567');
  });

  it('survives strings, fractions and nonsense', () => {
    expect(formatCount('42')).toBe('42');
    expect(formatCount(12.7)).toBe('12');
    expect(formatCount(undefined)).toBe('0');
    expect(formatCount('nope')).toBe('0');
  });
});

describe('scanCategoryLabel', () => {
  it('labels a single file and many files', () => {
    expect(scanCategoryLabel('unsupported', 1)).toBe('file that is not karaoke');
    expect(scanCategoryLabel('unsupported', 2382)).toBe('files that are not karaoke');
    expect(scanCategoryLabel('corrupt_archive', 2)).toBe('damaged ZIP archives');
  });

  it('falls back to the raw category for unknown ones', () => {
    expect(scanCategoryLabel('mystery', 1)).toBe('mystery');
  });
});

describe('describeScanReport', () => {
  it('calls skipped files informational, not failures', () => {
    const view = describeScanReport({
      counts: { unsupported: 2382, filtered: 3 },
      entries: [{ category: 'unsupported', path: 'movie.mp4' }],
    });
    expect(view.severity).toBe('info');
    expect(view.problemCount).toBe(0);
    expect(view.infoCount).toBe(2385);
    expect(view.summary).toBe(
      'Scan finished — skipped 2,382 files that are not karaoke and 3 files you filtered out',
    );
  });

  it('leads with the problems when files genuinely failed', () => {
    const view = describeScanReport({
      counts: { corrupt_archive: 1, unreadable: 2, unsupported: 5 },
      entries: [],
    });
    expect(view.severity).toBe('warn');
    expect(view.problemCount).toBe(3);
    expect(view.summary).toBe(
      'Scan finished with 3 problems: 1 damaged ZIP archive, 2 files that could not be read',
    );
  });

  it('says so when every file was usable', () => {
    const view = describeScanReport({ counts: { unsupported: 0 }, entries: [] });
    expect(view.severity).toBe('info');
    expect(view.hasIssues).toBe(false);
    expect(view.summary).toBe('Scan finished — every file was usable');
    expect(view.details).toEqual([]);
  });

  it('groups paths by category, problems first', () => {
    const view = describeScanReport({
      counts: { unsupported: 2, corrupt_archive: 1 },
      entries: [
        { category: 'unsupported', path: 'a.mp4' },
        { category: 'unsupported', path: 'b.txt' },
        { category: 'corrupt_archive', path: 'broken.zip' },
      ],
    });
    expect(view.details.map((d) => d.category)).toEqual(['corrupt_archive', 'unsupported']);
    expect(view.details[0]).toMatchObject({
      label: 'damaged ZIP archive',
      count: 1,
      paths: ['broken.zip'],
      hidden: 0,
    });
    expect(view.details[1].paths).toEqual(['a.mp4', 'b.txt']);
    expect(view.details[1].count).toBe(2);
  });

  it('truncates a long path list and reports what it hid', () => {
    const entries = Array.from({ length: 12 }, (_, i) => ({
      category: 'unreadable',
      path: `f${i}.cdg`,
    }));
    const view = describeScanReport({ counts: { unreadable: 12 }, entries }, { maxDetails: 5 });
    expect(view.details[0].paths).toHaveLength(5);
    expect(view.details[0].hidden).toBe(7);
    expect(view.details[0].count).toBe(12);
  });

  it('handles a missing report', () => {
    const view = describeScanReport(null);
    expect(view.hasIssues).toBe(false);
    expect(view.details).toEqual([]);
  });
});

describe('describeResults', () => {
  it('invites the user to add a folder when the library is empty', () => {
    const view = describeResults({ libraryCount: 0 });
    expect(view.heading).toBe('Songs');
    expect(view.count).toBe('');
    expect(view.empty).toMatchObject({ kind: 'no-library', action: 'add-folder' });
    expect(view.empty.title).toBe('No songs yet');
  });

  it('browses the whole library when the search box is empty', () => {
    const view = describeResults({ libraryCount: 272, query: '', shown: 272 });
    expect(view.heading).toBe('All songs');
    expect(view.count).toBe('272');
    expect(view.hint).toBe('');
    expect(view.empty).toBeNull();
  });

  it('explains a library too large to list at once', () => {
    const view = describeResults({ libraryCount: 2382, query: '', shown: BROWSE_LIMIT });
    expect(view.count).toBe('300 of 2,382');
    expect(view.hint).toBe('Showing the first 300 — type to search the rest.');
  });

  it('lists search matches with a count', () => {
    const view = describeResults({ libraryCount: 272, query: 'queen', matched: 12, shown: 12 });
    expect(view.heading).toBe('Results');
    expect(view.count).toBe('12 songs');
    expect(view.empty).toBeNull();

    const single = describeResults({ libraryCount: 272, query: 'queen', matched: 1, shown: 1 });
    expect(single.count).toBe('1 song');
  });

  it('explains that nothing matched the search', () => {
    const view = describeResults({ libraryCount: 272, query: 'zzz', matched: 0, shown: 0 });
    expect(view.count).toBe('None');
    expect(view.empty.kind).toBe('no-matches');
    expect(view.empty.title).toBe('No songs match “zzz”');
    expect(view.empty.action).toBe('clear-search');
  });

  it('separates matches hidden by the format filters from no matches', () => {
    const view = describeResults({ libraryCount: 272, query: 'love', matched: 12, shown: 0 });
    expect(view.count).toBe('12 hidden');
    expect(view.empty.kind).toBe('filtered-out');
    expect(view.empty.title).toBe('12 match the search but not the format filters');
    expect(view.empty.action).toBe('reset-filters');
  });

  it('tells the user when a search hit the engine limit', () => {
    const view = describeResults({
      libraryCount: 5000,
      query: 'a',
      matched: 500,
      shown: 500,
      limit: 500,
    });
    expect(view.hint).toBe('Showing the best 500 matches — add another word to narrow.');
  });

  it('treats a whitespace-only query as browsing', () => {
    const view = describeResults({ libraryCount: 10, query: '   ', shown: 10 });
    expect(view.heading).toBe('All songs');
  });
});

describe('describeQueue', () => {
  it('explains how to fill an empty queue', () => {
    const info = describeQueue({ length: 0 });
    expect(info.count).toBe('Empty');
    expect(info.hint).toContain('press Enter to add it');
  });

  it('counts the queued songs and names the next one', () => {
    expect(describeQueue({ length: 1, nextLabel: 'Song — Artist' })).toEqual({
      count: '1 song',
      hint: 'Up next: Song — Artist',
    });
    expect(describeQueue({ length: 3, nextLabel: 'A' }).count).toBe('3 songs');
    expect(describeQueue({ length: 2, nextLabel: '' }).hint).toBe(
      'Queue is playing out — nothing waiting.',
    );
  });
});

describe('describePlayback', () => {
  it('is idle, with the transport disabled, before a song is chosen', () => {
    const info = describePlayback({});
    expect(info).toMatchObject({
      state: 'idle',
      label: 'Nothing loaded',
      playDisabled: true,
      stopDisabled: true,
      seekDisabled: true,
    });
  });

  it('offers pause, stop and seek while playing', () => {
    const info = describePlayback({ song: { id: 's' }, playing: true });
    expect(info).toMatchObject({
      state: 'playing',
      label: 'Playing',
      playLabel: 'Pause',
      playDisabled: false,
      stopDisabled: false,
      seekDisabled: false,
    });
  });

  it('offers resume while paused', () => {
    const info = describePlayback({ song: { id: 's' }, playing: false });
    expect(info).toMatchObject({ state: 'paused', label: 'Paused', playLabel: 'Play' });
  });

  it('turns Play into Retry after a load failure, but cannot seek', () => {
    const info = describePlayback({ song: { id: 's' }, playing: false, failed: true });
    expect(info).toMatchObject({
      state: 'error',
      label: 'Playback failed',
      playLabel: 'Retry',
      playDisabled: false,
      stopDisabled: false,
      seekDisabled: true,
    });
  });

  it('ignores a stale failure flag once no song is loaded', () => {
    expect(describePlayback({ failed: true }).state).toBe('idle');
  });
});

describe('describeEngine', () => {
  it('says it is starting before the engine is ready', () => {
    expect(describeEngine({}).text).toBe('Starting…');
  });

  it('reports readiness without runtime jargon in the label', () => {
    const ready = describeEngine({ ready: true, version: 'Pyodide 0.27.2' });
    expect(ready.text).toBe('Ready');
    expect(ready.title).toContain('Pyodide 0.27.2');
    expect(ready.title).not.toContain('PyScript ready');
  });

  it('states a failure plainly', () => {
    const failed = describeEngine({ failed: true });
    expect(failed.text).toBe('Engine unavailable');
    expect(failed.title).toContain('Reload');
  });
});

describe('describePlaybackError', () => {
  it('names the missing audio file', () => {
    expect(describePlaybackError('no audio file found for this CDG')).toContain('.mp3');
    expect(describePlaybackError('no audio file found for this LRC')).toContain('.wav');
  });

  it('explains the zip limitations', () => {
    expect(describePlaybackError('video inside zip is not supported')).toContain('extract');
    expect(describePlaybackError('member not found in zip: Song.cdg')).toContain(
      'inside the ZIP archive could not be read',
    );
  });

  it('explains an unreadable song file', () => {
    expect(describePlaybackError('could not parse MIDI file')).toContain('damaged');
  });

  it('passes an unknown message through unchanged', () => {
    expect(describePlaybackError('disk on fire')).toBe('disk on fire');
    expect(describePlaybackError('')).toBe('unknown error');
  });
});

describe('needsRescan', () => {
  it('flags the scan-time settings', () => {
    for (const key of RESCAN_KEYS) {
      expect(needsRescan({ [key]: key === 'look_inside_zips' ? false : [] })).toBe(true);
    }
  });

  it('does not flag settings that apply immediately', () => {
    expect(needsRescan({ volume: 0.5 })).toBe(false);
    expect(needsRescan({ cdg_zoom: 'full' })).toBe(false);
    expect(needsRescan({ sort: 'title' })).toBe(false);
    expect(needsRescan({ folders: ['C:/Songs'] })).toBe(false);
    expect(needsRescan()).toBe(false);
  });
});

describe('queueBadgeFor', () => {
  const song = { id: 'a', filename: 'a.cdg' };

  it('is empty for a song outside the queue', () => {
    expect(queueBadgeFor(song, [{ id: 'b' }], null)).toEqual({
      positions: [],
      count: 0,
      playing: false,
      label: '',
    });
  });

  it('counts duplicates and gives their positions', () => {
    const badge = queueBadgeFor(song, [{ id: 'b' }, song, { id: 'a' }], null);
    expect(badge.positions).toEqual([2, 3]);
    expect(badge.count).toBe(2);
    expect(badge.label).toBe('queued ×2');
  });

  it('marks the song that is playing', () => {
    expect(queueBadgeFor(song, [], 'a').label).toBe('playing');
    expect(queueBadgeFor(song, [song], 'a').label).toBe('playing · queued');
  });
});

describe('SongQueue.insert (undo remove)', () => {
  it('puts a song back where it was', () => {
    const queue = new SongQueue([{ id: 'a' }, { id: 'b' }, { id: 'c' }]);
    const [removed] = queue.items.splice(1, 1);
    queue.insert(1, removed);
    expect(queue.items.map((s) => s.id)).toEqual(['a', 'b', 'c']);
  });

  it('clamps an out-of-range index instead of losing the song', () => {
    const queue = new SongQueue([{ id: 'a' }]);
    queue.insert(99, { id: 'b' });
    queue.insert(-4, { id: 'c' });
    expect(queue.items.map((s) => s.id)).toEqual(['c', 'a', 'b']);
  });

  it('fills an empty queue', () => {
    const queue = new SongQueue();
    queue.insert(0, { id: 'a' });
    expect(queue.length).toBe(1);
  });
});

describe('SHORTCUTS', () => {
  const keysOf = (shortcut) => shortcut.keys;

  it('documents the preserved bindings', () => {
    const all = SHORTCUTS.map(keysOf).join(' | ');
    expect(all).toContain('/');
    expect(all).toContain('Ctrl+K');
    expect(all).toContain('Esc');
    expect(all).toContain('Space');
    expect(all).toContain('Enter');
    expect(all).toContain('↑');
  });

  it('every entry has a key label and a description', () => {
    expect(SHORTCUTS.length).toBeGreaterThan(5);
    for (const shortcut of SHORTCUTS) {
      expect(shortcut.keys.trim().length).toBeGreaterThan(0);
      expect(shortcut.description.trim().length).toBeGreaterThan(5);
    }
  });

  it('documents the queue reorder and removal keys it implements', () => {
    const all = SHORTCUTS.map(keysOf).join(' | ');
    expect(all).toContain('Alt+↑');
    expect(all).toContain('Delete');
  });
});

describe('index.html: wiring contract with app.js', () => {
  const webDir = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..', 'src', 'web');
  const html = readFileSync(resolve(webDir, 'index.html'), 'utf8');
  const appJs = readFileSync(resolve(webDir, 'src', 'app.js'), 'utf8');

  // Ids the app looks up through a literal $('...') call, plus the ones it
  // iterates over in small lists (disabled-while-busy, format filters, ...).
  const literalIds = [...appJs.matchAll(/\$\('([a-z0-9-]+)'\)/g)].map((m) => m[1]);
  const listedIds = [
    'add-folder-btn',
    'scan-library-btn',
    'replace-library-btn',
    'export-library-btn',
    'import-library-btn',
    'filter-cdg',
    'filter-kar',
    'filter-mpg',
    'filter-lrc',
    'settings-rescan-btn',
  ];
  const ids = [...new Set([...literalIds, ...listedIds])];

  it('provides every element id app.js looks up', () => {
    expect(ids.length).toBeGreaterThan(40);
    expect(ids.filter((id) => !html.includes(`id="${id}"`))).toEqual([]);
  });

  it('gives icon-only controls an accessible name', () => {
    for (const id of [
      'play-btn',
      'stop-btn',
      'prev-btn',
      'next-btn',
      'rewind-btn',
      'ff-btn',
      'settings-btn',
      'settings-close-btn',
      'search-input',
      'volume-slider',
      'progress-slider',
      'folder-picker',
      'import-library-picker',
    ]) {
      const tag = new RegExp(`<[^>]*id="${id}"[^>]*>`).exec(html);
      expect(tag, `missing element #${id}`).toBeTruthy();
      expect(tag[0], `#${id} needs an aria-label`).toContain('aria-label=');
    }
  });

  it('names the CD+G surface with a figure and no role on the canvas', () => {
    // <canvas> is HTML interactive content, so it must not carry a
    // non-interactive role; the native <figure> around it carries the name,
    // which is also the element the role="img" would have imitated.
    const view = /<figure id="cdg-view"[^>]*>/.exec(html);
    expect(view, 'missing the #cdg-view figure').toBeTruthy();
    expect(view[0]).toContain('aria-label=');
    expect(view[0]).not.toContain('role=');
    const canvas = (html.match(/<canvas[^>]*>/g) || []).find((tag) =>
      tag.includes('id="cdg-canvas"'),
    );
    expect(canvas, 'missing the #cdg-canvas element').toBeTruthy();
    expect(canvas).not.toContain('role=');
  });

  it('never gives an interactive element a non-interactive role', () => {
    const interactive = html.match(/<(button|a|input|select|textarea|canvas)[^>]*>/g) || [];
    const offenders = interactive.filter((tag) =>
      /role="(img|presentation|none|document|heading|status|list|listitem|group)"/.test(tag),
    );
    expect(offenders).toEqual([]);
  });

  it('uses the native element instead of an ARIA role that has one', () => {
    // status/group/listbox/img/list/option all have native equivalents, and
    // every one of them is now the element itself rather than a role.
    const tags = html.match(/<[a-z][^>]*>/gi) || [];
    const offenders = tags.filter((tag) =>
      /role="(img|status|group|listbox|list|option|presentation|none|document|heading)"/.test(tag),
    );
    expect(offenders).toEqual([]);
  });

  it('keeps the live regions and control groups as native elements', () => {
    for (const id of [
      'library-count',
      'scan-summary',
      'playback-state',
      'notices',
      'status-message',
      'settings-rescan-note',
    ]) {
      const output = new RegExp(`<output[^>]*id="${id}"`);
      expect(output.test(html), `#${id} should be an <output>`).toBe(true);
    }
    expect(html).toMatch(/<fieldset class="filter-row"/);
    expect(html).toMatch(/<fieldset class="player-controls"/);
    expect(html).toMatch(/<ul id="results-list"/);
    expect(html).toMatch(/<figure id="cdg-view"/);
  });

  it('marks the selected row with aria-current, not a listbox option', () => {
    // The rows are list items, so "selected" is aria-current; aria-selected
    // and role="option" are only valid inside a listbox.
    expect(appJs).toContain("const row = document.createElement('li')");
    expect(appJs).not.toContain("setAttribute('role'");
    expect(appJs).not.toContain('aria-selected');
    expect(appJs).toContain("row.setAttribute('aria-current', 'true')");
  });

  it('keeps template interpolations flat', () => {
    // A template literal inside an interpolation used to be how the engine
    // label was built. The nested ternaries at the other reported call sites
    // became statements, which no regex can recognise reliably (a property
    // colon and a ternary colon look identical), so this guards the template
    // case, walking each interpolation to its matching brace.
    const nestedInsideInterpolation = (src) => {
      const hits = [];
      for (let i = src.indexOf('${'); i !== -1; i = src.indexOf('${', i + 1)) {
        let depth = 1;
        let j = i + 2;
        while (j < src.length && depth > 0) {
          if (src[j] === '{') depth += 1;
          else if (src[j] === '}') depth -= 1;
          j += 1;
        }
        const body = src.slice(i + 2, j - 1);
        if (body.includes('`')) hits.push(body.trim().slice(0, 60));
      }
      return hits;
    };
    expect(nestedInsideInterpolation(appJs)).toEqual([]);
  });

  it('declares each stylesheet selector only once', () => {
    const style = /<style[^>]*>([\s\S]*?)<\/style>/.exec(html);
    expect(style, 'missing the inline stylesheet').toBeTruthy();
    const css = style[1].replace(/\/\*[\s\S]*?\*\//g, '');
    const selectors = [];
    // Linear scan instead of /(?:^|\})\s*([^{}]+)\{/g: split each rule
    // block on '}' and take the selector group before the first '{'.
    // Equivalent matches (a group holds no braces either way) with no
    // backtracking.
    for (const block of css.split('}')) {
      const brace = block.indexOf('{');
      if (brace === -1) continue;
      for (const sel of block.slice(0, brace).split(',')) {
        const name = sel.trim().replace(/\s+/g, ' ');
        if (name) selectors.push(name);
      }
    }
    expect(selectors.length).toBeGreaterThan(100);
    const counts = new Map();
    for (const sel of selectors) counts.set(sel, (counts.get(sel) || 0) + 1);
    const duplicates = [...counts].filter(([, n]) => n > 1).map(([sel]) => sel);
    expect(duplicates).toEqual([]);
  });

  it('marks the settings that need a rescan next to their labels', () => {
    for (const id of [
      'setting-zips',
      'setting-exclude',
      'setting-naming',
      'setting-include-patterns',
      'setting-exclude-patterns',
    ]) {
      const block = new RegExp(String.raw`<div class="settings-row">([\s\S]*?)id="${id}"`).exec(html);
      expect(block, `missing settings row for #${id}`).toBeTruthy();
      expect(block[1]).toContain('rescan');
    }
  });

  it('keeps the rescan note and the shortcuts list in the settings panel', () => {
    expect(html).toContain('id="settings-rescan-note"');
    expect(html).toContain('id="shortcuts-list"');
    // The note lives inside the panel, next to the controls it explains.
    const panel = /id="settings-panel"[\s\S]*?<script type="py">/.exec(html)[0];
    expect(panel).toContain('id="settings-rescan-note"');
    expect(panel).toContain('id="shortcuts-list"');
  });

  it('exposes the region hooks the app writes into', () => {
    for (const hook of [
      'results-list',
      'results-count',
      'results-hint',
      'results-empty',
      'scan-issues',
      'scan-details',
      'queue-count',
      'queue-hint',
      'playback-state',
      'notices',
      'status-message',
      'engine-status',
      'library-count',
      'library-folders',
      'replace-hint',
      'engine-detail',
    ]) {
      expect(html, `missing #${hook}`).toContain(`id="${hook}"`);
    }
  });

  it('keeps the no-results placeholder out of the markup and CSS', () => {
    // Empty states are rendered by the app with specific wording; a static
    // placeholder would fight with them.
    expect(appJs).not.toContain('no-results');
  });
});
