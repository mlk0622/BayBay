const { app, BrowserWindow, ipcMain, dialog, Menu, Tray, nativeImage } = require('electron');
const { autoUpdater } = require('electron-updater');
const path = require('path');
const { spawn, execFile } = require('child_process');
const net = require('net');
const fs = require('fs');

// Configuration
const APP_NAME = 'Bay Bay';
const APP_VERSION = '2.1.0';
const BACKEND_PORT = 5000;
const BACKEND_HOST = '127.0.0.1';

// Variables globales
let mainWindow = null;
let splashWindow = null;
let backendProcess = null;
let tray = null;
let isQuitting = false;

// Logging vers fichier
const logFile = path.join(app.getPath('userData'), 'app.log');

function log(message) {
    const timestamp = new Date().toISOString();
    const logMessage = `[${timestamp}] ${message}\n`;
    console.log(message);
    try {
        fs.appendFileSync(logFile, logMessage);
    } catch (e) {
        // Ignore
    }
}

function logError(message, error) {
    log(`ERROR: ${message}`);
    if (error) {
        log(`  -> ${error.message || error}`);
        if (error.stack) {
            log(`  -> Stack: ${error.stack}`);
        }
    }
}

// Chemins
function getBackendPath() {
    let backendPath;
    if (app.isPackaged) {
        // En production, le backend est dans resources/backend
        backendPath = path.join(process.resourcesPath, 'backend', 'BayBay.exe');
    } else {
        // En développement
        backendPath = path.join(__dirname, '..', 'dist', 'BayBay', 'BayBay.exe');
    }
    log(`Backend path: ${backendPath}`);
    log(`Backend exists: ${fs.existsSync(backendPath)}`);
    return backendPath;
}

function getBackendDir() {
    return path.dirname(getBackendPath());
}

// Vérifier si un port est disponible
function isPortAvailable(port) {
    return new Promise((resolve) => {
        const server = net.createServer();
        server.once('error', () => resolve(false));
        server.once('listening', () => {
            server.close();
            resolve(true);
        });
        server.listen(port, BACKEND_HOST);
    });
}

// Attendre que le serveur soit prêt
function waitForServer(port, maxAttempts = 60) {
    return new Promise((resolve, reject) => {
        let attempts = 0;

        const checkServer = () => {
            attempts++;
            log(`Tentative de connexion au serveur ${attempts}/${maxAttempts}...`);

            const client = new net.Socket();
            client.setTimeout(2000);

            client.on('connect', () => {
                log('Connexion au serveur réussie!');
                client.destroy();
                resolve(true);
            });

            client.on('timeout', () => {
                client.destroy();
                if (attempts < maxAttempts) {
                    setTimeout(checkServer, 500);
                } else {
                    reject(new Error('Timeout en attendant le serveur'));
                }
            });

            client.on('error', (err) => {
                client.destroy();
                if (attempts < maxAttempts) {
                    setTimeout(checkServer, 500);
                } else {
                    reject(new Error(`Impossible de se connecter au serveur: ${err.message}`));
                }
            });

            client.connect(port, BACKEND_HOST);
        };

        checkServer();
    });
}

// Créer la fenêtre de splash
function createSplashWindow() {
    splashWindow = new BrowserWindow({
        width: 400,
        height: 300,
        frame: false,
        transparent: true,
        alwaysOnTop: true,
        resizable: false,
        skipTaskbar: true,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true
        }
    });

    const splashPath = app.isPackaged
        ? path.join(process.resourcesPath, 'app.asar', 'splash.html')
        : path.join(__dirname, 'splash.html');

    log(`Loading splash from: ${splashPath}`);
    splashWindow.loadFile(path.join(__dirname, 'splash.html'));
    splashWindow.center();
}

// Créer la fenêtre principale
function createMainWindow() {
    mainWindow = new BrowserWindow({
        width: 1400,
        height: 900,
        minWidth: 1000,
        minHeight: 700,
        show: false,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js')
        },
        titleBarStyle: 'default',
        autoHideMenuBar: true
    });

    // Masquer le menu
    mainWindow.setMenu(null);

    // Charger l'application
    const url = `http://${BACKEND_HOST}:${BACKEND_PORT}`;
    log(`Loading URL: ${url}`);
    mainWindow.loadURL(url);

    // Gérer les erreurs de chargement
    mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
        logError(`Failed to load: ${errorDescription} (${errorCode})`);
    });

    // Afficher quand prêt
    mainWindow.once('ready-to-show', () => {
        log('Main window ready to show');
        if (splashWindow) {
            splashWindow.close();
            splashWindow = null;
        }
        mainWindow.show();
        mainWindow.focus();
    });

    // Gérer la fermeture
    mainWindow.on('close', (event) => {
        if (!isQuitting) {
            event.preventDefault();
            mainWindow.hide();

            if (tray) {
                tray.displayBalloon({
                    title: APP_NAME,
                    content: 'L\'application continue en arrière-plan.'
                });
            }
        }
    });

    mainWindow.on('closed', () => {
        mainWindow = null;
    });

    // Ouvrir les liens externes dans le navigateur par défaut
    mainWindow.webContents.setWindowOpenHandler(({ url }) => {
        require('electron').shell.openExternal(url);
        return { action: 'deny' };
    });
}

// Créer l'icône dans la barre système
function createTray() {
    try {
        // Créer une icône par défaut
        const icon = nativeImage.createEmpty();
        tray = new Tray(icon);
        tray.setToolTip(APP_NAME);

        const contextMenu = Menu.buildFromTemplate([
            {
                label: 'Ouvrir Bay Bay',
                click: () => {
                    if (mainWindow) {
                        mainWindow.show();
                        mainWindow.focus();
                    }
                }
            },
            { type: 'separator' },
            {
                label: 'Quitter',
                click: () => {
                    isQuitting = true;
                    app.quit();
                }
            }
        ]);

        tray.setContextMenu(contextMenu);

        tray.on('click', () => {
            if (mainWindow) {
                if (mainWindow.isVisible()) {
                    mainWindow.focus();
                } else {
                    mainWindow.show();
                }
            }
        });
    } catch (error) {
        logError('Failed to create tray', error);
    }
}

// Démarrer le backend Python
async function startBackend() {
    const backendPath = getBackendPath();
    const backendDir = getBackendDir();

    log(`Starting backend...`);
    log(`  Path: ${backendPath}`);
    log(`  Dir: ${backendDir}`);
    log(`  App packaged: ${app.isPackaged}`);
    log(`  Resources path: ${process.resourcesPath}`);

    // Vérifier que l'exécutable existe
    if (!fs.existsSync(backendPath)) {
        const error = new Error(`Backend non trouvé: ${backendPath}`);
        logError('Backend not found', error);
        throw error;
    }

    // Vérifier le contenu du dossier backend
    try {
        const files = fs.readdirSync(backendDir);
        log(`Backend dir contents: ${files.join(', ')}`);
    } catch (e) {
        logError('Cannot read backend dir', e);
    }

    // Vérifier si le port est disponible
    const portAvailable = await isPortAvailable(BACKEND_PORT);
    log(`Port ${BACKEND_PORT} available: ${portAvailable}`);

    if (!portAvailable) {
        log('Port already in use, server might be running...');
        // Essayer de se connecter au serveur existant
        try {
            await waitForServer(BACKEND_PORT, 5);
            log('Connected to existing server');
            return true;
        } catch (e) {
            logError('Port in use but cannot connect', e);
            throw new Error(`Le port ${BACKEND_PORT} est utilisé par une autre application`);
        }
    }

    return new Promise((resolve, reject) => {
        log('Spawning backend process...');

        // Préparer l'environnement
        const env = {
            ...process.env,
            ELECTRON_MODE: '1',
            PYTHONIOENCODING: 'utf-8'
        };

        // Démarrer le processus backend avec execFile pour éviter les problèmes de shell
        backendProcess = spawn(backendPath, [], {
            cwd: backendDir,
            env: env,
            stdio: ['ignore', 'pipe', 'pipe'],
            windowsHide: true,
            detached: false
        });

        log(`Backend PID: ${backendProcess.pid}`);

        let stdoutBuffer = '';
        let stderrBuffer = '';

        backendProcess.stdout.on('data', (data) => {
            const text = data.toString();
            stdoutBuffer += text;
            log(`[Backend stdout] ${text.trim()}`);
        });

        backendProcess.stderr.on('data', (data) => {
            const text = data.toString();
            stderrBuffer += text;
            log(`[Backend stderr] ${text.trim()}`);
        });

        backendProcess.on('error', (error) => {
            logError('Backend process error', error);
            reject(error);
        });

        backendProcess.on('exit', (code, signal) => {
            log(`Backend exited with code ${code}, signal ${signal}`);
            log(`Stdout: ${stdoutBuffer}`);
            log(`Stderr: ${stderrBuffer}`);

            if (!isQuitting) {
                const errorMsg = stderrBuffer || stdoutBuffer || `Exit code: ${code}`;
                if (mainWindow) {
                    dialog.showErrorBox(
                        'Erreur',
                        `Le serveur s'est arrêté:\n${errorMsg.substring(0, 500)}`
                    );
                }
                app.quit();
            }
        });

        // Attendre que le serveur soit prêt
        waitForServer(BACKEND_PORT, 60)
            .then(() => {
                log('Backend started successfully');
                resolve(true);
            })
            .catch((error) => {
                logError('Failed to connect to backend', error);
                log(`Final stdout: ${stdoutBuffer}`);
                log(`Final stderr: ${stderrBuffer}`);

                // Tuer le processus s'il existe encore
                if (backendProcess && !backendProcess.killed) {
                    backendProcess.kill();
                }

                reject(new Error(`${error.message}\n\nLogs:\n${stderrBuffer || stdoutBuffer}`));
            });
    });
}

// Arrêter le backend
function stopBackend() {
    if (backendProcess) {
        log('Stopping backend...');

        try {
            if (process.platform === 'win32') {
                spawn('taskkill', ['/pid', backendProcess.pid.toString(), '/f', '/t'], {
                    windowsHide: true
                });
            } else {
                backendProcess.kill('SIGTERM');
            }
        } catch (e) {
            logError('Error stopping backend', e);
        }

        backendProcess = null;
    }
}

// Configuration de l'auto-updater
function setupAutoUpdater() {
    if (!app.isPackaged) {
        log('Skipping auto-updater in development');
        return;
    }

    autoUpdater.autoDownload = false;
    autoUpdater.autoInstallOnAppQuit = true;

    autoUpdater.on('error', (error) => {
        logError('Auto-updater error', error);
    });

    autoUpdater.on('update-available', (info) => {
        dialog.showMessageBox(mainWindow, {
            type: 'info',
            title: 'Mise à jour disponible',
            message: `Version ${info.version} disponible. Télécharger ?`,
            buttons: ['Oui', 'Non']
        }).then((result) => {
            if (result.response === 0) {
                autoUpdater.downloadUpdate();
            }
        });
    });

    autoUpdater.on('update-downloaded', () => {
        dialog.showMessageBox(mainWindow, {
            type: 'info',
            title: 'Mise à jour prête',
            message: 'Redémarrer pour installer ?',
            buttons: ['Redémarrer', 'Plus tard']
        }).then((result) => {
            if (result.response === 0) {
                isQuitting = true;
                autoUpdater.quitAndInstall();
            }
        });
    });
}

// Initialisation de l'application
app.whenReady().then(async () => {
    log('='.repeat(50));
    log('Application starting...');
    log(`Version: ${APP_VERSION}`);
    log(`Packaged: ${app.isPackaged}`);
    log(`User data: ${app.getPath('userData')}`);
    log(`Resources: ${process.resourcesPath}`);
    log('='.repeat(50));

    // Créer le splash screen
    createSplashWindow();

    try {
        // Démarrer le backend
        await startBackend();

        // Créer l'icône système
        createTray();

        // Créer la fenêtre principale
        createMainWindow();

        // Configurer l'auto-updater
        setupAutoUpdater();

    } catch (error) {
        logError('Startup error', error);

        if (splashWindow) {
            splashWindow.close();
        }

        dialog.showErrorBox(
            'Erreur de démarrage',
            `${error.message}\n\nConsultez le fichier de log:\n${logFile}`
        );

        app.quit();
    }
});

// Empêcher plusieurs instances
const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
    app.quit();
} else {
    app.on('second-instance', () => {
        if (mainWindow) {
            if (mainWindow.isMinimized()) mainWindow.restore();
            mainWindow.show();
            mainWindow.focus();
        }
    });
}

// Gestion de la fermeture
app.on('before-quit', () => {
    log('Application quitting...');
    isQuitting = true;
});

app.on('will-quit', () => {
    stopBackend();
    if (tray) {
        tray.destroy();
    }
});

app.on('window-all-closed', () => {
    // Ne pas quitter - on reste dans le tray
});

// IPC handlers
ipcMain.handle('get-version', () => APP_VERSION);
ipcMain.handle('quit-app', () => {
    isQuitting = true;
    app.quit();
});
