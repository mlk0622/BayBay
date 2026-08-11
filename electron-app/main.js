const { app, BrowserWindow, shell, dialog, ipcMain } = require('electron');
const path = require('path');

// Hardware acceleration enabled for GPU rendering & high performance UI
const fs = require('fs');
const https = require('https');
const { spawn } = require('child_process');
const net = require('net');

// Configuration
const APP_NAME = 'Bay Bay';
let CLOUD_URL = 'http://88.190.118.23:33081'; // URL par défaut du serveur Cloud
let BACKEND_PORT = 5001;
let BACKEND_HOST = 'localhost';

// Charger config.json s'il existe pour pouvoir écraser l'URL si besoin
try {
    const configPath = path.join(__dirname, 'config.json');
    if (fs.existsSync(configPath)) {
        const configData = JSON.parse(fs.readFileSync(configPath, 'utf8'));
        if (configData.CLOUD_URL) {
            CLOUD_URL = configData.CLOUD_URL;
        }
        if (configData.BACKEND_PORT) {
            BACKEND_PORT = configData.BACKEND_PORT;
        }
        if (configData.BACKEND_HOST) {
            BACKEND_HOST = configData.BACKEND_HOST;
        }
    }
} catch (e) {
    console.error('Erreur chargement config.json:', e.message);
}

// Charger theme_config.json pour mémoriser le thème de l'application
let appTheme = 'light';
const themeConfigPath = path.join(app.getPath('userData'), 'theme_config.json');
try {
    if (fs.existsSync(themeConfigPath)) {
        const data = JSON.parse(fs.readFileSync(themeConfigPath, 'utf8'));
        if (data.theme) {
            appTheme = data.theme;
        }
    }
} catch (e) {
    console.error('Erreur chargement theme_config.json:', e.message);
}

let mainWindow;
let windowLoaded = false;
let minTimePassed = false;

function checkAndShow() {
    if (windowLoaded && minTimePassed) {
        if (splashWindow && !splashWindow.isDestroyed()) {
            splashWindow.close();
        }
        if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.show();
            mainWindow.focus();
        }
    }
}

// Fonction utilitaire pour tester si le serveur Cloud est joignable de manière asynchrone rapide
function checkUrlReachable(urlStr, timeoutMs) {
    return new Promise((resolve) => {
        try {
            const parsed = new URL(urlStr);
            const port = parsed.port || (parsed.protocol === 'https:' ? 443 : 80);
            const host = parsed.hostname;
            
            const socket = new net.Socket();
            let resolved = false;
            
            socket.setTimeout(timeoutMs);
            
            socket.on('connect', () => {
                socket.destroy();
                if (!resolved) {
                    resolved = true;
                    resolve(true);
                }
            });
            
            socket.on('timeout', () => {
                socket.destroy();
                if (!resolved) {
                    resolved = true;
                    resolve(false);
                }
            });
            
            socket.on('error', () => {
                socket.destroy();
                if (!resolved) {
                    resolved = true;
                    resolve(false);
                }
            });
            
            socket.connect(port, host);
        } catch (e) {
            resolve(false);
        }
    });
}

function getConnectionErrorPage() {
    const isDark = appTheme !== 'light';
    const bg = isDark ? '#0b131a' : '#F2EFF6';
    const cardBg = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(255,255,255,0.7)';
    const cardBorder = isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)';
    const titleColor = isDark ? '#f3f7ff' : '#121214';
    const textColor = isDark ? 'rgba(203,213,225,0.8)' : '#5C5C64';
    const btnBg = isDark ? 'linear-gradient(135deg,#4fafd9 0%,#1f5fb6 100%)' : 'linear-gradient(135deg,rgba(168,85,247,0.8) 0%,rgba(192,132,252,0.4) 100%)';
    const btnShadow = isDark ? 'rgba(31,95,182,0.4)' : 'rgba(168,85,247,0.25)';

    return `data:text/html;charset=utf-8,${encodeURIComponent(`<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:100%;height:100%;background:${bg};display:flex;justify-content:center;align-items:center;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;-webkit-app-region:drag}
.card{background:${cardBg};border:1px solid ${cardBorder};border-radius:20px;padding:40px;max-width:420px;text-align:center;box-shadow:0 10px 40px rgba(0,0,0,0.15);-webkit-app-region:no-drag}
.icon{font-size:48px;margin-bottom:16px}
h1{font-size:20px;font-weight:700;color:${titleColor};margin-bottom:8px}
p{font-size:14px;color:${textColor};line-height:1.6;margin-bottom:24px}
.btn{display:inline-block;padding:12px 32px;border-radius:12px;font-size:14px;font-weight:600;cursor:pointer;border:1px solid rgba(255,255,255,0.25);color:#fff;background:${btnBg};box-shadow:0 4px 15px ${btnShadow};text-decoration:none;transition:all 0.2s ease}
.btn:hover{transform:translateY(-1px);filter:brightness(1.1)}
.url{font-size:12px;color:${textColor};opacity:0.6;margin-top:16px;word-break:break-all}
</style></head><body>
<div class="card">
<div class="icon">📡</div>
<h1>Connexion impossible</h1>
<p>Impossible de se connecter au serveur Bay Bay.<br>Vérifiez votre connexion internet et réessayez.</p>
<a class="btn" href="javascript:void(0)" onclick="window.location.reload()">Réessayer</a>
<div class="url">${CLOUD_URL}</div>
</div>
</body></html>`)}`;
}

function createMainWindow() {
    if (mainWindow) return mainWindow;
    mainWindow = new BrowserWindow({
        width: 1400,
        height: 900,
        minWidth: 1000,
        minHeight: 600,
        show: false,
        frame: false,
        backgroundColor: appTheme === 'light' ? '#F2EFF6' : '#0b131a',
        autoHideMenuBar: true,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            webSecurity: true,
            preload: path.join(__dirname, 'preload.js')
        },
        title: APP_NAME
    });

    // Track which URLs have already failed to prevent infinite cascade
    let failedUrls = new Set();

    // Raccourci F8 pour effacer la session (déconnexion forcée), F5 pour recharger
    mainWindow.webContents.on('before-input-event', (event, input) => {
        if (input.key === 'F8') {
            const session = mainWindow.webContents.session;
            session.clearStorageData().then(() => {
                console.log("Session et cookies effacés.");
                failedUrls.clear();
                mainWindow.loadURL(CLOUD_URL);
            });
        }
        if (input.key === 'F5') {
            console.log("F5 pressed: reloading and retrying Cloud...");
            failedUrls.clear();
            mainWindow.loadURL(CLOUD_URL);
        }
    });

    function loadCloudOrFallback() {
        console.log(`Vérification de la disponibilité du serveur Cloud : ${CLOUD_URL}...`);
        checkUrlReachable(CLOUD_URL, 3000).then((isReachable) => {
            if (mainWindow.isDestroyed()) return;
            mainWindow.webContents.session.clearCache().then(() => {
                if (mainWindow.isDestroyed()) return;
                console.log("Cache Electron effacé pour éviter l'ancien thème/code");
                if (isReachable) {
                    console.log(`Le serveur Cloud est en ligne. Chargement de : ${CLOUD_URL}`);
                    mainWindow.loadURL(CLOUD_URL);
                } else {
                    console.log(`Le serveur Cloud est hors ligne. Affichage de l'écran d'erreur de connexion.`);
                    showConnectionError();
                }
            });
        });
    }

    function showConnectionError() {
        if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.loadURL(getConnectionErrorPage());
        }
    }

    loadCloudOrFallback();

    // Repli automatique en cas de problème de connexion
    mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription, validatedURL) => {
        // Ignore aborted loads (e.g. when we navigate away before the page finishes)
        if (errorCode === -3) return;

        console.log(`Échec du chargement de l'URL : ${validatedURL} (Erreur ${errorCode}: ${errorDescription})`);
        failedUrls.add(validatedURL);

        // If Cloud URL failed, try local backend once
        const localUrl = `http://${BACKEND_HOST}:${BACKEND_PORT}`;
        if (validatedURL.startsWith(CLOUD_URL) && !failedUrls.has(localUrl)) {
            console.log(`Serveur Cloud inaccessible. Repli sur le serveur local : ${localUrl}...`);
            mainWindow.loadURL(localUrl);
        } else {
            // All options exhausted — show styled error page instead of white screen
            console.log(`Tous les serveurs sont inaccessibles. Affichage de la page d'erreur.`);
            showConnectionError();
        }
    });

    // When user clicks "Réessayer" on the error page, it does a reload which triggers navigation
    // We intercept will-navigate to clear failedUrls and retry the Cloud
    mainWindow.webContents.on('will-navigate', (event, url) => {
        // If we're on the error page and user triggers reload, redirect to Cloud
        if (url.startsWith('data:')) {
            event.preventDefault();
            failedUrls.clear();
            loadCloudOrFallback();
        }
    });

    mainWindow.webContents.setWindowOpenHandler(({ url }) => {
        shell.openExternal(url);
        return { action: 'deny' };
    });

    mainWindow.on('closed', () => {
        mainWindow = null;
    });

    windowLoaded = false;
    minTimePassed = false;

    mainWindow.webContents.on('did-finish-load', () => {
        console.log("mainWindow: did-finish-load event fired.");
        // Always mark as loaded after a short delay to prevent white screen
        setTimeout(() => {
            if (!windowLoaded) {
                console.log("mainWindow: did-finish-load fallback triggered (no frontend-ready received).");
                windowLoaded = true;
                checkAndShow();
            }
        }, 2000);
    });

    setTimeout(() => {
        minTimePassed = true;
        checkAndShow();
    }, 2800); // 2.8 seconds minimum splash display

    if (!app.isPackaged) {
        mainWindow.webContents.openDevTools();
    }

    mainWindow.setMenuBarVisibility(false);

    return mainWindow;
}

let splashWindow;
function createSplashWindow() {
    splashWindow = new BrowserWindow({
        width: 500,
        height: 420,
        frame: false,
        transparent: true,
        alwaysOnTop: true,
        resizable: false,
        hasShadow: true,
        show: false, // Hide initially to prevent a brief white screen flash before content loads
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true
        }
    });

    const version = app.getVersion();
    splashWindow.loadFile(path.join(__dirname, 'splash.html'), { query: { version, theme: appTheme } });

    // Only show the splash screen once it has fully loaded to prevent white/blank rendering box
    splashWindow.once('ready-to-show', () => {
        if (splashWindow && !splashWindow.isDestroyed()) {
            splashWindow.show();
        }
    });

    splashWindow.on('closed', () => {
        splashWindow = null;
    });
}

function isNewerVersion(current, remote) {
    const cleanCurrent = current.replace(/^v/, '');
    const cleanRemote = remote.replace(/^v/, '');
    const currentParts = cleanCurrent.split('.').map(x => parseInt(x, 10) || 0);
    const remoteParts = cleanRemote.split('.').map(x => parseInt(x, 10) || 0);
    
    for (let i = 0; i < Math.max(currentParts.length, remoteParts.length); i++) {
        const c = currentParts[i] || 0;
        const r = remoteParts[i] || 0;
        if (r > c) return true;
        if (c > r) return false;
    }
    return false;
}

function checkForUpdates(callback) {
    console.log('[Updater] Checking for updates on GitHub...');
    const options = {
        hostname: 'api.github.com',
        path: '/repos/mlk0622/BayBay/releases/latest',
        headers: {
            'User-Agent': 'BayBay-Electron-App'
        },
        timeout: 8000
    };

    const req = https.get(options, (res) => {
        let data = '';
        res.on('data', (chunk) => { data += chunk; });
        res.on('end', () => {
            try {
                if (res.statusCode !== 200) {
                    console.log(`[Updater] GitHub API returned status ${res.statusCode}`);
                    callback(null);
                    return;
                }
                const release = JSON.parse(data);
                const remoteVersion = release.tag_name;
                const currentVersion = app.getVersion();
                console.log(`[Updater] Local version: ${currentVersion}, Remote version: ${remoteVersion}`);
                
                if (remoteVersion && isNewerVersion(currentVersion, remoteVersion)) {
                    let downloadUrl = null;
                    let assetName = null;
                    if (release.assets && release.assets.length > 0) {
                        for (const asset of release.assets) {
                            const name = asset.name.toLowerCase();
                            if (name.endsWith('.exe') && (name.includes('setup') || name.includes('install') || name.includes('baybay'))) {
                                downloadUrl = asset.browser_download_url;
                                assetName = asset.name;
                                break;
                            }
                        }
                        if (!downloadUrl) {
                            for (const asset of release.assets) {
                                if (asset.name.toLowerCase().endsWith('.exe')) {
                                    downloadUrl = asset.browser_download_url;
                                    assetName = asset.name;
                                    break;
                                }
                            }
                        }
                    }
                    if (downloadUrl) {
                        console.log(`[Updater] New update available! Download URL: ${downloadUrl}`);
                        callback({
                            version: remoteVersion,
                            downloadUrl: downloadUrl,
                            assetName: assetName,
                            notes: release.body || ''
                        });
                    } else {
                        console.log('[Updater] No executable asset found in the latest release.');
                        callback(null);
                    }
                } else {
                    console.log('[Updater] App is up to date.');
                    callback(null);
                }
            } catch (e) {
                console.error('[Updater] Error parsing update check response:', e);
                callback(null);
            }
        });
    });

    req.on('error', (err) => {
        console.error('[Updater] Error checking for updates:', err);
        callback(null);
    });

    req.on('timeout', () => {
        req.destroy();
        console.log('[Updater] Update check timed out');
        callback(null);
    });
}

function updateDownloadProgress(splashWindow, percent, downloadedSize, totalSize) {
    if (!splashWindow || splashWindow.isDestroyed()) return;
    const downloadedMB = (downloadedSize / (1024 * 1024)).toFixed(1);
    const totalMB = totalSize ? (totalSize / (1024 * 1024)).toFixed(1) : "113.0";
    console.log(`[Updater] Download progress: ${percent}% (${downloadedMB}MB/${totalMB}MB)`);
    splashWindow.webContents.executeJavaScript(`
        let p = document.querySelector('.progress-bar');
        if (p) {
            p.style.animation = 'none';
            p.style.width = '${percent}%';
        }
        let txt = document.querySelector('.update-txt');
        if (!txt) {
            let container = document.querySelector('.loading');
            if (container) {
                txt = document.createElement('div');
                txt.className = 'update-txt';
                txt.style.fontSize = '13px';
                txt.style.color = 'var(--loading-text)';
                txt.style.marginTop = '10px';
                txt.style.fontWeight = '500';
                container.appendChild(txt);
            }
        }
        if (txt) {
            txt.textContent = 'Téléchargement de la mise à jour : ${downloadedMB} Mo / ${totalMB} Mo (${percent}%)';
        }
    `);
}

function showInstallingScreen(splashWindow) {
    if (!splashWindow || splashWindow.isDestroyed()) return;
    console.log(`[Updater] Showing installing screen...`);
    splashWindow.webContents.executeJavaScript(`
        let p = document.querySelector('.progress-bar');
        if (p) {
            p.style.width = '100%';
            p.style.animation = 'loading 1.5s ease-in-out infinite';
        }
        let txt = document.querySelector('.update-txt');
        if (txt) {
            txt.textContent = 'Installation de la mise à jour en cours...';
        }
    `);
}

function downloadAndInstallUpdate(downloadUrl, splashWindow) {
    const tempDir = app.getPath('temp');
    const fileName = 'BayBaySetupUpdate.exe';
    const filePath = path.join(tempDir, fileName);
    console.log(`[Updater] Starting download to ${filePath}...`);

    try {
        if (fs.existsSync(filePath)) {
            fs.unlinkSync(filePath);
        }
    } catch (e) {
        console.error('[Updater] Error deleting old update file:', e);
    }

    const file = fs.createWriteStream(filePath);
    
    function download(url) {
        const req = https.get(url, { headers: { 'User-Agent': 'BayBay-Electron-App' } }, (response) => {
            if (response.statusCode === 301 || response.statusCode === 302) {
                console.log(`[Updater] Redirected to: ${response.headers.location}`);
                download(response.headers.location);
                return;
            }
            
            if (response.statusCode !== 200) {
                console.error(`[Updater] HTTP error during download: ${response.statusCode}`);
                dialog.showErrorBox('Erreur de mise à jour', `Le serveur a renvoyé le statut ${response.statusCode}`);
                createMainWindow();
                return;
            }

            const totalSizeHeader = response.headers['content-length'];
            const totalSize = totalSizeHeader ? parseInt(totalSizeHeader, 10) : 0;
            let downloadedSize = 0;
            console.log(`[Updater] Total file size: ${(totalSize / (1024 * 1024)).toFixed(2)} MB`);

            response.on('data', (chunk) => {
                downloadedSize += chunk.length;
                file.write(chunk);
                
                let percent = 0;
                if (totalSize && totalSize > 0) {
                    percent = Math.round((downloadedSize / totalSize) * 100);
                } else {
                    const estimatedTotal = 113 * 1024 * 1024;
                    percent = Math.min(Math.round((downloadedSize / estimatedTotal) * 100), 99);
                }
                updateDownloadProgress(splashWindow, percent, downloadedSize, totalSize);
            });

            file.on('finish', () => {
                console.log('[Updater] File write stream finished. Executable fully written to disk.');
                showInstallingScreen(splashWindow);

                setTimeout(() => {
                    try {
                        console.log('[Updater] Launching installer setup silently...');
                        const child = spawn(filePath, ['/S'], {
                            detached: true,
                            stdio: 'ignore'
                        });
                        
                        child.unref();
                        
                        // Quit Electron after 1 second so the installer can overwrite the files
                        setTimeout(() => {
                            console.log('[Updater] Quitting application to let installer run...');
                            app.quit();
                        }, 1000);

                    } catch (e) {
                        console.error('[Updater] Error spawning installer:', e);
                        dialog.showErrorBox('Erreur de lancement', `Impossible de lancer l'installateur: ${e.message}`);
                        createMainWindow();
                    }
                }, 1000);
            });

            response.on('end', () => {
                file.end();
                console.log('[Updater] Response download finished.');
            });
        });

        req.on('error', (err) => {
            file.end();
            try { fs.unlinkSync(filePath); } catch (e) {}
            console.error('[Updater] Network error during download:', err);
            dialog.showErrorBox('Erreur de téléchargement', `Impossible de télécharger la mise à jour: ${err.message}`);
            createMainWindow();
        });
    }

    download(downloadUrl);
}

ipcMain.on('window-minimize', () => {
    if (mainWindow && !mainWindow.isDestroyed()) mainWindow.minimize();
});

ipcMain.on('window-maximize', () => {
    if (mainWindow && !mainWindow.isDestroyed()) {
        if (mainWindow.isMaximized()) {
            mainWindow.unmaximize();
        } else {
            mainWindow.maximize();
        }
    }
});

ipcMain.on('window-close', () => {
    if (mainWindow && !mainWindow.isDestroyed()) mainWindow.close();
});

ipcMain.on('set-theme', (event, theme) => {
    appTheme = theme;
    try {
        fs.writeFileSync(themeConfigPath, JSON.stringify({ theme }), 'utf8');
        console.log(`[Main] Thème enregistré: ${theme}`);
        if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.setBackgroundColor(theme === 'light' ? '#F2EFF6' : '#0b131a');
        }
    } catch (e) {
        console.error('[Main] Impossible d\'enregistrer le thème:', e.message);
    }
});

app.whenReady().then(() => {
    console.log(`Démarrage de ${APP_NAME} en mode Cloud`);
    createSplashWindow();
    
    // Vérification des mises à jour au démarrage
    setTimeout(() => {
        checkForUpdates((update) => {
            if (update && splashWindow && !splashWindow.isDestroyed()) {
                console.log('[Updater] Update available. Showing custom modal in splash window.');
                const notesEscaped = JSON.stringify(update.notes);
                splashWindow.webContents.executeJavaScript(`showUpdateModal("${update.version}", ${notesEscaped})`);
                
                splashWindow.on('page-title-updated', (event, title) => {
                    if (title === 'update-accept') {
                        console.log('[Updater] User accepted update. Downloading...');
                        downloadAndInstallUpdate(update.downloadUrl, splashWindow);
                    } else if (title === 'update-decline') {
                        console.log('[Updater] User declined update. Starting application...');
                        createMainWindow();
                    }
                });
            } else {
                createMainWindow();
            }
        });
    }, 500);
});

ipcMain.on('frontend-ready', () => {
    console.log('[Main] Received frontend-ready signal from webapp.');
    windowLoaded = true;
    checkAndShow();
});

app.on('window-all-closed', () => {
    app.quit();
});

app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
        createMainWindow();
    }
});
