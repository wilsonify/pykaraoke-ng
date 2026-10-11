import { escapeHtml, songLabel, KIND_BADGE, ELRC_EXT, companionBaseName, companionMember, SongQueue, buildLyricLines, partClass, partLabel } from '../helpers.js';

export const SCAN_CATEGORY_LABELS = {
  unsupported: 'unsupported',
  filtered: 'filtered',
  corrupt_archive: 'corrupt archive',
  unsupported_compression: 'unsupported compression',
  unreadable: 'unreadable',
  parse_failure: 'parse failure',
};

export function renderLibraryCount(state) {
  const total = state.callApi('library_songs')?.songs?.length || 0;
  state.$('library-count').textContent = `${total} songs`;
}

export function parsePatternList(text) {
  return String(text).split(/[\n,]/).map((s) => s.trim()).filter(Boolean);
}

export function renderScanSummary(state) {
  const el = state.$('scan-summary');
  let report = null;
  try { report = state.callApi('scan_report'); } catch { report = null; }
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
    try { state.callApi('clear_scan_report'); } catch { /* engine may be gone */ }
    el.hidden = true;
    el.textContent = '';
  });
  el.append(' ', clear);
  el.hidden = false;
}

export function renderLyricLines(state) {
  const box = state.$('lyrics');
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

export function renderResults(state) {
  const list = state.$('results-list');
  const kindFilter = {
    cdg: state.$('filter-cdg').checked,
    kar: state.$('filter-kar').checked,
    mpg: state.$('filter-mpg').checked,
    lrc: state.$('filter-lrc').checked,
  };
  const visible = state.results.filter((s) => kindFilter[s.kind]);
  if (!state.results.length) {
    list.innerHTML = '<div class="no-results">Type to search your library</div>';
    state.selectedResult = -1;
    return;
  }
  if (!visible.length) {
    list.innerHTML = '<div class="no-results">No results match the filters</div>';
    state.selectedResult = -1;
    return;
  }
  list.innerHTML = '';
  visible.forEach((song, i) => {
    const row = document.createElement('div');
    row.className = 'song-row';
    row.setAttribute('role', 'option');
    row.setAttribute('aria-selected', 'false');
    row.dataset.index = String(i);

    const info = document.createElement('div');
    info.className = 'song-row-info';
    info.innerHTML = `<span class="song-row-title">${escapeHtml(songLabel(song))}</span>` +
      `<span class="song-row-file muted">${escapeHtml(song.filename)}</span>`;

    const badge = document.createElement('span');
    badge.className = `badge badge-${song.kind}`;
    badge.textContent = KIND_BADGE[song.kind] || song.kind;
    if (state.hasElrc?.(song)) {
      badge.textContent = 'ELRC';
      badge.title = 'Word-level timing (.elrc)';
    }

    const play = document.createElement('button');
    play.className = 'btn btn-icon btn-row-play';
    play.title = 'Play now';
    play.textContent = '▶';
    play.addEventListener('click', (e) => {
      e.stopPropagation();
      state.playSong(song);
    });

    row.append(badge, info, play);
    row.addEventListener('click', () => state.enqueue(song));
    row.addEventListener('dblclick', () => state.playSong(song));
    list.appendChild(row);
  });
  state.selectedResult = -1;
}

export function selectResult(state, i) {
  const rows = state.$('results-list').querySelectorAll('.song-row');
  if (!rows.length) return;
  state.selectedResult = (i + rows.length) % rows.length;
  rows.forEach((r, idx) => {
    const selected = idx === state.selectedResult;
    r.classList.toggle('selected', selected);
    r.setAttribute('aria-selected', String(selected));
  });
  rows[state.selectedResult].scrollIntoView({ block: 'nearest' });
}

export function renderQueue(state) {
  const list = state.$('queue-list');
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
      renderQueue(state);
      state.persist();
    });
    row.append(info, remove);
    row.addEventListener('dblclick', () => state.playSong(song));
    list.appendChild(row);
  });
}

export function setStatus(msg) {
  document.getElementById('status-message').textContent = msg;
}

export function setEngineStatus(msg) {
  document.getElementById('engine-status').textContent = msg;
}

export function setPlaying(state, song) {
  state.current = song;
  document.getElementById('current-song-title').textContent = song ? songLabel(song) : '—';
  document.getElementById('current-song-artist').textContent = song ? song.filename : '';
  document.getElementById('play-btn').textContent = state.playing ? '⏸' : '▶';
  document.getElementById('stage-empty').style.display = song ? 'none' : '';
}

export function applyZoom(state) {
  const scale = state.settings.zoom === 'quick' ? 0.75 :
    state.settings.zoom === 'int' ? 1 :
    state.settings.zoom === 'full' ? 1.5 :
    state.settings.zoom === 'soft' ? 2 : 1;
  const canvas = document.getElementById('cdg-canvas');
  canvas.width = Math.round(288 * scale);
  canvas.height = Math.round(192 * scale);
  canvas.style.width = `${canvas.width}px`;
  canvas.style.height = `${canvas.height}px`;
}
