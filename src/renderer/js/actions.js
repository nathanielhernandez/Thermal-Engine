/**
 * Editing operations on the element list, shared by the layer panel,
 * keyboard shortcuts and the application menu.
 */

import { createElement, cloneElement, uniqueName, elementBounds } from './model.js';

export class Actions {
  constructor(store) {
    this.store = store;
  }

  addElement(type) {
    const { store } = this;
    store.checkpoint();
    const el = createElement(type, store.elements);
    store.setElements([el, ...store.elements]);
    store.select([el]);
    return el;
  }

  duplicateSelection() {
    const { store } = this;
    const selection = store.selection;
    if (!selection.length) return;
    store.checkpoint();
    const all = [...store.elements];
    // Duplicated groups get a new group name so they stay independent.
    const groupRenames = new Map();
    const copies = selection.map((el) => {
      const copy = cloneElement(el);
      copy.name = uniqueName(`${el.name.replace(/_copy_\d+$/, '')}_copy`, all);
      copy.x += 20;
      copy.y += 20;
      copy.locked = false;
      if (el.group) {
        if (!groupRenames.has(el.group)) groupRenames.set(el.group, this.newGroupName(el.group));
        copy.group = groupRenames.get(el.group);
      }
      all.push(copy);
      return copy;
    });
    const insertAt = Math.min(...selection.map((el) => store.elements.indexOf(el)));
    const next = [...store.elements];
    next.splice(insertAt, 0, ...copies);
    store.setElements(next);
    store.select(copies, { group: groupRenames.size > 0 && copies.every((c) => c.group) });
  }

  deleteSelection() {
    const { store } = this;
    const selection = store.selection.filter((el) => !el.locked);
    if (!selection.length) return;
    store.checkpoint();
    store.setElements(store.elements.filter((el) => !selection.includes(el)));
    store.select([]);
  }

  newGroupName(base = 'Group') {
    const names = new Set(this.store.elements.map((el) => el.group).filter(Boolean));
    const root = base.replace(/ \d+$/, '');
    let i = 1;
    while (names.has(`${root} ${i}`)) i++;
    return `${root} ${i}`;
  }

  groupSelection() {
    const { store } = this;
    const selection = store.selection;
    if (selection.length < 2) return;
    store.checkpoint();
    const name = this.newGroupName();
    for (const el of selection) el.group = name;
    store.setElements(store.elements);
    store.select(store.groupMembers(name), { group: true });
  }

  ungroupSelection() {
    const { store } = this;
    const groups = new Set(store.selection.map((el) => el.group).filter(Boolean));
    if (!groups.size) return;
    store.checkpoint();
    for (const el of store.elements) if (groups.has(el.group)) el.group = null;
    store.setElements(store.elements);
    store.select(store.selection);
  }

  renameGroup(oldName, newName) {
    const name = newName.trim();
    if (!name || name === oldName) return;
    const { store } = this;
    store.checkpoint();
    for (const el of store.elements) if (el.group === oldName) el.group = name;
    store.setElements(store.elements);
  }

  setLocked(locked) {
    const { store } = this;
    if (!store.selection.length) return;
    store.checkpoint();
    for (const el of store.selection) el.locked = locked;
    store.touched(store.selection);
    store.emit('elements');
  }

  /** Top-level units: ungrouped elements or whole groups, in list order. */
  units() {
    const units = [];
    for (const el of this.store.elements) {
      const last = units[units.length - 1];
      if (el.group && last && last.group === el.group) last.members.push(el);
      else units.push({ group: el.group, members: [el] });
    }
    return units;
  }

  /** Move the selection one step toward the front (-1) or back (+1). */
  move(direction) {
    const { store } = this;
    const selection = store.selection;
    if (!selection.length) return;
    const units = this.units();

    // A single element inside a group moves within its group.
    if (selection.length === 1 && selection[0].group && !store.groupSelection) {
      const el = selection[0];
      const members = store.groupMembers(el.group);
      const i = members.indexOf(el);
      const j = i + direction;
      if (j < 0 || j >= members.length) return;
      store.checkpoint();
      const next = [...store.elements];
      const a = next.indexOf(members[i]);
      const b = next.indexOf(members[j]);
      [next[a], next[b]] = [next[b], next[a]];
      store.setElements(next);
      return;
    }

    const index = units.findIndex((u) => u.members.some((m) => selection.includes(m)));
    const target = index + direction;
    if (index < 0 || target < 0 || target >= units.length) return;
    store.checkpoint();
    [units[index], units[target]] = [units[target], units[index]];
    store.setElements(units.flatMap((u) => u.members));
  }

  /**
   * Move `moving` elements so they sit just before `target` (or at the end if
   * target is null). `targetGroup` is the group they should end up in.
   */
  moveTo(moving, target, targetGroup) {
    const { store } = this;
    if (!moving.length || moving.includes(target)) return;
    store.checkpoint();
    const rest = store.elements.filter((el) => !moving.includes(el));
    let index = target ? rest.indexOf(target) : rest.length;
    if (index < 0) index = rest.length;
    for (const el of moving) {
      if (targetGroup !== undefined) el.group = targetGroup;
    }
    rest.splice(index, 0, ...moving);
    store.setElements(rest);
  }

  alignSelection(mode) {
    const { store } = this;
    const units = this.alignmentUnits();
    if (units.length < 2) return;
    store.checkpoint();
    const all = this.boundsOf(units.flatMap((u) => u.members));
    for (const unit of units) {
      const b = this.boundsOf(unit.members);
      let dx = 0;
      let dy = 0;
      if (mode === 'left') dx = all.x - b.x;
      if (mode === 'hcenter') dx = all.x + all.w / 2 - (b.x + b.w / 2);
      if (mode === 'right') dx = all.x + all.w - (b.x + b.w);
      if (mode === 'top') dy = all.y - b.y;
      if (mode === 'vmiddle') dy = all.y + all.h / 2 - (b.y + b.h / 2);
      if (mode === 'bottom') dy = all.y + all.h - (b.y + b.h);
      this.offset(unit.members, dx, dy);
    }
    store.touched(store.selection);
  }

  distributeSelection(axis) {
    const { store } = this;
    const units = this.alignmentUnits();
    if (units.length < 3) return;
    store.checkpoint();
    const withBounds = units.map((u) => ({ ...u, b: this.boundsOf(u.members) }));
    const pos = axis === 'horizontal' ? 'x' : 'y';
    const size = axis === 'horizontal' ? 'w' : 'h';
    withBounds.sort((a, b) => a.b[pos] - b.b[pos]);
    const first = withBounds[0].b;
    const last = withBounds[withBounds.length - 1].b;
    const totalSize = withBounds.reduce((s, u) => s + u.b[size], 0);
    const gap = (last[pos] + last[size] - first[pos] - totalSize) / (withBounds.length - 1);
    let cursor = first[pos];
    for (const u of withBounds) {
      const delta = cursor - u.b[pos];
      this.offset(u.members, pos === 'x' ? delta : 0, pos === 'y' ? delta : 0);
      cursor += u.b[size] + gap;
    }
    store.touched(store.selection);
  }

  /** Move the whole selection so its bounds start at (x, y). */
  moveSelectionTo(x, y) {
    const { store } = this;
    const b = this.boundsOf(store.selection);
    if (!b) return;
    store.checkpoint('selection-move');
    this.offset(store.selection, x - b.x, y - b.y);
    store.touched(store.selection);
  }

  /** Selected groups move as one unit when aligning; other elements individually. */
  alignmentUnits() {
    const selection = this.store.selection;
    const units = [];
    const seenGroups = new Set();
    for (const el of selection) {
      if (el.group && this.store.groupMembers(el.group).every((m) => selection.includes(m))) {
        if (seenGroups.has(el.group)) continue;
        seenGroups.add(el.group);
        units.push({ members: this.store.groupMembers(el.group) });
      } else {
        units.push({ members: [el] });
      }
    }
    return units;
  }

  boundsOf(elements) {
    if (!elements.length) return null;
    let x1 = Infinity; let y1 = Infinity; let x2 = -Infinity; let y2 = -Infinity;
    for (const el of elements) {
      const b = elementBounds(el);
      x1 = Math.min(x1, b.x); y1 = Math.min(y1, b.y);
      x2 = Math.max(x2, b.x + b.w); y2 = Math.max(y2, b.y + b.h);
    }
    return { x: x1, y: y1, w: x2 - x1, h: y2 - y1 };
  }

  offset(elements, dx, dy) {
    for (const el of elements) {
      if (el.locked) continue;
      el.x = Math.round(el.x + dx);
      el.y = Math.round(el.y + dy);
    }
  }

}
