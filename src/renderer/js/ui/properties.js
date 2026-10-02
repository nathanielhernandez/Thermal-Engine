/**
 * Properties panel. Builds its form from property-schema.js for the selected
 * element, or shows alignment tools when several elements are selected.
 */

import { DATA_SOURCES_CATEGORIZED } from '../constants.js';
import { getElementType } from '../elements/index.js';
import { loadImageSize } from '../media.js';
import { SECTIONS, fieldApplies, fieldVisible } from './property-schema.js';
import { h } from './dom.js';
import { editGradient, gradientCss } from './gradient-editor.js';

let fontFamilies = null;

/** System font families via the Local Font Access API (falls back to common fonts). */
async function loadFontFamilies() {
  if (fontFamilies) return fontFamilies;
  const fallback = ['Arial', 'Bahnschrift', 'Calibri', 'Cambria', 'Consolas', 'Courier New', 'Georgia', 'Impact', 'Segoe UI', 'Tahoma', 'Times New Roman', 'Trebuchet MS', 'Verdana'];
  try {
    const fonts = await window.queryLocalFonts();
    fontFamilies = [...new Set(fonts.map((f) => f.family))].sort((a, b) => a.localeCompare(b));
  } catch {
    fontFamilies = fallback;
  }
  if (!fontFamilies.length) fontFamilies = fallback;
  const list = document.getElementById('font-families');
  list.replaceChildren(...fontFamilies.map((f) => h('option', { value: f })));
  return fontFamilies;
}

export class PropertiesPanel {
  constructor(root, store, actions) {
    this.root = root;
    this.store = store;
    this.actions = actions;
    this.element = null;
    this.bindings = []; // { field, row, refresh() }

    store.on('selection', () => this.render());
    store.on('elements', () => this.render());
    store.on('element', (el) => {
      if (el === this.element) this.refresh();
      else if (this.store.selection.includes(el)) this.refreshMulti?.();
    });
    loadFontFamilies();
    this.render();
  }

  render() {
    const selection = this.store.selection;
    this.root.replaceChildren();
    this.bindings = [];
    this.refreshMulti = null;
    this.element = selection.length === 1 ? selection[0] : null;

    if (selection.length > 1) {
      this.renderMulti(selection);
    } else if (this.element) {
      this.renderElement(this.element);
    } else {
      this.root.append(h('div', { className: 'empty-hint' }, 'Select an element to edit its properties.'));
    }
  }

  // -------------------------------------------------------------------------
  // Single element

  renderElement(el) {
    const typeName = getElementType(el.type)?.name || el.type;
    this.root.append(h('div', { className: 'props-header' }, typeName));

    for (const section of SECTIONS) {
      const fields = section.fields.filter((f) => fieldApplies(f, el));
      if (!fields.length) continue;
      const body = h('div', { className: 'section-body' });
      const sectionEl = h('section', { className: 'props-section' }, h('h3', {}, section.title), body);
      const rows = fields.map((field) => {
        const row = this.buildField(field, el);
        body.append(row);
        return { field, row };
      });
      this.bindings.push({ section: sectionEl, rows });
      this.root.append(sectionEl);
    }
    this.refresh();
  }

  /** Update visibility, enabled state and values from the element (skipping focused inputs). */
  refresh() {
    const el = this.element;
    if (!el) return;
    for (const { section, rows } of this.bindings) {
      let anyVisible = false;
      for (const { field, row } of rows) {
        const visible = fieldVisible(field, el);
        row.hidden = !visible;
        anyVisible ||= visible;
        row.update?.();
        const lockable = !(field.kind === 'checkbox' && field.key === 'locked');
        row.classList.toggle('disabled', el.locked && lockable);
        row.querySelectorAll('input, select, button').forEach((input) => {
          input.disabled = el.locked && lockable;
        });
      }
      section.hidden = !anyVisible;
    }
  }

  set(key, value, coalesce = true) {
    const el = this.element;
    if (!el) return;
    const patch = { [key]: value };

    // Keep image proportions when editing one dimension.
    if (el.type === 'image' && el.scale_proportionally && el.aspect_ratio > 0) {
      if (key === 'width') patch.height = Math.max(1, Math.round(value / el.aspect_ratio));
      if (key === 'height') patch.width = Math.max(1, Math.round(value * el.aspect_ratio));
    }
    this.store.update(el, patch, coalesce ? key : null);
  }

  row(label, ...controls) {
    return h('div', { className: 'field' }, h('label', { className: 'field-label' }, label || ''), h('div', { className: 'field-control' }, ...controls));
  }

  buildField(field, el) {
    switch (field.kind) {
      case 'text': return this.textField(field, el);
      case 'number': return this.numberField(field, el);
      case 'pair': return this.pairField(field, el);
      case 'checkbox': return this.checkboxField(field, el);
      case 'select': return this.selectField(field, el);
      case 'color': return this.colorField(field, el);
      case 'font': return this.fontField(field, el);
      case 'align': return this.alignField(field, el);
      case 'source': return this.sourceField(field, el);
      case 'file': return this.fileField(field, el);
      case 'gradient': return this.gradientField(field, el);
      case 'subheading': return h('div', { className: 'subheading' }, field.label);
      default: return h('div');
    }
  }

  textField(field, el) {
    const input = h('input', { type: 'text', className: 'text-input', oninput: () => this.set(field.key, input.value) });
    const row = this.row(field.label, input);
    row.update = () => { if (document.activeElement !== input) input.value = el[field.key] ?? ''; };
    return row;
  }

  numberInput(field, el) {
    const input = h('input', {
      type: 'number',
      className: 'number-input',
      min: field.min,
      max: field.max,
      step: field.step || 1,
      oninput: () => {
        const v = Number(input.value);
        if (input.value !== '' && Number.isFinite(v)) this.set(field.key, v);
      },
    });
    const wrap = h('div', { className: 'number-wrap' }, field.prefix ? h('span', { className: 'affix' }, field.prefix) : null, input, field.suffix ? h('span', { className: 'affix' }, field.suffix) : null);
    wrap.update = () => {
      if (document.activeElement !== input) {
        const v = Number(el[field.key]) || 0;
        input.value = Number.isInteger(v) ? v : v.toFixed(1);
      }
    };
    return wrap;
  }

  numberField(field, el) {
    const wrap = this.numberInput(field, el);
    const row = this.row(field.label, wrap);
    row.update = wrap.update;
    return row;
  }

  pairField(field, el) {
    const inputs = field.fields.map((f) => this.numberInput(f, el));
    const row = this.row(field.label, h('div', { className: 'pair' }, inputs));
    row.update = () => inputs.forEach((i) => i.update());
    return row;
  }

  checkboxField(field, el) {
    const input = h('input', { type: 'checkbox', onchange: () => this.set(field.key, input.checked, false) });
    const row = this.row('', h('label', { className: 'check' }, input, h('span', {}, field.label)));
    row.update = () => { input.checked = !!el[field.key]; };
    return row;
  }

  selectField(field, el) {
    const select = h('select', { className: 'select', onchange: () => this.set(field.key, select.value, false) },
      field.options.map(([value, label]) => h('option', { value }, label)));
    const row = this.row(field.label, select);
    row.update = () => { select.value = el[field.key]; };
    return row;
  }

  colorField(field, el) {
    const color = h('input', { type: 'color', className: 'color-input', oninput: () => this.set(field.key, color.value) });
    const controls = [color];
    let opacity = null;
    let opacityLabel = null;
    if (field.opacityKey) {
      opacity = h('input', { type: 'range', min: 0, max: 100, className: 'range', oninput: () => {
        opacityLabel.textContent = `${opacity.value}%`;
        this.set(field.opacityKey, Number(opacity.value));
      } });
      opacityLabel = h('span', { className: 'range-value' });
      controls.push(opacity, opacityLabel);
    }
    const row = this.row(field.label, ...controls);
    row.update = () => {
      color.value = String(el[field.key] || '#000000').slice(0, 7);
      if (opacity && document.activeElement !== opacity) {
        opacity.value = el[field.opacityKey];
        opacityLabel.textContent = `${el[field.opacityKey]}%`;
      }
    };
    return row;
  }

  fontField(field, el) {
    const p = field.prefix || '';
    const keys = { family: `${p}font_family`, size: `${p}font_size`, bold: `${p}font_bold`, italic: `${p}font_italic` };
    const family = h('input', { type: 'text', className: 'text-input', list: 'font-families', oninput: () => this.set(keys.family, family.value) });
    const size = h('input', { type: 'number', className: 'number-input small', min: 4, max: 400, oninput: () => {
      const v = Number(size.value);
      if (v > 0) this.set(keys.size, v);
    } });
    const bold = h('button', { className: 'btn toggle', title: 'Bold', onclick: () => this.set(keys.bold, !el[keys.bold], false) }, h('b', {}, 'B'));
    const italic = h('button', { className: 'btn toggle', title: 'Italic', onclick: () => this.set(keys.italic, !el[keys.italic], false) }, h('i', {}, 'I'));
    const row = h('div', { className: 'field-group' },
      this.row(field.label, family),
      this.row('Size', h('div', { className: 'pair' }, size, bold, italic)));
    row.update = () => {
      if (document.activeElement !== family) {
        family.value = el[keys.family];
        family.style.fontFamily = `"${el[keys.family]}", sans-serif`;
      }
      if (document.activeElement !== size) size.value = el[keys.size];
      bold.classList.toggle('active', !!el[keys.bold]);
      italic.classList.toggle('active', !!el[keys.italic]);
    };
    return row;
  }

  alignField(field, el) {
    const buttons = ['left', 'center', 'right'].map((value) => h('button', {
      className: 'btn toggle',
      title: `Align ${value}`,
      dataset: { value },
      onclick: () => this.set(field.key, value, false),
    }, { left: '⇤', center: '↔', right: '⇥' }[value]));
    const row = this.row(field.label, h('div', { className: 'button-row' }, buttons));
    row.update = () => buttons.forEach((b) => b.classList.toggle('active', el[field.key] === b.dataset.value));
    return row;
  }

  sourceField(field, el) {
    const select = h('select', { className: 'select', onchange: () => {
      this.set(field.key, select.value, false);
      this.refresh();
    } }, Object.entries(DATA_SOURCES_CATEGORIZED).map(([category, sources]) => h('optgroup', { label: category },
      sources.map(([id, name, , symbol]) => h('option', { value: id }, `${name} (${symbol})`)))));
    const row = this.row(field.label, select);
    row.update = () => { select.value = el[field.key]; };
    return row;
  }

  fileField(field, el) {
    const label = h('span', { className: 'file-name' });
    const browse = h('button', { className: 'btn', onclick: () => this.browse(field, el) }, 'Browse…');
    const clear = h('button', { className: 'btn icon', title: 'Clear', onclick: () => this.set(field.key, '', false) }, '✕');
    const row = this.row(field.label, h('div', { className: 'file-row' }, label, browse, clear));
    row.update = () => {
      const value = el[field.key] || '';
      label.textContent = value ? value.split(/[\\/]/).pop() : 'None';
      label.title = value;
    };
    return row;
  }

  async browse(field, el) {
    const filePath = await window.te.files.chooseMedia(field.media);
    if (!filePath) return;
    const patch = { [field.key]: filePath };
    if (field.media === 'image') {
      try {
        const { width, height } = await loadImageSize(filePath);
        patch.aspect_ratio = width / height;
        if (el.scale_proportionally) patch.height = Math.max(1, Math.round(el.width / patch.aspect_ratio));
      } catch {
        // Unreadable image: the element shows an error placeholder.
      }
    }
    this.store.update(el, patch);
  }

  gradientField(field, el) {
    const preview = h('button', { className: 'gradient-preview', title: 'Edit gradient', onclick: async () => {
      const stops = await editGradient(el[field.key]);
      if (stops) this.set(field.key, stops, false);
    } });
    const row = this.row(field.label, preview);
    row.update = () => { preview.style.background = gradientCss(el[field.key]); };
    return row;
  }

  // -------------------------------------------------------------------------
  // Multiple elements

  renderMulti(selection) {
    const { actions, store } = this;
    const groups = new Set(selection.map((el) => el.group));
    const singleGroup = groups.size === 1 && [...groups][0] ? [...groups][0] : null;

    this.root.append(h('div', { className: 'props-header' }, singleGroup ? `Group: ${singleGroup}` : `${selection.length} elements selected`));

    const general = h('div', { className: 'section-body' });
    if (singleGroup) {
      const name = h('input', { type: 'text', className: 'text-input', value: singleGroup, onchange: () => actions.renameGroup(singleGroup, name.value) });
      general.append(this.row('Group name', name));
    }
    const x = h('input', { type: 'number', className: 'number-input' });
    const y = h('input', { type: 'number', className: 'number-input' });
    const onMove = () => actions.moveSelectionTo(Number(x.value) || 0, Number(y.value) || 0);
    x.addEventListener('input', onMove);
    y.addEventListener('input', onMove);
    general.append(this.row('Position', h('div', { className: 'pair' },
      h('div', { className: 'number-wrap' }, h('span', { className: 'affix' }, 'X'), x),
      h('div', { className: 'number-wrap' }, h('span', { className: 'affix' }, 'Y'), y))));
    this.refreshMulti = () => {
      const b = actions.boundsOf(store.selection);
      if (!b) return;
      if (document.activeElement !== x) x.value = Math.round(b.x);
      if (document.activeElement !== y) y.value = Math.round(b.y);
    };
    this.refreshMulti();

    const align = (mode, label, title) => h('button', { className: 'btn icon', title, onclick: () => actions.alignSelection(mode) }, label);
    const alignment = h('div', { className: 'section-body' },
      this.row('Horizontal', h('div', { className: 'button-row' },
        align('left', '⇤', 'Align left'), align('hcenter', '↔', 'Align centers horizontally'), align('right', '⇥', 'Align right'))),
      this.row('Vertical', h('div', { className: 'button-row' },
        align('top', '⤒', 'Align top'), align('vmiddle', '↕', 'Align middles vertically'), align('bottom', '⤓', 'Align bottom'))),
      this.row('Distribute', h('div', { className: 'button-row' },
        h('button', { className: 'btn', onclick: () => actions.distributeSelection('horizontal') }, 'Horizontally'),
        h('button', { className: 'btn', onclick: () => actions.distributeSelection('vertical') }, 'Vertically'))));

    const anyLocked = selection.some((el) => el.locked);
    const arrange = h('div', { className: 'section-body' }, h('div', { className: 'button-row wrap' },
      singleGroup
        ? h('button', { className: 'btn', onclick: () => actions.ungroupSelection() }, 'Ungroup')
        : h('button', { className: 'btn', onclick: () => actions.groupSelection() }, 'Group'),
      h('button', { className: 'btn', onclick: () => actions.setLocked(!anyLocked) }, anyLocked ? 'Unlock' : 'Lock'),
      h('button', { className: 'btn', onclick: () => actions.duplicateSelection() }, 'Duplicate'),
      h('button', { className: 'btn danger', onclick: () => actions.deleteSelection() }, 'Delete')));

    this.root.append(
      h('section', { className: 'props-section' }, h('h3', {}, 'Selection'), general),
      h('section', { className: 'props-section' }, h('h3', {}, 'Align'), alignment),
      h('section', { className: 'props-section' }, h('h3', {}, 'Arrange'), arrange),
    );
  }
}
