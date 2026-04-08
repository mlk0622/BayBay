const { app, BrowserWindow, Menu, shell, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const net = require('net');
const { autoUpdater } = require('electron-updater');
const fs = require('fs');

// Configuration
const APP_NAME = 'Bay Bay';
const APP_VERSION = '2.3.2';
const BACKEND_PORT = 5001;
const BACKEND_HOST = 'localhost';
const MAX_STARTUP_TIME = 30000; // 30 secondes

let mainWindow;
let splashWindow;
let backendProcess = null;
let isQuitting = false;

// Configuration de l'auto-updater
if (!app.isPackaged) {
    console.log('Mode développement - auto-updater désactivé');
} else {
    // Configurer l'auto-updater pour GitHub
    autoUpdater.autoDownload = true;
    autoUpdater.autoInstallOnAppQuit = true;

    autoUpdater.on('checking-for-update', () => {
        log('Vérification des mises à jour...');
    });

    autoUpdater.on('update-available', (info) => {
        log(`Mise à jour disponible: v${info.version}`);
    });

    autoUpdater.on('update-not-available', () => {
        log('Application à jour');
    });

    autoUpdater.on('download-progress', (progress) => {
        log(`Téléchargement: ${Math.round(progress.percent)}%`);
    });

    autoUpdater.on('update-downloaded', (info) => {
        log(`Mise à jour v${info.version} téléchargée, installation au prochain redémarrage`);
        // Installer automatiquement après téléchargement
        autoUpdater.quitAndInstall(false, true);
    });

    autoUpdater.on('error', (error) => {
        log(`Erreur auto-update: ${error.message}`);
    });

    // Vérifier les mises à jour au démarrage (après un délai pour laisser l'app se charger)
    setTimeout(() => {
        autoUpdater.checkForUpdates().catch(err => {
            log(`Impossible de vérifier les mises à jour: ${err.message}`);
        });
    }, 3000);
}

function log(message) {
    console.log(`[${new Date().toISOString()}] ${message}`);
}

function getBackendPath() {
    if (app.isPackaged) {
        return path.join(path.dirname(process.execPath), 'resources', 'backend', 'BayBay.exe');
    } else {
        return path.join(__dirname, '..', 'dist', 'BayBay', 'BayBay.exe');
    }
}

function getBackendDirectory() {
    if (app.isPackaged) {
        return path.join(path.dirname(process.execPath), 'resources', 'backend');
    } else {
        return path.join(__dirname, '..', 'dist', 'BayBay');
    }
}

function createSplashWindow() {
    splashWindow = new BrowserWindow({
        width: 420,
        height: 340,
        frame: false,
        alwaysOnTop: true,
        transparent: true,
        resizable: false,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true
        }
    });

    splashWindow.loadFile('splash.html');

    splashWindow.on('closed', () => {
        splashWindow = null;
    });

    return splashWindow;
}

function checkPort(port, callback) {
    const socket = new net.Socket();

    socket.setTimeout(1000);

    socket.on('connect', () => {
        socket.destroy();
        callback(true);
    });

    socket.on('timeout', () => {
        socket.destroy();
        callback(false);
    });

    socket.on('error', () => {
        callback(false);
    });

    socket.connect(port, BACKEND_HOST);
}

function waitForBackend(callback, startTime = Date.now()) {
    const elapsed = Date.now() - startTime;

    if (elapsed > MAX_STARTUP_TIME) {
        log('Timeout: Le backend n\'a pas démarré à temps');
        return callback(false);
    }

    checkPort(BACKEND_PORT, (isOpen) => {
        if (isOpen) {
            log(`Backend prêt sur le port ${BACKEND_PORT}`);
            callback(true);
        } else {
            setTimeout(() => waitForBackend(callback, startTime), 500);
        }
    });
}

function startBackend() {
    return new Promise((resolve, reject) => {
        const backendPath = getBackendPath();
        const backendDir = getBackendDirectory();

        log(`Démarrage du backend: ${backendPath}`);
        log(`Répertoire de travail: ${backendDir}`);

        if (!fs.existsSync(backendPath)) {
            log(`ERREUR: Backend non trouvé à ${backendPath}`);
            return reject(new Error(`Backend non trouvé: ${backendPath}`));
        }

        try {
            backendProcess = spawn(backendPath, [], {
                cwd: backendDir,
                env: { ...process.env, ELECTRON_MODE: '1' },
                stdio: ['ignore', 'pipe', 'pipe'],
                windowsHide: true,
                detached: false
            });

            log(`Backend démarré avec PID: ${backendProcess.pid}`);

            backendProcess.stdout.on('data', (data) => {
                log(`Backend stdout: ${data.toString().trim()}`);
            });

            backendProcess.stderr.on('data', (data) => {
                log(`Backend stderr: ${data.toString().trim()}`);
            });

            backendProcess.on('error', (error) => {
                log(`Erreur backend: ${error.message}`);
                reject(error);
            });

            backendProcess.on('exit', (code, signal) => {
                log(`Backend fermé avec code ${code}, signal ${signal}`);
                if (!isQuitting) {
                    log('Backend fermé de manière inattendue');
                }
            });

            waitForBackend((success) => {
                if (success) {
                    resolve();
                } else {
                    reject(new Error('Le backend n\'a pas pu démarrer'));
                }
            });

        } catch (error) {
            log(`Erreur lors du démarrage: ${error.message}`);
            reject(error);
        }
    });
}

function createMainWindow() {
    mainWindow = new BrowserWindow({
        width: 1400,
        height: 900,
        minWidth: 1000,
        minHeight: 600,
        show: false,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            webSecurity: true
        },
        title: APP_NAME
    });

    mainWindow.loadURL(`http://${BACKEND_HOST}:${BACKEND_PORT}`);

    mainWindow.webContents.setWindowOpenHandler(({ url }) => {
        shell.openExternal(url);
        return { action: 'deny' };
    });

    mainWindow.on('closed', () => {
        mainWindow = null;
    });

    mainWindow.once('ready-to-show', () => {
        if (splashWindow) {
            splashWindow.close();
        }
        mainWindow.show();
        mainWindow.focus();
    });

    if (!app.isPackaged) {
        mainWindow.webContents.openDevTools();
    }

    Menu.setApplicationMenu(Menu.buildFromTemplate([
        {
            label: 'Bay Bay',
            submenu: [
                {
                    label: `À propos de ${APP_NAME}`,
                    click: () => {
                        shell.openExternal('https://github.com/mlk0622/BayBay');
                    }
                },
                { type: 'separator' },
                { label: 'Quitter', accelerator: 'Ctrl+Q', click: () => app.quit() }
            ]
        },
        {
            label: 'Édition',
            submenu: [
                { label: 'Annuler', accelerator: 'Ctrl+Z', role: 'undo' },
                { label: 'Rétablir', accelerator: 'Ctrl+Y', role: 'redo' },
                { type: 'separator' },
                { label: 'Couper', accelerator: 'Ctrl+X', role: 'cut' },
                { label: 'Copier', accelerator: 'Ctrl+C', role: 'copy' },
                { label: 'Coller', accelerator: 'Ctrl+V', role: 'paste' }
            ]
        },
        {
            label: 'Affichage',
            submenu: [
                { label: 'Recharger', accelerator: 'Ctrl+R', role: 'reload' },
                { label: 'Forcer le rechargement', accelerator: 'Ctrl+Shift+R', role: 'forceReload' },
                { type: 'separator' },
                { label: 'Zoom avant', accelerator: 'Ctrl+Plus', role: 'zoomIn' },
                { label: 'Zoom arrière', accelerator: 'Ctrl+-', role: 'zoomOut' },
                { label: 'Zoom réel', accelerator: 'Ctrl+0', role: 'resetZoom' },
                { type: 'separator' },
                { label: 'Plein écran', accelerator: 'F11', role: 'togglefullscreen' }
            ]
        },
        {
            label: 'Aide',
            submenu: [
                {
                    label: 'Documentation',
                    click: () => shell.openExternal('https://github.com/mlk0622/BayBay#readme')
                },
                {
                    label: 'Signaler un problème',
                    click: () => shell.openExternal('https://github.com/mlk0622/BayBay/issues')
                }
            ]
        }
    ]));

    return mainWindow;
}

function stopBackend() {
    if (backendProcess && !backendProcess.killed) {
        log('Arrêt du backend...');
        isQuitting = true;

        backendProcess.kill('SIGTERM');

        setTimeout(() => {
            if (!backendProcess.killed) {
                log('Arrêt forcé du backend');
                backendProcess.kill('SIGKILL');
            }
        }, 5000);
    }
}

app.whenReady().then(async () => {
    log(`Démarrage de ${APP_NAME} v${APP_VERSION}`);

    createSplashWindow();

    try {
        await startBackend();
        log('Backend démarré avec succès');
        createMainWindow();
    } catch (error) {
        log(`Erreur de démarrage: ${error.message}`);

        if (splashWindow) {
            splashWindow.close();
        }

        const errorWindow = new BrowserWindow({
            width: 500,
            height: 400,
            resizable: false,
            webPreferences: {
                nodeIntegration: false,
                contextIsolation: true
            }
        });

        errorWindow.loadURL(`data:text/html;charset=utf-8,
            <html>
            <head>
                <title>Erreur de démarrage</title>
                <style>
                    body { font-family: Arial; padding: 20px; background: #f5f5f5; }
                    .error { background: #fee; border: 1px solid #fcc; padding: 15px; border-radius: 5px; }
                    .title { color: #c33; font-size: 18px; margin-bottom: 10px; }
                    .message { margin-bottom: 15px; }
                    .details { background: #eee; padding: 10px; font-family: monospace; font-size: 12px; }
                </style>
            </head>
            <body>
                <div class="error">
                    <div class="title">❌ Erreur de démarrage de Bay Bay</div>
                    <div class="message">L'application n'a pas pu démarrer correctement.</div>
                    <div class="details">${error.message}</div>
                </div>
            </body>
            </html>
        `);
    }
});

app.on('window-all-closed', () => {
    stopBackend();
    app.quit();
});

app.on('before-quit', () => {
    isQuitting = true;
    stopBackend();
});

app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
        createMainWindow();
    }
});

process.on('SIGINT', () => {
    log('Signal SIGINT reçu');
    stopBackend();
    app.quit();
});

process.on('SIGTERM', () => {
    log('Signal SIGTERM reçu');
    stopBackend();
    app.quit();
});
