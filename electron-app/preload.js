const { contextBridge, ipcRenderer } = require('electron');

// Exposer des APIs sécurisées au renderer
contextBridge.exposeInMainWorld('electronAPI', {
    // Version de l'application
    getVersion: () => ipcRenderer.invoke('get-version'),

    // Vérifier les mises à jour
    checkUpdates: () => ipcRenderer.invoke('check-updates'),

    // Quitter l'application
    quitApp: () => ipcRenderer.invoke('quit-app'),

    // Événements de mise à jour
    onUpdateAvailable: (callback) => {
        ipcRenderer.on('update-available', (event, info) => callback(info));
    },

    onUpdateDownloaded: (callback) => {
        ipcRenderer.on('update-downloaded', (event, info) => callback(info));
    },

    onUpdateProgress: (callback) => {
        ipcRenderer.on('update-progress', (event, progress) => callback(progress));
    }
});

// Désactiver les raccourcis de rechargement en production
window.addEventListener('keydown', (e) => {
    // Désactiver F5, Ctrl+R, Ctrl+Shift+R
    if (e.key === 'F5' ||
        (e.ctrlKey && e.key === 'r') ||
        (e.ctrlKey && e.shiftKey && e.key === 'R')) {
        e.preventDefault();
    }
});
