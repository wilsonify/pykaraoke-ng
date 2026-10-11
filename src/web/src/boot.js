import { createStore } from './store.js';
import { wireUi } from './ui/wire-ui.js';
import { makePlayback } from './ui/playback.js';
import { renderLibraryCount, renderScanSummary, renderResults, renderQueue, setStatus, setEngineStatus, setPlaying, applyZoom, selectResult } from './ui/render.js';
import { focusSearchKey, dismissSearchKey, enqueueSelectedKey, moveSelectionKey, deleteQueueItemKey, reorderQueueKey, nextSongKey } from './ui/commands.js';
import { SongQueue } from './helpers.js';

export function boot() {
  const tauriCore = window.__TAURI__?.core;
  const callApi = (name, ...args) => {
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
  };

  const state = {
    queue: new SongQueue(),
    settings: { volume: 0.75, sort: 'filename', zoom: 'int', lookInsideZips: true },
    files: new Map(),
    pathByBase: new Map(),
    results: [],
    selectedResult: -1,
    current: null,
    playing: false,
    durationMs: 0,
    lyricLines: null,
    parts: null,
    lastLyricLine: -1,
    cdgKey: null,
    audioEl: null,
    videoEl: null,
    synth: null,
    songClock: 0,
    rafId: null,
    frameFn: null,
    callApi,
    $,
    tauriCore,
    visibleResults() {
      const kindFilter = {
        cdg: this.$('filter-cdg').checked,
        kar: this.$('filter-kar').checked,
        mpg: this.$('filter-mpg').checked,
        lrc: this.$('filter-lrc').checked,
      };
      return this.results.filter((s) => kindFilter[s.kind]);
    },
    enqueue,
    togglePlay,
    stopPlayback,
    seekTo,
    playSong,
    playNext,
    playPrev,
    updateSettings,
    scanEntries,
    scanZips,
    restoreState,
    refreshSettings,
    persist,
    renderLibraryCount: () => renderLibraryCount(state),
    renderScanSummary: () => renderScanSummary(state),
    renderResults: () => renderResults(state),
    renderQueue: () => renderQueue(state),
    setStatus: (msg) => setStatus(state, msg),
    setEngineStatus: (msg) => setEngineStatus(state, msg),
    setPlaying: (song) => setPlaying(state, song),
    applyZoom: () => applyZoom(state),
    selectResult: (i) => selectResult(state, i),
    focusSearchKey: (e, input) => focusSearchKey(e, input),
    dismissSearchKey: (e, inInput, input) => dismissSearchKey(e, inInput, input),
    enqueueSelectedKey: (e, inInput) => enqueueSelectedKey(e, inInput),
    moveSelectionKey: (e, inInput) => moveSelectionKey(e, inInput),
    deleteQueueItemKey: (e, inInput) => deleteQueueItemKey(e, inInput),
    reorderQueueKey: (e) => reorderQueueKey(e),
    nextSongKey: (e) => nextSongKey(e),
  };

  wireUi(state);
  const playback = makePlayback(state);
  Object.assign(state, playback);
  state.boot();
}

function enqueue(song) {
  this.queue.push(song);
  this.renderQueue();
  this.persist();
  setStatus(this, `Queued: ${songLabel(song)}`);
}

function togglePlay() {
  if (!this.current) return;
  if (this.playing) {
    this.pauseMedia();
  } else {
    this.resumeMedia();
  }
}

function pauseMedia() {
  this.playing = false;
  if (this.audioEl) this.audioEl.pause();
  if (this.synth) this.synth.pause();
  if (this.videoEl) this.videoEl.pause();
  cancelAnimationFrame(this.rafId);
  this.$('play-btn').textContent = '▶';
}

function resumeMedia() {
  this.playing = true;
  this.$('play-btn').textContent = '⏸';
  if (this.audioEl) this.audioEl.play();
  if (this.synth) this.synth.resume();
  if (this.videoEl) this.videoEl.play();
  if (this.frameFn) this.startLoop(this.frameFn);
}

function playNext() {
  if (this.queue.length) {
    const next = this.queue.next();
    this.renderQueue();
    if (next) this.playSong(next);
    else {
      this.stopPlayback();
      this.setPlaying(null);
      setStatus(this, 'Queue finished');
    }
  }
}

function playPrev() {
  if (this.queue.length) {
    const items = this.queue.items;
    const prev = items[Math.max(0, items.length - 2)];
    if (prev) this.playSong(prev);
  }
}

function stopPlayback() {
  this.playing = false;
  cancelAnimationFrame(this.rafId);
  this.frameFn = null;
  if (this.audioEl) {
    this.audioEl.pause();
    this.audioEl.src = '';
    this.audioEl = null;
  }
  if (this.synth) {
    this.synth.stop();
    this.synth = null;
  }
  if (this.videoEl) {
    this.videoEl.pause();
    this.videoEl.src = '';
    this.videoEl = null;
    this.$('video-slot').innerHTML = '';
  }
  if (this.cdgKey) {
    this.callApi('cdg_close', this.cdgKey);
    this.cdgKey = null;
  }
  this.lyricLines = null;
  this.parts = null;
  this.$('lyrics').innerHTML = '';
  this.$('lyrics').style.display = 'none';
  this.durationMs = 0;
  this.$('time-current').textContent = '0:00';
  this.$('time-total').textContent = '0:00';
  this.$('progress-slider').value = 0;
  this.$('play-btn').textContent = '▶';
}

function seekTo(ms) {
  ms = Math.max(0, ms);
  if (this.audioEl) this.audioEl.currentTime = ms / 1000;
  if (this.cdgKey) {
    this.callApi('cdg_seek', this.cdgKey, ms);
    this.drawCdgUpdate(this.callApi('cdg_update', this.cdgKey, ms));
  }
  if (this.synth) this.synth.seek(ms);
  if (this.videoEl) this.videoEl.currentTime = ms / 1000;
  this.updateTransport(ms);
  this.updateLyrics(ms);
}

function updateTransport(ms) {
  this.songClock = ms;
  this.$('time-current').textContent = ms === 0 && this.durationMs === 0 ? '0:00' : formatTime(ms);
  const max = this.durationMs || 1;
  this.$('progress-slider').value = Math.min(1000, Math.round((ms / max) * 1000));
}

import { formatTime } from './helpers.js';
