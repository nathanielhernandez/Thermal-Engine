/**
 * Editor preview: shows the rendered frame scaled to fit, draws selection
 * boxes, and handles selecting, dragging, resizing and nudging elements.
 */

import { elementBounds, isRadial } from '../model.js';

const HANDLE_SIZE = 10;
const SELECTION_COLOR = 'rgb(0, 150, 255)';
const MIN_SIZE = 20;
const MIN_RADIUS = 30;

function unionBounds(elements) {
  if (!elements.length) return null;
  let x1 = Infinity; let y1 = Infinity; let x2 = -Infinity; let y2 = -Infinity;
  for (const el of elements) {
    const b = elementBounds(el);
    x1 = Math.min(x1, b.x); y1 = Math.min(y1, b.y);
    x2 = Math.max(x2, b.x + b.w); y2 = Math.max(y2, b.y + b.h);
  }
  return { x: x1, y: y1, w: x2 - x1, h: y2 - y1 };
}

export class CanvasView {
  constructor(canvas, store, engine) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.store = store;
    this.engine = engine;
    this.scale = 0.5;
    this.op = null; // active drag/resize operation

    new ResizeObserver(() => this.layout()).observe(canvas.parentElement);
    canvas.addEventListener('pointerdown', (e) => this.onPointerDown(e));
    canvas.addEventListener('pointermove', (e) => this.onPointerMove(e));
    canvas.addEventListener('pointerup', (e) => this.onPointerUp(e));
    canvas.addEventListener('pointercancel', (e) => this.onPointerUp(e));
    canvas.addEventListener('keydown', (e) => this.onKeyDown(e));
    store.on('theme', () => {
      const { width, height } = store.canvasSize;
      if (width !== this.size?.width || height !== this.size?.height) this.layout();
    });
    this.layout();
  }

  layout() {
    const wrap = this.canvas.parentElement;
    const available = Math.max(200, wrap.clientWidth - 32);
    const availableH = Math.max(100, wrap.clientHeight - 32);
    this.size = this.store.canvasSize;
    const { width, height } = this.size;
    this.scale = Math.min(1, available / width, availableH / height);
    const cssW = Math.round(width * this.scale);
    const cssH = Math.round(height * this.scale);
    const dpr = window.devicePixelRatio || 1;
    this.canvas.style.width = `${cssW}px`;
    this.canvas.style.height = `${cssH}px`;
    this.canvas.width = Math.round(cssW * dpr);
    this.canvas.height = Math.round(cssH * dpr);
    this.paint();
  }

  /** Paint the latest engine frame plus selection overlays. */
  paint() {
    const { ctx } = this;
    const dpr = window.devicePixelRatio || 1;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.imageSmoothingQuality = 'high';
    const { width, height } = this.size;
    // The engine canvas is resized when orientation changes; skip until it catches up.
    if (this.engine.canvas.width !== width || this.engine.canvas.height !== height) return;
    ctx.drawImage(this.engine.canvas, 0, 0, width * this.scale, height * this.scale);

    const selection = this.store.selection;
    if (selection.length > 1) {
      this.drawSelectionBox(unionBounds(selection));
    } else if (selection.length === 1) {
      this.drawSelectionBox(elementBounds(selection[0]), selection[0].locked);
    }
  }

  toView(b) {
    return { x: b.x * this.scale, y: b.y * this.scale, w: b.w * this.scale, h: b.h * this.scale };
  }

  drawSelectionBox(bounds, locked = false) {
    const { ctx } = this;
    const b = this.toView(bounds);
    ctx.save();
    ctx.strokeStyle = locked ? 'rgb(150, 150, 150)' : SELECTION_COLOR;
    ctx.lineWidth = 2;
    ctx.setLineDash([6, 4]);
    ctx.strokeRect(b.x, b.y, b.w, b.h);
    if (!locked) {
      ctx.fillStyle = SELECTION_COLOR;
      for (const [hx, hy] of this.handlePoints(b)) {
        ctx.fillRect(hx - HANDLE_SIZE / 2, hy - HANDLE_SIZE / 2, HANDLE_SIZE, HANDLE_SIZE);
      }
    }
    ctx.restore();
  }

  handlePoints(b) {
    return [[b.x, b.y], [b.x + b.w, b.y], [b.x, b.y + b.h], [b.x + b.w, b.y + b.h]];
  }

  /** Which corner handle ('tl','tr','bl','br') is under the view point, if any. */
  handleAt(bounds, px, py) {
    const names = ['tl', 'tr', 'bl', 'br'];
    const points = this.handlePoints(this.toView(bounds));
    for (let i = 0; i < 4; i++) {
      const [hx, hy] = points[i];
      if (Math.abs(px - hx) <= HANDLE_SIZE && Math.abs(py - hy) <= HANDLE_SIZE) return names[i];
    }
    return null;
  }

  /** Front-most element under a display-space point (index 0 is in front). */
  elementAt(dx, dy) {
    return this.store.elements.find((el) => {
      if (isRadial(el)) return Math.hypot(dx - el.x, dy - el.y) <= el.radius;
      const b = elementBounds(el);
      return dx >= b.x && dx <= b.x + b.w && dy >= b.y && dy <= b.y + b.h;
    }) || null;
  }

  eventPoint(e) {
    const rect = this.canvas.getBoundingClientRect();
    const px = e.clientX - rect.left;
    const py = e.clientY - rect.top;
    return { px, py, dx: px / this.scale, dy: py / this.scale };
  }

  onPointerDown(e) {
    if (e.button !== 0) return;
    this.canvas.focus();
    const { px, py, dx, dy } = this.eventPoint(e);
    const { store } = this;
    const selection = store.selection;
    const anyLocked = selection.some((el) => el.locked);

    // Resize handles of the current selection take priority.
    if (selection.length && !anyLocked) {
      const bounds = selection.length > 1 ? unionBounds(selection) : elementBounds(selection[0]);
      const handle = this.handleAt(bounds, px, py);
      if (handle) {
        this.beginOp(e, {
          kind: 'resize',
          handle,
          bounds,
          start: { dx, dy },
          originals: new Map(selection.map((el) => [el, { x: el.x, y: el.y, width: el.width, height: el.height, radius: el.radius }])),
        });
        return;
      }
    }

    const hit = this.elementAt(dx, dy);
    if (!hit) {
      if (!e.ctrlKey && !e.shiftKey) store.select([]);
      return;
    }

    let next = [...selection];
    let group = store.groupSelection;
    if (e.ctrlKey) {
      const targets = hit.group ? store.groupMembers(hit.group) : [hit];
      const allSelected = targets.every((el) => next.includes(el));
      next = allSelected ? next.filter((el) => !targets.includes(el)) : [...next, ...targets.filter((el) => !next.includes(el))];
      group = false;
    } else if (e.shiftKey && next.length) {
      const els = store.elements;
      const a = els.indexOf(next[next.length - 1]);
      const b = els.indexOf(hit);
      for (let i = Math.min(a, b); i <= Math.max(a, b); i++) if (!next.includes(els[i])) next.push(els[i]);
      group = false;
    } else if (!next.includes(hit)) {
      next = hit.group ? store.groupMembers(hit.group) : [hit];
      group = !!hit.group;
    }
    store.select(next, { group });

    if (!store.selection.some((el) => el.locked)) {
      this.beginOp(e, {
        kind: 'drag',
        start: { dx, dy },
        originals: new Map(store.selection.map((el) => [el, { x: el.x, y: el.y }])),
      });
    }
  }

  beginOp(e, op) {
    this.op = { ...op, moved: false };
    this.canvas.setPointerCapture(e.pointerId);
  }

  onPointerMove(e) {
    const { px, py, dx, dy } = this.eventPoint(e);
    if (!this.op) {
      this.updateCursor(px, py);
      return;
    }
    const ddx = dx - this.op.start.dx;
    const ddy = dy - this.op.start.dy;
    if (!this.op.moved) {
      if (Math.abs(ddx) < 1 && Math.abs(ddy) < 1) return;
      this.store.checkpoint();
      this.op.moved = true;
    }
    if (this.op.kind === 'drag') this.applyDrag(ddx, ddy);
    else if (this.op.originals.size > 1) this.applyMultiResize(ddx, ddy);
    else this.applyResize(ddx, ddy);
    this.store.touched(this.op.originals.keys());
  }

  onPointerUp(e) {
    if (this.op && this.canvas.hasPointerCapture(e.pointerId)) this.canvas.releasePointerCapture(e.pointerId);
    this.op = null;
  }

  applyDrag(ddx, ddy) {
    const { width, height } = this.size;
    for (const [el, o] of this.op.originals) {
      el.x = Math.round(Math.max(0, Math.min(o.x + ddx, width - 50)));
      el.y = Math.round(Math.max(0, Math.min(o.y + ddy, height - 50)));
    }
  }

  applyResize(ddx, ddy) {
    const { handle } = this.op;
    const [el, o] = this.op.originals.entries().next().value;
    const right = handle === 'tr' || handle === 'br';
    const bottom = handle === 'bl' || handle === 'br';

    if (isRadial(el)) {
      const delta = (ddx + ddy) / 2;
      el.radius = Math.round(Math.max(MIN_RADIUS, o.radius + (right ? delta : -delta)));
      return;
    }

    let w = Math.max(MIN_SIZE, right ? o.width + ddx : o.width - ddx);
    let h = Math.max(MIN_SIZE, bottom ? o.height + ddy : o.height - ddy);
    if (el.type === 'image' && el.scale_proportionally && el.aspect_ratio > 0) {
      if (Math.abs(w / o.width - 1) > Math.abs(h / o.height - 1)) h = Math.max(MIN_SIZE, w / el.aspect_ratio);
      else w = Math.max(MIN_SIZE, h * el.aspect_ratio);
    }
    el.width = Math.round(w);
    el.height = Math.round(h);
    el.x = Math.round(right ? o.x : o.x + o.width - el.width);
    el.y = Math.round(bottom ? o.y : o.y + o.height - el.height);
  }

  applyMultiResize(ddx, ddy) {
    const { handle, bounds } = this.op;
    const right = handle === 'tr' || handle === 'br';
    const bottom = handle === 'bl' || handle === 'br';
    const sx = Math.max(0.1, bounds.w > 0 ? (bounds.w + (right ? ddx : -ddx)) / bounds.w : 1);
    const sy = Math.max(0.1, bounds.h > 0 ? (bounds.h + (bottom ? ddy : -ddy)) / bounds.h : 1);
    const ax = right ? bounds.x : bounds.x + bounds.w;
    const ay = bottom ? bounds.y : bounds.y + bounds.h;
    for (const [el, o] of this.op.originals) {
      el.x = Math.round(ax + (o.x - ax) * sx);
      el.y = Math.round(ay + (o.y - ay) * sy);
      if (isRadial(el)) el.radius = Math.round(Math.max(MIN_RADIUS, o.radius * (sx + sy) / 2));
      else {
        el.width = Math.round(Math.max(MIN_SIZE, o.width * sx));
        el.height = Math.round(Math.max(MIN_SIZE, o.height * sy));
      }
    }
  }

  updateCursor(px, py) {
    const selection = this.store.selection;
    let cursor = 'default';
    if (selection.length && !selection.some((el) => el.locked)) {
      const bounds = selection.length > 1 ? unionBounds(selection) : elementBounds(selection[0]);
      const handle = this.handleAt(bounds, px, py);
      if (handle === 'tl' || handle === 'br') cursor = 'nwse-resize';
      else if (handle === 'tr' || handle === 'bl') cursor = 'nesw-resize';
    }
    if (cursor === 'default' && this.elementAt(px / this.scale, py / this.scale)) cursor = 'move';
    this.canvas.style.cursor = cursor;
  }

  onKeyDown(e) {
    const deltas = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] };
    const delta = deltas[e.key];
    const selection = this.store.selection;
    if (!delta || !selection.length || selection.some((el) => el.locked)) return;
    e.preventDefault();
    const step = e.shiftKey ? 10 : 1;
    this.store.checkpoint('nudge');
    for (const el of selection) {
      el.x += delta[0] * step;
      el.y += delta[1] * step;
    }
    this.store.touched(selection);
  }
}
