/**
 * Frame loop: applies sensor values, renders the scene once per frame and
 * hands that frame to both the editor preview and the LCD.
 *
 * Uses setTimeout rather than requestAnimationFrame so it keeps running while
 * the window is hidden in the tray.
 */

import { DISPLAY_WIDTH, DISPLAY_HEIGHT, getOrientation } from './constants.js';
import { renderScene, createRenderEnv, advanceEnv } from './render.js';

const IDLE_CHECK_MS = 250;

export class Engine {
  constructor(store, { sendFrame, onFrame }) {
    this.store = store;
    this.sendFrame = sendFrame;
    this.onFrame = onFrame;
    // Upright theme canvas (sized by orientation) and the native panel frame.
    this.canvas = new OffscreenCanvas(DISPLAY_WIDTH, DISPLAY_HEIGHT);
    this.ctx = this.canvas.getContext('2d', { alpha: false });
    this.panel = new OffscreenCanvas(DISPLAY_WIDTH, DISPLAY_HEIGHT);
    this.panelCtx = this.panel.getContext('2d', { alpha: false });
    this.env = createRenderEnv();
    this.sensors = {};
    this.connected = false;
    this.visible = true;
    this.targetFps = 30;
    this.jpegQuality = 0.8;
    this.encoding = false;
    this.timer = null;
    this.nextFrameAt = 0;
    this.invalidated = false;
    this.framesRendered = 0;
  }

  start() {
    this.nextFrameAt = performance.now();
    this._schedule(0);
  }

  setSensors(data) {
    this.sensors = data;
  }

  setConnected(connected) {
    this.connected = connected;
  }

  setVisible(visible) {
    this.visible = visible;
    if (visible) this.invalidate();
  }

  setTargetFps(fps) {
    this.targetFps = fps;
    this.nextFrameAt = performance.now();
  }

  setJpegQuality(quality) {
    this.jpegQuality = Math.max(0.3, Math.min(1, quality / 100));
  }

  /** Re-render and repaint the preview as soon as possible (after edits). */
  invalidate() {
    if (this.invalidated) return;
    this.invalidated = true;
    requestAnimationFrame(() => {
      this.invalidated = false;
      this.render();
      this.onFrame();
    });
  }

  applySensorValues() {
    for (const el of this.store.elements) {
      if (el.source && el.source !== 'static' && el.source in this.sensors) {
        el.value = this.sensors[el.source];
      }
    }
  }

  render() {
    const { width, height } = getOrientation(this.store.orientation);
    if (this.canvas.width !== width || this.canvas.height !== height) {
      this.canvas.width = width;
      this.canvas.height = height;
    }
    this.applySensorValues();
    advanceEnv(this.env, this.store.elements);
    renderScene(this.ctx, this.store.scene, this.env);
    this.framesRendered++;
  }

  _schedule(delay) {
    this.timer = setTimeout(() => this._tick(), Math.max(0, delay));
  }

  _tick() {
    if (!this.connected && !this.visible) {
      this._schedule(IDLE_CHECK_MS);
      return;
    }

    this.render();
    if (this.connected) this._encodeAndSend();
    if (this.visible) this.onFrame();

    // Drift-corrected pacing; if we fall far behind, resync instead of bursting.
    const interval = 1000 / this.targetFps;
    const now = performance.now();
    this.nextFrameAt += interval;
    if (now - this.nextFrameAt > interval * 2) this.nextFrameAt = now + interval;
    this._schedule(this.nextFrameAt - now);
  }

  async _encodeAndSend() {
    // Skip this frame if the previous one is still encoding.
    if (this.encoding) return;
    this.encoding = true;
    try {
      const blob = await this._panelFrame().convertToBlob({ type: 'image/jpeg', quality: this.jpegQuality });
      this.sendFrame(await blob.arrayBuffer());
    } catch (err) {
      console.error('[Engine] Frame encode failed:', err);
    } finally {
      this.encoding = false;
    }
  }

  /** The current frame rotated into the panel's native 1280x480 orientation. */
  _panelFrame() {
    const { rotation } = getOrientation(this.store.orientation);
    if (rotation === 0) return this.canvas;
    const ctx = this.panelCtx;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.translate(DISPLAY_WIDTH / 2, DISPLAY_HEIGHT / 2);
    ctx.rotate((rotation * Math.PI) / 180);
    ctx.drawImage(this.canvas, -this.canvas.width / 2, -this.canvas.height / 2);
    return this.panel;
  }

  /** Current upright frame as PNG bytes, scaled so its longest side fits `maxSize`. */
  async snapshotPng(maxSize = DISPLAY_WIDTH) {
    this.render();
    const { width, height } = this.canvas;
    const scale = Math.min(1, maxSize / Math.max(width, height));
    let source = this.canvas;
    if (scale < 1) {
      source = new OffscreenCanvas(Math.round(width * scale), Math.round(height * scale));
      const ctx = source.getContext('2d');
      ctx.imageSmoothingQuality = 'high';
      ctx.drawImage(this.canvas, 0, 0, source.width, source.height);
    }
    const blob = await source.convertToBlob({ type: 'image/png' });
    return new Uint8Array(await blob.arrayBuffer());
  }

  takeRenderedCount() {
    const n = this.framesRendered;
    this.framesRendered = 0;
    return n;
  }
}
