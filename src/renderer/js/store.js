/**
 * Editor state: the theme being edited, the selection and undo/redo history.
 */

import { DISPLAY_WIDTH, DISPLAY_HEIGHT } from './constants.js';
import { normalizeElement, serializeElement, normalizeGroups } from './model.js';

const MAX_UNDO = 50;
const COALESCE_MS = 1000;

export class Store extends EventTarget {
  constructor(video) {
    super();
    this.video = video;
    this.themeName = 'Untitled Theme';
    this.themePath = null;
    this.backgroundColor = '#0f0f19';
    this.elements = [];
    this.selection = [];
    this.groupSelection = false;
    this.undoStack = [];
    this.redoStack = [];
    this.lastCheckpoint = { key: null, time: 0 };
  }

  emit(type, detail) {
    this.dispatchEvent(new CustomEvent(type, { detail }));
  }

  on(type, cb) {
    this.addEventListener(type, (e) => cb(e.detail));
  }

  // -------------------------------------------------------------------------
  // Theme load/save

  get scene() {
    return { backgroundColor: this.backgroundColor, elements: this.elements, video: this.video };
  }

  toThemeData() {
    return {
      name: this.themeName,
      background_color: this.backgroundColor,
      display_width: DISPLAY_WIDTH,
      display_height: DISPLAY_HEIGHT,
      elements: this.elements.map(serializeElement),
      video_background: this.video.toJSON(),
    };
  }

  loadTheme(data, { path = null, recordHistory = true } = {}) {
    if (recordHistory) this.checkpoint();
    this.themeName = data.name || 'Untitled';
    this.themePath = path;
    this.backgroundColor = data.background_color || '#0f0f19';
    this.elements = normalizeGroups((data.elements || []).map(normalizeElement));
    const vb = data.video_background;
    if (vb && vb.enabled && vb.video_path) this.video.load(vb.video_path, vb.fit_mode || 'fit_height');
    else this.video.clear();
    this.select([]);
    this.emit('theme');
    this.emit('elements');
  }

  setThemeName(name) {
    this.themeName = name;
    this.emit('theme');
  }

  setBackgroundColor(color) {
    this.checkpoint('background');
    this.backgroundColor = color;
    this.emit('theme');
  }

  // -------------------------------------------------------------------------
  // Elements

  /** Replace the element list (after add/remove/reorder). Call checkpoint() first. */
  setElements(elements) {
    this.elements = normalizeGroups(elements);
    this.selection = this.selection.filter((el) => this.elements.includes(el));
    this.emit('elements');
    this.emit('selection');
  }

  /** Change properties of one element, coalescing rapid edits of the same field into one undo step. */
  update(el, patch, coalesceKey = null) {
    if (el.locked && !('locked' in patch)) return;
    this.checkpoint(coalesceKey ? `${el.name}:${coalesceKey}` : null);
    Object.assign(el, patch);
    this.emit('element', el);
  }

  /** Notify that elements were mutated directly (e.g. canvas drag). */
  touched(elements) {
    for (const el of elements) this.emit('element', el);
  }

  // -------------------------------------------------------------------------
  // Selection

  select(elements, { group = false } = {}) {
    this.selection = elements.filter((el) => this.elements.includes(el));
    this.groupSelection = group && this.selection.length > 1;
    this.emit('selection');
  }

  get selected() {
    return this.selection.length === 1 ? this.selection[0] : null;
  }

  groupMembers(groupName) {
    return this.elements.filter((el) => el.group === groupName);
  }

  // -------------------------------------------------------------------------
  // Undo / redo

  snapshot() {
    return {
      elements: this.elements.map(serializeElement),
      backgroundColor: this.backgroundColor,
    };
  }

  /**
   * Save the current state for undo. Calls with the same key within a short
   * window are merged so typing or dragging a slider is one undo step.
   */
  checkpoint(key = null) {
    const now = Date.now();
    if (key && key === this.lastCheckpoint.key && now - this.lastCheckpoint.time < COALESCE_MS) {
      this.lastCheckpoint.time = now;
      return;
    }
    this.lastCheckpoint = { key, time: now };
    this.undoStack.push(this.snapshot());
    if (this.undoStack.length > MAX_UNDO) this.undoStack.shift();
    this.redoStack = [];
    this.emit('history');
  }

  restore(state) {
    this.elements = state.elements.map(normalizeElement);
    this.backgroundColor = state.backgroundColor;
    this.lastCheckpoint = { key: null, time: 0 };
    this.select([]);
    this.emit('theme');
    this.emit('elements');
    this.emit('history');
  }

  undo() {
    if (!this.undoStack.length) return false;
    this.redoStack.push(this.snapshot());
    this.restore(this.undoStack.pop());
    return true;
  }

  redo() {
    if (!this.redoStack.length) return false;
    this.undoStack.push(this.snapshot());
    this.restore(this.redoStack.pop());
    return true;
  }
}
