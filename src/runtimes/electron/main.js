/**
 * PyKaraoke-NG Electron Main Process
 * 
 * This is the main entry point for the Electron desktop application.
 * It creates the browser window and manages the Python backend process.
 */

const { app, BrowserWindow, ipcMain, dialog, Menu, shell } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const Store = require('electron-store');

// Initialize persistent storage
const store = new Store({
    defaults: {
        windowBounds: { width: 1024, height: 768 },
        songsFolder: '',
        recentFiles: [],
        settings: {
            fullscreen: false,
            volume: 0.75,
            theme: 'dark'
        }
    }
});

// Keep a global reference to prevent garbage collection
let mainWindow = null;
let pythonProcess = null;

// Determine if we're in development mode
const isDev = process.argv.includes('--dev') || process.env.NODE_ENV === 'development';

/**
 * Get the path to the Python executable
 */
function getPythonPath() {
    if (isDev) {
        // In development, use the system Python or venv
        return process.platform === 'win32' ? 'python' : 'python3';
    }
    
    // In production, look for bundled Python
    const resourcesPath = process.resourcesPath;
    if (process.platform === 'win32') {
        return path.join(resourcesPath, 'python', 'python.exe');
    }
    return path.join(resourcesPath, 'python', 'bin', 'python3');
}

/**
 * Get the path to the Python scripts
 */
function getScriptsPath() {
    if (isDev) {
        return path.join(__dirname, '..');
    }
    return path.join(process.resourcesPath, 'python');
}

/**
 * Create the main application window
 */
function createWindow() {
    const { width, height } = store.get('windowBounds');
    
    mainWindow = new BrowserWindow({
        width,
        height,
        minWidth: 800,
        minHeight: 600,
        title: 'PyKaraoke-NG',
        icon: path.join(__dirname, 'assets', 'icon.png'),
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            nodeIntegration: false,
            contextIsolation: true,
            sandbox: true
        },
        show: false, // Don't show until ready
        backgroundColor: '#1e1e1e'
    });

    // Load the HTML file
    mainWindow.loadFile(path.join(__dirname, 'index.html'));

    // Show window when ready
    mainWindow.once('ready-to-show', () => {
        mainWindow.show();
        if (isDev) {
            mainWindow.webContents.openDevTools();
        }
    });

    // Save window bounds on resize
    mainWindow.on('resize', () => {
        const bounds = mainWindow.getBounds();
        store.set('windowBounds', { width: bounds.width, height: bounds.height });
    });

    // Handle window close
    mainWindow.on('closed', () => {
        mainWindow = null;
        stopPythonProcess();
    });

    // Create application menu
    createMenu();
}

/**
 * Create the application menu
 */
function createMenu() {
    const template = [
        {
            label: 'File',
            submenu: [
                {
                    label: 'Open Song...',
                    accelerator: 'CmdOrCtrl+O',
                    click: () => openSongDialog()
                },
                {
                    label: 'Open Songs Folder...',
                    click: () => openFolderDialog()
                },
                { type: 'separator' },
                {
                    label: 'Recent Files',
                    submenu: buildRecentFilesMenu()
                },
                { type: 'separator' },
                { role: 'quit' }
            ]
        },
        {
            label: 'Playback',
            submenu: [
                {
                    label: 'Play/Pause',
                    accelerator: 'Space',
                    click: () => sendToRenderer('playback:toggle')
                },
                {
                    label: 'Stop',
                    accelerator: 'CmdOrCtrl+.',
                    click: () => sendToRenderer('playback:stop')
                },
                { type: 'separator' },
                {
                    label: 'Previous',
                    accelerator: 'CmdOrCtrl+Left',
                    click: () => sendToRenderer('playback:previous')
                },
                {
                    label: 'Next',
                    accelerator: 'CmdOrCtrl+Right',
                    click: () => sendToRenderer('playback:next')
                }
            ]
        },
        {
            label: 'View',
            submenu: [
                { role: 'reload' },
                { role: 'forceReload' },
                { role: 'toggleDevTools' },
                { type: 'separator' },
                { role: 'resetZoom' },
                { role: 'zoomIn' },
                { role: 'zoomOut' },
                { type: 'separator' },
                { role: 'togglefullscreen' }
            ]
        },
        {
            label: 'Help',
            submenu: [
                {
                    label: 'Documentation',
                    click: () => shell.openExternal('https://github.com/wilsonify/pykaraoke-ng')
                },
                {
                    label: 'Report Issue',
                    click: () => shell.openExternal('https://github.com/wilsonify/pykaraoke-ng/issues')
                },
                { type: 'separator' },
                {
                    label: 'About',
                    click: () => showAboutDialog()
                }
            ]
        }
    ];

    const menu = Menu.buildFromTemplate(template);
    Menu.setApplicationMenu(menu);
}

/**
 * Build recent files submenu
 */
function buildRecentFilesMenu() {
    const recentFiles = store.get('recentFiles', []);
    if (recentFiles.length === 0) {
        return [{ label: 'No recent files', enabled: false }];
    }
    
    return recentFiles.map(file => ({
        label: path.basename(file),
        click: () => openSong(file)
    }));
}

/**
 * Open file dialog to select a song
 */
async function openSongDialog() {
    const result = await dialog.showOpenDialog(mainWindow, {
        title: 'Open Karaoke Song',
        filters: [
            { name: 'Karaoke Files', extensions: ['cdg', 'kar', 'mid', 'mpg', 'mpeg', 'avi'] },
            { name: 'All Files', extensions: ['*'] }
        ],
        properties: ['openFile']
    });

    if (!result.canceled && result.filePaths.length > 0) {
        openSong(result.filePaths[0]);
    }
}

/**
 * Open folder dialog to select songs folder
 */
async function openFolderDialog() {
    const result = await dialog.showOpenDialog(mainWindow, {
        title: 'Select Songs Folder',
        properties: ['openDirectory']
    });

    if (!result.canceled && result.filePaths.length > 0) {
        store.set('songsFolder', result.filePaths[0]);
        sendToRenderer('folder:selected', result.filePaths[0]);
    }
}

/**
 * Open a song file
 */
function openSong(filePath) {
    // Add to recent files
    const recentFiles = store.get('recentFiles', []);
    const updated = [filePath, ...recentFiles.filter(f => f !== filePath)].slice(0, 10);
    store.set('recentFiles', updated);
    
    sendToRenderer('song:open', filePath);
}

/**
 * Show about dialog
 */
function showAboutDialog() {
    dialog.showMessageBox(mainWindow, {
        type: 'info',
        title: 'About PyKaraoke-NG',
        message: 'PyKaraoke-NG',
        detail: `Version: 0.7.5\n\nA modern karaoke player supporting CDG, MIDI/KAR, and MPEG formats.\n\nLicense: LGPL-2.1-or-later`
    });
}

/**
 * Send message to renderer process
 */
function sendToRenderer(channel, data) {
    if (mainWindow && mainWindow.webContents) {
        mainWindow.webContents.send(channel, data);
    }
}

/**
 * Start Python backend process
 */
function startPythonProcess() {
    if (pythonProcess) return;

    const pythonPath = getPythonPath();
    const scriptsPath = getScriptsPath();

    // For now, just validate Python is available
    pythonProcess = spawn(pythonPath, ['-c', 'from pykaraoke.config import version; print(version.PYKARAOKE_VERSION_STRING)'], {
        cwd: scriptsPath,
        stdio: ['pipe', 'pipe', 'pipe']
    });

    pythonProcess.stdout.on('data', (data) => {
        console.log(`Python: ${data}`);
    });

    pythonProcess.stderr.on('data', (data) => {
        console.error(`Python Error: ${data}`);
    });

    pythonProcess.on('close', (code) => {
        console.log(`Python process exited with code ${code}`);
        pythonProcess = null;
    });
}

/**
 * Stop Python backend process
 */
function stopPythonProcess() {
    if (pythonProcess) {
        pythonProcess.kill();
        pythonProcess = null;
    }
}

// =============================================================================
// IPC Handlers
// =============================================================================

ipcMain.handle('get-settings', () => {
    return store.get('settings');
});

ipcMain.handle('set-settings', (event, settings) => {
    store.set('settings', settings);
    return true;
});

ipcMain.handle('get-songs-folder', () => {
    return store.get('songsFolder');
});

ipcMain.handle('get-recent-files', () => {
    return store.get('recentFiles');
});

ipcMain.handle('open-song-dialog', () => {
    return openSongDialog();
});

ipcMain.handle('open-folder-dialog', () => {
    return openFolderDialog();
});

// =============================================================================
// App Lifecycle
// =============================================================================

app.whenReady().then(() => {
    createWindow();
    
    // macOS: Re-create window when dock icon is clicked
    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

app.on('window-all-closed', () => {
    // On macOS, apps typically stay open until explicitly quit
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('before-quit', () => {
    stopPythonProcess();
});

// Security: Prevent new window creation
app.on('web-contents-created', (event, contents) => {
    contents.setWindowOpenHandler(() => {
        return { action: 'deny' };
    });
});
