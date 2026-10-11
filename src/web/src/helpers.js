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
  const filename = String((song && song.filename) || '');
  const stem = filename.replace(/\.[^.]+$/, '').toLowerCase();
  return stem ? `${stem}${ext}` : null;
}

/**
 * Zip member name of a companion file for a song inside a zip, or null.
 * Mirrors the `zip!member` id that readSongBytes() splits apart.
 */
export function companionMember(song, ext) {
  if (!song || !song.zip_name) return null;
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
  if (!lines || !lines.length) return { lineIdx: -1, litCount: 0 };
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
