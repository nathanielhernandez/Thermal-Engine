/**
 * Preset storage: one JSON file (plus optional PNG thumbnail) per preset in
 * <userData>/presets.
 */

const fs = require('fs');
const path = require('path');
const { app } = require('electron');
const { validateTheme, isSafeFilename, sanitizePresetName } = require('./validation');

const BUILTIN_DEFAULT = {
  name: 'Default',
  background_color: '#0f0f19',
  elements: [
    { type: 'circle_gauge', name: 'cpu_temp_gauge', x: 200, y: 240, radius: 120, text: 'CPU TEMP', source: 'cpu_temp', color: '#00ff96', value: 45 },
    { type: 'circle_gauge', name: 'cpu_util_gauge', x: 480, y: 240, radius: 120, text: 'CPU UTIL', source: 'cpu_percent', color: '#00c8ff', value: 30 },
    { type: 'circle_gauge', name: 'gpu_util_gauge', x: 760, y: 240, radius: 120, text: 'GPU UTIL', source: 'gpu_percent', color: '#c864ff', value: 55 },
    { type: 'circle_gauge', name: 'gpu_temp_gauge', x: 1040, y: 240, radius: 120, text: 'GPU TEMP', source: 'gpu_temp', color: '#ff9632', value: 62 },
    { type: 'text', name: 'title', x: 490, y: 20, text: 'SYSTEM MONITOR', font_size: 36, color: '#666680', width: 300, height: 50 },
  ],
};

function presetsDir() {
  return path.join(app.getPath('userData'), 'presets');
}

function bundledPresetsDir() {
  return app.isPackaged
    ? path.join(process.resourcesPath, 'presets')
    : path.join(__dirname, '..', '..', 'presets');
}

/** Presets saved by the Python version (installed to %LOCALAPPDATA%\ThermalEngine). */
function legacyPresetsDir() {
  return process.env.LOCALAPPDATA ? path.join(process.env.LOCALAPPDATA, 'ThermalEngine', 'presets') : null;
}

function copyPresetFiles(fromDir, toDir) {
  if (!fromDir || !fs.existsSync(fromDir)) return 0;
  let copied = 0;
  for (const file of fs.readdirSync(fromDir)) {
    if (!/\.(json|png)$/i.test(file) || !isSafeFilename(file).safe) continue;
    const target = path.join(toDir, file);
    if (fs.existsSync(target)) continue;
    fs.copyFileSync(path.join(fromDir, file), target);
    copied++;
  }
  return copied;
}

/** Create the presets folder on first run, seeded with bundled and legacy presets. */
function ensurePresetsDir() {
  const dir = presetsDir();
  if (fs.existsSync(dir)) return;
  fs.mkdirSync(dir, { recursive: true });
  copyPresetFiles(bundledPresetsDir(), dir);
  const migrated = copyPresetFiles(legacyPresetsDir(), dir);
  if (migrated) console.log(`[Presets] Imported ${migrated} files from the previous ThermalEngine install`);
}

function readThumbnail(file) {
  try {
    return `data:image/png;base64,${fs.readFileSync(file).toString('base64')}`;
  } catch {
    return null;
  }
}

function list() {
  ensurePresetsDir();
  const presets = new Map();
  presets.set('Default', { name: 'Default', data: BUILTIN_DEFAULT, builtin: true, thumbnail: null });

  const dir = presetsDir();
  for (const file of fs.readdirSync(dir)) {
    if (!file.endsWith('.json') || !isSafeFilename(file).safe) continue;
    const filePath = path.join(dir, file);
    try {
      const data = JSON.parse(fs.readFileSync(filePath, 'utf8'));
      const { valid, errors } = validateTheme(data);
      if (!valid) {
        console.warn(`[Presets] Invalid preset ${file}:`, errors.slice(0, 5).join('; '));
        continue;
      }
      const name = data.name || file.slice(0, -5);
      presets.set(name, {
        name,
        data,
        builtin: false,
        file: filePath,
        thumbnail: readThumbnail(filePath.replace(/\.json$/, '.png')),
      });
    } catch (err) {
      console.warn(`[Presets] Failed to load ${file}:`, err.message);
    }
  }

  return [...presets.values()].sort((a, b) => {
    if (a.name === 'Default') return -1;
    if (b.name === 'Default') return 1;
    return a.name.toLowerCase().localeCompare(b.name.toLowerCase());
  });
}

function filePaths(name) {
  const safeName = sanitizePresetName(name);
  const check = isSafeFilename(`${safeName}.json`);
  if (!check.safe) throw new Error(`Invalid preset name: ${check.error}`);
  const dir = presetsDir();
  return { json: path.join(dir, `${safeName}.json`), png: path.join(dir, `${safeName}.png`) };
}

function exists(name) {
  return fs.existsSync(filePaths(name).json);
}

/** Save a preset. `thumbnail` is an optional PNG as a Uint8Array/Buffer. */
function save(name, data, thumbnail) {
  ensurePresetsDir();
  const { valid, errors } = validateTheme(data);
  if (!valid) throw new Error(`Invalid theme: ${errors.slice(0, 5).join(', ')}`);
  const paths = filePaths(name);
  fs.writeFileSync(paths.json, JSON.stringify(data, null, 2));
  if (thumbnail) fs.writeFileSync(paths.png, Buffer.from(thumbnail));
}

function remove(name) {
  const preset = list().find((p) => p.name === name && !p.builtin);
  if (!preset) return;
  for (const file of [preset.file, preset.file.replace(/\.json$/, '.png')]) {
    if (fs.existsSync(file)) fs.unlinkSync(file);
  }
}

function folder() {
  ensurePresetsDir();
  return presetsDir();
}

module.exports = { list, save, remove, exists, folder, BUILTIN_DEFAULT };
