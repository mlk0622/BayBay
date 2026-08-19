const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("electronAPI", {
    minimize: () => ipcRenderer.send("window-minimize"),
    maximize: () => ipcRenderer.send("window-maximize"),
    close: () => ipcRenderer.send("window-close"),
    frontendReady: () => ipcRenderer.send("frontend-ready"),
    setTheme: (theme) => ipcRenderer.send("set-theme", theme)
});
