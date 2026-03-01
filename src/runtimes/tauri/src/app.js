// PyKaraoke NG – Browser Frontend
// Talks directly to the backend REST API via fetch().
// No Tauri dependency — works in any browser.

class PyKaraokeApp {
    constructor() {
        this.backendRunning = false;
        this.currentState = null;
        this.searchResults = [];
        this.init();
    }

    async init() {
        this.setupEventListeners();
        await this.checkBackend();
        this.startStatePolling();
    }

    // ── Backend communication ────────────────────────────────────────────

    async api(method, path, body) {
        const opts = { method, headers: {} };
        if (body !== undefined) {
            opts.headers['Content-Type'] = 'application/json';
            opts.body = JSON.stringify(body);
        }
        const res = await fetch(path, opts);
        if (!res.ok) throw new Error(method + ' ' + path + ' -> ' + res.status);
        return res.json();
    }

    async sendCommand(action, params) {
        return this.api('POST', '/api/command', { action, params: params || {} });
    }

    async checkBackend() {
        try {
            this.updateStatus('Connecting to backend…');
            await this.api('GET', '/health');
            this.backendRunning = true;
            this.updateBackendStatus(true);
            this.updateStatus('Backend connected');
        } catch (e) {
            console.error('Backend unreachable:', e);
            this.updateStatus('Backend unreachable');
            this.updateBackendStatus(false);
        }
    }

    startStatePolling() {
        setInterval(async () => {
            if (!this.backendRunning) return;
            try {
                var r = await this.sendCommand('get_state');
                if (r.status === 'ok' && r.data) this.updateUIFromState(r.data);
            } catch (_) { /* backend may be momentarily busy */ }
        }, 500);
    }

    // ── Event listeners ──────────────────────────────────────────────────

    setupEventListeners() {
        var self = this;
        function $(id) { return document.getElementById(id); }

        $('play-btn').addEventListener('click', function() { self.sendCommand('play'); });
        $('pause-btn').addEventListener('click', function() { self.sendCommand('pause'); });
        $('stop-btn').addEventListener('click', function() { self.sendCommand('stop'); });
        $('next-btn').addEventListener('click', function() { self.sendCommand('next'); });
        $('prev-btn').addEventListener('click', function() { self.sendCommand('previous'); });

        $('volume-slider').addEventListener('input', function(e) {
            var v = parseInt(e.target.value);
            self.sendCommand('set_volume', { volume: v / 100 });
            $('volume-value').textContent = v + '%';
        });

        $('search-btn').addEventListener('click', function() { self.handleSearch(); });
        $('search-input').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') self.handleSearch();
        });
        $('search-input').addEventListener('input', function() {
            clearTimeout(self._debounce);
            self._debounce = setTimeout(function() { self.handleSearch(); }, 200);
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
        $('settings-btn').addEventListener('click', function() { self.handleShowSettings(); });
        if ($('settings-close-btn'))  $('settings-close-btn').addEventListener('click', closeSettings);
        if ($('settings-cancel-btn')) $('settings-cancel-btn').addEventListener('click', closeSettings);
        if ($('settings-save-btn'))   $('settings-save-btn').addEventListener('click', function() { self.handleSaveSettings(); });

        $('clear-playlist-btn').addEventListener('click', function() { self.sendCommand('clear_playlist'); });
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
        var folder = input ? input.value.trim() : '';
        if (!folder) {
            this.updateStatus('Enter a folder path first');
            return;
        }
        this.updateStatus('Adding folder: ' + folder);
        try {
            await this.sendCommand('add_folder', { folder: folder });
            this.updateStatus('Folder added: ' + folder);
        } catch (e) {
            this.updateStatus('Error: ' + e.message);
        }
    }

    async handleScanLibrary() {
        this.updateStatus('Scanning library…');
        try { await this.sendCommand('scan_library'); }
        catch (e) { this.updateStatus('Scan failed: ' + e.message); }
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
        } catch (e) { this.updateStatus('Error: ' + e.message); }
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

        if (s.duration_ms > 0) {
            var pct = (s.position_ms / s.duration_ms) * 100;
            document.getElementById('progress-fill').style.width = pct + '%';
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
            html += '<div class="song-item" data-index="' + i + '" tabindex="0" role="option">'
                  + '<div class="song-item-info">'
                  + '<div class="song-item-title">' + (s.title || s.filename) + '</div>'
                  + '<div class="song-item-artist">' + (s.artist || '') + '</div>'
                  + '</div></div>';
        }
        el.innerHTML = html;

        el.querySelectorAll('.song-item').forEach(function(item) {
            var handler = function() {
                var song = self.searchResults[parseInt(item.dataset.index)];
                self.sendCommand('add_to_playlist', { filepath: song.filepath });
                self.updateStatus('Added "' + (song.title || song.filename) + '" to playlist');
            };
            item.addEventListener('click', handler);
            item.addEventListener('keydown', function(e) { if (e.key === 'Enter') handler(); });
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
}

// Boot
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() { new PyKaraokeApp(); });
} else {
    new PyKaraokeApp();
}
