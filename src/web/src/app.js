// PyKaraoke NG — web UI (vanilla ES module, no framework, no bundler).
//
// Architecture: this module owns the UI, file access and playback; Python
// (PyScript/Pyodide, see the `<script type="py">` block in index.html)
// owns the engine: library, search, CDG decoding, MIDI parsing.  The JS to
// Python boundary is the single `window.pykaraoke_api(name, ...args)`
// dispatcher.
//
// Pure helpers (song metadata, lyrics, CDG/MIDI maths) live in ./helpers.js
// and are unit-tested with vitest; this module holds the browser wiring,
// which runs only when a DOM exists.  index.html loads this module and the
// same file is served in both development and production.

import { CDG_WIDTH, CDG_HEIGHT, ZOOM_SCALES, formatTime, debounce, escapeHtml, songLabel, KIND_BADGE, ELRC_EXT, companionBaseName, companionMember, SongQueue, partClass, partLabel, buildLyricLines, highlightState, computeNoteTimeline, writeTileRgba } from './helpers.js';

let __app = null;

// ─────────────────────────────────────────────────────────────────────
// Browser wiring (only when a DOM exists)
// ─────────────────────────────────────────────────────────────────────

const isBrowser = typeof window !== 'undefined' && typeof document !== 'undefined';

if (isBrowser) {
  const $ = (id) => document.getElementById(id);

  const tauriCore = window.__TAURI__?.core; // {invoke, convertFileSrc} (withGlobalTauri)

  // Engine bridge
  function callApi(name, ...args) {
    const fn = window.pykaraoke_api;
    if (typeof fn !== 'function') throw new Error('engine not ready');
    const proxy = fn(name, ...args);
    if (proxy == null) return null;
    if (proxy.toJs) {
      const value = proxy.toJs({ dict_converter: Object.fromEntries });
      proxy.destroy();
      return value;
    }
    return proxy;
  }

  // ── State ──────────────────────────────────────────────────────────
  const state = {
    queue: new SongQueue(),
    settings: { volume: 0.75, sort: 'filename', zoom: 'int', lookInsideZips: true },
    files: new Map(),       // browser mode: relative path -> File
    pathByBase: new Map(),  // lowercased basename -> loadable path (both modes)
    results: [],
    selectedResult: -1,
    current: null,          // Song being played
    playing: false,
    durationMs: 0,
    lyricLines: null,
    parts: null,           // song-level duet names {a, b} (or null)
    lastLyricLine: -1,
    cdgKey: null,
    audioEl: null,
    videoEl: null,
    synth: null,
    songClock: 0,
    rafId: null,
    frameFn: null,
  };

  // ── File access ────────────────────────────────────────────────────
  async function readBytes(path) {
    if (tauriCore) {
      const res = await tauriCore.invoke('read_file', { path });
      if (res instanceof ArrayBuffer) return new Uint8Array(res);
      if (ArrayBuffer.isView(res)) return new Uint8Array(res.buffer, res.byteOffset, res.byteLength);
      if (Array.isArray(res)) return Uint8Array.from(res);
      throw new Error(`unexpected read_file response for ${path}`);
    }
    const file = state.files.get(path);
    if (!file) throw new Error(`file not loaded: ${path}`);
    return new Uint8Array(await file.arrayBuffer());
  }

  function mediaUrl(path) {
    if (tauriCore) return tauriCore.convertFileSrc(path);
    const file = state.files.get(path);
    if (!file) throw new Error(`file not loaded: ${path}`);
    return URL.createObjectURL(file);
  }

  /** Decode text bytes: UTF-8 first, fall back to Windows-1252. */
  function decodeText(bytes) {
    const utf8 = new TextDecoder('utf-8', { fatal: false }).decode(bytes);
    if (!utf8.includes('\uFFFD')) return utf8;
    return new TextDecoder('windows-1252').decode(bytes);
  }

  function resolveSongPath(song) {
    // Tauri: absolute path. Browser: webkitRelativePath.
    return song.path;
  }

  function resolveAudioPath(song) {
    if (song.audio_name) {
      const base = state.pathByBase.get(String(song.audio_name).toLowerCase());
      if (base) return base;
    }
    // Fallback: sibling file with the same stem and an audio extension.
    const stem = song.filename.replace(/\.[^.]+$/, '').toLowerCase();
    const candidates = ['.mp3', '.ogg', '.wav'];
    for (const ext of candidates) {
      const hit = state.pathByBase.get(`${stem}${ext}`);
      if (hit) return hit;
    }
    return null;
  }

  /** Bytes of the song's own file (.cdg/.kar/.mid/.mpg), reading through zips. */
  async function readSongBytes(song) {
    if (song.zip_name) {
      const zipPath = state.pathByBase.get(String(song.zip_name).toLowerCase());
      if (!zipPath) throw new Error(`zip not loaded: ${song.zip_name}`);
      const member = String(song.id).split('!').slice(1).join('!');
      const bytes = callApi('read_zip_member', song.zip_name, member);
      if (!bytes) throw new Error(`member not found in zip: ${member}`);
      return bytes;
    }
    return readBytes(resolveSongPath(song));
  }

  /**
   * Text of a companion file (e.g. ``.elrc``) for *song*, or null when it
   * is missing or unreadable — a companion file is always optional.
   */
  async function readCompanionText(song, ext) {
    try {
      if (song.zip_name) {
        const member = companionMember(song, ext);
        if (!member) return null;
        const bytes = callApi('read_zip_member', song.zip_name, member);
        if (!bytes?.length) return null;
        return decodeText(bytes);
      }
      const base = companionBaseName(song, ext);
      const path = base && state.pathByBase.get(base);
      if (!path) return null;
      return decodeText(await readBytes(path));
    } catch (err) {
      console.warn(`companion ${ext} read failed`, err);
      return null;
    }
  }

  /** Whether a companion .elrc (word timing) file exists for *song*. */
  function hasElrc(song) {
    if (song?.kind !== 'lrc') return false;
    if (song.zip_name) {
      const member = companionMember(song, ELRC_EXT);
      if (!member) return false;
      try {
        const names = callApi('zip_members', song.zip_name);
        return Array.isArray(names) &&
          names.some((name) => String(name).toLowerCase() === member.toLowerCase());
      } catch {
        return false; // engine not ready (or zip not loaded yet)
      }
    }
    const base = companionBaseName(song, ELRC_EXT);
    return !!(base && state.pathByBase.has(base));
  }

  // ── Engine / boot ──────────────────────────────────────────────────
  function waitFor(cond, timeoutMs) {
    return new Promise((resolve) => {
      const start = Date.now();
      const tick = () => {
        if (cond()) return resolve(true);
        if (Date.now() - start > timeoutMs) return resolve(false);
        setTimeout(tick, 100);
      };
      tick();
    });
  }

  async function boot() {
    setStatus('Loading engine (Pyodide)…');
    const ready = await waitFor(() => typeof window.pykaraoke_api === 'function', 120000);
    if (!ready) {
      setStatus('Engine failed to load — check the browser console');
      return;
    }
    const pyVer = window.pyodide?.version || '';
    const pyTag = pyVer ? ` (Pyodide ${pyVer})` : '';
    setEngineStatus(`PyScript ready${pyTag}`);
    await restoreState();
    await refreshSettings();
    renderQueue();
    setStatus(tauriCore ? 'Ready — desktop filesystem' : 'Ready — add a folder to scan');
  }

  async function restoreState() {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) callApi('from_json', saved);
      const queueIds = JSON.parse(localStorage.getItem(QUEUE_KEY) || '[]');
      const songs = callApi('library_songs')?.songs || [];
      const byId = new Map(songs.map((s) => [s.id, s]));
      state.queue = new SongQueue(queueIds.map((id) => byId.get(id)).filter(Boolean));
    } catch (err) {
      console.warn('restore failed', err);
    }
    renderLibraryCount();
  }

  async function refreshSettings() {
    const s = callApi('get_settings') || {};
    state.settings = {
      volume: Number(s.volume ?? 0.75),
      sort: s.sort || 'filename',
      zoom: s.cdg_zoom || 'int',
      lookInsideZips: s.look_inside_zips !== false,
      excludeNonMatching: !!s.exclude_non_matching,
      deriveSongInfo: s.derive_song_info !== false,
      fileNameType: Number(s.file_name_type ?? 3),
      includePatterns: Array.isArray(s.include_patterns) ? s.include_patterns : [],
      excludePatterns: Array.isArray(s.exclude_patterns) ? s.exclude_patterns : [],
    };
    $('volume-slider').value = Math.round(state.settings.volume * 100);
    $('volume-value').textContent = `${Math.round(state.settings.volume * 100)}%`;
    $('setting-sort').value = state.settings.sort;
    $('setting-zoom').value = state.settings.zoom;
    $('setting-zips').checked = state.settings.lookInsideZips;
    $('setting-exclude').checked = state.settings.excludeNonMatching;
    $('setting-derive').checked = state.settings.deriveSongInfo;
    $('setting-naming').value = String(state.settings.fileNameType);
    $('setting-include-patterns').value = state.settings.includePatterns.join(', ');
    $('setting-exclude-patterns').value = state.settings.excludePatterns.join(', ');
    applyZoom();
  }

  function persist() {
    try {
      localStorage.setItem(STORAGE_KEY, callApi('to_json'));
      localStorage.setItem(
        QUEUE_KEY,
        JSON.stringify(state.queue.items.map((s) => s.id)),
      );
    } catch (err) {
      console.warn('persist failed', err);
    }
  }

  // ── Scanning ───────────────────────────────────────────────────────
  async function scanEntries(entries, replace = false) {
    if (!entries.length) return;
    // Keep a basename index (lowercased) for audio/zip lookup.
    for (const e of entries) {
      const base = e.name.toLowerCase();
      if (!state.pathByBase.has(base)) state.pathByBase.set(base, e.path);
    }
    if (!tauriCore) {
      for (const file of window.__pickedFiles || []) {
        const path = file.webkitRelativePath || file.name;
        state.files.set(path, file);
        const base = file.name.toLowerCase();
        if (!state.pathByBase.has(base)) state.pathByBase.set(base, path);
      }
      window.__pickedFiles = [];
    }
    const result = callApi('scan_files', entries, replace);
    await scanZips(entries);
    await refreshSettings();
    renderLibraryCount();
    renderScanSummary();
    persist();
    setStatus(`Library: ${result.total} songs`);
    return result;
  }

  async function scanZips(entries) {
    const zips = entries.filter((e) => e.name.toLowerCase().endsWith('.zip'));
    const setting = callApi('get_settings') || {};
    if (!setting.look_inside_zips) return;
    for (const zip of zips) {
      try {
        const bytes = await readBytes(zip.path);
        const r = callApi('scan_zip', zip.name, bytes);
        setStatus(`Added ${r.added} songs from ${zip.name}`);
      } catch (err) {
        console.warn(`zip scan failed: ${zip.name}`, err);
      }
    }
  }

  // ── Rendering ──────────────────────────────────────────────────────
  function renderLibraryCount() {
    const total = callApi('library_songs')?.songs?.length || 0;
    $('library-count').textContent = `${total} songs`;
  }

  function parsePatternList(text) {
    return String(text).split(/[\n,]/).map((s) => s.trim()).filter(Boolean);
  }

  const SCAN_CATEGORY_LABELS = {
    unsupported: 'unsupported',
    filtered: 'filtered',
    corrupt_archive: 'corrupt archive',
    unsupported_compression: 'unsupported compression',
    unreadable: 'unreadable',
    parse_failure: 'parse failure',
  };

  function renderScanSummary() {
    const el = $('scan-summary');
    let report = null;
    try { report = callApi('scan_report'); } catch { report = null; }
    if (!report || !(report.entries || []).length) {
      el.hidden = true;
      el.textContent = '';
      return;
    }
    const parts = [];
    for (const [key, n] of Object.entries(report.counts || {})) {
      if (n > 0) parts.push(`${n} ${SCAN_CATEGORY_LABELS[key] || key}`);
    }
    const shown = (report.entries || [])
      .filter((e) => e.category !== 'unsupported' && e.category !== 'filtered')
      .slice(0, 3)
      .map((e) => e.path);
    el.textContent = `Scan: ${parts.join(', ') || '0 issues'}`;
    if (shown.length) {
      el.textContent += ` — e.g. ${shown.join('; ')}`;
    }
    const clear = document.createElement('button');
    clear.className = 'btn btn-secondary btn-sm';
    clear.textContent = 'Dismiss';
    clear.addEventListener('click', () => {
      try { callApi('clear_scan_report'); } catch { /* engine may be gone */ }
      el.hidden = true;
      el.textContent = '';
    });
    el.append(' ', clear);
    el.hidden = false;
  }

  function renderResults() {
    const list = $('results-list');
    const datalist = $('search-results');
    const kindFilter = {
      cdg: $('filter-cdg').checked,
      kar: $('filter-kar').checked,
      mpg: $('filter-mpg').checked,
      lrc: $('filter-lrc').checked,
    };
    const visible = state.results.filter((s) => kindFilter[s.kind]);
    if (!state.results.length) {
      list.innerHTML = '<div class="no-results">Type to search your library</div>';
      datalist.innerHTML = '';
      state.selectedResult = -1;
      return;
    }
    if (!visible.length) {
      list.innerHTML = '<div class="no-results">No results match the filters</div>';
      datalist.innerHTML = '';
      state.selectedResult = -1;
      return;
    }
    list.innerHTML = '';
    datalist.innerHTML = '';
    visible.forEach((song, i) => {
      // Accessible path: native datalist option bound to the search input.
      const option = document.createElement('option');
      option.value = songLabel(song);
      option.label = song.filename;
      datalist.appendChild(option);

      const row = document.createElement('div');
      row.className = 'song-row';
      row.dataset.index = String(i);

      const info = document.createElement('div');
      info.className = 'song-row-info';
      info.innerHTML = `<span class="song-row-title">${escapeHtml(songLabel(song))}</span>` +
        `<span class="song-row-file muted">${escapeHtml(song.filename)}</span>`;

      const badge = document.createElement('span');
      badge.className = `badge badge-${song.kind}`;
      badge.textContent = KIND_BADGE[song.kind] || song.kind;
      if (hasElrc(song)) {
        badge.textContent = 'ELRC';
        badge.title = 'Word-level timing (.elrc)';
      }

      const play = document.createElement('button');
      play.className = 'btn btn-icon btn-row-play';
      play.title = 'Play now';
      play.textContent = '▶';
      play.addEventListener('click', (e) => {
        e.stopPropagation();
        playSong(song);
      });

      row.append(badge, info, play);
      row.addEventListener('click', () => enqueue(song));
      row.addEventListener('dblclick', () => playSong(song));
      list.appendChild(row);
    });
    state.selectedResult = -1;
  }

  function selectResult(i) {
    const rows = $('results-list').querySelectorAll('.song-row');
    if (!rows.length) return;
    state.selectedResult = (i + rows.length) % rows.length;
    rows.forEach((r, idx) => {
      r.classList.toggle('selected', idx === state.selectedResult);
    });
    rows[state.selectedResult].scrollIntoView({ block: 'nearest' });
  }

  function renderQueue() {
    const list = $('queue-list');
    if (!state.queue.length) {
      list.innerHTML = '<li class="no-results">Queue is empty — add songs with Enter</li>';
      return;
    }
    list.innerHTML = '';
    state.queue.items.forEach((song, i) => {
      const row = document.createElement('li');
      row.className = 'song-row queue-row';
      const info = document.createElement('div');
      info.className = 'song-row-info';
      info.innerHTML = `<span class="song-row-title">${i + 1}. ${escapeHtml(songLabel(song))}</span>` +
        `<span class="song-row-file muted">${escapeHtml(song.filename)}</span>`;
      const remove = document.createElement('button');
      remove.className = 'btn btn-icon';
      remove.title = 'Remove (Delete)';
      remove.textContent = '✕';
      remove.addEventListener('click', (e) => {
        e.stopPropagation();
        state.queue.removeAt(i);
        renderQueue();
        persist();
      });
      row.append(info, remove);
      row.addEventListener('dblclick', () => playSong(song));
      list.appendChild(row);
    });
  }

  function setStatus(msg) {
    $('status-message').textContent = msg;
  }

  function setEngineStatus(msg) {
    $('engine-status').textContent = msg;
  }

  function setPlaying(song) {
    state.current = song;
    $('current-song-title').textContent = song ? songLabel(song) : '—';
    $('current-song-artist').textContent = song ? song.filename : '';
    $('play-btn').textContent = state.playing ? '⏸' : '▶';
    $('stage-empty').style.display = song ? 'none' : '';
  }

  // ── Stage rendering (CDG) ──────────────────────────────────────────
  const canvas = $('cdg-canvas');
  const stageCtx = canvas.getContext('2d');
  const fullFrame = new ImageData(CDG_WIDTH, CDG_HEIGHT);
  const blitCanvas = document.createElement('canvas');
  blitCanvas.width = CDG_WIDTH;
  blitCanvas.height = CDG_HEIGHT;
  const blitCtx = blitCanvas.getContext('2d');

  function applyZoom() {
    const scale = ZOOM_SCALES[state.settings.zoom] || 1;
    canvas.width = Math.round(CDG_WIDTH * scale);
    canvas.height = Math.round(CDG_HEIGHT * scale);
    canvas.style.width = `${canvas.width}px`;
    canvas.style.height = `${canvas.height}px`;
  }

  function drawCdgUpdate(update) {
    if (update?.border) {
      const [r, g, b] = update.border;
      stageCtx.fillStyle = `rgb(${r},${g},${b})`;
      stageCtx.fillRect(0, 0, canvas.width, canvas.height);
    }
    if (update?.tiles) {
      for (const tile of update.tiles) {
        writeTileRgba(tile.data, fullFrame.data, CDG_WIDTH, tile.x, tile.y);
      }
    }
    // Blit the full 288x192 frame, scaled by the canvas transform.
    blitCtx.putImageData(fullFrame, 0, 0);
    stageCtx.imageSmoothingEnabled = false;
    stageCtx.drawImage(blitCanvas, 0, 0, canvas.width, canvas.height);
  }

  // ── Lyrics rendering ───────────────────────────────────────────────
  function renderLyricLines() {
    const box = $('lyrics');
    if (!state.lyricLines?.length) {
      box.innerHTML = '';
      box.style.display = 'none';
      return;
    }
    box.style.display = '';
    state.lastLyricLine = -1;
  }

  function updateLyrics(ms) {
    const lines = state.lyricLines;
    if (!lines?.length) return;
    const { lineIdx, litCount } = highlightState(lines, ms);
    if (lineIdx !== state.lastLyricLine) {
      state.lastLyricLine = lineIdx;
      const box = $('lyrics');
      box.innerHTML = '';
      for (const line of lines.slice(lineIdx, lineIdx + 2)) {
        const div = document.createElement('div');
        div.className = 'lyric-line';
        const cls = partClass(line.part);
        if (cls) {
          div.classList.add(cls);
          div.dataset.part = line.part;
          // The part chip labels who sings this line (A, B or shared).
          const chip = document.createElement('span');
          chip.className = 'lyric-part';
          chip.textContent = partLabel(state.parts, line.part);
          div.appendChild(chip);
        }
        if (line !== lines[lineIdx]) div.classList.add('lyric-next');
        line.syllables.forEach((syl) => {
          const span = document.createElement('span');
          span.className = 'lyric-syl';
          span.dataset.ms = String(syl.ms);
          span.textContent = syl.text.trimEnd() + '\u00A0';
          div.appendChild(span);
        });
        box.appendChild(div);
      }
    }
    // Toggle lit state per syllable, order-independent.  Syllables with
    // ms > current are unlit, so a backward seek clears stale highlights.
    const els = $('lyrics').querySelectorAll('.lyric-syl');
    els.forEach((el, i) => el.classList.toggle('lit', i < litCount));
  }

  // ── Transport ──────────────────────────────────────────────────────
  async function playSong(song) {
    stopPlayback();
    state.playing = true;
    setPlaying(song);
    $('stage-empty').style.display = 'none';
    try {
      if (song.kind === 'cdg') {
        await playCdg(song);
      } else if (song.kind === 'kar') {
        await playKar(song);
      } else if (song.kind === 'lrc') {
        await playLrc(song);
      } else {
        await playMpg(song);
      }
    } catch (err) {
      console.error(err);
      // Only tear down if this song is still the current one — a rapid
      // play-next can supersede it before its (async) setup settles.
      if (state.current === song) {
        setStatus(`Playback error: ${err.message}`);
        state.playing = false;
        setPlaying(song);
      }
    }
  }

  /** Drive per-frame work (transport + kind-specific rendering) via rAF. */
  function startLoop(frameFn) {
    cancelAnimationFrame(state.rafId);
    const tick = () => {
      if (!state.playing) return;
      frameFn();
      state.rafId = requestAnimationFrame(tick);
    };
    state.rafId = requestAnimationFrame(tick);
  }

  async function playCdg(song) {
    // Resolve the audio first: a .cdg without a matching audio file cannot
    // play, and opening the decoder before this check would leak it.
    const audioPath = resolveAudioPath(song);
    if (!audioPath) throw new Error('no audio file found for this CDG');
    const cdgBytes = await readSongBytes(song);
    state.cdgKey = callApi('cdg_open', song.id, cdgBytes);
    const audio = new Audio(mediaUrl(audioPath));
    audio.volume = state.settings.volume;
    audio.addEventListener('ended', onSongEnded);
    audio.addEventListener('loadedmetadata', () => {
      state.durationMs = audio.duration * 1000;
      $('time-total').textContent = formatTime(state.durationMs);
    });
    state.audioEl = audio;
    await audio.play();
    drawCdgUpdate(callApi('cdg_update', state.cdgKey, 0));
    startCdgLoop();
  }

  function startCdgLoop() {
    state.frameFn = () => {
      if (!state.audioEl) return;
      const ms = state.audioEl.currentTime * 1000;
      updateTransport(ms);
      try {
        const update = callApi('cdg_update', state.cdgKey, ms);
        if (update) drawCdgUpdate(update);
      } catch (err) {
        console.warn('cdg update failed', err);
      }
    };
    startLoop(state.frameFn);
  }

  async function playKar(song) {
    const bytes = await readSongBytes(song);
    const parsed = callApi('parse_midi', bytes);
    if (!parsed || parsed.error) throw new Error(parsed?.error || 'could not parse MIDI');
    state.durationMs = parsed.duration_ms || 0;
    $('time-total').textContent = formatTime(state.durationMs);
    // MIDI/KAR lyrics carry no duet parts, so nothing to label.
    state.parts = null;
    state.lyricLines = buildLyricLines(parsed.lyrics || []);
    renderLyricLines();
    state.synth = new MidiSynth(parsed);
    state.synth.onEnded = onSongEnded;
    state.synth.setVolume(state.settings.volume);
    state.synth.start();
    startSynthLoop();
  }

  function startSynthLoop() {
    state.frameFn = () => {
      if (!state.synth) return;
      const ms = state.synth.currentMs();
      updateTransport(ms);
      updateLyrics(ms);
    };
    startLoop(state.frameFn);
  }

  async function playLrc(song) {
    const bytes = await readSongBytes(song);
    // Word-level timing lives in a companion .elrc next to the .lrc.
    const elrcText = await readCompanionText(song, ELRC_EXT);
    const parsed = callApi('parse_lrc', decodeText(bytes), elrcText);
    if (!parsed || parsed.error) throw new Error(parsed?.error || 'could not parse LRC lyrics');
    const audioPath = resolveAudioPath(song);
    if (!audioPath) throw new Error('no audio file found for this LRC');
    // Song-level duet singers ([pa:]/[pb:]) label the per-line part chips.
    state.parts = parsed.parts || null;
    state.lyricLines = buildLyricLines(parsed.lyrics || []);
    renderLyricLines();
    const audio = new Audio(mediaUrl(audioPath));
    audio.volume = state.settings.volume;
    audio.addEventListener('ended', onSongEnded);
    audio.addEventListener('loadedmetadata', () => {
      state.durationMs = audio.duration * 1000;
      $('time-total').textContent = formatTime(state.durationMs);
    });
    state.audioEl = audio;
    await audio.play();
    state.frameFn = () => {
      if (!state.audioEl) return;
      const ms = state.audioEl.currentTime * 1000;
      updateTransport(ms);
      updateLyrics(ms);
    };
    startLoop(state.frameFn);
  }

  async function playMpg(song) {
    if (song.zip_name) throw new Error('video inside zip is not supported');
    const video = document.createElement('video');
    video.src = mediaUrl(resolveSongPath(song));
    video.volume = state.settings.volume;
    video.style.width = '100%';
    video.addEventListener('ended', onSongEnded);
    video.addEventListener('loadedmetadata', () => {
      state.durationMs = video.duration * 1000;
      $('time-total').textContent = formatTime(state.durationMs);
    });
    state.videoEl = video;
    $('video-slot').innerHTML = '';
    $('video-slot').appendChild(video);
    await video.play();
    startVideoLoop();
  }

  function startVideoLoop() {
    state.frameFn = () => {
      if (!state.videoEl) return;
      updateTransport(state.videoEl.currentTime * 1000);
    };
    startLoop(state.frameFn);
  }

  function updateTransport(ms) {
    state.songClock = ms;
    $('time-current').textContent = formatTime(ms);
    const max = state.durationMs || 1;
    $('progress-slider').value = Math.min(1000, Math.round((ms / max) * 1000));
  }

  function pauseMedia() {
    state.playing = false;
    if (state.audioEl) state.audioEl.pause();
    if (state.synth) state.synth.pause();
    if (state.videoEl) state.videoEl.pause();
    cancelAnimationFrame(state.rafId);
    $('play-btn').textContent = '▶';
  }

  function resumeMedia() {
    state.playing = true;
    $('play-btn').textContent = '⏸';
    if (state.audioEl) state.audioEl.play();
    if (state.synth) state.synth.resume();
    if (state.videoEl) state.videoEl.play();
    if (state.frameFn) startLoop(state.frameFn);
  }

  function togglePlay() {
    if (!state.current) return;
    if (state.playing) pauseMedia();
    else resumeMedia();
  }

  function stopPlayback() {
    state.playing = false;
    cancelAnimationFrame(state.rafId);
    state.frameFn = null;
    if (state.audioEl) {
      state.audioEl.pause();
      state.audioEl.src = '';
      state.audioEl = null;
    }
    if (state.synth) {
      state.synth.stop();
      state.synth = null;
    }
    if (state.videoEl) {
      state.videoEl.pause();
      state.videoEl.src = '';
      state.videoEl = null;
      $('video-slot').innerHTML = '';
    }
    if (state.cdgKey) {
      callApi('cdg_close', state.cdgKey);
      state.cdgKey = null;
    }
    state.lyricLines = null;
    state.parts = null;
    $('lyrics').innerHTML = '';
    $('lyrics').style.display = 'none';
    state.durationMs = 0;
    $('time-current').textContent = '0:00';
    $('time-total').textContent = '0:00';
    $('progress-slider').value = 0;
    $('play-btn').textContent = '▶';
  }

  function onSongEnded() {
    const next = state.queue.next();
    renderQueue();
    persist();
    if (next) playSong(next);
    else {
      stopPlayback();
      setPlaying(null);
      setStatus('Queue finished');
    }
  }

  function seekTo(ms) {
    ms = Math.max(0, ms);
    if (state.audioEl) state.audioEl.currentTime = ms / 1000;
    if (state.cdgKey) {
      callApi('cdg_seek', state.cdgKey, ms);
      drawCdgUpdate(callApi('cdg_update', state.cdgKey, ms));
    }
    if (state.synth) state.synth.seek(ms);
    if (state.videoEl) state.videoEl.currentTime = ms / 1000;
    updateTransport(ms);
    // Refresh the displayed lyric immediately (also while paused, when the
    // animation loop is not running).
    updateLyrics(ms);
  }

  function enqueue(song) {
    state.queue.push(song);
    renderQueue();
    persist();
    setStatus(`Queued: ${songLabel(song)}`);
  }

  function playNext() {
    if (state.queue.length) {
      const next = state.queue.next();
      renderQueue();
      persist();
      playSong(next);
    } else {
      setStatus('Queue is empty');
    }
  }

  function playPrev() {
    if (!state.current) return;
    const ms = state.songClock;
    if (ms > 5000) seekTo(0);
    else if (state.queue.length) {
      const next = state.queue.next();
      renderQueue();
      persist();
      playSong(next);
    }
  }

  // ── Settings ───────────────────────────────────────────────────────
  function updateSettings(patch) {
    Object.assign(state.settings, patch);
    callApi('set_settings', patch);
    persist();
    if (patch.volume !== undefined) {
      const v = state.settings.volume;
      if (state.audioEl) state.audioEl.volume = v;
      if (state.videoEl) state.videoEl.volume = v;
      if (state.synth) state.synth.setVolume(v);
    }
    if (patch.cdg_zoom !== undefined) {
      // The settings panel patches the engine key (cdg_zoom); mirror it into
      // the local settings so the canvas resizes immediately.
      state.settings.zoom = patch.cdg_zoom;
      applyZoom();
    }
    if (patch.zoom !== undefined) applyZoom();
  }

  // Keyboard-first controls: one small handler per binding, dispatched
  // in the same order as before (a keydown may trigger several of them,
  // e.g. Ctrl+ArrowDown both moves selection and reorders the queue).
  function focusSearchKey(e, searchInput) {
    if (e.key !== '/' && !(e.key === 'k' && (e.ctrlKey || e.metaKey))) return false;
    e.preventDefault();
    searchInput.focus();
    return true;
  }

  function dismissSearchKey(e, inInput, searchInput) {
    if (e.key !== 'Escape' || !inInput) return false;
    e.target.value = '';
    if (e.target === searchInput) {
      state.results = [];
      renderResults();
    }
    e.target.blur();
    return true;
  }

  function togglePlaybackKey(e, inInput) {
    if (e.key !== ' ' || inInput) return false;
    e.preventDefault();
    togglePlay();
    return true;
  }

  function enqueueSelectedKey(e, inInput) {
    if (e.key !== 'Enter' || inInput || state.selectedResult < 0) return false;
    const song = visibleResults()[state.selectedResult];
    if (song) enqueue(song);
    return true;
  }

  function moveSelectionKey(e, inInput) {
    if (inInput) return;
    const count = Math.max(1, visibleResults().length);
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      selectResult((state.selectedResult + 1) % count);
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      selectResult((state.selectedResult - 1 + count) % count);
    }
  }

  function deleteQueueItemKey(e, inInput) {
    if (e.key !== 'Delete' || inInput) return;
    const list = $('queue-list');
    const selected = list.querySelector('.selected');
    if (!selected) return;
    const idx = [...list.children].indexOf(selected);
    state.queue.removeAt(idx);
    renderQueue();
    persist();
  }

  function reorderQueueKey(e) {
    if (e.key === 'ArrowDown' && e.ctrlKey) {
      e.preventDefault();
      state.queue.move(0, 1);
      renderQueue();
      persist();
    }
    if (e.key === 'ArrowUp' && e.ctrlKey) {
      e.preventDefault();
      state.queue.move(state.queue.length - 1, -1);
      renderQueue();
      persist();
    }
  }

  function nextSongKey(e) {
    if (e.key !== 'ArrowRight' || !e.ctrlKey) return;
    e.preventDefault();
    playNext();
  }

  // ── UI wiring ──────────────────────────────────────────────────────
  const STORAGE_KEY = 'pykaraoke-ng:state';
  const QUEUE_KEY = 'pykaraoke-ng:queue';

  function wireUi() {
    // Folder picking.
    $('add-folder-btn').addEventListener('click', pickFolder);
    $('scan-library-btn').addEventListener('click', rescanFolders);
    $('replace-library-btn').addEventListener('click', replaceLibrary);
    $('export-library-btn').addEventListener('click', exportLibrary);
    $('import-library-btn').addEventListener('click', () => $('import-library-picker').click());
    $('import-library-picker').addEventListener('change', async (e) => {
      const file = e.target.files?.[0];
      e.target.value = '';
      if (!file) return;
      try {
        const text = await file.text();
        const result = callApi('import_json', text);
        if (result?.ok) {
          await refreshSettings();
          renderLibraryCount();
          renderResults();
          persist();
          const total = callApi('library_songs')?.songs?.length || 0;
          setStatus(`Library imported: ${total} songs`);
        } else {
          setStatus(`Import failed: ${result?.error || 'unknown error'}`);
        }
      } catch (err) {
        setStatus(`Import failed: ${err.message}`);
      }
    });
    $('folder-picker').addEventListener('change', async (e) => {
      const files = [...e.target.files];
      window.__pickedFiles = files;
      const entries = files.map((f) => ({
        name: f.name,
        path: f.webkitRelativePath || f.name,
        size: f.size,
      }));
      await scanEntries(entries);
      e.target.value = '';
    });

    // Search.
    const searchInput = $('search-input');
    searchInput.addEventListener('input', debounce(async () => {
      const q = searchInput.value.trim();
      if (!q) {
        state.results = [];
        renderResults();
        return;
      }
      try {
        const r = callApi('search', q, 500);
        state.results = r?.results || [];
      } catch (err) {
        state.results = [];
        setStatus(`Search error: ${err.message}`);
      }
      renderResults();
    }, 150));

    // Accessible selection: a datalist option picked from the search input
    // enqueues the matching result (mirrors clicking a result row).
    searchInput.addEventListener('change', () => {
      const label = searchInput.value.trim();
      if (!label) return;
      const song = visibleResults().find((s) => songLabel(s) === label);
      if (!song) return;
      enqueue(song);
      searchInput.value = '';
    });

    // Transport.
    $('play-btn').addEventListener('click', togglePlay);
    $('stop-btn').addEventListener('click', () => {
      stopPlayback();
      setPlaying(null);
    });
    $('next-btn').addEventListener('click', playNext);
    $('prev-btn').addEventListener('click', playPrev);
    $('rewind-btn').addEventListener('click', () => seekTo(state.songClock - 5000));
    $('ff-btn').addEventListener('click', () => seekTo(state.songClock + 5000));
    $('progress-slider').addEventListener('input', (e) => {
      const max = state.durationMs || 1;
      seekTo((Number(e.target.value) / 1000) * max);
    });

    // Volume.
    $('volume-slider').addEventListener('input', (e) => {
      const v = Number(e.target.value) / 100;
      $('volume-value').textContent = `${e.target.value}%`;
      updateSettings({ volume: v });
    });

    // Queue.
    $('clear-queue-btn').addEventListener('click', () => {
      state.queue.clear();
      renderQueue();
      persist();
    });

    // Settings panel (inline, no modal).
    $('settings-btn').addEventListener('click', () => {
      $('settings-panel').hidden = !$('settings-panel').hidden;
    });
    $('setting-sort').addEventListener('change', (e) => updateSettings({ sort: e.target.value }));
    $('setting-zoom').addEventListener('change', (e) => updateSettings({ cdg_zoom: e.target.value }));
    $('setting-zips').addEventListener('change', (e) => updateSettings({ look_inside_zips: e.target.checked }));
    $('setting-exclude').addEventListener('change', (e) => updateSettings({ exclude_non_matching: e.target.checked }));
    $('setting-derive').addEventListener('change', (e) => updateSettings({ derive_song_info: e.target.checked }));
    $('setting-naming').addEventListener('change', (e) => updateSettings({ file_name_type: Number(e.target.value) }));
    $('setting-include-patterns').addEventListener('change', (e) => updateSettings({ include_patterns: parsePatternList(e.target.value) }));
    $('setting-exclude-patterns').addEventListener('change', (e) => updateSettings({ exclude_patterns: parsePatternList(e.target.value) }));

    // Kind filters.
    ['filter-cdg', 'filter-kar', 'filter-mpg', 'filter-lrc'].forEach((id) => {
      $(id).addEventListener('change', renderResults);
    });

    document.addEventListener('keydown', (e) => {
      const target = e.target;
      const inInput = target && (target.tagName === 'INPUT' || target.tagName === 'SELECT');
      if (focusSearchKey(e, searchInput)) return;
      if (dismissSearchKey(e, inInput, searchInput)) return;
      if (togglePlaybackKey(e, inInput)) return;
      if (enqueueSelectedKey(e, inInput)) return;
      moveSelectionKey(e, inInput);
      deleteQueueItemKey(e, inInput);
      reorderQueueKey(e);
      nextSongKey(e);
    });
  }

  function visibleResults() {
    const kindFilter = {
      cdg: $('filter-cdg').checked,
      kar: $('filter-kar').checked,
      mpg: $('filter-mpg').checked,
      lrc: $('filter-lrc').checked,
    };
    return state.results.filter((s) => kindFilter[s.kind]);
  }

  async function pickFolder() {
    if (tauriCore) {
      try {
        const path = await tauriCore.invoke('pick_folder');
        if (!path) return;
        const entries = await tauriCore.invoke('list_folder', { path });
        const s = callApi('get_settings') || {};
        const folders = Array.isArray(s.folders) ? s.folders : [];
        if (!folders.includes(path)) updateSettings({ folders: [...folders, path] });
        await scanEntries(entries);
      } catch (err) {
        setStatus(`Folder error: ${err.message}`);
      }
    } else {
      $('folder-picker').click();
    }
  }

  async function rescanFolders() {
    const s = callApi('get_settings') || {};
    const folders = s.folders || [];
    if (!folders.length) {
      setStatus('No folders configured — use ＋ Folder');
      return;
    }
    if (!tauriCore) {
      setStatus('In the browser, re-pick the folder to reload files');
      $('folder-picker').click();
      return;
    }
    for (const folder of folders) {
      try {
        const entries = await tauriCore.invoke('list_folder', { path: folder });
        await scanEntries(entries);
      } catch (err) {
        setStatus(`Scan error for ${folder}: ${err.message}`);
      }
    }
  }

  async function collectLibraryEntries() {
    if (tauriCore) {
      const s = callApi('get_settings') || {};
      const folders = s.folders || [];
      const all = [];
      for (const folder of folders) {
        try {
          all.push(...(await tauriCore.invoke('list_folder', { path: folder })));
        } catch (err) {
          setStatus(`Scan error for ${folder}: ${err.message}`);
        }
      }
      return all;
    }
    // Browser mode: rebuild entries from the kept File handles.
    return [...state.files.entries()].map(([path, file]) => ({
      name: file.name,
      path,
      size: file.size,
    }));
  }

  async function replaceLibrary() {
    const entries = await collectLibraryEntries();
    if (!entries.length) {
      setStatus('Nothing to rescan — use ＋ Folder (or re-pick in the browser) first');
      return;
    }
    await scanEntries(entries, true);
    const total = callApi('library_songs')?.songs?.length || 0;
    setStatus(`Library replaced: ${total} songs`);
  }

  function exportLibrary() {
    try {
      const payload = callApi('export_json');
      const blob = new Blob([payload], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'pykaraoke-library.json';
      a.click();
      URL.revokeObjectURL(url);
      setStatus('Library exported');
    } catch (err) {
      setStatus(`Export failed: ${err.message}`);
    }
  }

  // ── MidiSynth: WebAudio-backed KAR playback ────────────────────────
  class MidiSynth {
    constructor(parsed) {
      this.notes = parsed.notes || [];
      this.programs = parsed.programs || {};
      this.durationMs = parsed.duration_ms || 0;
      this.timeline = computeNoteTimeline(this.notes, this.programs);
      this.ctx = new AudioContext();
      this.master = this.ctx.createGain();
      this.master.gain.value = 0.75;
      this.master.connect(this.ctx.destination);
      this.t0 = 0;
      this.nextIndex = 0;
      this.paused = false;
      this.timer = null;
      this.onEnded = null;
    }

    start() {
      this.ctx.resume();
      this.t0 = this.ctx.currentTime;
      this.nextIndex = 0;
      this.paused = false;
      this._schedule();
    }

    resume() {
      if (!this.paused) return;
      this.paused = false;
      this.t0 = this.ctx.currentTime - this.currentMs() / 1000;
      this._schedule();
    }

    pause() {
      this.paused = true;
      clearTimeout(this.timer);
      this.timer = null;
    }

    stop() {
      this.paused = true;
      clearTimeout(this.timer);
      this.timer = null;
      this.ctx.close().catch(() => {});
    }

    seek(ms) {
      clearTimeout(this.timer);
      this.nextIndex = this.timeline.findIndex((n) => n.startMs >= ms);
      if (this.nextIndex < 0) this.nextIndex = this.timeline.length;
      this.t0 = this.ctx.currentTime - ms / 1000;
      if (!this.paused) this._schedule();
    }

    currentMs() {
      return Math.max(0, (this.ctx.currentTime - this.t0) * 1000);
    }

    setVolume(v) {
      this.master.gain.value = v;
    }

    _schedule() {
      clearTimeout(this.timer);
      this.timer = null;
      const lookaheadMs = 200;
      const now = this.currentMs();
      while (
        this.nextIndex < this.timeline.length &&
        this.timeline[this.nextIndex].startMs <= now + lookaheadMs
      ) {
        this._play(this.timeline[this.nextIndex], now);
        this.nextIndex++;
      }
      if (this.nextIndex < this.timeline.length) {
        this.timer = setTimeout(() => this._schedule(), 40);
      } else if (now >= this.durationMs && this.durationMs > 0) {
        if (this.onEnded) this.onEnded();
      } else {
        this.timer = setTimeout(() => this._schedule(), 40);
      }
    }

    _play(note, now) {
      const t = this.t0 + note.startMs / 1000;
      const dur = (note.endMs - note.startMs) / 1000;
      if (note.drum) {
        this._playDrum(t, note.gain);
        return;
      }
      const osc = this.ctx.createOscillator();
      osc.type = note.type;
      osc.frequency.value = note.freq;
      const gain = this.ctx.createGain();
      const peak = note.gain;
      gain.gain.setValueAtTime(0.0001, t);
      gain.gain.exponentialRampToValueAtTime(peak, t + 0.008);
      gain.gain.setValueAtTime(peak, t + Math.max(0, dur - 0.06));
      gain.gain.exponentialRampToValueAtTime(0.0001, t + dur + 0.02);
      osc.connect(gain).connect(this.master);
      osc.start(t);
      osc.stop(t + dur + 0.05);
    }

    _playDrum(t, gain) {
      const buffer = this.ctx.createBuffer(1, Math.floor(this.ctx.sampleRate * 0.12), this.ctx.sampleRate);
      const data = buffer.getChannelData(0);
      // White noise for the drum voice: cryptographic randomness (not
      // Math.random) so the generator choice is audit-clean.
      const rand = new Uint32Array(data.length);
      crypto.getRandomValues(rand);
      for (let i = 0; i < data.length; i++) {
        data[i] = ((rand[i] / 0xffffffff) * 2 - 1) * Math.pow(1 - i / data.length, 2);
      }
      const src = this.ctx.createBufferSource();
      src.buffer = buffer;
      const g = this.ctx.createGain();
      g.gain.value = gain;
      src.connect(g).connect(this.master);
      src.start(t);
    }
  }

  // Test hook: expose the wired app for DOM-level tests.  Production uses the
  // same boot()/wireUi() path via the DOMContentLoaded listener below.
  __app = { boot, wireUi, state, callApi, setStatus, setEngineStatus };

  // Boot.
  document.addEventListener('DOMContentLoaded', () => {
    wireUi();
    boot();
  });
}
export const app = __app;
