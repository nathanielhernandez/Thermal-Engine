/**
 * Persistent settings stored as JSON in the user data directory.
 */

const fs = require('fs');
const path = require('path');
const { app } = require('electron');

const DEFAULT_SETTINGS = {
  launch_at_login: true,
  launch_minimized: true,
  minimize_to_tray: true,
  close_to_tray: true,
  target_fps: 30,
  default_preset: null,
  suppress_60fps_warning: false,
  jpeg_quality: 80,
};

let settings = null;

function settingsFile() {
  return path.join(app.getPath('userData'), 'settings.json');
}

function load() {
  settings = { ...DEFAULT_SETTINGS };
  try {
    const raw = JSON.parse(fs.readFileSync(settingsFile(), 'utf8'));
    if (raw && typeof raw === 'object') Object.assign(settings, raw);
  } catch (err) {
    if (err.code !== 'ENOENT') console.error('[Settings] Error loading settings:', err.message);
    save();
  }
  return settings;
}

function save() {
  try {
    fs.mkdirSync(path.dirname(settingsFile()), { recursive: true });
    fs.writeFileSync(settingsFile(), JSON.stringify(settings, null, 2));
  } catch (err) {
    console.error('[Settings] Error saving settings:', err.message);
  }
}

function get(key, fallback = null) {
  if (!settings) load();
  return key in settings ? settings[key] : fallback;
}

function set(key, value) {
  if (!settings) load();
  settings[key] = value;
  save();
}

function all() {
  if (!settings) load();
  return { ...settings };
}

/** Sync the Windows "run at login" entry with the current settings. */
function applyAutostart() {
  if (process.platform !== 'win32' || !app.isPackaged) return;
  const args = get('launch_minimized', true) ? ['--minimized'] : [];
  app.setLoginItemSettings({ openAtLogin: !!get('launch_at_login', true), args });
}

module.exports = { load, get, set, all, applyAutostart, DEFAULT_SETTINGS };
