/** Small DOM helpers: element builder, context menu and modal dialogs. */

/** Create an element: h('div', { className: 'x', onclick }, child, 'text'). */
export function h(tag, props = {}, ...children) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(props || {})) {
    if (value == null || value === false) continue;
    if (key.startsWith('on') && typeof value === 'function') el.addEventListener(key.slice(2), value);
    else if (key === 'className') el.className = value;
    else if (key === 'dataset') Object.assign(el.dataset, value);
    else if (key === 'style' && typeof value === 'object') Object.assign(el.style, value);
    else if (key in el && typeof value !== 'string') el[key] = value;
    else el.setAttribute(key, value === true ? '' : value);
  }
  for (const child of children.flat()) {
    if (child == null || child === false) continue;
    el.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return el;
}

let openMenu = null;

function closeContextMenu() {
  openMenu?.remove();
  openMenu = null;
}

document.addEventListener('pointerdown', (e) => {
  if (openMenu && !openMenu.contains(e.target)) closeContextMenu();
});
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeContextMenu();
});
window.addEventListener('blur', closeContextMenu);

/** items: [{ label, action, shortcut, danger, disabled } | { separator: true }] */
export function showContextMenu(x, y, items) {
  closeContextMenu();
  const menu = h('div', { className: 'context-menu' });
  for (const item of items) {
    if (item.separator) {
      menu.append(h('div', { className: 'context-separator' }));
      continue;
    }
    menu.append(h('button', {
      className: `context-item${item.danger ? ' danger' : ''}`,
      disabled: !!item.disabled,
      onclick: () => {
        closeContextMenu();
        item.action();
      },
    }, h('span', {}, item.label), item.shortcut ? h('span', { className: 'shortcut' }, item.shortcut) : null));
  }
  document.body.append(menu);
  const rect = menu.getBoundingClientRect();
  menu.style.left = `${Math.min(x, window.innerWidth - rect.width - 4)}px`;
  menu.style.top = `${Math.min(y, window.innerHeight - rect.height - 4)}px`;
  openMenu = menu;
}

/**
 * Show a modal dialog. `buttons` is [{ label, value, primary }]. Resolves with
 * the clicked button's value (or null when dismissed). `onClose` can veto.
 */
export function showModal({ title, body, buttons = [{ label: 'Close', value: null }], width = 480, onOpen }) {
  return new Promise((resolve) => {
    const overlay = h('div', { className: 'modal-overlay' });
    const dialog = h('div', { className: 'modal', style: { width: `${width}px` }, role: 'dialog' });
    const close = (value) => {
      overlay.remove();
      document.removeEventListener('keydown', onKey, true);
      resolve(value);
    };
    const onKey = (e) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        close(null);
      } else if (e.key === 'Enter' && e.target.tagName !== 'TEXTAREA') {
        const primary = buttons.find((b) => b.primary);
        if (primary) {
          e.preventDefault();
          e.stopPropagation();
          close(primary.value);
        }
      }
    };
    dialog.append(
      h('div', { className: 'modal-title' }, title),
      h('div', { className: 'modal-body' }, body),
      h('div', { className: 'modal-buttons' }, buttons.map((b) => h('button', {
        className: `btn${b.primary ? ' primary' : ''}`,
        onclick: () => close(b.value),
      }, b.label))),
    );
    overlay.append(dialog);
    overlay.addEventListener('pointerdown', (e) => {
      if (e.target === overlay) close(null);
    });
    document.addEventListener('keydown', onKey, true);
    document.body.append(overlay);
    onOpen?.(dialog);
  });
}

/** Ask for a line of text. Resolves with the trimmed string or null. */
export async function promptText(title, label, initial = '') {
  const input = h('input', { type: 'text', className: 'text-input', value: initial });
  const result = await showModal({
    title,
    body: h('label', { className: 'field-stack' }, h('span', {}, label), input),
    buttons: [{ label: 'Cancel', value: null }, { label: 'OK', value: 'ok', primary: true }],
    width: 380,
    onOpen: () => {
      input.focus();
      input.select();
    },
  });
  return result === 'ok' ? input.value.trim() : null;
}
