// PyKaraoke NG - Frontend Application
// Handles UI interactions and communicates with Tauri backend

let invoke, listen;

try {
    invoke = window.__TAURI__.tauri.invoke;
    listen = window.__TAURI__.event.listen;
} catch (e) {
    console.warn('Tauri API not available:', e);
    // Provide no-op stubs so the UI still renders
    invoke = async () => { throw new Error('Tauri API not available'); };
    listen = async () => {};
}

class PyKaraokeApp {
    constructor() {
        this.backendRunning = false;
        this.currentState = null;
        this.searchResults = [];
        this.playlist = [];
        
        this.init();
    }
    
    async init() {
        // Initialize UI event listeners
        this.setupEventListeners();
        
        // Start the Python backend
        await this.startBackend();
        
        // Listen for backend events
        this.listenForBackendEvents();
        
        // Poll for state updates
        this.startStatePolling();
    }
    
    setupEventListeners() {
        // Player controls
        document.getElementById('play-btn').addEventListener('click', () => this.handlePlay());
        document.getElementById('pause-btn').addEventListener('click', () => this.handlePause());
        document.getElementById('stop-btn').addEventListener('click', () => this.handleStop());
        document.getElementById('next-btn').addEventListener('click', () => this.handleNext());
        document.getElementById('prev-btn').addEventListener('click', () => this.handlePrevious());
        
        // Volume control
        document.getElementById('volume-slider').addEventListener('input', (e) => {
            const volume = parseInt(e.target.value) / 100;
            this.handleVolumeChange(volume);
            document.getElementById('volume-value').textContent = `${e.target.value}%`;
        });
        
        // Search
        document.getElementById('search-btn').addEventListener('click', () => this.handleSearch());
        document.getElementById('search-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.handleSearch();
        });
        
        // Library management
        document.getElementById('add-folder-btn').addEventListener('click', () => this.handleAddFolder());
        document.getElementById('scan-library-btn').addEventListener('click', () => this.handleScanLibrary());
        
        // Playlist
        document.getElementById('clear-playlist-btn').addEventListener('click', () => this.handleClearPlaylist());
    }
    
    async startBackend() {
        try {
            this.updateStatus('Starting Python backend...');
            const result = await invoke('start_backend');
            console.log('Backend started:', result);
            this.backendRunning = true;
            this.updateBackendStatus(true);
            this.updateStatus('Backend connected');
        } catch (error) {
            console.error('Failed to start backend:', error);
            this.updateStatus(`Error: ${error}`);
            this.updateBackendStatus(false);
        }
    }
    
    listenForBackendEvents() {
        listen('backend-event', (event) => {
            console.log('Backend event:', event.payload);
            this.handleBackendEvent(event.payload);
        });
    }
    
    handleBackendEvent(event) {
        const eventType = event.type;
        const data = event.data;
        
        switch (eventType) {
            case 'state_changed':
                this.updateUIFromState(data);
                break;
            case 'song_finished':
                this.onSongFinished();
                break;
            case 'playback_error':
                this.showError(data.error);
                break;
            case 'playlist_updated':
                this.updatePlaylistUI(data.playlist);
                break;
            case 'library_scan_complete':
                this.updateStatus('Library scan complete');
                break;
            default:
                console.log('Unhandled event type:', eventType);
        }
    }
    
    async sendCommand(action, params = {}) {
        try {
            const response = await invoke('send_command', { action, params });
            console.log('Command response:', response);
            return response;
        } catch (error) {
            console.error('Command error:', error);
            this.showError(error);
            throw error;
        }
    }
    
    async startStatePolling() {
        // Poll for state every 500ms
        setInterval(async () => {
            if (this.backendRunning) {
                try {
                    const response = await this.sendCommand('get_state');
                    if (response.status === 'ok' && response.data) {
                        this.updateUIFromState(response.data);
                    }
                } catch (error) {
                    // Silently fail - backend might not be ready
                }
            }
        }, 500);
    }
    
    updateUIFromState(state) {
        this.currentState = state;
        
        // Update now playing info
        if (state.current_song) {
            document.getElementById('current-song-title').textContent = 
                state.current_song.title || state.current_song.filename || 'Unknown';
            document.getElementById('current-song-artist').textContent = 
                state.current_song.artist || '';
        } else {
            document.getElementById('current-song-title').textContent = 'No song loaded';
            document.getElementById('current-song-artist').textContent = '';
        }
        
        // Update playback controls based on state
        const isPlaying = state.playback_state === 'playing';
        const isPaused = state.playback_state === 'paused';
        
        document.getElementById('play-btn').style.display = isPlaying ? 'none' : 'inline-block';
        document.getElementById('pause-btn').style.display = isPlaying ? 'inline-block' : 'none';
        
        // Update progress bar
        if (state.duration_ms > 0) {
            const progress = (state.position_ms / state.duration_ms) * 100;
            document.getElementById('progress-fill').style.width = `${progress}%`;
            document.getElementById('time-current').textContent = this.formatTime(state.position_ms);
            document.getElementById('time-total').textContent = this.formatTime(state.duration_ms);
        }
        
        // Update playlist
        if (state.playlist) {
            this.updatePlaylistUI(state.playlist);
        }
    }
    
    updatePlaylistUI(playlist) {
        const playlistEl = document.getElementById('playlist');
        
        if (!playlist || playlist.length === 0) {
            playlistEl.innerHTML = '<div class="no-results">Playlist is empty</div>';
            return;
        }
        
        playlistEl.innerHTML = playlist.map((song, index) => `
            <div class="song-item ${this.currentState?.playlist_index === index ? 'active' : ''}" 
                 data-index="${index}">
                <div class="song-item-title">${song.title || song.filename}</div>
                <div class="song-item-artist">${song.artist || ''}</div>
            </div>
        `).join('');
        
        // Add click handlers
        playlistEl.querySelectorAll('.song-item').forEach(item => {
            item.addEventListener('click', () => {
                const index = parseInt(item.dataset.index);
                this.handlePlayFromPlaylist(index);
            });
            
            item.addEventListener('contextmenu', (e) => {
                e.preventDefault();
                const index = parseInt(item.dataset.index);
                this.handleRemoveFromPlaylist(index);
            });
        });
    }
    
    updateSearchResults(results) {
        const resultsEl = document.getElementById('results-list');
        
        if (!results || results.length === 0) {
            resultsEl.innerHTML = '<div class="no-results">No results found</div>';
            return;
        }
        
        resultsEl.innerHTML = results.map((song, index) => `
            <div class="song-item" data-index="${index}">
                <div class="song-item-title">${song.title || song.filename}</div>
                <div class="song-item-artist">${song.artist || ''}</div>
            </div>
        `).join('');
        
        // Add click handlers
        resultsEl.querySelectorAll('.song-item').forEach(item => {
            item.addEventListener('click', () => {
                const index = parseInt(item.dataset.index);
                this.handleAddToPlaylist(results[index]);
            });
        });
    }
    
    // Command handlers
    
    async handlePlay() {
        await this.sendCommand('play');
    }
    
    async handlePause() {
        await this.sendCommand('pause');
    }
    
    async handleStop() {
        await this.sendCommand('stop');
    }
    
    async handleNext() {
        await this.sendCommand('next');
    }
    
    async handlePrevious() {
        await this.sendCommand('previous');
    }
    
    async handleVolumeChange(volume) {
        await this.sendCommand('set_volume', { volume });
    }
    
    async handleSearch() {
        const query = document.getElementById('search-input').value;
        if (!query) return;
        
        this.updateStatus('Searching...');
        try {
            const response = await this.sendCommand('search_songs', { query });
            if (response.status === 'ok' && response.data) {
                this.searchResults = response.data.results || [];
                this.updateSearchResults(this.searchResults);
                this.updateStatus(`Found ${this.searchResults.length} results`);
            }
        } catch (error) {
            this.updateStatus('Search failed');
        }
    }
    
    async handleAddFolder() {
        // In a real implementation, this would open a folder picker
        // For now, we'll just show a message
        alert('Folder picker not implemented yet. This would open a native folder selection dialog.');
    }
    
    async handleScanLibrary() {
        this.updateStatus('Scanning library...');
        await this.sendCommand('scan_library');
    }
    
    async handleAddToPlaylist(song) {
        await this.sendCommand('add_to_playlist', { filepath: song.filepath });
        this.updateStatus(`Added "${song.title || song.filename}" to playlist`);
    }
    
    async handleRemoveFromPlaylist(index) {
        await this.sendCommand('remove_from_playlist', { index });
    }
    
    async handleClearPlaylist() {
        if (confirm('Clear entire playlist?')) {
            await this.sendCommand('clear_playlist');
        }
    }
    
    async handlePlayFromPlaylist(index) {
        await this.sendCommand('play', { playlist_index: index });
    }
    
    // UI helpers
    
    onSongFinished() {
        this.updateStatus('Song finished');
    }
    
    showError(message) {
        this.updateStatus(`Error: ${message}`);
        console.error('Error:', message);
    }
    
    updateStatus(message) {
        document.getElementById('status-message').textContent = message;
    }
    
    updateBackendStatus(connected) {
        const statusEl = document.getElementById('backend-status');
        statusEl.textContent = connected ? 'Backend: Connected' : 'Backend: Disconnected';
        statusEl.className = connected ? 'connected' : 'disconnected';
    }
    
    formatTime(ms) {
        const seconds = Math.floor(ms / 1000);
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }
}

// Initialize app when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => new PyKaraokeApp());
} else {
    new PyKaraokeApp();
}
