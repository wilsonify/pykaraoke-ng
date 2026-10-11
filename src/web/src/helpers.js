export const CDG_WIDTH = 288;
export const CDG_HEIGHT = 192;

export const ZOOM_SCALES = { quick: 0.75, int: 1, full: 1.5, soft: 2 };

export function formatTime(ms) {
  const total = Math.max(0, Math.floor(ms / 1000));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${String(s).padStart(2, '0')}`;
}

export function debounce(fn, wait) {
  let timer = null;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), wait);
  };
}

export function escapeHtml(text) {
  return String(text).replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]));
}

/** Parse "Artist - Title" style display strings out of song metadata. */
export function songLabel(song) {
  const title = song.title || song.filename.replace(/\.[^.]+$/, '');
  const artist = song.artist ? ` — ${song.artist}` : '';
  return `${title}${artist}`;
}

export const KIND_BADGE = { cdg: 'CDG', kar: 'KAR', mpg: 'MPG', lrc: 'LRC' };

/** Extension of the companion file carrying word-level lyric timing. */
export const ELRC_EXT = '.elrc';

/**
 * Lowercased basename key for a loose-file companion of *song*
 * (e.g. `song.elrc` next to `song.lrc`), or null when unusable.
 * Looks the key up in `state.pathByBase`.
 */
export function companionBaseName(song, ext) {
  const filename = String(song?.filename || '');
  const stem = filename.replace(/\.[^.]+$/, '').toLowerCase();
  return stem ? `${stem}${ext}` : null;
}

/**
 * Zip member name of a companion file for a song inside a zip, or null.
 * Mirrors the `zip!member` id that readSongBytes() splits apart.
 */
export function companionMember(song, ext) {
  if (!song?.zip_name) return null;
  const member = String(song.id || '').split('!').slice(1).join('!');
  if (!member) return null;
  return member.replace(/\.[^./\\]+$/, ext);
}

/** A FIFO queue of songs with indexed removal / moves. */
export class SongQueue {
  constructor(items = []) {
    this.items = [...items];
  }
  get length() {
    return this.items.length;
  }
  push(song) {
    this.items.push(song);
  }
  removeAt(index) {
    if (index < 0 || index >= this.items.length) return null;
    return this.items.splice(index, 1)[0];
  }
  /** Put *song* back at *index* (used by "Undo remove"). */
  insert(index, song) {
    const at = Math.max(0, Math.min(Math.trunc(index) || 0, this.items.length));
    this.items.splice(at, 0, song);
  }
  move(index, delta) {
    const target = index + delta;
    if (index < 0 || index >= this.items.length) return;
    if (target < 0 || target >= this.items.length) return;
    const [item] = this.items.splice(index, 1);
    this.items.splice(target, 0, item);
  }
  clear() {
    this.items = [];
  }
  next() {
    return this.items.shift() ?? null;
  }
}

/** Generic duet part ids (never gendered); 'ab' is a shared A+B line. */
export const PART_IDS = ['a', 'b', 'ab'];

/**
 * CSS modifier class for a lyric line's part: 'part-a' | 'part-b' |
 * 'part-ab', or '' when the line has no (recognised) part.
 */
export function partClass(part) {
  const id = String(part || '').toLowerCase();
  return PART_IDS.includes(id) ? `part-${id}` : '';
}

/**
 * Human label for a lyric line's part, for the in-line part chip.
 * `parts` is the song's optional {a, b} display-name map; the generic
 * "A", "B" or "A+B" id is the fallback when no singer is named.
 */
export function partLabel(parts, part) {
  const id = String(part || '').toLowerCase();
  if (!PART_IDS.includes(id)) return '';
  const names = parts || {};
  if (id === 'ab') {
    return names.a && names.b ? `${names.a} + ${names.b}` : 'A+B';
  }
  return names[id] || id.toUpperCase();
}

/**
 * Group timed lyric syllables into display lines.
 * Input: [{ms, text, type, line, part?}] — type 0 is a sung syllable,
 * part ('a'|'b'|'ab') marks a duet line.
 * Output: [{line, ms, part, syllables: [{ms, text}]}] sorted by time.
 */
export function buildLyricLines(lyrics) {
  const sung = (lyrics || []).filter((s) => Number(s.type || 0) === 0);
  const byLine = new Map();
  for (const syl of sung) {
    const key = Number(syl.line) || 0;
    if (!byLine.has(key)) byLine.set(key, []);
    byLine.get(key).push(syl);
  }
  const lines = [...byLine.entries()]
    .sort((a, b) => a[1][0].ms - b[1][0].ms)
    .map(([line, syllables]) => ({
      line,
      ms: syllables[0].ms,
      // Duet part shared by every syllable of the line, if tagged.
      part: syllables.find((s) => s.part && partClass(s.part))?.part || null,
      // Deterministic per-line order by time so the renderer can highlight
      // by index even when the source timestamps are out of order.
      syllables: syllables
        .map((s) => ({ ms: s.ms, text: s.text }))
        .sort((a, b) => a.ms - b.ms),
    }));
  return lines;
}

/** First syllable strictly after *ms* (the upcoming one), else null. */
export function findSyllableAt(lines, ms) {
  for (const line of lines) {
    for (const syl of line.syllables) {
      if (syl.ms > ms) return syl;
    }
  }
  return null;
}

/**
 * Pure highlight state for a lyric timeline at *ms*.
 *
 * Returns the active line index and how many of its syllables have been
 * sung.  Deterministic and order-independent — safe to call every frame
 * from the playback loop and from tests with a fake clock.
 */
export function highlightState(lines, ms) {
  if (!lines?.length) return { lineIdx: -1, litCount: 0 };
  let lineIdx = 0;
  while (lineIdx < lines.length - 1 && lines[lineIdx + 1].ms <= ms) lineIdx++;
  const line = lines[lineIdx];
  let litCount = 0;
  for (const syl of line.syllables) {
    if (syl.ms <= ms) litCount++;
    else break;
  }
  return { lineIdx, litCount };
}

/** MIDI note number → frequency in Hz (A4 = 69 = 440 Hz). */
export function noteToFrequency(note) {
  return 440 * Math.pow(2, (note - 69) / 12);
}

/**
 * Small General-MIDI-ish voice map: program → {type, gain, shift}.
 * Kept intentionally tiny — good enough for karaoke backing tracks.
 */
const GM_VOICES = {
  0: { type: 'triangle', gain: 0.30, shift: 0 },   // Acoustic grand piano
  24: { type: 'triangle', gain: 0.28, shift: 0 },  // Nylon guitar
  25: { type: 'triangle', gain: 0.28, shift: 0 },  // Steel guitar
  32: { type: 'sawtooth', gain: 0.16, shift: -1 }, // Acoustic bass
  33: { type: 'sawtooth', gain: 0.16, shift: -1 }, // Electric bass
  34: { type: 'sawtooth', gain: 0.16, shift: -1 }, // Fretless bass
  40: { type: 'triangle', gain: 0.28, shift: 0 },  // Violin
  41: { type: 'triangle', gain: 0.28, shift: 0 },  // Viola
  48: { type: 'sawtooth', gain: 0.18, shift: 0 },  // String ensemble
  52: { type: 'sawtooth', gain: 0.18, shift: 0 },  // Synth choir
  56: { type: 'sawtooth', gain: 0.18, shift: 0 },  // Orchestra hit
  73: { type: 'triangle', gain: 0.30, shift: 1 },  // Flute
  74: { type: 'triangle', gain: 0.30, shift: 1 },  // Recorder
  80: { type: 'square', gain: 0.16, shift: 0 },    // Square lead
  81: { type: 'sawtooth', gain: 0.20, shift: 0 },  // Saw lead
};

export function voiceFor(program, channel) {
  if (channel === 9) return { drum: true };
  return GM_VOICES[program] ?? GM_VOICES[0];
}

/**
 * Convert parsed MIDI notes into a plain audio timeline.
 * Input notes: [startMs, channel, note, velocity, durationMs].
 * Output: [{startMs, endMs, freq, gain, type, drum}] sorted by start.
 */
export function computeNoteTimeline(notes, programs = {}) {
  const timeline = [];
  for (const [startMs, channel, note, velocity, durationMs] of notes) {
    const voice = voiceFor(programs[String(channel)], channel);
    const vel = Math.min(1, Math.max(0.1, (velocity || 80) / 127));
    timeline.push({
      startMs,
      endMs: startMs + Math.max(durationMs, 40),
      freq: voice.drum ? 0 : noteToFrequency(note + (voice.shift || 0) * 12),
      gain: (voice.gain || 0.2) * vel,
      type: voice.type || 'triangle',
      drum: !!voice.drum,
    });
  }
  timeline.sort((a, b) => a.startMs - b.startMs);
  return timeline;
}

/**
 * Write a CDG tile's RGB bytes into a full-frame RGBA buffer.
 * tile.data is 48*48*3 bytes; (x, y) is the tile grid position (0-5, 0-3).
 */
/* ── Presentation helpers ──────────────────────────────────────────────
 *
 * Pure functions behind the user-facing wording and control states.  They
 * live here so the text and the enable/disable rules can be unit-tested
 * without a DOM; app.js only places their results into elements.
 */

/** Thousands-separated integer for counts (2382 -> "2,382"). */
export function formatCount(value) {
  const n = Math.trunc(Number(value));
  if (!Number.isFinite(n)) return '0';
  return n.toLocaleString('en-US');
}

/** How many songs the browse view shows before asking the user to search. */
export const BROWSE_LIMIT = 300;

/** Friendly wording for each scan-report category, singular and plural. */
export const SCAN_CATEGORY_LABELS = {
  corrupt_archive: { one: 'damaged ZIP archive', many: 'damaged ZIP archives' },
  unsupported_compression: {
    one: 'ZIP using unsupported compression',
    many: 'ZIPs using unsupported compression',
  },
  unreadable: { one: 'file that could not be read', many: 'files that could not be read' },
  parse_failure: {
    one: 'file name that could not be parsed',
    many: 'file names that could not be parsed',
  },
  unsupported: { one: 'file that is not karaoke', many: 'files that are not karaoke' },
  filtered: { one: 'file you filtered out', many: 'files you filtered out' },
};

/** Human phrase for one scan category at a given count. */
export function scanCategoryLabel(category, count = 1) {
  const labels = SCAN_CATEGORY_LABELS[category];
  if (!labels) return String(category);
  return Number(count) === 1 ? labels.one : labels.many;
}

/** Categories that mean the scan could not use a file, not that it failed. */
export const SCAN_PROBLEM_CATEGORIES = [
  'corrupt_archive',
  'unsupported_compression',
  'unreadable',
  'parse_failure',
];

export const SCAN_INFO_CATEGORIES = ['unsupported', 'filtered'];

function plural(label, count) {
  return count === 1 ? label : `${label}s`;
}

/**
 * Turn a raw scan report into wording a user can act on.
 *
 * Returns the notification line, how many entries genuinely need attention,
 * and the per-category detail rows (paths first seen for each category).
 */
export function describeScanReport(report, { maxDetails = 50 } = {}) {
  const counts = report?.counts || {};
  const entries = report?.entries || [];
  const present = (list) => list.filter((c) => Number(counts[c]) > 0);
  const problems = present(SCAN_PROBLEM_CATEGORIES);
  const info = present(SCAN_INFO_CATEGORIES);
  const problemCount = problems.reduce((sum, c) => sum + Number(counts[c]), 0);
  const infoCount = info.reduce((sum, c) => sum + Number(counts[c]), 0);

  const phrase = (category) => {
    const n = Number(counts[category]);
    return `${formatCount(n)} ${scanCategoryLabel(category, n)}`;
  };

  let summary = '';
  if (problems.length) {
    summary = `Scan finished with ${formatCount(problemCount)} ${plural('problem', problemCount)}: ${problems.map(phrase).join(', ')}`;
  } else if (infoCount) {
    summary = `Scan finished — skipped ${info.map(phrase).join(' and ')}`;
  } else {
    summary = 'Scan finished — every file was usable';
  }

  const details = [];
  let used = 0;
  for (const category of [...SCAN_PROBLEM_CATEGORIES, ...SCAN_INFO_CATEGORIES]) {
    const paths = entries.filter((e) => e.category === category).map((e) => e.path);
    if (!paths.length) continue;
    const remaining = Math.max(0, maxDetails - used);
    const shown = paths.slice(0, remaining);
    used += shown.length;
    const count = Number(counts[category] || paths.length);
    details.push({
      category,
      label: scanCategoryLabel(category, count),
      count,
      paths: shown,
      hidden: Math.max(0, paths.length - shown.length),
    });
  }

  return {
    severity: problems.length ? 'warn' : 'info',
    hasIssues: problemCount + infoCount > 0,
    problemCount,
    infoCount,
    summary,
    details,
  };
}

/**
 * Heading, count and empty-state wording for the song list.
 *
 * * an empty library invites the user to add a folder,
 * * an empty search box browses the library,
 * * a query with no matches explains what to try instead, and
 * * a query whose matches are all filtered out offers to reset filters.
 */
export function describeResults({
  libraryCount = 0,
  query = '',
  matched = 0,
  shown = 0,
  limit = BROWSE_LIMIT,
} = {}) {
  const q = String(query == null ? '' : query).trim();
  if (libraryCount <= 0) {
    return {
      heading: 'Songs',
      count: '',
      hint: '',
      empty: {
        kind: 'no-library',
        title: 'No songs yet',
        hint: 'Add the folder that holds your karaoke files.',
        action: 'add-folder',
        actionLabel: 'Add folder',
      },
    };
  }
  if (!q) {
    const truncated = libraryCount > shown;
    return {
      heading: 'All songs',
      count: truncated
        ? `${formatCount(shown)} of ${formatCount(libraryCount)}`
        : formatCount(libraryCount),
      hint: truncated
        ? `Showing the first ${formatCount(shown)} — type to search the rest.`
        : '',
      empty: null,
    };
  }
  if (matched <= 0) {
    return {
      heading: 'Results',
      count: 'None',
      hint: '',
      empty: {
        kind: 'no-matches',
        title: `No songs match “${q}”`,
        hint: 'Check the spelling, try fewer words, or search the artist instead.',
        action: 'clear-search',
        actionLabel: 'Clear search',
      },
    };
  }
  if (shown <= 0) {
    return {
      heading: 'Results',
      count: `${formatCount(matched)} hidden`,
      hint: '',
      empty: {
        kind: 'filtered-out',
        title: `${formatCount(matched)} match the search but not the format filters`,
        hint: 'Switch a format back on to see them.',
        action: 'reset-filters',
        actionLabel: 'Show all formats',
      },
    };
  }
  return {
    heading: 'Results',
    count: `${formatCount(shown)} ${shown === 1 ? 'song' : 'songs'}`,
    hint: matched >= limit ? `Showing the best ${formatCount(limit)} matches — add another word to narrow.` : '',
    empty: null,
  };
}

/** Count badge and next-up line for the queue section. */
export function describeQueue({ length = 0, nextLabel = '' } = {}) {
  if (length <= 0) {
    return {
      count: 'Empty',
      hint: 'Songs you queue appear here, in order. Select a song and press Enter to add it.',
    };
  }
  return {
    count: `${formatCount(length)} ${length === 1 ? 'song' : 'songs'}`,
    hint: nextLabel ? `Up next: ${nextLabel}` : 'Queue is playing out — nothing waiting.',
  };
}

/**
 * Playback state chip plus which transport controls can do anything.
 *
 * A song that failed to load can be retried, so Play stays enabled and
 * relabels itself; seeking and stopping stay available for a loaded song.
 */
export function describePlayback({ song = null, playing = false, failed = false } = {}) {
  if (failed && song) {
    return {
      state: 'error',
      label: 'Playback failed',
      playDisabled: false,
      playLabel: 'Retry',
      stopDisabled: false,
      seekDisabled: true,
      mediaState: 'Playback failed',
    };
  }
  if (!song) {
    return {
      state: 'idle',
      label: 'Nothing loaded',
      playDisabled: true,
      playLabel: 'Play',
      stopDisabled: true,
      seekDisabled: true,
      mediaState: 'No song loaded',
    };
  }
  if (playing) {
    return {
      state: 'playing',
      label: 'Playing',
      playDisabled: false,
      playLabel: 'Pause',
      stopDisabled: false,
      seekDisabled: false,
      mediaState: 'Playing',
    };
  }
  return {
    state: 'paused',
    label: 'Paused',
    playDisabled: false,
    playLabel: 'Play',
    stopDisabled: false,
    seekDisabled: false,
    mediaState: 'Paused',
  };
}

/** App-level engine wording; the technical detail belongs in the tooltip. */
export function describeEngine({ ready = false, failed = false, version = '' } = {}) {
  if (failed) {
    return {
      text: 'Engine unavailable',
      title: 'The karaoke engine did not load. Reload the app to try again.',
    };
  }
  if (!ready) {
    return {
      text: 'Starting…',
      title: 'Loading the karaoke engine. The first run can take a few seconds.',
    };
  }
  return {
    text: 'Ready',
    title: version ? `Karaoke engine ready (${version})` : 'Karaoke engine ready',
  };
}

/** Settings that only take effect the next time the library is scanned. */
export const RESCAN_KEYS = [
  'look_inside_zips',
  'exclude_non_matching',
  'file_name_type',
  'include_patterns',
  'exclude_patterns',
];

/**
 * Turn an engine playback error into wording that names the fix.
 *
 * The engine raises short technical messages ("no audio file found for
 * this CDG"); a singer needs to know which file is missing.
 */
export function describePlaybackError(message = '') {
  const text = String(message || '').toLowerCase();
  if (text.includes('no audio file found')) {
    return 'no audio file next to it — add an .mp3, .ogg or .wav with the same name';
  }
  if (text.includes('video inside zip')) {
    return 'video inside a ZIP archive cannot play yet — extract the .mpg next to it';
  }
  if (text.includes('member not found') || text.includes('zip not loaded')) {
    return 'the file inside the ZIP archive could not be read';
  }
  if (text.includes('could not parse') || text.includes('parse')) {
    return 'the file looks damaged, or uses a variant that is not supported';
  }
  return String(message || 'unknown error');
}

export function needsRescan(patch = {}) {
  return RESCAN_KEYS.some((key) => Object.hasOwn(patch, key));
}

/** Queue position and duplicate count for one song, or an empty label. */
export function queueBadgeFor(song, queueItems = [], currentId = null) {
  const id = song?.id;
  const positions = [];
  queueItems.forEach((item, index) => {
    if (item?.id === id) positions.push(index + 1);
  });
  const playing = id != null && currentId != null && id === currentId;
  const parts = [];
  if (playing) parts.push('playing');
  if (positions.length) parts.push(positions.length > 1 ? `queued ×${positions.length}` : 'queued');
  return { positions, count: positions.length, playing, label: parts.join(' · ') };
}

/** Every keyboard binding the UI implements, in the order users see them. */
export const SHORTCUTS = [
  { keys: '/  or  Ctrl+K', description: 'Focus the search box' },
  { keys: '↑ / ↓', description: 'Move through the song list, or the queue when a queued song is selected' },
  { keys: 'Enter', description: 'Add the highlighted song to the queue' },
  { keys: 'Space', description: 'Play or pause (outside a text field)' },
  { keys: 'Ctrl+→  /  Ctrl+↓', description: 'Play the next queued song' },
  { keys: 'Ctrl+↑', description: 'Restart the current song, or play the previous one' },
  { keys: 'Delete', description: 'Remove the selected queue song' },
  { keys: 'Alt+↑ / Alt+↓', description: 'Move the selected queue song earlier or later' },
  { keys: 'Esc', description: 'Clear the search box, or leave the queue' },
];

export function writeTileRgba(tileData, rgba, width, x, y) {
  const TILE = 48;
  for (let row = 0; row < TILE; row++) {
    const src = row * TILE * 3;
    const dst = ((y * TILE + row) * width + x * TILE) * 4;
    for (let col = 0; col < TILE; col++) {
      rgba[dst + col * 4] = tileData[src + col * 3];
      rgba[dst + col * 4 + 1] = tileData[src + col * 3 + 1];
      rgba[dst + col * 4 + 2] = tileData[src + col * 3 + 2];
      rgba[dst + col * 4 + 3] = 255;
    }
  }
}
