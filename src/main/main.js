/**
 * Thermal Engine - Electron main process.
 */

const path = require('path');
const fs = require('fs');
const { app, BrowserWindow, Tray, Menu, ipcMain, dialog, shell, powerMonitor, nativeImage } = require('electron');

const settings = require('./settings');
const presets = require('./presets');
const { validateTheme, sanitizePresetName } = require('./validation');
const { SensorService } = require('./sensors');
const { DisplayDevice } = require('./display');
const { registerSchemePrivileges, handleProtocol } = require('./protocol');
const { buildMenu } = require('./menu');

const ASSETS = path.join(__dirname, '..', '..', 'assets');
const startMinimized = process.argv.includes('--minimized');

// The display keeps updating while the window is hidden in the tray, so the
// renderer must never be throttled or suspended in the background.
app.commandLine.appendSwitch('disable-background-timer-throttling');
app.commandLine.appendSwitch('disable-renderer-backgrounding');
app.commandLine.appendSwitch('disable-backgrounding-occluded-windows');
app.commandLine.appendSwitch('disable-background-media-suspend');

registerSchemePrivileges();

if (!app.requestSingleInstanceLock()) {
  app.quit();
  process.exit(0);
}

let mainWindow = null;
let tray = null;
let isQuitting = false;
let metricsTimer = null;
const sensors = new SensorService();
const display = new DisplayDevice();

function send(channel, ...args) {
  if (mainWindow && !mainWindow.isDestroyed()) mainWindow.webContents.send(channel, ...args);
}

function showWindow() {
  if (!mainWindow) return;
  if (mainWindow.isMinimized()) mainWindow.restore();
  mainWindow.show();
  mainWindow.focus();
}

function refreshMenu() {
  buildMenu({
    send: (command, arg) => send('menu', command, arg),
    connected: display.connected,
    targetFps: settings.get('target_fps', 30),
    onToggleConnection: toggleConnection,
    onQuit: quit,
  });
  refreshTrayMenu();
}

function refreshTrayMenu() {
  if (!tray) return;
  tray.setContextMenu(Menu.buildFromTemplate([
    { label: 'Show', click: showWindow },
    { label: display.connected ? 'Disconnect Display' : 'Connect Display', click: toggleConnection },
    { type: 'separator' },
    { label: 'Quit', click: quit },
  ]));
}

async function toggleConnection() {
  if (display.connected) await display.disconnect({ userInitiated: true });
  else await display.connect({ userInitiated: true });
}

function quit() {
  isQuitting = true;
  app.quit();
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 820,
    minWidth: 1200,
    minHeight: 700,
    title: 'Thermal Engine',
    icon: path.join(ASSETS, 'icon.png'),
    backgroundColor: '#2d2d32',
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      backgroundThrottling: false,
    },
  });

  mainWindow.loadURL('te://app/index.html');

  mainWindow.once('ready-to-show', () => {
    if (!startMinimized) mainWindow.show();
  });

  mainWindow.on('close', (event) => {
    if (!isQuitting && settings.get('close_to_tray', true)) {
      event.preventDefault();
      mainWindow.hide();
    }
  });

  mainWindow.on('minimize', () => {
    if (settings.get('minimize_to_tray', true)) mainWindow.hide();
  });

  for (const [eventName, visible] of [['show', true], ['restore', true], ['hide', false], ['minimize', false]]) {
    mainWindow.on(eventName, () => send('app:visibility', visible && mainWindow.isVisible()));
  }

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https:\/\//.test(url)) shell.openExternal(url);
    return { action: 'deny' };
  });
}

function createTray() {
  const icon = nativeImage.createFromPath(path.join(ASSETS, 'icon.png')).resize({ width: 16, height: 16 });
  tray = new Tray(icon);
  tray.setToolTip('Thermal Engine');
  tray.on('double-click', showWindow);
  refreshTrayMenu();
}

function startMetrics() {
  metricsTimer = setInterval(() => {
    const procs = app.getAppMetrics();
    const cpu = procs.reduce((sum, p) => sum + p.cpu.percentCPUUsage, 0);
    const memoryMB = procs.reduce((sum, p) => sum + p.memory.workingSetSize, 0) / 1024;
    send('app:metrics', { ...display.takeStats(), cpu, memoryMB });
  }, 1000);
}

function readThemeFile(filePath) {
  const data = JSON.parse(fs.readFileSync(filePath, 'utf8'));
  const { valid, errors } = validateTheme(data);
  if (!valid) throw new Error(`Theme file has invalid format:\n${errors.slice(0, 5).join('\n')}`);
  return data;
}

function registerIpc() {
  ipcMain.handle('sensors:diagnose', () => sensors.diagnose());

  ipcMain.handle('display:status', () => display.status());
  ipcMain.handle('display:connect', () => display.connect({ userInitiated: true }));
  ipcMain.handle('display:disconnect', () => display.disconnect({ userInitiated: true }));
  ipcMain.on('display:frame', (_event, jpeg) => display.submitFrame(Buffer.from(jpeg)));

  ipcMain.handle('presets:list', () => presets.list());
  ipcMain.handle('presets:exists', (_e, name) => presets.exists(name));
  ipcMain.handle('presets:save', (_e, name, data, thumbnail) => presets.save(name, data, thumbnail));
  ipcMain.handle('presets:remove', (_e, name) => {
    presets.remove(name);
    if (settings.get('default_preset') === name) settings.set('default_preset', null);
  });
  ipcMain.handle('presets:open-folder', () => shell.openPath(presets.folder()));

  ipcMain.handle('settings:all', () => settings.all());
  ipcMain.handle('settings:set', (_e, key, value) => {
    settings.set(key, value);
    if (['launch_at_login', 'launch_minimized'].includes(key)) settings.applyAutostart();
    if (key === 'target_fps') refreshMenu();
  });

  ipcMain.handle('files:open-theme', async () => {
    const result = await dialog.showOpenDialog(mainWindow, {
      title: 'Open Theme',
      filters: [{ name: 'Theme Files', extensions: ['json'] }, { name: 'All Files', extensions: ['*'] }],
      properties: ['openFile'],
    });
    if (result.canceled || !result.filePaths.length) return null;
    const filePath = result.filePaths[0];
    return { path: filePath, data: readThemeFile(filePath) };
  });

  ipcMain.handle('files:save-theme', (_e, filePath, data) => {
    fs.writeFileSync(filePath, JSON.stringify(data, null, 2));
    return filePath;
  });

  ipcMain.handle('files:save-theme-as', async (_e, suggestedName, data) => {
    const result = await dialog.showSaveDialog(mainWindow, {
      title: 'Save Theme',
      defaultPath: `${sanitizePresetName(suggestedName)}.json`,
      filters: [{ name: 'Theme Files', extensions: ['json'] }],
    });
    if (result.canceled || !result.filePath) return null;
    fs.writeFileSync(result.filePath, JSON.stringify(data, null, 2));
    return result.filePath;
  });

  ipcMain.handle('files:export-image', async (_e, suggestedName, png) => {
    const result = await dialog.showSaveDialog(mainWindow, {
      title: 'Export Image',
      defaultPath: `${sanitizePresetName(suggestedName)}.png`,
      filters: [{ name: 'PNG Image', extensions: ['png'] }],
    });
    if (result.canceled || !result.filePath) return null;
    fs.writeFileSync(result.filePath, Buffer.from(png));
    return result.filePath;
  });

  const MEDIA_FILTERS = {
    image: [{ name: 'Images', extensions: ['png', 'jpg', 'jpeg', 'bmp', 'gif', 'webp'] }],
    gif: [{ name: 'GIF Images', extensions: ['gif'] }],
    video: [{ name: 'Videos', extensions: ['mp4', 'webm', 'mkv', 'mov', 'm4v'] }],
  };
  ipcMain.handle('files:choose-media', async (_e, kind) => {
    const result = await dialog.showOpenDialog(mainWindow, {
      title: `Select ${kind}`,
      filters: [...(MEDIA_FILTERS[kind] || []), { name: 'All Files', extensions: ['*'] }],
      properties: ['openFile'],
    });
    return result.canceled ? null : result.filePaths[0];
  });

  ipcMain.handle('dialog:message', (_e, options) => dialog.showMessageBox(mainWindow, options));

  ipcMain.handle('app:is-visible', () => !!mainWindow?.isVisible());
  ipcMain.on('app:set-title', (_e, title) => mainWindow?.setTitle(title));
  ipcMain.on('app:refresh-menu', refreshMenu);
  ipcMain.on('app:quit', quit);
}

app.on('second-instance', showWindow);

app.whenReady().then(() => {
  settings.load();
  settings.applyAutostart();
  handleProtocol();
  registerIpc();
  createWindow();
  createTray();
  refreshMenu();

  sensors.onUpdate((data, status) => send('sensors:update', data, status));
  sensors.start();

  display.on('status', (status) => {
    send('display:status', status);
    refreshMenu();
  });
  display.connect();

  powerMonitor.on('suspend', () => {
    console.log('[Power] System going to sleep');
    display.suspend();
  });
  powerMonitor.on('resume', () => {
    console.log('[Power] System waking up');
    display.resume();
    send('power:resume');
  });

  startMetrics();
});

app.on('before-quit', () => {
  isQuitting = true;
});

app.on('will-quit', (event) => {
  clearInterval(metricsTimer);
  sensors.stop();
  if (display.connected) {
    // Release the HID device before exiting so the display is free for other software.
    event.preventDefault();
    display.disconnect({ userInitiated: true }).finally(() => app.exit(0));
  }
});

// Keep running in the tray when the window is closed.
app.on('window-all-closed', () => {});
