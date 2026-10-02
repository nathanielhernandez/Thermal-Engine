/** Preset gallery: click to load, right-click to set default or delete. */

import { getOrientation } from '../constants.js';
import { normalizeElement } from '../model.js';
import { renderScene, createRenderEnv, advanceEnv } from '../render.js';
import { h, showContextMenu, promptText } from './dom.js';

const THUMB_SIZE = 300;

/** Render preset data to a data URL for presets saved without a thumbnail. */
async function renderThumbnail(data) {
  const { width, height } = getOrientation(data.orientation);
  const canvas = new OffscreenCanvas(width, height);
  const ctx = canvas.getContext('2d', { alpha: false });
  const elements = (data.elements || []).map(normalizeElement);
  const env = advanceEnv(createRenderEnv(), elements);
  renderScene(ctx, { backgroundColor: data.background_color || '#0f0f19', elements, video: null }, env);
  const scale = THUMB_SIZE / Math.max(width, height);
  const thumb = new OffscreenCanvas(Math.round(width * scale), Math.round(height * scale));
  const tctx = thumb.getContext('2d');
  tctx.imageSmoothingQuality = 'high';
  tctx.drawImage(canvas, 0, 0, thumb.width, thumb.height);
  const blob = await thumb.convertToBlob({ type: 'image/png' });
  return URL.createObjectURL(blob);
}

export class PresetsPanel {
  constructor(root, app) {
    this.root = root;
    this.app = app;
    this.presets = [];
    this.defaultPreset = null;
    this.objectUrls = [];

    this.grid = h('div', { className: 'preset-grid' });
    root.append(
      h('div', { className: 'panel-toolbar' },
        h('button', { className: 'btn primary', onclick: () => this.createNew() }, '＋ New Preset'),
        h('button', { className: 'btn', title: 'Open the presets folder', onclick: () => window.te.presets.openFolder() }, 'Open Folder')),
      this.grid,
    );
  }

  async refresh() {
    const [presets, settings] = await Promise.all([window.te.presets.list(), window.te.settings.all()]);
    this.presets = presets;
    this.defaultPreset = settings.default_preset;
    this.objectUrls.forEach((url) => URL.revokeObjectURL(url));
    this.objectUrls = [];

    this.grid.replaceChildren(...presets.map((preset) => {
      const img = h('img', { className: 'preset-thumb', alt: '' });
      if (preset.thumbnail) img.src = preset.thumbnail;
      else renderThumbnail(preset.data).then((url) => { this.objectUrls.push(url); img.src = url; });
      const isDefault = preset.name === this.defaultPreset;
      return h('button', {
        className: `preset-card${isDefault ? ' is-default' : ''}`,
        title: isDefault ? `${preset.name} (loads on startup)` : preset.name,
        onclick: () => this.app.loadPreset(preset.data),
        oncontextmenu: (e) => {
          e.preventDefault();
          showContextMenu(e.clientX, e.clientY, [
            { label: 'Load', action: () => this.app.loadPreset(preset.data) },
            isDefault
              ? { label: 'Don’t load on startup', action: () => this.setDefault(null) }
              : { label: 'Load on startup', action: () => this.setDefault(preset.name) },
            { separator: true },
            { label: 'Delete', danger: true, disabled: preset.builtin, action: () => this.remove(preset.name) },
          ]);
        },
      }, img, h('span', { className: 'preset-name' }, isDefault ? `★ ${preset.name}` : preset.name));
    }));
  }

  defaultPresetData() {
    return this.presets.find((p) => p.name === this.defaultPreset)?.data || null;
  }

  async setDefault(name) {
    await window.te.settings.set('default_preset', name);
    await this.refresh();
  }

  async remove(name) {
    const { response } = await window.te.dialog.message({
      type: 'question',
      title: 'Delete Preset',
      message: `Delete the preset "${name}"?`,
      buttons: ['Delete', 'Cancel'],
      defaultId: 1,
      cancelId: 1,
    });
    if (response !== 0) return;
    await window.te.presets.remove(name);
    await this.refresh();
  }

  async createNew() {
    const name = await promptText('New Preset', 'Preset name', 'New Theme');
    if (!name) return;
    if (this.presets.some((p) => p.name === name)) {
      await window.te.dialog.message({ type: 'warning', title: 'Name Exists', message: `A preset named "${name}" already exists. Please choose a different name.` });
      return;
    }
    const data = {
      name,
      background_color: '#000000',
      // New presets start in the current orientation, which usually matches how the panel is mounted.
      orientation: this.app.store.orientation,
      display_width: getOrientation(this.app.store.orientation).width,
      display_height: getOrientation(this.app.store.orientation).height,
      elements: [],
      video_background: { video_path: '', fit_mode: 'fit_height', enabled: false },
    };
    await window.te.presets.save(name, data, null);
    await this.refresh();
    this.app.loadPreset(data);
  }
}
