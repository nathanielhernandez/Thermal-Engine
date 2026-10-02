/**
 * Bridge between the renderer and the main process. Exposed as `window.te`.
 */

const { contextBridge, ipcRenderer } = require('electron');

function subscribe(channel, callback) {
  const listener = (_event, ...args) => callback(...args);
  ipcRenderer.on(channel, listener);
  return () => ipcRenderer.removeListener(channel, listener);
}

contextBridge.exposeInMainWorld('te', {
  sensors: {
    onUpdate: (cb) => subscribe('sensors:update', cb),
    diagnose: () => ipcRenderer.invoke('sensors:diagnose'),
  },
  display: {
    status: () => ipcRenderer.invoke('display:status'),
    connect: () => ipcRenderer.invoke('display:connect'),
    disconnect: () => ipcRenderer.invoke('display:disconnect'),
    sendFrame: (jpeg) => ipcRenderer.send('display:frame', jpeg),
    onStatus: (cb) => subscribe('display:status', cb),
  },
  presets: {
    list: () => ipcRenderer.invoke('presets:list'),
    exists: (name) => ipcRenderer.invoke('presets:exists', name),
    save: (name, data, thumbnail) => ipcRenderer.invoke('presets:save', name, data, thumbnail),
    remove: (name) => ipcRenderer.invoke('presets:remove', name),
    openFolder: () => ipcRenderer.invoke('presets:open-folder'),
  },
  settings: {
    all: () => ipcRenderer.invoke('settings:all'),
    set: (key, value) => ipcRenderer.invoke('settings:set', key, value),
  },
  files: {
    openTheme: () => ipcRenderer.invoke('files:open-theme'),
    saveTheme: (filePath, data) => ipcRenderer.invoke('files:save-theme', filePath, data),
    saveThemeAs: (suggestedName, data) => ipcRenderer.invoke('files:save-theme-as', suggestedName, data),
    exportImage: (suggestedName, png) => ipcRenderer.invoke('files:export-image', suggestedName, png),
    chooseMedia: (kind) => ipcRenderer.invoke('files:choose-media', kind),
  },
  dialog: {
    message: (options) => ipcRenderer.invoke('dialog:message', options),
  },
  app: {
    onMenu: (cb) => subscribe('menu', cb),
    onMetrics: (cb) => subscribe('app:metrics', cb),
    onResume: (cb) => subscribe('power:resume', cb),
    onVisibility: (cb) => subscribe('app:visibility', cb),
    isVisible: () => ipcRenderer.invoke('app:is-visible'),
    setTitle: (title) => ipcRenderer.send('app:set-title', title),
    refreshMenu: () => ipcRenderer.send('app:refresh-menu'),
    quit: () => ipcRenderer.send('app:quit'),
  },
});
