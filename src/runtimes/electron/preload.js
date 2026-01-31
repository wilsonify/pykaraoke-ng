/**
 * PyKaraoke-NG Electron Preload Script
 * 
 * This script runs before the renderer process and provides a secure
 * bridge between the isolated renderer and the main process via contextBridge.
 */

const { contextBridge, ipcRenderer } = require('electron');

// Define valid channels for security
const validSendChannels = [
    'playback:toggle',
    'playback:stop',
    'playback:previous',
    'playback:next',
    'volume:change',
    'fullscreen:toggle'
];

const validReceiveChannels = [
    'song:open',
    'folder:selected',
    'playback:toggle',
    'playback:stop',
    'playback:previous',
    'playback:next',
    'settings:updated'
];

const validInvokeChannels = [
    'get-settings',
    'set-settings',
    'get-songs-folder',
    'get-recent-files',
    'open-song-dialog',
    'open-folder-dialog'
];

// Expose protected APIs to renderer
contextBridge.exposeInMainWorld('electronAPI', {
    /**
     * Send a message to the main process
     * @param {string} channel - The channel name
     * @param {any} data - The data to send
     */
    send: (channel, data) => {
        if (validSendChannels.includes(channel)) {
            ipcRenderer.send(channel, data);
        } else {
            console.warn(`Attempted to send on invalid channel: ${channel}`);
        }
    },

    /**
     * Receive messages from the main process
     * @param {string} channel - The channel name
     * @param {function} callback - The callback function
     * @returns {function} - Cleanup function to remove listener
     */
    receive: (channel, callback) => {
        if (validReceiveChannels.includes(channel)) {
            const subscription = (event, ...args) => callback(...args);
            ipcRenderer.on(channel, subscription);
            
            // Return cleanup function
            return () => {
                ipcRenderer.removeListener(channel, subscription);
            };
        } else {
            console.warn(`Attempted to receive on invalid channel: ${channel}`);
            return () => {};
        }
    },

    /**
     * Invoke a handler in the main process and wait for response
     * @param {string} channel - The channel name
     * @param {any} args - Arguments to pass
     * @returns {Promise} - Promise that resolves with the response
     */
    invoke: (channel, ...args) => {
        if (validInvokeChannels.includes(channel)) {
            return ipcRenderer.invoke(channel, ...args);
        } else {
            console.warn(`Attempted to invoke invalid channel: ${channel}`);
            return Promise.reject(new Error(`Invalid channel: ${channel}`));
        }
    },

    /**
     * Platform information
     */
    platform: process.platform,
    
    /**
     * App version
     */
    version: require('./package.json').version
});

// Expose settings API
contextBridge.exposeInMainWorld('settingsAPI', {
    get: () => ipcRenderer.invoke('get-settings'),
    set: (settings) => ipcRenderer.invoke('set-settings', settings)
});

// Expose file operations API
contextBridge.exposeInMainWorld('fileAPI', {
    openSongDialog: () => ipcRenderer.invoke('open-song-dialog'),
    openFolderDialog: () => ipcRenderer.invoke('open-folder-dialog'),
    getSongsFolder: () => ipcRenderer.invoke('get-songs-folder'),
    getRecentFiles: () => ipcRenderer.invoke('get-recent-files')
});

// Log preload completion
console.log('PyKaraoke-NG preload script loaded');
