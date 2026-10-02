/**
 * Layer list: elements in front-to-back order, with groups shown as
 * collapsible parents. Supports multi-select, drag-to-reorder, rename and a
 * context menu.
 */

import { elementTypes, getElementType } from '../elements/index.js';
import { showContextMenu } from './dom.js';

const TYPE_ICONS = {
  circle_gauge: '◔', bar_gauge: '▬', text: 'T', rectangle: '▭', clock: '⏲',
  analog_clock: '🕒', image: '🖼', gif: '🎞', line_chart: '📈',
};

export class ElementList {
  constructor(root, store, actions) {
    this.root = root;
    this.store = store;
    this.actions = actions;
    this.collapsed = new Set();
    this.anchor = null;
    this.dragging = null;

    root.innerHTML = `
      <div class="panel-toolbar">
        <div class="dropdown">
          <button class="btn primary" data-act="add">＋ Add</button>
          <div class="dropdown-menu" hidden></div>
        </div>
        <button class="btn icon" data-act="up" title="Bring forward">▲</button>
        <button class="btn icon" data-act="down" title="Send backward">▼</button>
        <button class="btn icon" data-act="duplicate" title="Duplicate (Ctrl+D)">⧉</button>
        <button class="btn icon danger" data-act="delete" title="Delete (Del)">🗑</button>
      </div>
      <div class="layer-list" tabindex="0"></div>`;
    this.list = root.querySelector('.layer-list');
    this.menu = root.querySelector('.dropdown-menu');

    for (const type of elementTypes()) {
      const item = document.createElement('button');
      item.className = 'dropdown-item';
      item.textContent = `${TYPE_ICONS[type.type] || '•'}  ${type.name}`;
      item.addEventListener('click', () => {
        this.menu.hidden = true;
        actions.addElement(type.type);
      });
      this.menu.append(item);
    }

    root.querySelector('[data-act="add"]').addEventListener('click', (e) => {
      e.stopPropagation();
      this.menu.hidden = !this.menu.hidden;
    });
    document.addEventListener('click', () => { this.menu.hidden = true; });
    root.querySelector('[data-act="up"]').addEventListener('click', () => actions.move(-1));
    root.querySelector('[data-act="down"]').addEventListener('click', () => actions.move(1));
    root.querySelector('[data-act="duplicate"]').addEventListener('click', () => actions.duplicateSelection());
    root.querySelector('[data-act="delete"]').addEventListener('click', () => actions.deleteSelection());

    this.list.addEventListener('click', (e) => {
      if (e.target === this.list) store.select([]);
    });
    this.list.addEventListener('dragover', (e) => {
      if (this.dragging && e.target === this.list) e.preventDefault();
    });
    this.list.addEventListener('drop', (e) => {
      if (this.dragging && e.target === this.list) {
        e.preventDefault();
        actions.moveTo(this.dragging.members, null, this.dragging.isGroup ? undefined : null);
      }
    });

    store.on('elements', () => this.render());
    store.on('selection', () => this.updateSelection());
    store.on('element', (el) => this.updateRow(el));
    this.render();
  }

  render() {
    const { store } = this;
    this.list.innerHTML = '';
    this.rows = new Map();
    const renderedGroups = new Set();

    for (const el of store.elements) {
      if (!el.group) {
        this.list.append(this.elementRow(el, false));
        continue;
      }
      if (renderedGroups.has(el.group)) continue;
      renderedGroups.add(el.group);
      const members = store.groupMembers(el.group);
      this.list.append(this.groupRow(el.group, members));
      if (!this.collapsed.has(el.group)) {
        for (const member of members) this.list.append(this.elementRow(member, true));
      }
    }
    if (!store.elements.length) {
      const empty = document.createElement('div');
      empty.className = 'empty-hint';
      empty.textContent = 'No elements yet. Use ＋ Add to create one.';
      this.list.append(empty);
    }
    this.updateSelection();
  }

  elementRow(el, nested) {
    const row = document.createElement('div');
    row.className = `layer-row${nested ? ' nested' : ''}`;
    row.draggable = true;
    row.innerHTML = '<span class="layer-icon"></span><span class="layer-name"></span><span class="layer-type"></span><span class="layer-lock"></span>';
    row.querySelector('.layer-icon').textContent = TYPE_ICONS[el.type] || '•';
    this.rows.set(el, row);
    this.fillRow(el, row);

    row.addEventListener('click', (e) => this.onRowClick(e, el));
    row.addEventListener('dblclick', () => this.renameInline(row, el.name, (name) => {
      if (name && name !== el.name) this.store.update(el, { name });
    }));
    row.addEventListener('contextmenu', (e) => {
      e.preventDefault();
      if (!this.store.selection.includes(el)) this.store.select([el]);
      this.showMenu(e, { element: el });
    });
    this.setupDrag(row, () => ({ members: this.dragMembers(el), isGroup: false }), { target: el, group: el.group });
    return row;
  }

  groupRow(name, members) {
    const row = document.createElement('div');
    row.className = 'layer-row group';
    row.draggable = true;
    const collapsed = this.collapsed.has(name);
    row.innerHTML = `<span class="layer-toggle">${collapsed ? '▸' : '▾'}</span><span class="layer-icon">▣</span><span class="layer-name"></span><span class="layer-type">${members.length} items</span><span class="layer-lock">${members.every((m) => m.locked) ? '🔒' : ''}</span>`;
    row.querySelector('.layer-name').textContent = name;
    row.dataset.group = name;

    row.querySelector('.layer-toggle').addEventListener('click', (e) => {
      e.stopPropagation();
      if (collapsed) this.collapsed.delete(name);
      else this.collapsed.add(name);
      this.render();
    });
    row.addEventListener('click', (e) => {
      const groupMembers = this.store.groupMembers(name);
      if (e.ctrlKey) {
        const all = groupMembers.every((m) => this.store.selection.includes(m));
        const next = all
          ? this.store.selection.filter((m) => !groupMembers.includes(m))
          : [...this.store.selection, ...groupMembers.filter((m) => !this.store.selection.includes(m))];
        this.store.select(next);
      } else {
        this.store.select(groupMembers, { group: true });
      }
    });
    row.addEventListener('dblclick', () => this.renameInline(row, name, (newName) => this.actions.renameGroup(name, newName)));
    row.addEventListener('contextmenu', (e) => {
      e.preventDefault();
      this.store.select(this.store.groupMembers(name), { group: true });
      this.showMenu(e, { group: name });
    });
    this.setupDrag(row, () => ({ members: this.store.groupMembers(name), isGroup: true }), { target: members[0], group: null, isGroupRow: true });
    return row;
  }

  fillRow(el, row) {
    row.querySelector('.layer-name').textContent = el.name;
    row.querySelector('.layer-type').textContent = getElementType(el.type)?.name || el.type;
    row.querySelector('.layer-lock').textContent = el.locked ? '🔒' : '';
  }

  updateRow(el) {
    const row = this.rows?.get(el);
    if (row) this.fillRow(el, row);
  }

  updateSelection() {
    const selection = this.store.selection;
    for (const [el, row] of this.rows) row.classList.toggle('selected', selection.includes(el));
    for (const row of this.list.querySelectorAll('.layer-row.group')) {
      const members = this.store.groupMembers(row.dataset.group);
      row.classList.toggle('selected', members.length > 0 && members.every((m) => selection.includes(m)));
    }
    const first = selection[0] && this.rows.get(selection[0]);
    first?.scrollIntoView({ block: 'nearest' });
  }

  onRowClick(e, el) {
    const { store } = this;
    if (e.ctrlKey) {
      const next = store.selection.includes(el) ? store.selection.filter((s) => s !== el) : [...store.selection, el];
      store.select(next);
      this.anchor = el;
    } else if (e.shiftKey && this.anchor) {
      const a = store.elements.indexOf(this.anchor);
      const b = store.elements.indexOf(el);
      store.select(store.elements.slice(Math.min(a, b), Math.max(a, b) + 1));
    } else {
      store.select([el]);
      this.anchor = el;
    }
  }

  dragMembers(el) {
    const selection = this.store.selection;
    return selection.includes(el) ? this.store.elements.filter((s) => selection.includes(s)) : [el];
  }

  /**
   * Dropping on an element row inserts before it and joins its group (or
   * leaves groups when dropped on an ungrouped row). Dropping on a group row
   * inserts before the whole group. Dragged groups keep their membership.
   */
  setupDrag(row, getPayload, drop) {
    row.addEventListener('dragstart', (e) => {
      this.dragging = getPayload();
      e.dataTransfer.effectAllowed = 'move';
      row.classList.add('dragging');
    });
    row.addEventListener('dragend', () => {
      this.dragging = null;
      row.classList.remove('dragging');
      this.list.querySelectorAll('.drop-before').forEach((r) => r.classList.remove('drop-before'));
    });
    row.addEventListener('dragover', (e) => {
      if (!this.dragging) return;
      e.preventDefault();
      row.classList.add('drop-before');
    });
    row.addEventListener('dragleave', () => row.classList.remove('drop-before'));
    row.addEventListener('drop', (e) => {
      e.preventDefault();
      e.stopPropagation();
      row.classList.remove('drop-before');
      const payload = this.dragging;
      if (!payload) return;
      let target = drop.target;
      let group = drop.group;
      if (payload.isGroup) {
        group = undefined; // keep membership
        if (target.group) target = this.store.groupMembers(target.group)[0];
      } else if (drop.isGroupRow) {
        group = null;
      }
      this.actions.moveTo(payload.members, target, group);
    });
  }

  renameInline(row, current, commit) {
    const nameEl = row.querySelector('.layer-name');
    const input = document.createElement('input');
    input.className = 'inline-rename';
    input.value = current;
    nameEl.replaceWith(input);
    input.focus();
    input.select();
    let done = false;
    const finish = (save) => {
      if (done) return;
      done = true;
      if (save) commit(input.value.trim());
      this.render();
    };
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') finish(true);
      if (e.key === 'Escape') finish(false);
      e.stopPropagation();
    });
    input.addEventListener('blur', () => finish(true));
  }

  showMenu(e, { element, group }) {
    const { store, actions } = this;
    const selection = store.selection;
    const anyLocked = selection.some((el) => el.locked);
    const items = [];
    if (element) {
      items.push({ label: 'Rename', action: () => this.renameInline(this.rows.get(element), element.name, (name) => name && store.update(element, { name })) });
    }
    if (group) {
      const row = this.list.querySelector(`.layer-row.group[data-group="${CSS.escape(group)}"]`);
      items.push({ label: 'Rename Group', action: () => this.renameInline(row, group, (name) => actions.renameGroup(group, name)) });
    }
    items.push({ label: 'Duplicate', shortcut: 'Ctrl+D', action: () => actions.duplicateSelection() });
    if (selection.length > 1) items.push({ label: 'Group', shortcut: 'Ctrl+G', action: () => actions.groupSelection() });
    if (selection.some((el) => el.group)) items.push({ label: 'Ungroup', shortcut: 'Ctrl+Shift+G', action: () => actions.ungroupSelection() });
    items.push(anyLocked
      ? { label: 'Unlock', action: () => actions.setLocked(false) }
      : { label: 'Lock', action: () => actions.setLocked(true) });
    items.push({ separator: true });
    items.push({ label: 'Bring Forward', action: () => actions.move(-1) });
    items.push({ label: 'Send Backward', action: () => actions.move(1) });
    items.push({ separator: true });
    items.push({ label: 'Delete', shortcut: 'Del', danger: true, disabled: anyLocked, action: () => actions.deleteSelection() });
    showContextMenu(e.clientX, e.clientY, items);
  }
}
