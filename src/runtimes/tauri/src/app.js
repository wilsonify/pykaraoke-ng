// PyKaraoke NG – Tauri Frontend
// Talks to Rust commands via Tauri invoke().

// Keep a defensive fallback for environments where Tauri globals are absent.
let invoke = async function(command, payload) {
    return { command: command, payload: payload || {} };
};
let listen = async function() {
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
        listen = globalThis.__TAURI__.event.listen;
    }
    if (globalThis.__TAURI__?.dialog?.open) {
        dialogOpen = globalThis.__TAURI__.dialog.open;
    }
} catch (err) {
    // Browser mode: keep fallback functions.
    console.warn('Tauri API not available, using fallback mode:', err);
    dialogOpen = async function() { return null; };
}

class PyKaraokeApp {
    constructor() {
        this.searchResults = [];
        this.lastBackendCheckAt = 0;
        this.backendStartRetries = 0;
        this.maxBackendRetries = 3;
    }

    async init() {
        this.setupEventListeners();
        await this.ensureBackendStarted();
        this.startStatePolling();
    }

    // ── Backend communication ────────────────────────────────────────────

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

    async sendCommand(action, params) {
        if (!globalThis.__TAURI__?.tauri?.invoke) {
            throw new Error('Tauri bridge unavailable');
        }

        return invoke('send_command', {
            action: action,
            params: params || {},
        });
    }

    async ensureBackendStarted() {
        try {
            this.updateStatus('Starting backend...');
            await invoke('start_backend');

            // Validate round-trip so we know command pipe is alive.
            const r = await this.sendCommand('get_state');
            if (r?.status !== 'ok') {
                const msg = (r?.message) ? r.message : 'Unknown backend error';
                throw new Error(msg);
            }

            this.backendRunning = true;
            this.backendStartRetries = 0;
            this.updateBackendStatus(true);
            this.updateStatus('Backend connected');
        } catch (e) {
            console.error('Backend startup failed:', e);
            this.backendStartRetries++;
            if (this.backendStartRetries >= this.maxBackendRetries) {
                this.updateStatus(
                    'Backend failed after ' + this.maxBackendRetries + ' attempts. '
                    + 'Please check your installation and restart the application.'
                );
                this.backendRunning = false;
                this.updateBackendStatus(false);
                return;
            }
            this.updateStatus('Backend startup failed (' + this.backendStartRetries
                + '/' + this.maxBackendRetries + '): ' + this.errorMessage(e));
            this.backendRunning = false;
            this.updateBackendStatus(false);
        }
    }

    startStatePolling() {
        setInterval(async () => {
            if (!this.backendRunning) {
                if (this.backendStartRetries >= this.maxBackendRetries) {
                    return; // stop retrying after max attempts
                }
                const now = Date.now();
                if (now - this.lastBackendCheckAt > 3000) {
                    this.lastBackendCheckAt = now;
                    await this.ensureBackendStarted();
                }
                return;
            }

            try {
                let r = await this.sendCommand('get_state');
                if (r.status === 'ok' && r.data) {
                    this.updateUIFromState(r.data);
                } else if (r.status !== 'ok') {
                    this.backendRunning = false;
                    this.updateBackendStatus(false);
                }
            } catch (e) {
                console.error('State polling error:', e);
                this.backendRunning = false;
                this.updateBackendStatus(false);
            }
        }, 1000);
    }

    // ── Event listeners ──────────────────────────────────────────────────

    setupEventListeners() {
        function $(id) { return document.getElementById(id); }

        $('play-btn').addEventListener('click', async () => {
            try {
                let r = await this.sendCommand('play');
                if (r.status !== 'ok') this.updateStatus(r.message || 'Play failed');
            } catch (e) { this.updateStatus('Error: ' + this.errorMessage(e)); }
        });
        $('pause-btn').addEventListener('click', async () => {
            try {
                let r = await this.sendCommand('pause');
                if (r.status !== 'ok') this.updateStatus(r.message || 'Pause failed');
            } catch (e) { this.updateStatus('Error: ' + this.errorMessage(e)); }
        });
        $('stop-btn').addEventListener('click', async () => {
            try { await this.sendCommand('stop'); } catch (e) { this.updateStatus('Error: ' + this.errorMessage(e)); }
        });
        $('next-btn').addEventListener('click', async () => {
            try { await this.sendCommand('next'); } catch (e) { this.updateStatus('Error: ' + this.errorMessage(e)); }
        });
        $('prev-btn').addEventListener('click', async () => {
            try { await this.sendCommand('previous'); } catch (e) { this.updateStatus('Error: ' + this.errorMessage(e)); }
        });

        // Fast-forward / Rewind: single-click step + hold for continuous seeking
        globalThis._setupSeekButton('ff-btn', 'fast_forward', 10);
        globalThis._setupSeekButton('rewind-btn', 'rewind', 10);

        $('volume-slider').addEventListener('input', function(e) {
            let v = Number.parseInt(e.target.value);
            globalThis.sendCommand('set_volume', { volume: v / 100 });
            $('volume-value').textContent = v + '%';
        });

        $('progress-slider').addEventListener('input', function(e) {
            let s = globalThis.currentState;
            if (s && s.duration_ms > 0) {
                let pct = Number.parseInt(e.target.value) / 10;
                let pos_ms = Math.round((pct / 100) * s.duration_ms);
                document.getElementById('time-current').textContent = globalThis.fmtTime(pos_ms);
            }
        });

        $('progress-slider').addEventListener('change', async function(e) {
            let s = globalThis.currentState;
            if (s && s.duration_ms > 0) {
                let pct = Number.parseInt(e.target.value) / 10;
                let pos_ms = Math.round((pct / 100) * s.duration_ms);
                try {
                    let r = await globalThis.sendCommand('seek', { position_ms: pos_ms });
                    if (r && r.status !== 'ok') globalThis.updateStatus(r.message || 'Seek failed');
                } catch (ex) {
                    globalThis.updateStatus('Seek error: ' + globalThis.errorMessage(ex));
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

        $('clear-playlist-btn').addEventListener('click', function() { self.sendCommand('clear_playlist'); });

        // ── Queue drop-target: accept songs dragged from search results ──
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

    // ── Command handlers ─────────────────────────────────────────────────

    async handleSearch() {
        var query = document.getElementById('search-input').value;
        if (!query) return;
        this.updateStatus('Searching…');
        try {
            var r = await this.sendCommand('search_songs', { query: query });
            if (r.status === 'ok' && r.data) {
                this.searchResults = r.data.results || [];
                this.renderSearchResults();
                this.updateStatus('Found ' + this.searchResults.length + ' results');
            }
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
            await this.sendCommand('add_folder', { folder: folder });
            this.updateStatus('Folder added: ' + folder);
        } catch (e) {
            this.updateStatus('Error: ' + this.errorMessage(e));
        }
    }

    async handleScanLibrary() {
        this.updateStatus('Scanning library…');
        try {
            var r = await this.sendCommand('scan_library');
            if (r.status === 'ok') {
                var count = (r.data && r.data.song_count) || 0;
                this.updateStatus('Scan complete – ' + count + ' song' + (count !== 1 ? 's' : '') + ' found');
            } else {
                this.updateStatus('Scan finished: ' + (r.message || 'no songs found'));
            }
        }
        catch (e) { this.updateStatus('Scan failed: ' + this.errorMessage(e)); }
    }

    async handleShowSettings() {
        var modal = document.getElementById('settings-modal');
        if (!modal) return;
        try {
            var r = await this.sendCommand('get_settings');
            if (r.status === 'ok' && r.data) {
                var fs = document.getElementById('setting-fullscreen');
                var zm = document.getElementById('setting-zoom');
                if (fs) fs.checked = r.data.fullscreen || false;
                if (zm) zm.value = r.data.zoom_mode || 'soft';
            }
        } catch (_) {}
        modal.style.display = 'flex';
    }

    handleCloseSettings() {
        var m = document.getElementById('settings-modal');
        if (m) m.style.display = 'none';
    }

    async handleSaveSettings() {
        var params = {
            fullscreen: document.getElementById('setting-fullscreen') ? document.getElementById('setting-fullscreen').checked : false,
            zoom_mode: document.getElementById('setting-zoom') ? document.getElementById('setting-zoom').value : 'soft',
        };
        try {
            await this.sendCommand('update_settings', params);
            this.updateStatus('Settings saved');
            this.handleCloseSettings();
        } catch (e) { this.updateStatus('Error: ' + this.errorMessage(e)); }
    }

    // ── UI updates ───────────────────────────────────────────────────────

    updateUIFromState(s) {
        this.currentState = s;

        var title = 'No song loaded';
        var artist = '';
        if (s.current_song) {
            title = s.current_song.title || s.current_song.filename || 'Unknown';
            artist = s.current_song.artist || '';
        }
        document.getElementById('current-song-title').textContent = title;
        document.getElementById('current-song-artist').textContent = artist;

        var playing = s.playback_state === 'playing';
        document.getElementById('play-btn').style.display = playing ? 'none' : 'inline-block';
        document.getElementById('pause-btn').style.display = playing ? 'inline-block' : 'none';

        if (s.duration_ms > 0 && typeof s.position_ms === 'number') {
            var pct = Math.min(1000, Math.max(0, (s.position_ms / s.duration_ms) * 1000));
            document.getElementById('progress-slider').value = Math.round(pct);
            document.getElementById('time-current').textContent = this.fmtTime(s.position_ms);
            document.getElementById('time-total').textContent = this.fmtTime(s.duration_ms);
        }

        if (s.playlist) this.renderPlaylist(s.playlist);
    }

    renderPlaylist(list) {
        var el = document.getElementById('playlist');
        var self = this;
        if (!list || !list.length) {
            el.innerHTML = '<div class="no-results">Playlist is empty</div>';
            return;
        }
        var html = '';
        for (var i = 0; i < list.length; i++) {
            var s = list[i];
            var cls = (self.currentState && self.currentState.playlist_index === i) ? ' active' : '';
            html += '<div class="song-item' + cls + '" data-index="' + i + '">'
                  + '<div class="song-item-info">'
                  + '<div class="song-item-title">' + (s.title || s.filename) + '</div>'
                  + '<div class="song-item-artist">' + (s.artist || '') + '</div>'
                  + '</div>'
                  + '<button class="song-item-remove" data-i="' + i + '" title="Remove">✕</button>'
                  + '</div>';
        }
        el.innerHTML = html;

        el.querySelectorAll('.song-item').forEach(function(item) {
            item.addEventListener('click', function(e) {
                if (e.target.classList.contains('song-item-remove')) return;
                self.sendCommand('play', { playlist_index: parseInt(item.dataset.index) });
            });
        });
        el.querySelectorAll('.song-item-remove').forEach(function(btn) {
            btn.addEventListener('click', function(e) {
                e.stopPropagation();
                self.sendCommand('remove_from_playlist', { index: parseInt(btn.dataset.i) });
            });
        });
    }

    renderSearchResults() {
        var el = document.getElementById('results-list');
        var self = this;
        if (!this.searchResults.length) {
            el.innerHTML = '<div class="no-results">No results found</div>';
            return;
        }
        var html = '';
        for (var i = 0; i < this.searchResults.length; i++) {
            var s = this.searchResults[i];
            html += '<div class="song-item" data-index="' + i + '" tabindex="0" role="option" draggable="true">'
                  + '<div class="song-item-info">'
                  + '<div class="song-item-title">' + (s.title || s.filename) + '</div>'
                  + '<div class="song-item-artist">' + (s.artist || '') + '</div>'
                  + '</div></div>';
        }
        el.innerHTML = html;

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
            // Drag-start: attach song data for drop into queue
            item.addEventListener('dragstart', function(e) {
                var song = self.searchResults[parseInt(item.dataset.index)];
                console.debug('[PyKaraoke] drag-start:', song && song.filepath);
                e.dataTransfer.setData('application/x-pykaraoke-song', JSON.stringify(song));
                e.dataTransfer.effectAllowed = 'copy';
            });
        });
    }

    /**
     * Central enqueue function used by click, double-click, drag-drop,
     * and keyboard handlers.  All paths converge here so logging and
     * error handling are consistent.
     */
    async enqueueSong(song) {
        if (!song || !song.filepath) {
            console.error('[PyKaraoke] enqueueSong: missing song or filepath');
            this.updateStatus('Error: cannot enqueue – no file path');
            return;
        }
        console.debug('[PyKaraoke] enqueueSong:', song.filepath);
        try {
            var r = await this.sendCommand('add_to_playlist', { filepath: song.filepath });
            if (r && r.status === 'ok') {
                this.updateStatus('Added "' + (song.title || song.filename) + '" to queue');
            } else {
                var msg = (r && r.message) || 'Unknown error';
                console.error('[PyKaraoke] enqueue error:', msg);
                this.updateStatus('Failed to enqueue: ' + msg);
            }
        } catch (e) {
            console.error('[PyKaraoke] enqueue exception:', e);
            this.updateStatus('Failed to enqueue: ' + this.errorMessage(e));
        }
    }

    _setupSeekButton(btnId, action, stepSeconds) {
        var btn = document.getElementById(btnId);
        if (!btn) return;
        var self = this;
        var timer = null;

        function stopSeek() {
            if (timer) { clearInterval(timer); timer = null; }
        }

        function doSeek() {
            self.sendCommand(action, { amount_seconds: stepSeconds }).catch(function(e) {
                self.updateStatus('Error: ' + self.errorMessage(e));
                stopSeek();
            });
        }

        btn.addEventListener('mousedown', function() {
            doSeek();
            if (timer) clearInterval(timer);
            timer = setInterval(doSeek, 500);
        });

        btn.addEventListener('mouseup', stopSeek);
        btn.addEventListener('mouseleave', stopSeek);
        btn.addEventListener('click', function(e) {
            // Click is handled by mousedown; prevent double-fire
            e.preventDefault();
        });
    }

    updateStatus(msg) {
        document.getElementById('status-message').textContent = msg;
    }

    updateBackendStatus(ok) {
        var el = document.getElementById('backend-status');
        el.textContent = ok ? 'Backend: Connected' : 'Backend: Disconnected';
        el.className = ok ? 'connected' : 'disconnected';
    }

    fmtTime(ms) {
        var s = Math.floor(ms / 1000);
        var secs = s % 60;
        return Math.floor(s / 60) + ':' + (secs < 10 ? '0' : '') + secs;
    }
    backendRunning = false;
    currentState = null;
}

// Boot
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() { new PyKaraokeApp(); });
} else {
    new PyKaraokeApp();
}
