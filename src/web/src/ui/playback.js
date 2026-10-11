import {
  formatTime, buildLyricLines, highlightState, partClass, partLabel,
  writeTileRgba, CDG_WIDTH, CDG_HEIGHT, ELRC_EXT,
} from '../helpers.js';
import { setStatus, setEngineStatus, setPlaying, applyZoom, renderLyricLines } from './render.js';

export function makePlayback(state) {
  const { callApi, tauriCore, $, cdgKey, audioEl, videoEl, synth } = state;

  // ── File access ────────────────────────────────────────────────
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

  function decodeText(bytes) {
    const utf8 = new TextDecoder('utf-8', { fatal: false }).decode(bytes);
    if (!utf8.includes('\uFFFD')) return utf8;
    return new TextDecoder('windows-1252').decode(bytes);
  }

  function resolveSongPath(song) {
    return song.path;
  }

  function resolveAudioPath(song) {
    if (song.audio_name) {
      const base = state.pathByBase.get(String(song.audio_name).toLowerCase());
      if (base) return base;
    }
    const stem = song.filename.replace(/\.[^.]+$/, '').toLowerCase();
    const candidates = ['.mp3', '.ogg', '.wav'];
    for (const ext of candidates) {
      const hit = state.pathByBase.get(`${stem}${ext}`);
      if (hit) return hit;
    }
    return null;
  }

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

  async function readCompanionText(song, ext) {
    try {
      if (song.zip_name) {
        const member = companionMember(song, ext);
        if (!member) return null;
        const bytes = callApi('read_zip_member', song.zip_name, member);
        if (!bytes || !bytes.length) return null;
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

  function hasElrc(song) {
    if (!song || song.kind !== 'lrc') return false;
    if (song.zip_name) {
      const member = companionMember(song, ELRC_EXT);
      if (!member) return false;
      try {
        const names = callApi('zip_members', song.zip_name);
        return Array.isArray(names) &&
          names.some((name) => String(name).toLowerCase() === member.toLowerCase());
      } catch {
        return false;
      }
    }
    const base = companionBaseName(song, ELRC_EXT);
    return !!(base && state.pathByBase.has(base));
  }

  function companionMember(song, ext) {
    if (!song || !song.zip_name) return null;
    const member = String(song.id || '').split('!').slice(1).join('!');
    if (!member) return null;
    return member.replace(/\.[^./\\]+$/, ext);
  }

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

  // ── Boot ───────────────────────────────────────────────────────
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
    await state.restoreState();
    await state.refreshSettings();
    state.renderQueue();
    setStatus(tauriCore ? 'Ready — desktop filesystem' : 'Ready — add a folder to scan');
  }

  async function restoreState() {
    try {
      const saved = localStorage.getItem('pykaraoke-ng:state');
      if (saved) callApi('from_json', saved);
      const queueIds = JSON.parse(localStorage.getItem('pykaraoke-ng:queue') || '[]');
      const songs = callApi('library_songs')?.songs || [];
      const byId = new Map(songs.map((s) => [s.id, s]));
      state.queue = new SongQueue(queueIds.map((id) => byId.get(id)).filter(Boolean));
    } catch (err) {
      console.warn('restore failed', err);
    }
    state.renderLibraryCount();
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
    applyZoom(state);
  }

  function persist() {
    try {
      localStorage.setItem('pykaraoke-ng:state', callApi('to_json'));
      localStorage.setItem(
        'pykaraoke-ng:queue',
        JSON.stringify(state.queue.items.map((s) => s.id)),
      );
    } catch (err) {
      console.warn('persist failed', err);
    }
  }

  // ── Scanning ───────────────────────────────────────────────────
  async function scanEntries(entries, replace = false) {
    if (!entries.length) return;
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
    await state.scanZips(entries);
    await refreshSettings();
    state.renderLibraryCount();
    state.renderScanSummary();
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

  async function pickFolder() {
    if (tauriCore) {
      try {
        const path = await tauriCore.invoke('pick_folder');
        if (!path) return;
        const entries = await tauriCore.invoke('list_folder', { path });
        const s = callApi('get_settings') || {};
        const folders = Array.isArray(s.folders) ? s.folders : [];
        if (!folders.includes(path)) state.updateSettings({ folders: [...folders, path] });
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

  // ── Stage rendering (CDG) ──────────────────────────────────────
  const canvas = $('cdg-canvas');
  const stageCtx = canvas.getContext('2d');
  const fullFrame = new ImageData(CDG_WIDTH, CDG_HEIGHT);
  const blitCanvas = document.createElement('canvas');
  blitCanvas.width = CDG_WIDTH;
  blitCanvas.height = CDG_HEIGHT;
  const blitCtx = blitCanvas.getContext('2d');

  function drawCdgUpdate(update) {
    if (update && update.border) {
      const [r, g, b] = update.border;
      stageCtx.fillStyle = `rgb(${r},${g},${b})`;
      stageCtx.fillRect(0, 0, canvas.width, canvas.height);
    }
    if (update && update.tiles) {
      for (const tile of update.tiles) {
        writeTileRgba(tile.data, fullFrame.data, CDG_WIDTH, tile.x, tile.y);
      }
    }
    blitCtx.putImageData(fullFrame, 0, 0);
    stageCtx.imageSmoothingEnabled = false;
    stageCtx.drawImage(blitCanvas, 0, 0, canvas.width, canvas.height);
  }

  // ── Lyrics rendering ───────────────────────────────────────────
  function renderLyrics(state) {
    const box = $('lyrics');
    if (!state.lyricLines || !state.lyricLines.length) {
      box.innerHTML = '';
      box.style.display = 'none';
      return;
    }
    box.style.display = '';
    box.innerHTML = '';
    for (const line of state.lyricLines.slice(0, 2)) {
      const div = document.createElement('div');
      div.className = 'lyric-line';
      const cls = partClass(line.part);
      if (cls) {
        div.classList.add(cls);
        div.dataset.part = line.part;
        const chip = document.createElement('span');
        chip.className = 'lyric-part';
        chip.textContent = partLabel(state.parts, line.part);
        div.appendChild(chip);
      }
      line.syllables.forEach((syl) => {
        const span = document.createElement('span');
        span.className = 'lyric-syl';
        span.dataset.ms = String(syl.ms);
        span.textContent = syl.text.trimEnd() + '\u00A0';
        div.appendChild(span);
      });
      box.appendChild(div);
    }
    state.lastLyricLine = 0;
  }

  function updateLyrics(ms) {
    const lines = state.lyricLines;
    if (!lines || !lines.length) return;
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
    const els = $('lyrics').querySelectorAll('.lyric-syl');
    els.forEach((el, i) => el.classList.toggle('lit', i < litCount));
  }

  // ── Transport ──────────────────────────────────────────────────
  async function playSong(song) {
    state.stopPlayback();
    state.playing = true;
    setPlaying(state, song);
    $('stage-empty').style.display = 'none';
    try {
      if (song.kind === 'cdg') {
        await state.playCdg(song);
      } else if (song.kind === 'kar') {
        await state.playKar(song);
      } else if (song.kind === 'lrc') {
        await state.playLrc(song);
      } else {
        await state.playMpg(song);
      }
    } catch (err) {
      console.error(err);
      if (state.current === song) {
        setStatus(`Playback error: ${err.message}`);
        state.playing = false;
        setPlaying(state, song);
      }
    }
  }

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
    state.cdgKey = callApi('cdg_open', song.id, await readSongBytes(song));
    const audioPath = resolveAudioPath(song);
    if (!audioPath) throw new Error('no audio file found for this CDG');
    const audio = new Audio(mediaUrl(audioPath));
    audio.volume = state.settings.volume;
    audio.addEventListener('ended', state.onSongEnded);
    audio.addEventListener('loadedmetadata', () => {
      state.durationMs = audio.duration * 1000;
      $('time-total').textContent = formatTime(state.durationMs);
    });
    state.audioEl = audio;
    await audio.play();
    drawCdgUpdate(callApi('cdg_update', state.cdgKey, 0));
    state.startCdgLoop();
  }

  function startCdgLoop() {
    state.frameFn = () => {
      if (!state.audioEl) return;
      const ms = state.audioEl.currentTime * 1000;
      state.updateTransport(ms);
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
    state.parts = null;
    state.lyricLines = buildLyricLines(parsed.lyrics || []);
    renderLyricLines(state);
    const { computeNoteTimeline } = await import('../helpers.js');
    state.synth = new MidiSynth(parsed, computeNoteTimeline);
    state.synth.onEnded = state.onSongEnded;
    state.synth.setVolume(state.settings.volume);
    state.synth.start();
    state.startSynthLoop();
  }

  function startSynthLoop() {
    state.frameFn = () => {
      if (!state.synth) return;
      const ms = state.synth.currentMs();
      state.updateTransport(ms);
      updateLyrics(ms);
    };
    startLoop(state.frameFn);
  }

  async function playLrc(song) {
    const bytes = await readSongBytes(song);
    const elrcText = await readCompanionText(song, ELRC_EXT);
    const parsed = callApi('parse_lrc', decodeText(bytes), elrcText);
    if (!parsed || parsed.error) throw new Error(parsed?.error || 'could not parse LRC lyrics');
    const audioPath = resolveAudioPath(song);
    if (!audioPath) throw new Error('no audio file found for this LRC');
    state.parts = parsed.parts || null;
    state.lyricLines = buildLyricLines(parsed.lyrics || []);
    renderLyricLines(state);
    const audio = new Audio(mediaUrl(audioPath));
    audio.volume = state.settings.volume;
    audio.addEventListener('ended', state.onSongEnded);
    audio.addEventListener('loadedmetadata', () => {
      state.durationMs = audio.duration * 1000;
      $('time-total').textContent = formatTime(state.durationMs);
    });
    state.audioEl = audio;
    await audio.play();
    state.frameFn = () => {
      if (!state.audioEl) return;
      const ms = state.audioEl.currentTime * 1000;
      state.updateTransport(ms);
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
    video.addEventListener('ended', state.onSongEnded);
    video.addEventListener('loadedmetadata', () => {
      state.durationMs = video.duration * 1000;
      $('time-total').textContent = formatTime(state.durationMs);
    });
    state.videoEl = video;
    $('video-slot').innerHTML = '';
    $('video-slot').appendChild(video);
    await video.play();
    state.startVideoLoop();
  }

  function startVideoLoop() {
    state.frameFn = () => {
      if (!state.videoEl) return;
      state.updateTransport(state.videoEl.currentTime * 1000);
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
    state.renderQueue();
    state.persist();
    if (next) state.playSong(next);
    else {
      state.stopPlayback();
      setPlaying(state, null);
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
    state.updateTransport(ms);
    updateLyrics(ms);
  }

  function enqueue(song) {
    state.queue.push(song);
    state.renderQueue();
    state.persist();
    setStatus(`Queued: ${songLabel(song)}`);
  }

  function playNext() {
    if (state.queue.length) {
      const next = state.queue.next();
      state.renderQueue();
      if (next) state.playSong(next);
      else {
        state.stopPlayback();
        setPlaying(state, null);
        setStatus('Queue is empty');
      }
    }
  }

  function playPrev() {
    if (state.queue.length) {
      const items = state.queue.items;
      const prev = items[Math.max(0, items.length - 2)];
      if (prev) state.playSong(prev);
    }
  }

  function updateSettings(patch) {
    const s = state.callApi('set_settings', patch);
    state.settings = {
      volume: Number(s.volume ?? state.settings.volume),
      sort: s.sort || state.settings.sort,
      zoom: s.cdg_zoom || state.settings.zoom,
      lookInsideZips: s.look_inside_zips !== false,
      excludeNonMatching: !!s.exclude_non_matching,
      deriveSongInfo: s.derive_song_info !== false,
      fileNameType: Number(s.file_name_type ?? state.settings.fileNameType),
      includePatterns: Array.isArray(s.include_patterns) ? s.include_patterns : state.settings.includePatterns,
      excludePatterns: Array.isArray(s.exclude_patterns) ? s.exclude_patterns : state.settings.excludePatterns,
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
    applyZoom(state);
  }

  return {
    boot,
    pickFolder,
    rescanFolders,
    replaceLibrary,
    exportLibrary,
    scanEntries,
    scanZips,
    restoreState,
    refreshSettings,
    persist,
    readBytes,
    mediaUrl,
    decodeText,
    resolveSongPath,
    resolveAudioPath,
    readSongBytes,
    readCompanionText,
    hasElrc,
    companionMember,
    waitFor,
    applyZoom,
    drawCdgUpdate,
    renderLyrics,
    updateLyrics,
    playSong,
    startLoop,
    playCdg,
    startCdgLoop,
    playKar,
    startSynthLoop,
    playLrc,
    playMpg,
    startVideoLoop,
    updateTransport,
    pauseMedia,
    resumeMedia,
    togglePlay,
    stopPlayback,
    onSongEnded,
    seekTo,
    enqueue,
    playNext,
    playPrev,
    updateSettings,
  };
}

class MidiSynth {
  constructor(parsed, computeNoteTimeline) {
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
