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

import { CDG_WIDTH, CDG_HEIGHT, ZOOM_SCALES, formatTime, debounce, songLabel, KIND_BADGE, ELRC_EXT, companionBaseName, companionMember, SongQueue, partClass, partLabel, buildLyricLines, highlightState, computeNoteTimeline, writeTileRgba, formatCount, BROWSE_LIMIT, describeScanReport, describeResults, describeQueue, describePlayback, describeEngine, describePlaybackError, needsRescan, queueBadgeFor, SHORTCUTS } from './helpers.js';

let __app = null;

// ─────────────────────────────────────────────────────────────────────
// Browser wiring (only when a DOM exists)
// ─────────────────────────────────────────────────────────────────────

const isBrowser = typeof window !== 'undefined' && typeof document !== 'undefined';

if (isBrowser) {
  const $ = (id) => document.getElementById(id);

  const tauriCore = window.__TAURI__?.core; // {invoke, convertFileSrc} (withGlobalTauri)
  const SEARCH_LIMIT = 500; // most matches the engine returns for one query

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
    results: [],            // current match set: search hits, or the browse slice
    query: '',              // active search text ('' = browsing the library)
    selectedResult: -1,
    selectedQueue: -1,      // queue row the keyboard acts on (-1 = the song list)
    browse: null,           // cached first BROWSE_LIMIT songs (null = stale)
    libraryCount: 0,
    playingFailed: false,   // last load failed; Play becomes Retry
    busy: false,            // a scan is running: library actions are disabled
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
    setStatus('Starting…');
    setEngineStatus(describeEngine({ ready: false }));
    renderShortcuts();
    const ready = await waitFor(() => typeof window.pykaraoke_api === 'function', 120000);
    if (!ready) {
      setEngineStatus(describeEngine({ failed: true }));
      setStatus('Karaoke engine unavailable', { kind: 'error' });
      notify('The karaoke engine did not load. Reload the window to try again.', {
        kind: 'error',
        timeout: 0,
      });
      return;
    }
    const pyVer = window.pyodide?.version || '';
    setEngineStatus(describeEngine({ ready: true, version: pyVer ? `Pyodide ${pyVer}` : '' }));
    $('engine-detail').textContent = `Engine: ${pyVer ? `Pyodide ${pyVer}` : 'PyScript'} · runs offline in this window`;
    await restoreState();
    await refreshSettings();
    renderQueue();
    renderTransport();
    const total = state.libraryCount;
    setStatus(
      total
        ? `Ready — ${formatCount(total)} ${total === 1 ? 'song' : 'songs'} in the library`
        : 'Ready — add a folder to scan',
    );
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
    await refreshLibraryViews();
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
    renderLibraryFolders();
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
  /** Disable the library actions while a scan is running. */
  function setBusy(busy) {
    state.busy = busy;
    for (const id of [
      'scan-library-btn',
      'replace-library-btn',
      'import-library-btn',
      'export-library-btn',
      'add-folder-btn',
    ]) {
      const el = $(id);
      if (el) el.disabled = busy;
    }
  }

  async function scanEntries(entries, replace = false) {
    if (!entries.length) {
      notify('That folder held no files — pick the folder that contains your karaoke files.', {
        kind: 'warn',
      });
      return null;
    }
    setBusy(true);
    setStatus(replace ? 'Replacing the library…' : 'Scanning library…');
    try {
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
      const zips = await scanZips(entries);
      await refreshSettings();
      await refreshLibraryViews();
      renderScanReport();
      persist();
      const total = state.libraryCount;
      const headline = `${replace ? 'Library replaced' : 'Library scan complete'} — ${formatCount(total)} ${total === 1 ? 'song' : 'songs'}`;
      setStatus(headline);
      if (zips.failed) {
        notify(`${formatCount(zips.failed)} ZIP archive${zips.failed === 1 ? '' : 's'} could not be opened.`, { kind: 'warn' });
      }
      notify(scanView ? scanView.summary : headline, {
        kind: scanView?.severity === 'warn' ? 'warn' : 'info',
        actionLabel: scanView ? 'See details' : '',
        onAction: scanView ? openScanDetails : null,
      });
      return result;
    } catch (err) {
      console.error(err);
      setStatus(`Library scan failed — ${err.message}`, { kind: 'error' });
      notify(`The library scan failed: ${err.message}`, { kind: 'error', timeout: 0 });
      return null;
    } finally {
      setBusy(false);
    }
  }

  async function scanZips(entries) {
    const zips = entries.filter((e) => e.name.toLowerCase().endsWith('.zip'));
    const setting = callApi('get_settings') || {};
    if (!setting.look_inside_zips) return { added: 0, failed: 0 };
    let added = 0;
    let failed = 0;
    for (const zip of zips) {
      try {
        const bytes = await readBytes(zip.path);
        const r = callApi('scan_zip', zip.name, bytes);
        added += r?.added || 0;
      } catch (err) {
        failed += 1;
        console.warn(`zip scan failed: ${zip.name}`, err);
      }
    }
    return { added, failed };
  }

  // ── Rendering ──────────────────────────────────────────────────────
  function countLibrary() {
    try { return callApi('library_songs')?.songs?.length || 0; } catch { return 0; }
  }

  function renderLibraryCount() {
    const total = state.libraryCount;
    $('library-count').textContent = total
      ? `${formatCount(total)} ${total === 1 ? 'song' : 'songs'}`
      : 'No songs yet';
  }

  /** Which folders a rescan re-reads, so the button is never a mystery. */
  function renderLibraryFolders() {
    const el = $('library-folders');
    if (!el) return;
    let folders = [];
    try { folders = callApi('get_settings')?.folders || []; } catch { folders = []; }
    el.textContent = folders.length
      ? `Folders: ${folders.join(' · ')}`
      : 'No folders yet — use Add folder to choose the folder that holds your karaoke files.';
  }

  /** Re-read the library after any change: count, folders and song list. */
  function refreshLibraryViews() {
    state.browse = null;
    state.libraryCount = countLibrary();
    renderLibraryCount();
    renderLibraryFolders();
    return runSearch(state.query);
  }

  /** First page of the library, shown while the search box is empty. */
  function browseSongs() {
    if (!state.browse) {
      const songs = callApi('library_songs')?.songs || [];
      state.browse = songs.slice(0, BROWSE_LIMIT);
    }
    return state.browse;
  }

  function parsePatternList(text) {
    return String(text).split(/[\n,]/).map((s) => s.trim()).filter(Boolean);
  }

  // Described scan report for this session (null when there is nothing to
  // report).  Kept so the details stay reachable after the notice is gone.
  let scanView = null;

  function renderScanReport() {
    const summary = $('scan-summary');
    const chip = $('scan-issues');
    let report = null;
    try { report = callApi('scan_report'); } catch { report = null; }
    scanView = report && (report.entries || []).length ? describeScanReport(report) : null;
    $('scan-details').hidden = true;
    $('scan-details').textContent = '';
    chip.setAttribute('aria-expanded', 'false');
    if (!scanView) {
      summary.hidden = true;
      summary.textContent = '';
      chip.hidden = true;
      return;
    }
    summary.hidden = false;
    summary.textContent = scanView.summary;
    summary.dataset.severity = scanView.severity;
    const total = scanView.details.reduce((n, d) => n + d.count, 0);
    chip.hidden = false;
    chip.textContent = `Scan details (${formatCount(total)})`;
    chip.title = 'Every file the scan skipped or could not use';
  }

  function renderScanDetails() {
    const details = $('scan-details');
    details.textContent = '';
    if (!scanView) return;
    const list = document.createElement('ul');
    for (const group of scanView.details) {
      const item = document.createElement('li');
      const heading = document.createElement('span');
      heading.className = 'scan-category';
      heading.textContent = `${formatCount(group.count)} ${group.label}`;
      item.appendChild(heading);
      const paths = document.createElement('ul');
      for (const path of group.paths) {
        const li = document.createElement('li');
        li.textContent = path;
        paths.appendChild(li);
      }
      if (group.hidden) {
        const more = document.createElement('li');
        more.textContent = `…and ${formatCount(group.hidden)} more`;
        paths.appendChild(more);
      }
      item.appendChild(paths);
      list.appendChild(item);
    }
    details.appendChild(list);
    const clear = document.createElement('button');
    clear.className = 'btn btn-secondary btn-sm';
    clear.textContent = 'Clear scan details';
    clear.title = 'Forget these results until the next scan';
    clear.addEventListener('click', () => {
      try { callApi('clear_scan_report'); } catch { /* the engine may be gone */ }
      renderScanReport();
    });
    details.appendChild(clear);
  }

  function openScanDetails() {
    if (!scanView) return;
    renderScanDetails();
    $('scan-details').hidden = false;
    $('scan-issues').setAttribute('aria-expanded', 'true');
    $('scan-details').scrollIntoView({ block: 'nearest' });
  }

  function toggleScanDetails() {
    if ($('scan-details').hidden) openScanDetails();
    else {
      $('scan-details').hidden = true;
      $('scan-details').textContent = '';
      $('scan-issues').setAttribute('aria-expanded', 'false');
    }
  }

  /** The list the user sees: the match set filtered by the format boxes. */
  function visibleResults() {
    const kindFilter = {
      cdg: $('filter-cdg').checked,
      kar: $('filter-kar').checked,
      mpg: $('filter-mpg').checked,
      lrc: $('filter-lrc').checked,
    };
    return state.results.filter((s) => kindFilter[s.kind]);
  }

  function rowButton(glyph, label, onClick) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'btn btn-icon';
    button.title = label;
    button.setAttribute('aria-label', label);
    button.textContent = glyph;
    button.addEventListener('click', (e) => {
      e.stopPropagation();
      onClick();
    });
    return button;
  }

  /** The "queued ×2" / "playing" marker on a result row, or nothing. */
  function syncResultRow(row, song) {
    const label = queueBadgeFor(song, state.queue.items, state.current?.id).label;
    let tag = row.querySelector('.state-tag');
    if (!label) {
      if (tag) tag.remove();
      return;
    }
    if (!tag) {
      tag = document.createElement('span');
      tag.className = 'tag state-tag';
      row.insertBefore(tag, row.querySelector('.song-row-actions'));
    }
    tag.textContent = label;
  }

  /** Refresh just the queue markers on the rows already on screen. */
  function syncResultRows() {
    const visible = visibleResults();
    $('results-list').querySelectorAll('.song-row').forEach((row) => {
      const song = visible[Number(row.dataset.index)];
      if (song) syncResultRow(row, song);
    });
  }

  function emptyAction(empty) {
    const actions = {
      'add-folder': pickFolder,
      'clear-search': clearSearch,
      'reset-filters': resetKindFilters,
    };
    const run = actions[empty.action];
    if (!run) return null;
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'btn btn-secondary btn-sm';
    button.textContent = empty.actionLabel;
    button.addEventListener('click', () => run());
    return button;
  }

  function renderResults() {
    const list = $('results-list');
    const datalist = $('search-results');
    const visible = visibleResults();
    const view = describeResults({
      libraryCount: state.libraryCount,
      query: state.query,
      matched: state.results.length,
      shown: visible.length,
      limit: state.query ? SEARCH_LIMIT : BROWSE_LIMIT,
    });

    $('results-heading').textContent = view.heading;
    $('results-count').textContent = view.count;
    const hint = $('results-hint');
    hint.textContent = view.hint;
    hint.hidden = !view.hint;

    const empty = $('results-empty');
    list.innerHTML = '';
    datalist.innerHTML = '';
    state.selectedResult = -1;

    if (view.empty) {
      empty.hidden = false;
      empty.textContent = '';
      const title = document.createElement('span');
      title.className = 'empty-title';
      title.textContent = view.empty.title;
      const sub = document.createElement('span');
      sub.textContent = view.empty.hint;
      empty.append(title, sub);
      const action = emptyAction(view.empty);
      if (action) empty.appendChild(action);
      return;
    }
    empty.hidden = true;
    empty.textContent = '';

    visible.forEach((song, i) => {
      // Accessible path: native datalist option bound to the search input.
      const option = document.createElement('option');
      option.value = songLabel(song);
      option.label = song.filename;
      datalist.appendChild(option);

      const row = document.createElement('div');
      row.className = 'song-row';
      row.dataset.index = String(i);
      row.setAttribute('role', 'option');
      row.setAttribute('aria-selected', 'false');

      const badge = document.createElement('span');
      badge.className = `badge badge-${song.kind}`;
      badge.textContent = KIND_BADGE[song.kind] || song.kind;
      if (hasElrc(song)) {
        badge.textContent = 'ELRC';
        badge.title = 'Word-level timing (.elrc)';
      }

      const info = document.createElement('div');
      info.className = 'song-row-info';
      const title = document.createElement('span');
      title.className = 'song-row-title';
      title.textContent = songLabel(song);
      const file = document.createElement('span');
      file.className = 'song-row-file muted';
      file.textContent = song.filename;
      info.append(title, file);

      const actions = document.createElement('div');
      actions.className = 'song-row-actions';
      actions.append(
        rowButton('▶', `Play ${songLabel(song)} now`, () => playSong(song)),
        rowButton('➕', `Add ${songLabel(song)} to the queue`, () => enqueue(song)),
      );

      row.append(badge, info, actions);
      row.addEventListener('click', () => {
        selectResult(i);
        enqueue(song);
      });
      row.addEventListener('dblclick', () => playSong(song));
      list.appendChild(row);
      syncResultRow(row, song);
    });
  }

  function selectResult(i) {
    const rows = $('results-list').querySelectorAll('.song-row');
    if (!rows.length) return;
    state.selectedQueue = -1;
    state.selectedResult = (i + rows.length) % rows.length;
    rows.forEach((r, idx) => {
      const on = idx === state.selectedResult;
      r.classList.toggle('selected', on);
      r.setAttribute('aria-selected', String(on));
    });
    rows[state.selectedResult].scrollIntoView({ block: 'nearest' });
  }

  /** Run a search (or browse the library when *raw* is empty). */
  async function runSearch(raw) {
    const query = String(raw == null ? '' : raw).trim();
    state.query = query;
    if (!query) {
      state.results = browseSongs();
      renderResults();
      return;
    }
    try {
      const r = callApi('search', query, SEARCH_LIMIT);
      if (r?.error) throw new Error(r.error);
      state.results = r?.results || [];
    } catch (err) {
      console.error(err);
      state.results = [];
      setStatus(`Search failed — ${err.message}`, { kind: 'error' });
    }
    renderResults();
  }

  function clearSearch() {
    $('search-input').value = '';
    runSearch('');
  }

  function resetKindFilters() {
    for (const id of ['filter-cdg', 'filter-kar', 'filter-mpg', 'filter-lrc']) {
      $(id).checked = true;
    }
    renderResults();
  }

  function renderQueue() {
    const list = $('queue-list');
    const items = state.queue.items;
    const info = describeQueue({
      length: items.length,
      nextLabel: items.length ? songLabel(items[0]) : '',
    });
    $('queue-count').textContent = info.count;
    $('queue-hint').textContent = info.hint;
    $('clear-queue-btn').disabled = !items.length;
    list.innerHTML = '';

    if (!items.length) {
      state.selectedQueue = -1;
      const empty = document.createElement('li');
      empty.className = 'empty-state';
      empty.textContent = 'Nothing queued yet.';
      list.appendChild(empty);
      syncResultRows();
      return;
    }
    if (state.selectedQueue >= items.length) state.selectedQueue = items.length - 1;

    items.forEach((song, i) => {
      const row = document.createElement('li');
      row.className = 'song-row queue-row';
      row.dataset.index = String(i);
      row.tabIndex = -1;
      if (state.current && song.id === state.current.id) row.classList.add('current');
      if (i === state.selectedQueue) row.classList.add('selected');

      const position = document.createElement('span');
      position.className = 'queue-position';
      position.textContent = String(i + 1);

      const rowInfo = document.createElement('div');
      rowInfo.className = 'song-row-info';
      const title = document.createElement('span');
      title.className = 'song-row-title';
      title.textContent = songLabel(song);
      const file = document.createElement('span');
      file.className = 'song-row-file muted';
      file.textContent = song.filename;
      rowInfo.append(title, file);

      const actions = document.createElement('div');
      actions.className = 'song-row-actions';
      actions.append(
        rowButton('▶', `Play ${songLabel(song)} now`, () => playFromQueue(i)),
        rowButton('✕', `Remove ${songLabel(song)} from the queue`, () => removeQueueItem(i)),
      );

      row.append(position, rowInfo, actions);
      row.addEventListener('click', () => selectQueueItem(i));
      row.addEventListener('dblclick', () => playFromQueue(i));
      list.appendChild(row);
    });
    syncResultRows();
  }

  /**
   * Queue rows are selectable: while one is selected, the arrow keys and
   * Delete/Alt+arrow shortcuts act on the queue instead of the song list.
   */
  function selectQueueItem(i) {
    const rows = $('queue-list').querySelectorAll('.queue-row');
    if (!rows.length) return;
    state.selectedResult = -1;
    $('results-list').querySelectorAll('.song-row.selected').forEach((r) => {
      r.classList.remove('selected');
      r.setAttribute('aria-selected', 'false');
    });
    state.selectedQueue = (i + rows.length) % rows.length;
    rows.forEach((r, idx) => r.classList.toggle('selected', idx === state.selectedQueue));
    rows[state.selectedQueue].scrollIntoView({ block: 'nearest' });
  }

  function removeQueueItem(i) {
    const song = state.queue.items[i];
    if (!song) return;
    state.queue.removeAt(i);
    state.selectedQueue = Math.min(i, state.queue.length - 1);
    renderQueue();
    renderTransport();
    persist();
    notify(`Removed ${songLabel(song)} from the queue.`, {
      actionLabel: 'Undo',
      onAction: () => {
        state.queue.insert(i, song);
        state.selectedQueue = i;
        renderQueue();
        renderTransport();
        persist();
      },
    });
  }

  function moveQueueItem(i, delta) {
    const target = i + delta;
    if (i < 0 || i >= state.queue.length || target < 0 || target >= state.queue.length) return;
    state.queue.move(i, delta);
    state.selectedQueue = target;
    renderQueue();
    persist();
  }

  /** Play a queued song now: it leaves the queue, so it cannot replay later. */
  function playFromQueue(i) {
    const song = state.queue.items[i];
    if (!song) return;
    state.queue.removeAt(i);
    state.selectedQueue = Math.min(i, state.queue.length - 1);
    renderQueue();
    renderTransport();
    persist();
    playSong(song);
  }

  function clearQueue() {
    const removed = state.queue.items.slice();
    if (!removed.length) return;
    state.queue.clear();
    state.selectedQueue = -1;
    renderQueue();
    renderTransport();
    persist();
    notify(
      `Cleared ${formatCount(removed.length)} queued ${removed.length === 1 ? 'song' : 'songs'}.`,
      {
        actionLabel: 'Undo',
        onAction: () => {
          for (const song of removed) state.queue.push(song);
          renderQueue();
          renderTransport();
          persist();
        },
      },
    );
  }

  function setStatus(msg, { kind = 'info' } = {}) {
    const el = $('status-message');
    el.textContent = msg;
    el.dataset.kind = kind;
  }

  function setEngineStatus(info) {
    const el = $('engine-status');
    el.textContent = info.text;
    el.title = info.title;
  }

  let noticeTimer = null;

  function clearNotice() {
    if (noticeTimer) clearTimeout(noticeTimer);
    noticeTimer = null;
    const el = $('notices');
    el.hidden = true;
    el.textContent = '';
    el.removeAttribute('data-kind');
  }

  /** Non-blocking feedback, with an optional one-click action (Undo, Retry). */
  function notify(message, { kind = 'info', actionLabel = '', onAction = null, timeout = 8000 } = {}) {
    const el = $('notices');
    if (noticeTimer) clearTimeout(noticeTimer);
    el.textContent = '';
    el.dataset.kind = kind;
    const text = document.createElement('span');
    text.textContent = message;
    el.appendChild(text);
    if (actionLabel && onAction) {
      const action = document.createElement('button');
      action.type = 'button';
      action.className = 'btn btn-secondary btn-sm';
      action.textContent = actionLabel;
      action.addEventListener('click', () => {
        clearNotice();
        onAction();
      });
      el.appendChild(action);
    }
    const close = document.createElement('button');
    close.type = 'button';
    close.className = 'btn btn-icon';
    close.title = 'Dismiss';
    close.setAttribute('aria-label', 'Dismiss notification');
    close.textContent = '✕';
    close.addEventListener('click', clearNotice);
    el.appendChild(close);
    el.hidden = false;
    noticeTimer = timeout > 0 ? setTimeout(clearNotice, timeout) : null;
  }

  /**
   * Chip plus control availability for the transport: a control that cannot
   * do anything yet is disabled rather than failing on click.
   */
  function renderTransport() {
    const info = describePlayback({
      song: state.current,
      playing: state.playing,
      failed: state.playingFailed,
    });
    const chip = $('playback-state');
    chip.dataset.state = info.state;
    chip.textContent = info.label;
    chip.title = info.mediaState;

    const play = $('play-btn');
    play.disabled = info.playDisabled;
    play.textContent = state.playing ? '⏸' : info.playLabel === 'Retry' ? '↻' : '▶';
    play.title = `${info.playLabel} (Space)`;
    play.setAttribute('aria-label', info.playLabel);

    $('stop-btn').disabled = info.stopDisabled;
    $('prev-btn').disabled = !state.current;
    $('rewind-btn').disabled = info.seekDisabled;
    $('ff-btn').disabled = info.seekDisabled;
    $('next-btn').disabled = state.queue.length === 0;
    $('progress-slider').disabled = info.seekDisabled;
  }

  function setNowPlaying(song) {
    state.current = song;
    $('current-song-title').textContent = song ? songLabel(song) : '—';
    $('current-song-artist').textContent = song ? song.filename : '';
    $('stage-empty').style.display = song ? 'none' : '';
    renderTransport();
    renderQueue();
    syncResultRows();
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
    // Intrinsic size only: CSS caps the display width to the column
    // (`max-width: 100%` with `height: auto`), so a big zoom scales down
    // instead of being squashed out of shape.
    canvas.width = Math.round(CDG_WIDTH * scale);
    canvas.height = Math.round(CDG_HEIGHT * scale);
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
    state.playingFailed = false;
    setNowPlaying(song);
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
      renderTransport();
    } catch (err) {
      console.error(err);
      // Only tear down if this song is still the current one — a rapid
      // play-next can supersede it before its (async) setup settles.
      if (state.current === song) {
        state.playing = false;
        state.playingFailed = true;
        const reason = describePlaybackError(err.message);
        setStatus(`Playback error — ${reason}`, { kind: 'error' });
        notify(`Could not play ${songLabel(song)}: ${reason}`, {
          kind: 'error',
          timeout: 0,
          actionLabel: 'Retry',
          onAction: () => playSong(song),
        });
        renderTransport();
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
    renderTransport();
  }

  function resumeMedia() {
    state.playing = true;
    state.playingFailed = false;
    if (state.audioEl) state.audioEl.play();
    if (state.synth) state.synth.resume();
    if (state.videoEl) state.videoEl.play();
    if (state.frameFn) startLoop(state.frameFn);
    renderTransport();
  }

  function togglePlay() {
    if (!state.current) return;
    if (state.playing) pauseMedia();
    else if (state.playingFailed) playSong(state.current);
    else resumeMedia();
  }

  /** Stop button: unload the song and clear any previous error. */
  function stopNow() {
    stopPlayback();
    state.playingFailed = false;
    setNowPlaying(null);
    setStatus('Stopped — pick a song to sing');
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
    renderTransport();
  }

  function onSongEnded() {
    const next = state.queue.next();
    if (next) {
      renderQueue();
      renderTransport();
      persist();
      playSong(next);
      return;
    }
    stopPlayback();
    setNowPlaying(null);
    setStatus('Queue finished — pick the next song');
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
    const already = queueBadgeFor(song, state.queue.items, null).count;
    state.queue.push(song);
    renderQueue();
    renderTransport();
    persist();
    const undo = () => {
      const at = state.queue.items.lastIndexOf(song);
      if (at >= 0) state.queue.removeAt(at);
      renderQueue();
      renderTransport();
      persist();
    };
    if (already) {
      notify(`${songLabel(song)} was already queued — added again (${already + 1} in the queue).`, {
        kind: 'warn',
        actionLabel: 'Undo',
        onAction: undo,
      });
      return;
    }
    notify(`Added ${songLabel(song)} to the queue.`, { actionLabel: 'Undo', onAction: undo });
  }

  function playNext() {
    if (!state.queue.length) {
      setStatus('Nothing queued to play — add a song to the queue first');
      return;
    }
    const next = state.queue.next();
    renderQueue();
    renderTransport();
    persist();
    playSong(next);
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
    if (patch.sort !== undefined) {
      state.browse = null; // the engine re-orders library_songs
      runSearch(state.query);
    }
    if (needsRescan(patch)) showRescanNote();
  }

  /** These choices only take effect at the next scan — say so, plainly. */
  function showRescanNote() {
    const note = $('settings-rescan-note');
    if (note) note.hidden = false;
  }

  function hideRescanNote() {
    const note = $('settings-rescan-note');
    if (note) note.hidden = true;
  }

  function toggleSettings(open) {
    const panel = $('settings-panel');
    const show = open === undefined ? panel.hidden : !!open;
    panel.hidden = !show;
    $('settings-btn').setAttribute('aria-expanded', String(show));
    if (show) $('settings-heading').focus?.();
  }

  function renderShortcuts() {
    const box = $('shortcuts-list');
    if (!box) return;
    box.textContent = '';
    for (const shortcut of SHORTCUTS) {
      const keys = document.createElement('kbd');
      keys.textContent = shortcut.keys;
      const description = document.createElement('span');
      description.textContent = shortcut.description;
      box.append(keys, description);
    }
  }

  // Keyboard-first controls: one small handler per binding.  Each returns
  // true when it consumed the key, so one keydown triggers one action.
  function focusSearchKey(e, searchInput) {
    if (e.key !== '/' && !(e.key === 'k' && (e.ctrlKey || e.metaKey))) return false;
    e.preventDefault();
    searchInput.focus();
    searchInput.select?.();
    return true;
  }

  function escapeKey(e, inInput, searchInput) {
    if (e.key !== 'Escape') return false;
    if (inInput) {
      if (e.target === searchInput) {
        e.target.value = '';
        runSearch('');
      }
      e.target.blur();
      return true;
    }
    if (state.selectedQueue >= 0) {
      state.selectedQueue = -1;
      renderQueue();
      return true;
    }
    if (!$('settings-panel').hidden) {
      toggleSettings(false);
      return true;
    }
    if (state.query || searchInput.value) {
      clearSearch();
      return true;
    }
    return false;
  }

  function togglePlaybackKey(e, inInput) {
    if (e.key !== ' ' || inInput) return false;
    e.preventDefault();
    togglePlay();
    return true;
  }

  function enqueueSelectedKey(e, inInput) {
    if (e.key !== 'Enter' || inInput || state.selectedQueue >= 0) return false;
    if (state.selectedResult < 0) return false;
    const song = visibleResults()[state.selectedResult];
    if (song) enqueue(song);
    return true;
  }

  function moveSelectionKey(e, inInput) {
    if (inInput || e.altKey) return;
    if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return;
    e.preventDefault();
    const delta = e.key === 'ArrowDown' ? 1 : -1;
    // A selected queue row owns the arrow keys until Esc leaves the queue.
    if (state.selectedQueue >= 0 && state.queue.length) {
      selectQueueItem(state.selectedQueue + delta);
      return;
    }
    selectResult(state.selectedResult + delta);
  }

  function deleteQueueItemKey(e, inInput) {
    if (e.key !== 'Delete' || inInput || state.selectedQueue < 0) return false;
    e.preventDefault();
    removeQueueItem(state.selectedQueue);
    return true;
  }

  function reorderQueueKey(e, inInput) {
    if (!e.altKey || inInput) return false;
    if (e.key !== 'ArrowUp' && e.key !== 'ArrowDown') return false;
    e.preventDefault();
    if (state.selectedQueue < 0) {
      notify('Click a queued song first, then use Alt+↑ / Alt+↓ to move it.', { kind: 'info' });
      return true;
    }
    moveQueueItem(state.selectedQueue, e.key === 'ArrowUp' ? -1 : 1);
    return true;
  }

  function previousSongKey(e, inInput) {
    if (inInput || !e.ctrlKey || e.key !== 'ArrowUp') return false;
    e.preventDefault();
    playPrev();
    return true;
  }

  function nextSongKey(e, inInput) {
    if (inInput || !e.ctrlKey) return false;
    if (e.key !== 'ArrowRight' && e.key !== 'ArrowDown') return false;
    e.preventDefault();
    playNext();
    return true;
  }

  function helpKey(e, inInput) {
    if (inInput || e.key !== 'F1') return false;
    e.preventDefault();
    toggleSettings(true);
    return true;
  }

  // ── UI wiring ──────────────────────────────────────────────────────
  const STORAGE_KEY = 'pykaraoke-ng:state';
  const QUEUE_KEY = 'pykaraoke-ng:queue';

  function wireUi() {
    // Folder picking and library management.
    $('add-folder-btn').addEventListener('click', pickFolder);
    $('scan-library-btn').addEventListener('click', rescanFolders);
    $('replace-library-btn').addEventListener('click', armReplace);
    $('export-library-btn').addEventListener('click', exportLibrary);
    $('import-library-btn').addEventListener('click', () => $('import-library-picker').click());
    $('import-library-picker').addEventListener('change', importLibrary);
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
      disarmReplace();
    });

    // The scan chip is the permanent route back to the skipped-file list.
    $('scan-issues').addEventListener('click', toggleScanDetails);

    // Search.
    const searchInput = $('search-input');
    searchInput.addEventListener('input', debounce(() => runSearch(searchInput.value), 150));

    // Accessible selection: a datalist option picked from the search input
    // enqueues the matching result (mirrors clicking a result row).
    searchInput.addEventListener('change', () => {
      const label = searchInput.value.trim();
      if (!label) return;
      const song = visibleResults().find((s) => songLabel(s) === label);
      if (!song) return;
      enqueue(song);
      clearSearch();
    });

    // Transport.
    $('play-btn').addEventListener('click', togglePlay);
    $('stop-btn').addEventListener('click', stopNow);
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
    $('clear-queue-btn').addEventListener('click', clearQueue);

    // Settings panel (inline, no modal).
    $('settings-btn').addEventListener('click', () => toggleSettings());
    $('settings-close-btn').addEventListener('click', () => toggleSettings(false));
    $('settings-rescan-btn').addEventListener('click', () => {
      hideRescanNote();
      rescanFolders();
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
      $(id).addEventListener('change', () => {
        state.selectedResult = -1;
        renderResults();
      });
    });

    document.addEventListener('keydown', (e) => {
      const target = e.target;
      const tag = target?.tagName;
      const inInput = tag === 'INPUT' || tag === 'SELECT' || tag === 'TEXTAREA' || !!target?.isContentEditable;
      if (focusSearchKey(e, searchInput)) return;
      if (escapeKey(e, inInput, searchInput)) return;
      if (togglePlaybackKey(e, inInput)) return;
      if (enqueueSelectedKey(e, inInput)) return;
      if (reorderQueueKey(e, inInput)) return;
      if (deleteQueueItemKey(e, inInput)) return;
      if (previousSongKey(e, inInput)) return;
      if (nextSongKey(e, inInput)) return;
      if (helpKey(e, inInput)) return;
      moveSelectionKey(e, inInput);
    });
  }

  async function importLibrary(e) {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;
    try {
      const result = callApi('import_json', await file.text());
      if (!result?.ok) {
        const reason = result?.error || 'unknown error';
        setStatus(`Import failed — ${reason}`, { kind: 'error' });
        notify(`That library file could not be imported: ${reason}`, {
          kind: 'error',
          timeout: 0,
        });
        return;
      }
      await refreshSettings();
      await refreshLibraryViews();
      persist();
      const total = state.libraryCount;
      setStatus(`Library imported — ${formatCount(total)} ${total === 1 ? 'song' : 'songs'}`);
      notify(`Library imported — ${formatCount(total)} ${total === 1 ? 'song' : 'songs'}.`);
    } catch (err) {
      setStatus(`Import failed — ${err.message}`, { kind: 'error' });
      notify(`That library file could not be imported: ${err.message}`, {
        kind: 'error',
        timeout: 0,
      });
    }
  }

  let replaceArmed = false;
  let replaceTimer = null;

  /**
   * Replacing the library discards the current song list, so it asks for a
   * second click (and explains itself first) instead of doing it outright.
   */
  function armReplace() {
    if (replaceArmed) {
      disarmReplace();
      replaceLibrary();
      return;
    }
    replaceArmed = true;
    const button = $('replace-library-btn');
    button.textContent = 'Confirm replace';
    button.classList.add('btn-danger');
    const hint = $('replace-hint');
    hint.hidden = false;
    hint.textContent =
      'Replacing clears the current song list and re-reads your folders. Press “Confirm replace” to go ahead, or wait six seconds to cancel.';
    replaceTimer = setTimeout(disarmReplace, 6000);
  }

  function disarmReplace() {
    if (replaceTimer) clearTimeout(replaceTimer);
    replaceTimer = null;
    replaceArmed = false;
    const button = $('replace-library-btn');
    if (!button) return;
    button.textContent = 'Replace library';
    button.classList.remove('btn-danger');
    const hint = $('replace-hint');
    hint.hidden = true;
    hint.textContent = '';
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
        setStatus(`Could not read that folder — ${err.message}`, { kind: 'error' });
        notify(`Could not read that folder: ${err.message}`, { kind: 'error', timeout: 0 });
      }
    } else {
      $('folder-picker').click();
    }
  }

  async function rescanFolders() {
    const s = callApi('get_settings') || {};
    const folders = s.folders || [];
    if (!folders.length) {
      setStatus('No folders to scan yet');
      notify('No folders are configured yet — use Add folder to choose one.', { kind: 'warn' });
      if (!tauriCore) $('folder-picker').click();
      return;
    }
    if (!tauriCore) {
      notify('In the browser, pick the folder again to reload its files.', { kind: 'info' });
      $('folder-picker').click();
      return;
    }
    for (const folder of folders) {
      try {
        const entries = await tauriCore.invoke('list_folder', { path: folder });
        await scanEntries(entries);
      } catch (err) {
        setStatus(`Could not read ${folder} — ${err.message}`, { kind: 'error' });
        notify(`Could not read ${folder}: ${err.message}`, { kind: 'error', timeout: 0 });
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
      setStatus('Nothing to re-read yet');
      notify('There is nothing to re-read yet — use Add folder to choose your songs folder.', {
        kind: 'warn',
      });
      return;
    }
    await scanEntries(entries, true);
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
      setStatus('Library exported to pykaraoke-library.json');
      notify('Library exported — your browser saved pykaraoke-library.json.');
    } catch (err) {
      setStatus(`Export failed — ${err.message}`, { kind: 'error' });
      notify(`The library could not be exported: ${err.message}`, { kind: 'error', timeout: 0 });
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
  __app = {
    boot,
    wireUi,
    state,
    callApi,
    setStatus,
    setEngineStatus,
    notify,
    clearNotice,
    renderResults,
    renderQueue,
    renderTransport,
    renderScanReport,
    renderScanDetails,
    toggleScanDetails,
    openScanDetails,
    renderShortcuts,
    toggleSettings,
    runSearch,
    clearSearch,
    resetKindFilters,
    enqueue,
    clearQueue,
    removeQueueItem,
    moveQueueItem,
    playFromQueue,
    selectQueueItem,
    selectResult,
    syncResultRows,
    refreshLibraryViews,
    updateSettings,
    armReplace,
    disarmReplace,
  };

  // Boot.
  document.addEventListener('DOMContentLoaded', () => {
    wireUi();
    boot();
  });
}
export const app = __app;
