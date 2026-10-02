/**
 * Frame loop: applies sensor values, renders the scene once per frame and
 * hands that frame to both the editor preview and the LCD.
 *
 * Uses setTimeout rather than requestAnimationFrame so it keeps running while
 * the window is hidden in the tray.
 */

import { DISPLAY_WIDTH, DISPLAY_HEIGHT } from './constants.js';
import { renderScene, createRenderEnv, advanceEnv } from './render.js';

const IDLE_CHECK_MS = 250;

export class Engine {
  constructor(store, { sendFrame, onFrame }) {
    this.store = store;
    this.sendFrame = sendFrame;
    this.onFrame = onFrame;
    this.canvas = new OffscreenCanvas(DISPLAY_WIDTH, DISPLAY_HEIGHT);
    this.ctx = this.canvas.getContext('2d', { alpha: false });
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
      const blob = await this.canvas.convertToBlob({ type: 'image/jpeg', quality: this.jpegQuality });
      this.sendFrame(await blob.arrayBuffer());
    } catch (err) {
      console.error('[Engine] Frame encode failed:', err);
    } finally {
      this.encoding = false;
    }
  }

  /** Current frame as PNG bytes, optionally scaled to fit `maxWidth`. */
  async snapshotPng(maxWidth = DISPLAY_WIDTH) {
    this.render();
    const scale = Math.min(1, maxWidth / DISPLAY_WIDTH);
    let source = this.canvas;
    if (scale < 1) {
      source = new OffscreenCanvas(Math.round(DISPLAY_WIDTH * scale), Math.round(DISPLAY_HEIGHT * scale));
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
