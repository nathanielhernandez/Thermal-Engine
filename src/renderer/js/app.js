/**
 * Renderer entry point: wires the store, engine and UI panels together and
 * handles commands from the menu and keyboard.
 */

import { Store } from './store.js';
import { Engine } from './engine.js';
import { Actions } from './actions.js';
import { VideoBackground, onMediaLoaded, resetGifPlayback } from './media.js';
import { CanvasView } from './ui/canvas-view.js';
import { ElementList } from './ui/element-list.js';
import { PropertiesPanel } from './ui/properties.js';
import { PresetsPanel } from './ui/presets-panel.js';
import { showPreferences, showDiagnostics, showHwinfoHelp } from './ui/dialogs.js';

const te = window.te;
const $ = (selector) => document.querySelector(selector);

class App {
  constructor() {
    this.video = new VideoBackground();
    this.store = new Store(this.video);
    this.actions = new Actions(this.store);
    this.engine = new Engine(this.store, {
      sendFrame: (jpeg) => te.display.sendFrame(jpeg),
      onFrame: () => this.view.paint(),
    });
    this.settings = {};
    this.displayStatus = { connected: false };
    this.sensorStatus = null;
    this.savedPresetName = null;
    this.statusTimer = null;
  }

  async init() {
    this.settings = await te.settings.all();
    this.engine.setTargetFps(this.settings.target_fps || 30);
    this.engine.setJpegQuality(this.settings.jpeg_quality ?? 80);

    this.view = new CanvasView($('#preview'), this.store, this.engine);
    this.elementList = new ElementList($('#elements-panel'), this.store, this.actions);
    this.properties = new PropertiesPanel($('#properties-panel'), this.store, this.actions);
    this.presets = new PresetsPanel($('#presets-panel'), this);

    this.bindToolbar();
    this.bindTabs();
    this.bindShortcuts();
    this.bindStoreEvents();
    this.bindMainProcess();

    await this.presets.refresh();
    const startup = this.presets.defaultPresetData() || this.presets.presets.find((p) => p.name === 'Default')?.data;
    if (startup) {
      this.store.loadTheme(startup, { recordHistory: false });
      this.savedPresetName = this.presets.defaultPreset;
    }

    this.engine.setVisible(await te.app.isVisible());
    this.engine.start();
    this.updateDisplayStatus(await te.display.status());
  }

  // -------------------------------------------------------------------------
  // Wiring

  bindStoreEvents() {
    const { store } = this;
    const redraw = () => this.engine.invalidate();
    store.on('elements', redraw);
    store.on('element', redraw);
    store.on('selection', redraw);
    store.on('theme', () => {
      redraw();
      this.syncToolbar();
    });
    store.on('history', () => this.syncToolbar());
    onMediaLoaded(redraw);
    this.video.onChange = () => {
      if (this.video.error) this.status(this.video.error, 6000);
      this.syncToolbar();
      redraw();
    };
  }

  bindMainProcess() {
    te.sensors.onUpdate((data, status) => {
      this.engine.setSensors(data);
      this.updateSensorStatus(status);
    });
    te.display.onStatus((status) => this.updateDisplayStatus(status));
    te.app.onMetrics((metrics) => this.updateMetrics(metrics));
    te.app.onMenu((command, arg) => this.run(command, arg));
    te.app.onVisibility((visible) => this.engine.setVisible(visible));
    te.app.onResume(() => {
      resetGifPlayback();
      this.video.resume();
      this.engine.setTargetFps(this.engine.targetFps);
    });
  }

  bindTabs() {
    for (const tab of document.querySelectorAll('.tab')) {
      tab.addEventListener('click', () => {
        document.querySelectorAll('.tab').forEach((t) => t.classList.toggle('active', t === tab));
        document.querySelectorAll('.tab-panel').forEach((p) => { p.hidden = p.id !== tab.dataset.panel; });
      });
    }
  }

  bindToolbar() {
    const { store } = this;
    $('#theme-name').addEventListener('input', (e) => store.setThemeName(e.target.value));
    $('#save-btn').addEventListener('click', () => this.run('quick-save'));
    $('#bg-color').addEventListener('input', (e) => store.setBackgroundColor(e.target.value));
    $('#video-btn').addEventListener('click', () => this.chooseVideo());
    $('#video-fit').addEventListener('change', (e) => {
      if (this.video.enabled) this.video.fitMode = e.target.value;
      this.engine.invalidate();
    });
    $('#video-clear').addEventListener('click', () => {
      this.video.clear();
      this.syncToolbar();
      this.engine.invalidate();
      this.status('Video background cleared');
    });
    $('#display-chip').addEventListener('click', () => this.toggleConnection());
    $('#undo-btn').addEventListener('click', () => this.run('undo'));
    $('#redo-btn').addEventListener('click', () => this.run('redo'));
    $('#sensor-chip').addEventListener('click', () => (this.sensorStatus?.hwinfo ? showDiagnostics() : showHwinfoHelp()));
    $('#hwinfo-help').addEventListener('click', () => showHwinfoHelp());
    $('#hwinfo-dismiss').addEventListener('click', () => { $('#hwinfo-banner').hidden = true; this.hwinfoBannerDismissed = true; });
  }

  syncToolbar() {
    const { store, video } = this;
    const nameInput = $('#theme-name');
    if (document.activeElement !== nameInput) nameInput.value = store.themeName;
    $('#bg-color').value = store.backgroundColor.slice(0, 7);
    const videoName = video.path ? video.path.split(/[\\/]/).pop() : 'None';
    $('#video-btn').textContent = videoName.length > 16 ? `${videoName.slice(0, 14)}…` : videoName;
    $('#video-btn').title = video.path || 'Choose a video background';
    $('#video-fit').value = video.fitMode;
    $('#video-fit').disabled = !video.enabled;
    $('#video-clear').disabled = !video.enabled;
    $('#undo-btn').disabled = !store.undoStack.length;
    $('#redo-btn').disabled = !store.redoStack.length;
    te.app.setTitle(`Thermal Engine - ${store.themeName}`);
  }

  bindShortcuts() {
    document.addEventListener('keydown', (e) => {
      const target = e.target;
      const typing = target.matches?.('input:not([type=checkbox]):not([type=range]):not([type=color]), textarea, select');
      const ctrl = e.ctrlKey || e.metaKey;
      const key = e.key.toLowerCase();
      let command = null;

      if (ctrl && key === 's') command = e.shiftKey ? 'save-theme-as' : 'quick-save';
      else if (ctrl && key === 'o') command = 'open-theme';
      else if (ctrl && key === 'n') command = 'new-theme';
      else if (!typing && ctrl && (key === 'y' || (key === 'z' && e.shiftKey))) command = 'redo';
      else if (!typing && ctrl && key === 'z') command = 'undo';
      else if (!typing && ctrl && key === 'd') command = 'duplicate';
      else if (!typing && ctrl && key === 'g') command = e.shiftKey ? 'ungroup' : 'group';
      else if (!typing && ctrl && key === 'a') command = 'select-all';
      else if (!typing && e.key === 'Delete') command = 'delete';
      else if (!typing && e.key === 'Escape') command = 'deselect';
      else if (!typing && e.key.startsWith('Arrow') && target !== $('#preview') && this.store.selection.length) {
        // Arrow keys nudge the selection unless a text field has focus.
        this.view.onKeyDown(e);
        return;
      }

      if (command) {
        e.preventDefault();
        this.run(command);
      }
    });
  }

  // -------------------------------------------------------------------------
  // Commands

  async run(command, arg) {
    const { store, actions } = this;
    try {
      switch (command) {
        case 'new-theme': return this.newTheme();
        case 'open-theme': return this.openTheme();
        case 'quick-save': return this.quickSave();
        case 'save-theme-as': return this.saveThemeAs();
        case 'export-image': return this.exportImage();
        case 'open-presets-folder': return te.presets.openFolder();
        case 'undo': if (store.undo()) this.status('Undo', 1500); return undefined;
        case 'redo': if (store.redo()) this.status('Redo', 1500); return undefined;
        case 'duplicate': return actions.duplicateSelection();
        case 'delete': return actions.deleteSelection();
        case 'group': return actions.groupSelection();
        case 'ungroup': return actions.ungroupSelection();
        case 'select-all': return store.select([...store.elements]);
        case 'deselect': return store.select([]);
        case 'set-fps': return this.setTargetFps(arg);
        case 'diagnose-sensors': return showDiagnostics();
        case 'preferences': return this.preferences();
        default: return undefined;
      }
    } catch (err) {
      console.error(`[Command] ${command} failed:`, err);
      await te.dialog.message({ type: 'error', title: 'Error', message: err.message || String(err) });
      return undefined;
    }
  }

  newTheme() {
    this.store.loadTheme({ name: 'Untitled Theme', background_color: '#0f0f19', elements: [] });
    this.savedPresetName = null;
    this.status('New theme created');
  }

  async openTheme() {
    const result = await te.files.openTheme();
    if (!result) return;
    this.store.loadTheme(result.data, { path: result.path });
    this.savedPresetName = null;
    this.status(`Opened: ${result.path}`);
  }

  loadPreset(data) {
    this.store.loadTheme(data);
    this.savedPresetName = data.name;
    this.status(`Loaded preset: ${data.name}`);
  }

  /** Save to the presets folder under the theme name, with a thumbnail. */
  async quickSave() {
    const name = this.store.themeName.trim();
    if (!name) {
      this.status('Please enter a theme name first');
      $('#theme-name').focus();
      return;
    }
    if (name === 'Default' || (name !== this.savedPresetName && await te.presets.exists(name))) {
      const { response } = await te.dialog.message({
        type: 'question',
        title: 'Overwrite Preset',
        message: `A preset named "${name}" already exists. Overwrite it?`,
        buttons: ['Overwrite', 'Cancel'],
        defaultId: 1,
        cancelId: 1,
      });
      if (response !== 0) return;
    }
    const thumbnail = await this.engine.snapshotPng(300);
    await te.presets.save(name, this.store.toThemeData(), thumbnail);
    this.savedPresetName = name;
    await this.presets.refresh();
    this.status(`Saved: ${name}`);
  }

  async saveThemeAs() {
    const filePath = await te.files.saveThemeAs(this.store.themeName, this.store.toThemeData());
    if (!filePath) return;
    this.store.themePath = filePath;
    this.status(`Saved: ${filePath}`);
  }

  async exportImage() {
    const png = await this.engine.snapshotPng();
    const filePath = await te.files.exportImage(this.store.themeName, png);
    if (filePath) this.status(`Exported: ${filePath}`);
  }

  async chooseVideo() {
    const filePath = await te.files.chooseMedia('video');
    if (!filePath) return;
    this.video.load(filePath, $('#video-fit').value);
    this.syncToolbar();
    this.status(`Video background: ${filePath.split(/[\\/]/).pop()}`);
  }

  async setTargetFps(fps) {
    if (fps === 60 && !this.settings.suppress_60fps_warning) {
      const { response, checkboxChecked } = await te.dialog.message({
        type: 'warning',
        title: 'Performance Warning',
        message: '60 FPS mode',
        detail: 'Running at 60 FPS noticeably increases CPU usage and can raise temperatures. 30 FPS is smooth on most systems.',
        buttons: ['Use 60 FPS', 'Cancel'],
        defaultId: 1,
        cancelId: 1,
        checkboxLabel: "Don't show this warning again",
      });
      if (response !== 0) {
        te.app.refreshMenu();
        return;
      }
      if (checkboxChecked) await te.settings.set('suppress_60fps_warning', true);
    }
    await te.settings.set('target_fps', fps);
    this.settings = await te.settings.all();
    this.engine.setTargetFps(fps);
    this.status(`Frame rate set to ${fps} FPS`);
  }

  async preferences() {
    const updated = await showPreferences();
    if (!updated) return;
    this.settings = updated;
    this.engine.setJpegQuality(updated.jpeg_quality ?? 80);
    this.status('Settings saved', 2000);
  }

  async toggleConnection() {
    if (this.displayStatus.connected) await te.display.disconnect();
    else if (!(await te.display.connect())) {
      const status = await te.display.status();
      this.status(status.error || 'Display not found', 6000);
    }
  }

  // -------------------------------------------------------------------------
  // Status bar

  status(message, timeout = 4000) {
    const el = $('#status-message');
    el.textContent = message;
    clearTimeout(this.statusTimer);
    if (timeout) this.statusTimer = setTimeout(() => { el.textContent = 'Ready'; }, timeout);
  }

  updateDisplayStatus(status) {
    const wasConnected = this.displayStatus.connected;
    this.displayStatus = status;
    this.engine.setConnected(status.connected);
    const chip = $('#display-chip');
    chip.className = `chip clickable ${status.connected ? 'ok' : status.reconnecting ? 'warn' : ''}`;
    chip.textContent = status.connected ? 'Display connected' : status.reconnecting ? 'Display: searching…' : 'Display disconnected';
    chip.title = `${status.connected ? 'Click to disconnect' : 'Click to connect'}${status.error ? `
${status.error}` : ''}`;
    if (status.connected && !wasConnected) this.status('Connected to display - sending frames');
    if (!status.connected && wasConnected) this.status(status.wantConnected ? 'Display disconnected - reconnecting…' : 'Disconnected');
  }

  updateSensorStatus(status) {
    const changed = !this.sensorStatus || this.sensorStatus.hwinfo !== status.hwinfo;
    this.sensorStatus = status;
    if (!changed) return;
    const chip = $('#sensor-chip');
    chip.className = `chip clickable ${status.hwinfo ? 'ok' : 'warn'}`;
    chip.textContent = status.hwinfo ? 'HWiNFO connected' : 'HWiNFO not detected';
    chip.title = status.hwinfo ? 'Click for sensor diagnostics' : (status.error || 'Click for setup help');
    $('#hwinfo-banner').hidden = status.hwinfo || this.hwinfoBannerDismissed;
  }

  updateMetrics({ sent, dropped, cpu, memoryMB }) {
    const target = this.engine.targetFps;
    const indicator = $('#perf-indicator');
    const label = $('#perf-label');
    const mem = `RAM ${memoryMB.toFixed(0)} MB`;
    if (!this.displayStatus.connected) {
      indicator.className = 'perf-dot';
      label.textContent = `FPS -- | CPU ${cpu.toFixed(1)}% | ${mem}`;
      return;
    }
    const ratio = sent / target;
    indicator.className = `perf-dot ${ratio >= 0.9 ? 'good' : ratio >= 0.7 ? 'moderate' : 'bad'}`;
    label.textContent = `FPS ${sent}/${target} | CPU ${cpu.toFixed(1)}% | ${mem}${dropped ? ` | dropped ${dropped}` : ''}`;
  }
}

const app = new App();
window.addEventListener('DOMContentLoaded', () => {
  app.init().catch((err) => {
    console.error('[App] Startup failed:', err);
    document.body.prepend(Object.assign(document.createElement('pre'), { className: 'fatal', textContent: `Startup failed:\n${err.stack || err}` }));
  });
});
