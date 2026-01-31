/**
 * PyKaraoke-NG Renderer Process
 * 
 * This script runs in the browser/renderer process and handles
 * the UI logic for the karaoke application.
 */

// =============================================================================
// Application State
// =============================================================================

const state = {
    isPlaying: false,
    currentSong: null,
    queue: [],
    songs: [],
    settings: {
        fullscreen: false,
        volume: 75,
        theme: 'dark'
    }
};

// =============================================================================
// DOM Elements
// =============================================================================

const elements = {
    // Header
    searchInput: document.getElementById('search-input'),
    searchBtn: document.getElementById('search-btn'),
    settingsBtn: document.getElementById('settings-btn'),
    fullscreenBtn: document.getElementById('fullscreen-btn'),
    
    // Sidebar
    songsList: document.getElementById('songs-list'),
    addFolderBtn: document.getElementById('add-folder-btn'),
    openFolderBtn: document.getElementById('open-folder-btn'),
    
    // Display
    karaokeDisplay: document.getElementById('karaoke-display'),
    lyricsDisplay: document.getElementById('lyrics-display'),
    openFileBtn: document.getElementById('open-file-btn'),
    
    // Queue
    queuePanel: document.getElementById('queue-panel'),
    queueList: document.getElementById('queue-list'),
    queueBtn: document.getElementById('queue-btn'),
    clearQueueBtn: document.getElementById('clear-queue-btn'),
    
    // Playback controls
    playBtn: document.getElementById('play-btn'),
    stopBtn: document.getElementById('stop-btn'),
    prevBtn: document.getElementById('prev-btn'),
    nextBtn: document.getElementById('next-btn'),
    progressSlider: document.getElementById('progress-slider'),
    volumeSlider: document.getElementById('volume-slider'),
    muteBtn: document.getElementById('mute-btn'),
    timeCurrent: document.getElementById('time-current'),
    timeTotal: document.getElementById('time-total'),
    nowPlayingTitle: document.getElementById('now-playing-title'),
    nowPlayingArtist: document.getElementById('now-playing-artist'),
    
    // Settings modal
    settingsModal: document.getElementById('settings-modal'),
    closeSettingsBtn: document.getElementById('close-settings-btn'),
    saveSettingsBtn: document.getElementById('save-settings-btn'),
    cancelSettingsBtn: document.getElementById('cancel-settings-btn'),
    themeSelect: document.getElementById('theme-select'),
    fullscreenOnPlay: document.getElementById('fullscreen-on-play'),
    defaultVolume: document.getElementById('default-volume'),
    songsFolderPath: document.getElementById('songs-folder-path'),
    browseFolderBtn: document.getElementById('browse-folder-btn')
};

// =============================================================================
// Initialization
// =============================================================================

async function init() {
    console.log('Initializing PyKaraoke-NG...');
    
    // Load settings
    await loadSettings();
    
    // Apply theme
    applyTheme(state.settings.theme);
    
    // Set initial volume
    elements.volumeSlider.value = state.settings.volume;
    
    // Load songs folder
    const songsFolder = await window.fileAPI.getSongsFolder();
    if (songsFolder) {
        elements.songsFolderPath.value = songsFolder;
        // TODO: Load songs from folder
    }
    
    // Set up event listeners
    setupEventListeners();
    
    // Set up IPC listeners
    setupIPCListeners();
    
    console.log('PyKaraoke-NG initialized');
}

// =============================================================================
// Settings Management
// =============================================================================

async function loadSettings() {
    try {
        const settings = await window.settingsAPI.get();
        if (settings) {
            state.settings = { ...state.settings, ...settings };
        }
    } catch (error) {
        console.error('Failed to load settings:', error);
    }
}

async function saveSettings() {
    try {
        const settings = {
            fullscreen: elements.fullscreenOnPlay.checked,
            volume: parseInt(elements.defaultVolume.value, 10),
            theme: elements.themeSelect.value
        };
        
        await window.settingsAPI.set(settings);
        state.settings = settings;
        
        applyTheme(settings.theme);
        closeModal(elements.settingsModal);
    } catch (error) {
        console.error('Failed to save settings:', error);
    }
}

function applyTheme(theme) {
    if (theme === 'auto') {
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        theme = prefersDark ? 'dark' : 'light';
    }
    
    document.body.classList.remove('theme-light', 'theme-dark');
    document.body.classList.add(`theme-${theme}`);
}

// =============================================================================
// Event Listeners
// =============================================================================

function setupEventListeners() {
    // Header buttons
    elements.settingsBtn.addEventListener('click', () => openModal(elements.settingsModal));
    elements.fullscreenBtn.addEventListener('click', toggleFullscreen);
    elements.searchBtn.addEventListener('click', handleSearch);
    elements.searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSearch();
    });
    
    // Sidebar buttons
    elements.addFolderBtn?.addEventListener('click', openFolderDialog);
    elements.openFolderBtn?.addEventListener('click', openFolderDialog);
    elements.openFileBtn?.addEventListener('click', openSongDialog);
    
    // Playback controls
    elements.playBtn.addEventListener('click', togglePlayback);
    elements.stopBtn.addEventListener('click', stopPlayback);
    elements.prevBtn.addEventListener('click', playPrevious);
    elements.nextBtn.addEventListener('click', playNext);
    elements.volumeSlider.addEventListener('input', handleVolumeChange);
    elements.muteBtn.addEventListener('click', toggleMute);
    elements.progressSlider.addEventListener('input', handleSeek);
    
    // Queue
    elements.queueBtn.addEventListener('click', toggleQueuePanel);
    elements.clearQueueBtn?.addEventListener('click', clearQueue);
    
    // Settings modal
    elements.closeSettingsBtn.addEventListener('click', () => closeModal(elements.settingsModal));
    elements.cancelSettingsBtn.addEventListener('click', () => closeModal(elements.settingsModal));
    elements.saveSettingsBtn.addEventListener('click', saveSettings);
    elements.browseFolderBtn.addEventListener('click', openFolderDialog);
    
    // Modal backdrop click
    elements.settingsModal.addEventListener('click', (e) => {
        if (e.target === elements.settingsModal) {
            closeModal(elements.settingsModal);
        }
    });
    
    // Keyboard shortcuts
    document.addEventListener('keydown', handleKeyboard);
    
    // Drag and drop
    setupDragAndDrop();
}

function setupIPCListeners() {
    // Listen for song open events
    window.electronAPI.receive('song:open', (filePath) => {
        console.log('Opening song:', filePath);
        loadSong(filePath);
    });
    
    // Listen for folder selection
    window.electronAPI.receive('folder:selected', (folderPath) => {
        console.log('Folder selected:', folderPath);
        elements.songsFolderPath.value = folderPath;
        // TODO: Scan folder for songs
    });
    
    // Listen for playback control events from menu
    window.electronAPI.receive('playback:toggle', togglePlayback);
    window.electronAPI.receive('playback:stop', stopPlayback);
    window.electronAPI.receive('playback:previous', playPrevious);
    window.electronAPI.receive('playback:next', playNext);
}

function setupDragAndDrop() {
    const dropZone = elements.songsList;
    
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.add('drag-over');
    });
    
    dropZone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.remove('drag-over');
    });
    
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.remove('drag-over');
        
        const files = Array.from(e.dataTransfer.files);
        files.forEach(file => {
            if (isValidSongFile(file.name)) {
                addSong(file.path, file.name);
            }
        });
    });
}

// =============================================================================
// File Operations
// =============================================================================

async function openSongDialog() {
    await window.fileAPI.openSongDialog();
}

async function openFolderDialog() {
    await window.fileAPI.openFolderDialog();
}

function isValidSongFile(filename) {
    const validExtensions = ['.cdg', '.kar', '.mid', '.midi', '.mpg', '.mpeg', '.avi'];
    const ext = filename.toLowerCase().substring(filename.lastIndexOf('.'));
    return validExtensions.includes(ext);
}

function addSong(path, name) {
    const song = {
        id: Date.now(),
        path,
        name: name || path.split('/').pop(),
        title: extractTitle(name || path),
        artist: extractArtist(name || path)
    };
    
    state.songs.push(song);
    renderSongsList();
}

function extractTitle(filename) {
    // Try to extract title from filename (format: "Artist - Title.ext")
    const name = filename.replace(/\.[^/.]+$/, ''); // Remove extension
    const parts = name.split(' - ');
    return parts.length > 1 ? parts[1].trim() : name;
}

function extractArtist(filename) {
    const name = filename.replace(/\.[^/.]+$/, '');
    const parts = name.split(' - ');
    return parts.length > 1 ? parts[0].trim() : '';
}

// =============================================================================
// Playback Control
// =============================================================================

function loadSong(filePath) {
    const filename = filePath.split('/').pop();
    
    state.currentSong = {
        path: filePath,
        name: filename,
        title: extractTitle(filename),
        artist: extractArtist(filename)
    };
    
    updateNowPlaying();
    // TODO: Actually load and play the song via Python backend
}

function togglePlayback() {
    state.isPlaying = !state.isPlaying;
    
    if (state.isPlaying) {
        elements.playBtn.textContent = '⏸';
        // TODO: Start playback
    } else {
        elements.playBtn.textContent = '▶';
        // TODO: Pause playback
    }
}

function stopPlayback() {
    state.isPlaying = false;
    elements.playBtn.textContent = '▶';
    elements.progressSlider.value = 0;
    elements.timeCurrent.textContent = '0:00';
    // TODO: Stop playback
}

function playPrevious() {
    const currentIndex = state.songs.findIndex(s => s.path === state.currentSong?.path);
    if (currentIndex > 0) {
        loadSong(state.songs[currentIndex - 1].path);
    }
}

function playNext() {
    const currentIndex = state.songs.findIndex(s => s.path === state.currentSong?.path);
    if (currentIndex < state.songs.length - 1) {
        loadSong(state.songs[currentIndex + 1].path);
    } else if (state.queue.length > 0) {
        const nextSong = state.queue.shift();
        loadSong(nextSong.path);
        renderQueue();
    }
}

function handleVolumeChange() {
    const volume = elements.volumeSlider.value;
    updateVolumeIcon(volume);
    // TODO: Set actual volume
}

function toggleMute() {
    const isMuted = elements.volumeSlider.value === '0';
    if (isMuted) {
        elements.volumeSlider.value = state.settings.volume;
    } else {
        elements.volumeSlider.value = 0;
    }
    updateVolumeIcon(elements.volumeSlider.value);
}

function updateVolumeIcon(volume) {
    if (volume == 0) {
        elements.muteBtn.textContent = '🔇';
    } else if (volume < 50) {
        elements.muteBtn.textContent = '🔉';
    } else {
        elements.muteBtn.textContent = '🔊';
    }
}

function handleSeek() {
    const position = elements.progressSlider.value;
    // TODO: Seek to position
}

function updateNowPlaying() {
    if (state.currentSong) {
        elements.nowPlayingTitle.textContent = state.currentSong.title;
        elements.nowPlayingArtist.textContent = state.currentSong.artist;
    } else {
        elements.nowPlayingTitle.textContent = 'No song playing';
        elements.nowPlayingArtist.textContent = '';
    }
}

// =============================================================================
// Queue Management
// =============================================================================

function toggleQueuePanel() {
    elements.queuePanel.classList.toggle('hidden');
}

function addToQueue(song) {
    state.queue.push(song);
    renderQueue();
}

function clearQueue() {
    state.queue = [];
    renderQueue();
}

function renderQueue() {
    elements.queueList.innerHTML = '';
    
    state.queue.forEach((song, index) => {
        const item = document.createElement('li');
        item.className = 'queue-item';
        item.innerHTML = `
            <span class="queue-number">${index + 1}</span>
            <div class="song-info">
                <div class="song-title">${song.title}</div>
                <div class="song-artist">${song.artist}</div>
            </div>
            <button class="icon-btn remove-btn" data-index="${index}">✕</button>
        `;
        elements.queueList.appendChild(item);
    });
}

// =============================================================================
// Songs List
// =============================================================================

function renderSongsList() {
    if (state.songs.length === 0) {
        elements.songsList.innerHTML = `
            <div class="empty-state">
                <p>No songs loaded</p>
                <button id="open-folder-btn" class="btn btn-primary">Open Songs Folder</button>
                <p class="hint">or drag and drop files here</p>
            </div>
        `;
        document.getElementById('open-folder-btn')?.addEventListener('click', openFolderDialog);
        return;
    }
    
    elements.songsList.innerHTML = '';
    
    state.songs.forEach(song => {
        const item = document.createElement('div');
        item.className = 'song-item';
        if (state.currentSong?.path === song.path) {
            item.classList.add('active');
        }
        
        item.innerHTML = `
            <span class="song-icon">🎵</span>
            <div class="song-info">
                <div class="song-title">${song.title}</div>
                <div class="song-artist">${song.artist || 'Unknown Artist'}</div>
            </div>
        `;
        
        item.addEventListener('click', () => loadSong(song.path));
        item.addEventListener('contextmenu', (e) => {
            e.preventDefault();
            addToQueue(song);
        });
        
        elements.songsList.appendChild(item);
    });
}

function handleSearch() {
    const query = elements.searchInput.value.toLowerCase().trim();
    
    if (!query) {
        renderSongsList();
        return;
    }
    
    const filtered = state.songs.filter(song => 
        song.title.toLowerCase().includes(query) ||
        song.artist.toLowerCase().includes(query) ||
        song.name.toLowerCase().includes(query)
    );
    
    // Temporarily replace songs for rendering
    const allSongs = state.songs;
    state.songs = filtered;
    renderSongsList();
    state.songs = allSongs;
}

// =============================================================================
// UI Helpers
// =============================================================================

function openModal(modal) {
    modal.classList.remove('hidden');
    
    // Populate settings values
    if (modal === elements.settingsModal) {
        elements.themeSelect.value = state.settings.theme;
        elements.fullscreenOnPlay.checked = state.settings.fullscreen;
        elements.defaultVolume.value = state.settings.volume;
    }
}

function closeModal(modal) {
    modal.classList.add('hidden');
}

function toggleFullscreen() {
    if (document.fullscreenElement) {
        document.exitFullscreen();
        elements.fullscreenBtn.textContent = '⛶';
    } else {
        document.documentElement.requestFullscreen();
        elements.fullscreenBtn.textContent = '⛶';
    }
}

function handleKeyboard(e) {
    // Ignore if typing in input
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
        return;
    }
    
    switch (e.code) {
        case 'Space':
            e.preventDefault();
            togglePlayback();
            break;
        case 'KeyF':
            if (!e.ctrlKey && !e.metaKey) {
                toggleFullscreen();
            }
            break;
        case 'Escape':
            if (document.fullscreenElement) {
                document.exitFullscreen();
            } else if (!elements.settingsModal.classList.contains('hidden')) {
                closeModal(elements.settingsModal);
            }
            break;
    }
}

function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// =============================================================================
// Start Application
// =============================================================================

document.addEventListener('DOMContentLoaded', init);
