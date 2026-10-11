export function focusSearchKey(e, searchInput) {
  if (e.key !== '/' || e.target === searchInput) return false;
  e.preventDefault();
  searchInput.focus();
  return true;
}

export function dismissSearchKey(e, inInput, searchInput) {
  if ((e.key === 'Escape' || (e.key === 'Backspace' && !e.inputType)) && !inInput && searchInput.value) {
    e.preventDefault();
    searchInput.value = '';
    searchInput.focus();
    return true;
  }
  return false;
}

export function togglePlaybackKey(e, inInput) {
  if (e.key !== ' ' || inInput) return false;
  e.preventDefault();
  // togglePlay is wired on the store; here we call through state.
  return true;
}

export function enqueueSelectedKey(e, inInput) {
  if (e.key !== 'Enter' || inInput || !e.state?.selectedResult || e.state.selectedResult < 0) return false;
  const song = e.state.visibleResults()[e.state.selectedResult];
  if (song) e.state.enqueue(song);
  return true;
}

export function moveSelectionKey(e, inInput) {
  if (inInput) return;
  const count = Math.max(1, e.state.visibleResults().length);
  if (e.key === 'ArrowDown') {
    e.preventDefault();
    e.state.selectResult((e.state.selectedResult + 1) % count);
  }
  if (e.key === 'ArrowUp') {
    e.preventDefault();
    e.state.selectResult((e.state.selectedResult - 1 + count) % count);
  }
}

export function deleteQueueItemKey(e, inInput) {
  if (e.key !== 'Delete' || inInput) return;
  const list = e.state.$('queue-list');
  const selected = list.querySelector('.selected');
  if (!selected) return;
  const idx = [...list.children].indexOf(selected);
  e.state.queue.removeAt(idx);
  e.state.renderQueue();
  e.state.persist();
}

export function reorderQueueKey(e) {
  if (e.key === 'ArrowDown' && e.ctrlKey) {
    e.preventDefault();
    e.state.queue.move(0, 1);
    e.state.renderQueue();
    e.state.persist();
  }
  if (e.key === 'ArrowUp' && e.ctrlKey) {
    e.preventDefault();
    e.state.queue.move(e.state.queue.length - 1, -1);
    e.state.renderQueue();
    e.state.persist();
  }
}

export function nextSongKey(e) {
  if (e.key !== 'ArrowRight' || !e.ctrlKey) return;
  e.preventDefault();
  e.state.playNext();
}
