import { QUEUE_KEY, STORAGE_KEY, createStore } from '../store.js';
import {
  formatTime, debounce, escapeHtml, songLabel, KIND_BADGE,
  ELRC_EXT, companionBaseName, companionMember, SongQueue,
  partClass, partLabel, buildLyricLines,
} from '../helpers.js';

export function wireUi(state) {
  const { $, callApi } = state;

  // ── Folder picking ──────────────────────────────────────────────
  $('add-folder-btn').addEventListener('click', () => state.pickFolder());
  $('scan-library-btn').addEventListener('click', () => state.rescanFolders());
  $('replace-library-btn').addEventListener('click', () => state.replaceLibrary());
  $('export-library-btn').addEventListener('click', () => state.exportLibrary());
  $('import-library-btn').addEventListener('click', () => $('import-library-picker').click());
  $('import-library-picker').addEventListener('change', async (e) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;
    try {
      const text = await file.text();
      const result = callApi('import_json', text);
      if (result?.ok) {
        await state.refreshSettings();
        state.renderLibraryCount();
        state.renderResults();
        state.persist();
        const total = callApi('library_songs')?.songs?.length || 0;
        state.setStatus(`Library imported: ${total} songs`);
      } else {
        state.setStatus(`Import failed: ${result?.error || 'unknown error'}`);
      }
    } catch (err) {
      state.setStatus(`Import failed: ${err.message}`);
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
    await state.scanEntries(entries);
    e.target.value = '';
  });

  // ── Search ─────────────────────────────────────────────────────
  const searchInput = $('search-input');
  searchInput.addEventListener('input', debounce(async () => {
    const q = searchInput.value.trim();
    if (!q) {
      state.results = [];
      state.renderResults();
      return;
    }
    try {
      const r = callApi('search', q, 500);
      state.results = (r && r.results) || [];
    } catch (err) {
      state.results = [];
      state.setStatus(`Search error: ${err.message}`);
    }
    state.renderResults();
  }, 150));

  // ── Transport ──────────────────────────────────────────────────
  $('play-btn').addEventListener('click', () => state.togglePlay());
  $('stop-btn').addEventListener('click', () => {
    state.stopPlayback();
    state.setPlaying(null);
  });
  $('next-btn').addEventListener('click', () => state.playNext());
  $('prev-btn').addEventListener('click', () => state.playPrev());
  $('rewind-btn').addEventListener('click', () => state.seekTo(state.songClock - 5000));
  $('ff-btn').addEventListener('click', () => state.seekTo(state.songClock + 5000));
  $('progress-slider').addEventListener('input', (e) => {
    const max = state.durationMs || 1;
    state.seekTo((Number(e.target.value) / 1000) * max);
  });

  // ── Volume ─────────────────────────────────────────────────────
  $('volume-slider').addEventListener('input', (e) => {
    const v = Number(e.target.value) / 100;
    $('volume-value').textContent = `${e.target.value}%`;
    state.updateSettings({ volume: v });
  });

  // ── Queue ──────────────────────────────────────────────────────
  $('clear-queue-btn').addEventListener('click', () => {
    state.queue.clear();
    state.renderQueue();
    state.persist();
  });

  // ── Settings panel (inline, no modal) ─────────────────────────
  $('settings-btn').addEventListener('click', () => {
    $('settings-panel').hidden = !$('settings-panel').hidden;
  });
  $('setting-sort').addEventListener('change', (e) => state.updateSettings({ sort: e.target.value }));
  $('setting-zoom').addEventListener('change', (e) => state.updateSettings({ cdg_zoom: e.target.value }));
  $('setting-zips').addEventListener('change', (e) => state.updateSettings({ look_inside_zips: e.target.checked }));
  $('setting-exclude').addEventListener('change', (e) => state.updateSettings({ exclude_non_matching: e.target.checked }));
  $('setting-derive').addEventListener('change', (e) => state.updateSettings({ derive_song_info: e.target.checked }));
  $('setting-naming').addEventListener('change', (e) => state.updateSettings({ file_name_type: Number(e.target.value) }));
  $('setting-include-patterns').addEventListener('change', (e) => state.updateSettings({ include_patterns: state.parsePatternList(e.target.value) }));
  $('setting-exclude-patterns').addEventListener('change', (e) => state.updateSettings({ exclude_patterns: state.parsePatternList(e.target.value) }));

  // ── Kind filters ───────────────────────────────────────────────
  ['filter-cdg', 'filter-kar', 'filter-mpg', 'filter-lrc'].forEach((id) => {
    $(id).addEventListener('change', () => state.renderResults());
  });

  // ── Keyboard shortcuts ─────────────────────────────────────────
  document.addEventListener('keydown', (e) => {
    const target = e.target;
    const inInput = target && (target.tagName === 'INPUT' || target.tagName === 'SELECT');
    if (state.focusSearchKey(e, searchInput)) return;
    if (state.dismissSearchKey(e, inInput, searchInput)) return;
    if (state.togglePlaybackKey(e, inInput)) return;
    if (state.enqueueSelectedKey(e, inInput)) return;
    state.moveSelectionKey(e, inInput);
    state.deleteQueueItemKey(e, inInput);
    state.reorderQueueKey(e);
    state.nextSongKey(e);
  });
}
