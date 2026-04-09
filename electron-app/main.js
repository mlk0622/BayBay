const { app, BrowserWindow, Menu, shell, ipcMain, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const net = require('net');
const http = require('http');
const fs = require('fs');

// Configuration
const APP_NAME = 'Bay Bay';
const APP_VERSION = app.getVersion();
const BACKEND_PORT = 5001;
const BACKEND_HOST = 'localhost';
const MAX_STARTUP_TIME = 30000; // 30 secondes

let mainWindow;
let splashWindow;
let backendProcess = null;
let isQuitting = false;
let isUpdateInProgress = false;
let updateProgressWindow = null;
let updateStatusPollInterval = null;
let isUpdateProgressWindowReady = false;
let pendingProgressState = { percent: 0, message: 'Demarrage...' };

function escapeHtml(text) {
    return String(text || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function createUpdateProgressWindow() {
    if (updateProgressWindow && !updateProgressWindow.isDestroyed()) {
        updateProgressWindow.show();
        updateProgressWindow.focus();
        return updateProgressWindow;
    }

    const ownerWindow = mainWindow && !mainWindow.isDestroyed() ? mainWindow : undefined;
    updateProgressWindow = new BrowserWindow({
        width: 520,
        height: 240,
        resizable: false,
        minimizable: false,
        maximizable: false,
        alwaysOnTop: true,
        modal: !!ownerWindow,
        parent: ownerWindow,
        show: false,
        autoHideMenuBar: true,
        title: 'Mise a jour Bay Bay',
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true
        }
    });

    const html = `
        <html>
        <head>
            <meta charset="utf-8" />
            <title>Mise a jour</title>
            <style>
                body { font-family: Segoe UI, Arial, sans-serif; margin: 0; background: #f4f7fb; color: #1f2937; }
                .wrap { padding: 18px 20px; }
                h1 { font-size: 18px; margin: 0 0 8px; }
                .sub { font-size: 13px; color: #4b5563; margin-bottom: 14px; }
                .bar { width: 100%; height: 18px; background: #e5e7eb; border-radius: 9px; overflow: hidden; }
                .fill { height: 100%; width: 0%; background: linear-gradient(90deg, #059669, #10b981); transition: width 0.25s ease; }
                .meta { margin-top: 10px; display: flex; justify-content: space-between; font-size: 13px; }
                .status { margin-top: 14px; font-size: 13px; color: #374151; min-height: 20px; }
            </style>
        </head>
        <body>
            <div class="wrap">
                <h1>Mise a jour en cours...</h1>
                <div class="sub">Le telechargement peut prendre quelques minutes. Merci de patienter.</div>
                <div class="bar"><div id="fill" class="fill"></div></div>
                <div class="meta">
                    <div id="percent">0%</div>
                    <div id="hint">Preparation...</div>
                </div>
                <div id="bytes" class="status">0.0 / 0.0 MB</div>
                <div id="status" class="status">Demarrage...</div>
            </div>
            <script>
                window.setProgress = function(percent, message) {
                    const safePercent = Number.isFinite(percent) ? Math.max(0, Math.min(100, percent)) : 0;
                    document.getElementById('fill').style.width = safePercent + '%';
                    document.getElementById('percent').textContent = Math.round(safePercent) + '%';
                    document.getElementById('hint').textContent = safePercent >= 100 ? 'Termine' : 'Telechargement';
                    if (message) {
                        document.getElementById('status').textContent = message;
                    }
                };

                window.setBytes = function(downloaded, total) {
                    const d = Number.isFinite(downloaded) ? downloaded : 0;
                    const t = Number.isFinite(total) ? total : 0;
                    const suffix = t > 0 ? (d.toFixed(1) + ' / ' + t.toFixed(1) + ' MB') : (d.toFixed(1) + ' MB telecharges');
                    document.getElementById('bytes').textContent = suffix;
                };
            </script>
        </body>
        </html>
    `;

    isUpdateProgressWindowReady = false;
    updateProgressWindow.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(html)}`);
    updateProgressWindow.once('ready-to-show', () => {
        if (updateProgressWindow && !updateProgressWindow.isDestroyed()) {
            updateProgressWindow.show();
            updateProgressWindow.focus();
        }
    });

    updateProgressWindow.webContents.on('did-finish-load', () => {
        isUpdateProgressWindowReady = true;
        updateProgressWindowUi(
            pendingProgressState.percent,
            pendingProgressState.message,
            pendingProgressState.downloadedMb,
            pendingProgressState.totalMb
        );
    });

    updateProgressWindow.on('closed', () => {
        updateProgressWindow = null;
        isUpdateProgressWindowReady = false;
    });

    return updateProgressWindow;
}

function updateProgressWindowUi(percent, message, downloadedMb = 0, totalMb = 0) {
    pendingProgressState = {
        percent: Number.isFinite(percent) ? percent : 0,
        message: message || '',
        downloadedMb: Number.isFinite(downloadedMb) ? downloadedMb : 0,
        totalMb: Number.isFinite(totalMb) ? totalMb : 0
    };

    if (!updateProgressWindow || updateProgressWindow.isDestroyed()) {
        return;
    }

    if (!isUpdateProgressWindowReady) {
        return;
    }

    const p = pendingProgressState.percent;
    const m = escapeHtml(pendingProgressState.message || '');
    const downloaded = pendingProgressState.downloadedMb;
    const total = pendingProgressState.totalMb;
    updateProgressWindow.webContents.executeJavaScript(`window.setProgress(${p}, "${m}"); window.setBytes(${downloaded}, ${total});`).catch(() => {});
}

function stopUpdateStatusPolling() {
    if (updateStatusPollInterval) {
        clearInterval(updateStatusPollInterval);
        updateStatusPollInterval = null;
    }
}

function forceCloseForUpdate(reason) {
    log(`Fermeture forcee pour mise a jour (${reason})`);
    isQuitting = true;
    stopUpdateStatusPolling();

    const windows = BrowserWindow.getAllWindows();
    windows.forEach((win) => {
        try {
            win.destroy();
        } catch (e) {
            log(`Erreur fermeture fenetre: ${e.message}`);
        }
    });

    app.exit(0);
}

function startUpdateStatusPolling() {
    stopUpdateStatusPolling();

    updateStatusPollInterval = setInterval(() => {
        const options = {
            hostname: BACKEND_HOST,
            port: BACKEND_PORT,
            path: '/api/updates/status',
            method: 'GET',
            timeout: 10000
        };

        const req = http.request(options, (res) => {
            let data = '';
            res.on('data', (chunk) => { data += chunk; });
            res.on('end', () => {
                try {
                    const status = JSON.parse(data);
                    const percent = Number(status.progress || 0);
                    const message = status.message || 'Mise a jour en cours...';
                    const downloadedMb = Number(status.downloaded_mb || 0);
                    const totalMb = Number(status.total_mb || 0);
                    updateProgressWindowUi(percent, message, downloadedMb, totalMb);

                    if (status.error) {
                        stopUpdateStatusPolling();
                        dialog.showErrorBox('Erreur de mise a jour', status.error);
                        return;
                    }

                    // Quand le script d'installation est lance, on ferme l'UI Electron de force.
                    if (message.toLowerCase().includes('lancement de l\'installation')) {
                        forceCloseForUpdate('installation lancee');
                    }
                } catch (e) {
                    log(`Erreur parsing status update: ${e.message}`);
                }
            });
        });

        req.on('error', (error) => {
            log(`Erreur polling status update: ${error.message}`);
        });

        req.on('timeout', () => {
            req.destroy();
            log('Timeout polling status update');
        });

        req.end();
    }, 800);
}

// Fonction pour vérifier les mises à jour via l'API backend
function checkForUpdatesViaBackend() {
    if (!app.isPackaged) {
        log('Mode développement - vérification des mises à jour désactivée');
        return;
    }

    log('Vérification des mises à jour via le backend...');

    const options = {
        hostname: BACKEND_HOST,
        port: BACKEND_PORT,
        path: '/api/updates/check',
        method: 'GET',
        timeout: 15000
    };

    const req = http.request(options, (res) => {
        let data = '';

        res.on('data', (chunk) => {
            data += chunk;
        });

        res.on('end', () => {
            try {
                const result = JSON.parse(data);
                log(`Résultat vérification: ${JSON.stringify(result)}`);

                if (result.available) {
                    log(`Mise à jour disponible: ${result.version} (actuelle: ${result.current_version})`);

                    // Afficher une notification à l'utilisateur
                    if (mainWindow) {
                        dialog.showMessageBox(mainWindow, {
                            type: 'info',
                            title: 'Mise à jour disponible',
                            message: `Une nouvelle version de ${APP_NAME} est disponible!`,
                            detail: `Version actuelle: ${result.current_version}\nNouvelle version: ${result.version}\n\nVoulez-vous mettre à jour maintenant?\n\nVos données seront conservées.`,
                            buttons: ['Mettre à jour', 'Plus tard'],
                            defaultId: 0,
                            cancelId: 1
                        }).then(({ response }) => {
                            if (response === 0) {
                                // Lancer la mise à jour
                                triggerUpdate();
                            }
                        });
                    }
                } else {
                    log(`Application à jour (v${result.current_version})`);
                }
            } catch (e) {
                log(`Erreur parsing réponse mise à jour: ${e.message}`);
            }
        });
    });

    req.on('error', (error) => {
        log(`Erreur vérification mise à jour: ${error.message}`);
    });

    req.on('timeout', () => {
        req.destroy();
        log('Timeout lors de la vérification des mises à jour');
    });

    req.end();
}

// Fonction pour déclencher la mise à jour via le backend
function triggerUpdate() {
    log('Déclenchement de la mise à jour...');

    createUpdateProgressWindow();
    updateProgressWindowUi(0, 'Demarrage du telechargement...', 0, 0);

    const postData = JSON.stringify({ silent: false });

    const options = {
        hostname: BACKEND_HOST,
        port: BACKEND_PORT,
        path: '/api/updates/download',
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Content-Length': Buffer.byteLength(postData)
        },
        timeout: 600000  // 10 minutes timeout pour gros fichiers
    };

    const req = http.request(options, (res) => {
        let data = '';

        res.on('data', (chunk) => {
            data += chunk;
        });

        res.on('end', () => {
            try {
                const result = JSON.parse(data);
                log(`Résultat mise à jour: ${JSON.stringify(result)}`);

                if (result.success) {
                    isUpdateInProgress = true;
                    startUpdateStatusPolling();
                    updateProgressWindowUi(1, 'Telechargement en cours...', 0, 0);
                    log('Mise a jour demarree, suivi de progression actif');
                } else {
                    stopUpdateStatusPolling();
                    dialog.showErrorBox('Erreur de mise à jour', result.message || 'Impossible de lancer la mise à jour');
                }
            } catch (e) {
                log(`Erreur parsing réponse: ${e.message}`);
            }
        });
    });

    req.on('error', (error) => {
        log(`Erreur lors du déclenchement de la mise à jour: ${error.message}`);
        dialog.showErrorBox('Erreur de mise à jour', error.message);
    });

    req.on('timeout', () => {
        req.destroy();
        log('Timeout lors du téléchargement de la mise à jour');
    });

    req.write(postData);
    req.end();
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

    splashWindow.loadFile('splash.html', { query: { version: app.getVersion() } });

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
        autoHideMenuBar: true,
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

    mainWindow.setMenuBarVisibility(false);

    /* Menu.setApplicationMenu(Menu.buildFromTemplate([
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
                    label: 'Vérifier les mises à jour',
                    click: () => {
                        checkForUpdatesViaBackend();
                    }
                },
                { type: 'separator' },
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
    ]));*/

    Menu.setApplicationMenu(null);

    return mainWindow;
}

function stopBackend() {
    if (isUpdateInProgress) {
        log('Mise a jour en cours - backend conserve pour finaliser l installation');
        return;
    }

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

        // Vérifier les mises à jour immédiatement après le démarrage
        checkForUpdatesViaBackend();
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
    if (!isUpdateInProgress) {
        stopBackend();
    }
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
