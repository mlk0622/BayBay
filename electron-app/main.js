const { app, BrowserWindow, Menu, shell, ipcMain, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const net = require('net');
const http = require('http');
const fs = require('fs');

// Configuration
const APP_NAME = 'Bay Bay';
const APP_VERSION = '2.3.3.4';
const BACKEND_PORT = 5001;
const BACKEND_HOST = 'localhost';
const MAX_STARTUP_TIME = 30000; // 30 secondes

let mainWindow;
let splashWindow;
let backendProcess = null;
let isQuitting = false;

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
        timeout: 30000
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
                    // La mise à jour est lancée, le backend va fermer l'application
                    log('Mise à jour lancée, fermeture de l\'application...');
                } else {
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
