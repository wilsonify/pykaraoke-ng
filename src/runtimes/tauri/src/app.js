let invoke = async function(command, payload) {
    return { command: command, payload: payload || {} };
};
let listenEvent = async function() {
    return function() {};
};
let dialogOpen = async function() {
    return null;
};

try {
    if (globalThis.__TAURI__?.tauri?.invoke) {
        invoke = globalThis.__TAURI__.tauri.invoke;
    }
    if (globalThis.__TAURI__?.event?.listen) {
        listenEvent = globalThis.__TAURI__.event.listen;
    }
    if (globalThis.__TAURI__?.dialog?.open) {
        dialogOpen = globalThis.__TAURI__.dialog.open;
    }
} catch (err) {
    console.warn('Tauri API not available, using fallback mode:', err);
    dialogOpen = async function() { return null; };
}

class PyKaraokeApp {
    constructor() {
        this.searchResults = [];
        this.backendStartRetries = 0;
        this.maxBackendRetries = 3;
        this._unlisteners = [];
    }

    async init() {
        this.setupUIEventListeners();
        await this.ensureEngineStarted();
        this.setupEngineEventListeners();
    }

    errorMessage(err) {
        if (!err) return 'Unknown error';
        if (typeof err === 'string') return err;
        if (typeof err.message === 'string' && err.message.length > 0) return err.message;
        try {
            return JSON.stringify(err);
        } catch (e) {
            console.error('Failed to stringify error:', e);
            return String(err);
        }
    }

    // ── Engine lifecycle ───────────────────────────────────────────────

    async ensureEngineStarted() {
        try {
            this.updateStatus('Starting engine...');
            await invoke('engine_start');

            var status = await invoke('engine_status');
            var running = status === '"running"' || status === 'running';

            this.engineRunning = running;
            this.backendStartRetries = 0;
            this.updateBackendStatus(running);
            this.updateStatus('Engine connected');
        } catch (e) {
            console.error('Engine startup failed:', e);
            this.backendStartRetries++;
            if (this.backendStartRetries >= this.maxBackendRetries) {
                this.updateStatus(
                    'Engine failed after ' + this.maxBackendRetries + ' attempts. '
                    + 'Please check your installation and restart the application.'
                );
                this.engineRunning = false;
                this.updateBackendStatus(false);
                return;
            }
            this.updateStatus('Engine startup failed (' + this.backendStartRetries
                + '/' + this.maxBackendRetries + '): ' + this.errorMessage(e));
            this.engineRunning = false;
            this.updateBackendStatus(false);
        }
    }

    // ── Engine event listeners (event-driven, no polling) ──────────────

    setupEngineEventListeners() {
        var self = this;

        listenEvent('engine:cdg_frame', function(event) {
            self.renderCdgFrame(event.payload);
        }).then(function(unlisten) { self._unlisteners.push(unlisten); });

        listenEvent('engine:lyrics_changed', function(event) {
            self.renderLyrics(event.payload);
        }).then(function(unlisten) { self._unlisteners.push(unlisten); });

        listenEvent('engine:playback_changed', function(event) {
            var s = event.payload;
            self.updateUIFromState(s);
            var playing = s && s.status === 'playing';
            document.getElementById('play-btn').style.display = playing ? 'none' : 'inline-block';
            document.getElementById('pause-btn').style.display = playing ? 'inline-block' : 'none';
            self._updateTickInterval(s);
            if (!playing) {
                self.clearCdgDisplay();
                self.renderLyrics(null);
            }
        }).then(function(unlisten) { self._unlisteners.push(unlisten); });

        listenEvent('engine:queue_changed', function(event) {
            self.renderPlaylist(event.payload);
        }).then(function(unlisten) { self._unlisteners.push(unlisten); });

        listenEvent('engine:song_finished', function(event) {
            var song = event.payload && event.payload.song;
            var name = song && (song.displayName || song.title || song.filename);
            self.updateStatus(name ? 'Finished "' + name + '"' : 'Song finished');
        }).then(function(unlisten) { self._unlisteners.push(unlisten); });

        listenEvent('engine:library_changed', function(event) {
            self.updateStatus('Library updated');
        }).then(function(unlisten) { self._unlisteners.push(unlisten); });

        listenEvent('engine:settings_changed', function(event) {
            self.updateStatus('Settings updated');
        }).then(function(unlisten) { self._unlisteners.push(unlisten); });

        listenEvent('engine:scan_progress', function(event) {
            var p = event.payload;
            if (p && p.status === 'scanning') {
                self.updateStatus('Scanning… ' + (p.foldersScanned || 0) + ' folders, ' + (p.songsFound || 0) + ' songs');
            } else if (p && p.status === 'complete') {
                var count = p.songsFound || 0;
                self.updateStatus('Scan complete – ' + count + ' song' + (count !== 1 ? 's' : '') + ' found');
            } else if (p && p.status === 'error') {
                self.updateStatus('Scan failed');
            }
        }).then(function(unlisten) { self._unlisteners.push(unlisten); });

        listenEvent('engine:error', function(event) {
            self.updateStatus('Error: ' + event.payload.message);
        }).then(function(unlisten) { self._unlisteners.push(unlisten); });
    }

    // ── Playback tick (drives Rust decoders) ───────────────────────────

    _updateTickInterval(s) {
        var playing = s && s.status === 'playing';
        if (playing && !this._tickTimer) {
            var self = this;
            this._tickTimer = setInterval(function() {
                invoke('engine_tick', {}).catch(function(err) {
                    console.warn('Tick failed:', err);
                });
            }, 33); // ~30 fps
        } else if (!playing && this._tickTimer) {
            clearInterval(this._tickTimer);
            this._tickTimer = null;
        }
    }

    destroy() {
        this._unlisteners.forEach(function(fn) { fn(); });
        this._unlisteners = [];
        if (this._tickTimer) {
            clearInterval(this._tickTimer);
            this._tickTimer = null;
        }
    }

    // ── UI Event listeners ─────────────────────────────────────────────

    setupUIEventListeners() {
        function $(id) { return document.getElementById(id); }
        var self = this;

        $('play-btn').addEventListener('click', async function() {
            try {
                var state = await invoke('playback_play', {});
                self.updateUIFromState(state);
            } catch (e) { self.updateStatus('Error: ' + self.errorMessage(e)); }
        });
        $('pause-btn').addEventListener('click', async function() {
            try {
                var state = await invoke('playback_pause', {});
                self.updateUIFromState(state);
            } catch (e) { self.updateStatus('Error: ' + self.errorMessage(e)); }
        });
        $('stop-btn').addEventListener('click', async function() {
            try {
                var state = await invoke('playback_stop', {});
                self.updateUIFromState(state);
            } catch (e) { self.updateStatus('Error: ' + self.errorMessage(e)); }
        });
        $('next-btn').addEventListener('click', async function() {
            try {
                var state = await invoke('playback_next', {});
                self.updateUIFromState(state);
            } catch (e) { self.updateStatus('Error: ' + self.errorMessage(e)); }
        });
        $('prev-btn').addEventListener('click', async function() {
            try {
                var state = await invoke('playback_previous', {});
                self.updateUIFromState(state);
            } catch (e) { self.updateStatus('Error: ' + self.errorMessage(e)); }
        });

        // Fast-forward / Rewind: single-click step + hold for continuous seeking
        this._setupSeekButton('ff-btn', 10);
        this._setupSeekButton('rewind-btn', -10);

        $('volume-slider').addEventListener('input', function(e) {
            var v = Number.parseInt(e.target.value);
            $('volume-value').textContent = v + '%';
            invoke('playback_set_volume', { volume: v / 100 }).catch(function(err) {
                console.warn('Volume update failed:', err);
            });
        });

        $('progress-slider').addEventListener('input', function(e) {
            var s = self.currentState;
            if (s && s.durationMs > 0) {
                var pct = Number.parseInt(e.target.value) / 10;
                var pos_ms = Math.round((pct / 100) * s.durationMs);
                document.getElementById('time-current').textContent = self.fmtTime(pos_ms);
            }
        });

        $('progress-slider').addEventListener('change', async function(e) {
            var s = self.currentState;
            if (s && s.durationMs > 0) {
                var pct = Number.parseInt(e.target.value) / 10;
                var pos_ms = Math.round((pct / 100) * s.durationMs);
                try {
                    var state = await invoke('playback_seek', { position_ms: pos_ms });
                    self.updateUIFromState(state);
                } catch (ex) {
                    self.updateStatus('Seek error: ' + self.errorMessage(ex));
                }
            }
        });

        $('search-btn').addEventListener('click', function() { self.handleSearch(); });
        $('search-input').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') self.handleSearch();
        });
        $('search-input').addEventListener('input', function() {
            clearTimeout(self._searchDebounce);
            self._searchDebounce = setTimeout(function() { self.handleSearch(); }, 200);
        });

        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                $('search-input').value = '';
                $('search-input').focus();
                self.searchResults = [];
                self.renderSearchResults();
                self.updateStatus('');
                e.preventDefault();
            }
            var tag = document.activeElement.tagName;
            if (e.key === '/' && tag !== 'INPUT' && tag !== 'TEXTAREA' && tag !== 'SELECT') {
                $('search-input').focus();
                e.preventDefault();
            }
        });

        $('add-folder-btn').addEventListener('click', function() { self.handleAddFolder(); });
        $('scan-library-btn').addEventListener('click', function() { self.handleScanLibrary(); });

        var closeSettings = function() { self.handleCloseSettings(); };
        var settingsBtn = document.getElementById('settings-btn');
        settingsBtn.addEventListener('click', function() { self.handleShowSettings(); });
        if ($('settings-close-btn'))  $('settings-close-btn').addEventListener('click', closeSettings);
        if ($('settings-cancel-btn')) $('settings-cancel-btn').addEventListener('click', closeSettings);
        if ($('settings-save-btn'))   $('settings-save-btn').addEventListener('click', function() { self.handleSaveSettings(); });

        $('clear-playlist-btn').addEventListener('click', function() { self.handleClearPlaylist(); });

        // ── Queue drop-target ──
        var playlist = $('playlist');
        playlist.addEventListener('dragover', function(e) {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'copy';
            playlist.classList.add('drag-over');
        });
        playlist.addEventListener('dragleave', function() {
            playlist.classList.remove('drag-over');
        });
        playlist.addEventListener('drop', function(e) {
            e.preventDefault();
            playlist.classList.remove('drag-over');
            var raw = e.dataTransfer.getData('application/x-pykaraoke-song');
            if (!raw) {
                console.error('[PyKaraoke] drop: no song data in transfer');
                self.updateStatus('Drop failed: no song data');
                return;
            }
            try {
                var song = JSON.parse(raw);
                console.debug('[PyKaraoke] drop: received', song.filepath);
                self.enqueueSong(song);
            } catch (err) {
                console.error('[PyKaraoke] drop: invalid song data', err);
                self.updateStatus('Drop failed: invalid data');
            }
        });
    }

    // ── Command handlers ───────────────────────────────────────────────

    async handleSearch() {
        var query = document.getElementById('search-input').value;
        if (!query) {
            this.searchResults = [];
            this.renderSearchResults();
            this.updateStatus('');
            return;
        }
        this.updateStatus('Searching…');
        try {
            var result = await invoke('search', { query: query });
            this.searchResults = result.results || [];
            this.renderSearchResults();
            this.updateStatus('Found ' + this.searchResults.length + ' results');
        } catch (_) {
            this.updateStatus('Search failed');
        }
    }

    async handleAddFolder() {
        var input = document.getElementById('folder-input');
        var folder = '';

        try {
            var selected = await dialogOpen({
                directory: true,
                multiple: false,
                title: 'Select Karaoke Folder'
            });
            if (typeof selected === 'string') {
                folder = selected;
            }
        } catch (_) {
            // Ignore picker failures and fall back to manual input.
        }

        if (!folder && input) {
            folder = input.value.trim();
        }
        if (!folder) {
            this.updateStatus('No folder selected');
            return;
        }
        this.updateStatus('Adding folder: ' + folder);
        try {
            await invoke('library_add_folder', { path: folder });
            this.updateStatus('Folder added: ' + folder);
        } catch (e) {
            this.updateStatus('Error: ' + this.errorMessage(e));
        }
    }

    async handleScanLibrary() {
        this.updateStatus('Scanning library…');
        try {
            var result = await invoke('library_scan', {});
            var count = (result && result.songsFound) || 0;
            this.updateStatus('Scan complete – ' + count + ' song' + (count !== 1 ? 's' : '') + ' found');
        } catch (e) {
            this.updateStatus('Scan failed: ' + this.errorMessage(e));
        }
    }

    async handleShowSettings() {
        var modal = document.getElementById('settings-modal');
        if (!modal) return;
        try {
            var result = await invoke('settings_get', {});
            if (result && result.display) {
                var fs = document.getElementById('setting-fullscreen');
                if (fs) fs.checked = result.display.fullscreen || false;
                var zoom = document.getElementById('setting-zoom');
                if (zoom && result.display.zoom) {
                    zoom.value = result.display.zoom;
                }
            } else {
                this.updateStatus('Could not load settings');
            }
        } catch (_) {
            this.updateStatus('Could not load settings (engine unavailable)');
        }
        modal.style.display = 'flex';
    }

    handleCloseSettings() {
        var m = document.getElementById('settings-modal');
        if (m) m.style.display = 'none';
    }

    async handleSaveSettings() {
        var clean = {};
        var fsEl = document.getElementById('setting-fullscreen');
        if (fsEl) clean.fullscreen = fsEl.checked;
        var zoomEl = document.getElementById('setting-zoom');
        if (zoomEl) clean.zoom = zoomEl.value;
        try {
            await invoke('settings_update', { delta: clean });
            this.updateStatus('Settings saved');
            this.handleCloseSettings();
        } catch (e) {
            this.updateStatus('Error: ' + this.errorMessage(e));
        }
    }

    async handleClearPlaylist() {
        try {
            var result = await invoke('queue_clear', {});
            this.renderPlaylist(result);
            this.updateStatus('Playlist cleared');
        } catch (e) {
            this.updateStatus('Error: ' + this.errorMessage(e));
        }
    }

    // ── UI updates ─────────────────────────────────────────────────────

    updateUIFromState(s) {
        if (!s) return;
        this.currentState = s;

        var title = 'No song loaded';
        var artist = '';
        if (s.currentSong) {
            title = s.currentSong.title || s.currentSong.filename || 'Unknown';
            artist = s.currentSong.artist || '';
        }
        document.getElementById('current-song-title').textContent = title;
        document.getElementById('current-song-artist').textContent = artist;

        var playing = s.status === 'playing';
        document.getElementById('play-btn').style.display = playing ? 'none' : 'inline-block';
        document.getElementById('pause-btn').style.display = playing ? 'inline-block' : 'none';
        this._updateTickInterval(s);

        if (s.durationMs > 0 && typeof s.positionMs === 'number') {
            var pct = Math.min(1000, Math.max(0, (s.positionMs / s.durationMs) * 1000));
            document.getElementById('progress-slider').value = Math.round(pct);
            document.getElementById('time-current').textContent = this.fmtTime(s.positionMs);
            document.getElementById('time-total').textContent = this.fmtTime(s.durationMs);
        } else {
            document.getElementById('progress-slider').value = 0;
            document.getElementById('time-current').textContent = this.fmtTime(s.positionMs || 0);
            document.getElementById('time-total').textContent = this.fmtTime(0);
        }
    }

    // ── CDG / Lyrics rendering ─────────────────────────────────────

    renderCdgFrame(frame) {
        if (!frame || !frame.pixels || !frame.pixels.length) return;
        var canvas = document.getElementById('cdg-canvas');
        if (!canvas) return;
        var ctx = canvas.getContext('2d');
        if (!ctx) return;
        var w = frame.width || 300;
        var h = frame.height || 216;
        if (canvas.width !== w || canvas.height !== h) {
            canvas.width = w;
            canvas.height = h;
        }
        var imageData = ctx.createImageData(w, h);
        imageData.data.set(frame.pixels);
        ctx.putImageData(imageData, 0, 0);
    }

    clearCdgDisplay() {
        var canvas = document.getElementById('cdg-canvas');
        if (!canvas) return;
        var ctx = canvas.getContext('2d');
        if (!ctx) return;
        ctx.clearRect(0, 0, canvas.width, canvas.height);
    }

    renderLyrics(lyricsView) {
        var el = document.getElementById('lyrics-overlay');
        if (!el) return;
        if (!lyricsView || (!lyricsView.currentLine && !lyricsView.nextLine)) {
            el.innerHTML = '';
            return;
        }
        var html = '';
        if (lyricsView.currentLine) {
            html += '<div class="lyric-line lyric-current">' + this.escapeHtml(lyricsView.currentLine) + '</div>';
        }
        if (lyricsView.nextLine) {
            html += '<div class="lyric-line lyric-future">' + this.escapeHtml(lyricsView.nextLine) + '</div>';
        }
        el.innerHTML = html;
    }

    escapeHtml(text) {
        var div = document.createElement('div');
        div.appendChild(document.createTextNode(text));
        return div.innerHTML;
    }

    renderPlaylist(view) {
        var el = document.getElementById('playlist');
        var self = this;
        var list = view && view.songs ? view.songs : [];
        el.textContent = '';
        if (!list || !list.length) {
            var msg = document.createElement('div');
            msg.className = 'no-results';
            msg.textContent = 'Playlist is empty';
            el.appendChild(msg);
            return;
        }
        for (var i = 0; i < list.length; i++) {
            var s = list[i];
            var item = document.createElement('div');
            item.className = 'song-item' + (self.currentState && view.currentIndex === i ? ' active' : '');
            item.dataset.index = String(i);

            var info = document.createElement('div');
            info.className = 'song-item-info';

            var title = document.createElement('div');
            title.className = 'song-item-title';
            title.textContent = s.title || s.filename || '';

            var artist = document.createElement('div');
            artist.className = 'song-item-artist';
            artist.textContent = s.artist || '';

            info.appendChild(title);
            info.appendChild(artist);
            item.appendChild(info);

            var removeBtn = document.createElement('button');
            removeBtn.className = 'song-item-remove';
            removeBtn.dataset.i = String(i);
            removeBtn.title = 'Remove';
            removeBtn.textContent = '\u2715';
            item.appendChild(removeBtn);

            el.appendChild(item);
        }

        el.querySelectorAll('.song-item').forEach(function(item) {
            item.addEventListener('click', function(e) {
                if (e.target.classList.contains('song-item-remove')) return;
                var idx = parseInt(item.dataset.index);
                self.playFromQueue(idx);
            });
        });
        el.querySelectorAll('.song-item-remove').forEach(function(btn) {
            btn.addEventListener('click', function(e) {
                e.stopPropagation();
                var idx = parseInt(btn.dataset.i);
                invoke('queue_remove', { index: idx })
                    .then(function(result) { self.renderPlaylist(result); })
                    .catch(function(err) {
                        self.updateStatus('Error: ' + self.errorMessage(err));
                    });
            });
        });
    }

    async playFromQueue(index) {
        try {
            var queueResult = await invoke('queue_list', {});
            if (queueResult && queueResult.songs && queueResult.songs[index]) {
                var song = queueResult.songs[index];
                if (typeof song.id !== 'number') {
                    this.updateStatus('Error: queued song has no playable ID');
                    return;
                }
                var state = await invoke('playback_play', { song_id: song.id });
                this.updateUIFromState(state);
            }
        } catch (e) {
            this.updateStatus('Error: ' + this.errorMessage(e));
        }
    }

    renderSearchResults() {
        var el = document.getElementById('results-list');
        var self = this;
        el.textContent = '';
        if (!this.searchResults.length) {
            var msg = document.createElement('div');
            msg.className = 'no-results';
            msg.textContent = 'No results found';
            el.appendChild(msg);
            return;
        }
        for (var i = 0; i < this.searchResults.length; i++) {
            var s = this.searchResults[i];
            var item = document.createElement('div');
            item.className = 'song-item';
            item.dataset.index = String(i);
            item.tabIndex = 0;
            item.role = 'option';
            item.draggable = true;

            var info = document.createElement('div');
            info.className = 'song-item-info';

            var title = document.createElement('div');
            title.className = 'song-item-title';
            title.textContent = s.title || s.filename || '';

            var artist = document.createElement('div');
            artist.className = 'song-item-artist';
            artist.textContent = s.artist || '';

            info.appendChild(title);
            info.appendChild(artist);
            item.appendChild(info);
            el.appendChild(item);
        }

        el.querySelectorAll('.song-item').forEach(function(item) {
            var clickTimer = null;
            var enqueue = function() {
                var song = self.searchResults[parseInt(item.dataset.index)];
                if (!song || !song.filepath) {
                    console.error('[PyKaraoke] enqueue failed: no filepath for index', item.dataset.index);
                    self.updateStatus('Error: song has no file path');
                    return;
                }
                console.debug('[PyKaraoke] enqueue: click/enter on', song.filepath);
                self.enqueueSong(song);
            };
            item.addEventListener('click', function(e) {
                if (clickTimer) {
                    clearTimeout(clickTimer);
                    clickTimer = null;
                    return;
                }
                clickTimer = setTimeout(function() {
                    clickTimer = null;
                    enqueue();
                }, 250);
            });
            item.addEventListener('dblclick', function(e) {
                e.preventDefault();
                if (clickTimer) {
                    clearTimeout(clickTimer);
                    clickTimer = null;
                }
                enqueue();
            });
            item.addEventListener('keydown', function(e) { if (e.key === 'Enter') enqueue(); });
            item.addEventListener('dragstart', function(e) {
                var song = self.searchResults[parseInt(item.dataset.index)];
                console.debug('[PyKaraoke] drag-start:', song && song.filepath);
                e.dataTransfer.setData('application/x-pykaraoke-song', JSON.stringify(song));
                e.dataTransfer.effectAllowed = 'copy';
            });
        });
    }

    async enqueueSong(song) {
        if (!song || !song.filepath) {
            console.error('[PyKaraoke] enqueueSong: missing song or filepath');
            this.updateStatus('Error: cannot enqueue – no file path');
            return;
        }
        console.debug('[PyKaraoke] enqueueSong:', song.filepath);
        try {
            var result = await invoke('queue_enqueue', { filepath: song.filepath });
            this.renderPlaylist(result);
            this.updateStatus('Added "' + (song.title || song.filename) + '" to queue');
        } catch (e) {
            console.error('[PyKaraoke] enqueue exception:', e);
            this.updateStatus('Failed to enqueue: ' + this.errorMessage(e));
        }
    }

    _setupSeekButton(btnId, stepSeconds) {
        var btn = document.getElementById(btnId);
        if (!btn) return;
        var self = this;
        var timer = null;

        function stopSeek() {
            if (timer) { clearInterval(timer); timer = null; }
        }

        function doSeek() {
            var s = self.currentState;
            if (s && s.durationMs > 0 && typeof s.positionMs === 'number') {
                var newPos = s.positionMs + (stepSeconds * 1000);
                newPos = Math.max(0, Math.min(newPos, s.durationMs));
                invoke('playback_seek', { position_ms: newPos })
                    .then(function(state) { self.updateUIFromState(state); })
                    .catch(function(e) {
                        self.updateStatus('Error: ' + self.errorMessage(e));
                        stopSeek();
                    });
            }
        }

        btn.addEventListener('mousedown', function() {
            doSeek();
            if (timer) clearInterval(timer);
            timer = setInterval(doSeek, 500);
        });

        btn.addEventListener('mouseup', stopSeek);
        btn.addEventListener('mouseleave', stopSeek);
        btn.addEventListener('click', function(e) {
            e.preventDefault();
        });
    }

    updateStatus(msg) {
        document.getElementById('status-message').textContent = msg;
    }

    updateBackendStatus(ok) {
        var el = document.getElementById('backend-status');
        el.textContent = ok ? 'Engine: Connected' : 'Engine: Disconnected';
        el.className = ok ? 'connected' : 'disconnected';
    }

    fmtTime(ms) {
        var s = Math.floor(ms / 1000);
        var secs = s % 60;
        return Math.floor(s / 60) + ':' + (secs < 10 ? '0' : '') + secs;
    }
    engineRunning = false;
    currentState = null;
}

// Boot
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() { new PyKaraokeApp().init(); });
} else {
    new PyKaraokeApp().init();
}
