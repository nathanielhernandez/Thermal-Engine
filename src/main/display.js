/**
 * USB HID driver for the Thermalright Trofeo 1280x480 LCD.
 *
 * Frames are JPEGs. Each frame is sent as a 512-byte header report (which
 * also carries the first 492 bytes of JPEG data) followed by 512-byte chunks.
 * Every report is prefixed with report ID 0x00.
 */

const { EventEmitter } = require('events');

const VENDOR_ID = 0x0416;
const PRODUCT_ID = 0x5302;
const REPORT_SIZE = 512;
const HEADER_DATA_OFFSET = 20;
const MAGIC = [0xDA, 0xDB, 0xDC, 0xDD];
const MAX_RECONNECT_DELAY_MS = 30000;

function buildInitReport() {
  const report = Buffer.alloc(REPORT_SIZE + 1);
  report.set(MAGIC, 1);
  report[1 + 4] = 0x00;
  report[1 + 12] = 0x01;
  return report;
}

/** Split a JPEG into the report sequence the display expects (report ID included). */
function buildFrameReports(jpeg) {
  const firstChunk = Math.min(jpeg.length, REPORT_SIZE - HEADER_DATA_OFFSET);
  const remaining = jpeg.length - firstChunk;
  const chunkCount = Math.ceil(remaining / REPORT_SIZE);
  const reports = [];

  const header = Buffer.alloc(REPORT_SIZE + 1);
  header.set(MAGIC, 1);
  header[1 + 4] = 0x02;
  header.set([0x00, 0x05, 0xE0, 0x01], 1 + 8); // 1280 x 480
  header[1 + 12] = 0x02;
  header.writeUInt32LE(jpeg.length, 1 + 16);
  jpeg.copy(header, 1 + HEADER_DATA_OFFSET, 0, firstChunk);
  reports.push(header);

  for (let i = 0; i < chunkCount; i++) {
    const start = firstChunk + i * REPORT_SIZE;
    const report = Buffer.alloc(REPORT_SIZE + 1);
    jpeg.copy(report, 1, start, Math.min(start + REPORT_SIZE, jpeg.length));
    reports.push(report);
  }
  return reports;
}

class DisplayDevice extends EventEmitter {
  constructor() {
    super();
    this.device = null;
    this.wantConnected = true;
    this.connecting = false;
    this.pendingFrame = null;
    this.sending = false;
    this.reconnectTimer = null;
    this.reconnectAttempts = 0;
    this.framesSent = 0;
    this.framesDropped = 0;
    this.lastError = null;
  }

  get connected() {
    return this.device != null;
  }

  status() {
    return {
      connected: this.connected,
      wantConnected: this.wantConnected,
      reconnecting: this.reconnectTimer != null,
      error: this.lastError,
    };
  }

  _emitStatus() {
    this.emit('status', this.status());
  }

  /** Try to open the display. Returns true on success. */
  async connect({ userInitiated = false } = {}) {
    if (this.connected) return true;
    if (this.connecting) return false;
    this.wantConnected = true;
    this.connecting = true;
    try {
      const HID = require('node-hid');
      const device = await HID.HIDAsync.open(VENDOR_ID, PRODUCT_ID);
      device.on('error', (err) => this._handleDeviceError(err));
      await device.write(buildInitReport());
      this.device = device;
      this.lastError = null;
      this.reconnectAttempts = 0;
      this._clearReconnect();
      console.log('[Display] Connected');
      this._emitStatus();
      return true;
    } catch (err) {
      this.lastError = `Display not found (${err.message}). Make sure TRCC or other vendor software is closed.`;
      if (userInitiated) console.log(`[Display] ${this.lastError}`);
      this._scheduleReconnect();
      this._emitStatus();
      return false;
    } finally {
      this.connecting = false;
    }
  }

  /** Close the display. `userInitiated` stops auto-reconnect. */
  async disconnect({ userInitiated = false } = {}) {
    if (userInitiated) this.wantConnected = false;
    this._clearReconnect();
    this.pendingFrame = null;
    const device = this.device;
    this.device = null;
    if (device) {
      try {
        await device.close();
      } catch (err) {
        console.error('[Display] Error closing device:', err.message);
      }
      console.log('[Display] Disconnected');
    }
    this._emitStatus();
  }

  /** Queue a JPEG frame. If a frame is still being sent, only the newest one is kept. */
  submitFrame(jpeg) {
    if (!this.connected) return;
    if (this.pendingFrame) this.framesDropped++;
    this.pendingFrame = jpeg;
    if (!this.sending) this._pump();
  }

  async _pump() {
    this.sending = true;
    try {
      while (this.pendingFrame && this.device) {
        const frame = this.pendingFrame;
        this.pendingFrame = null;
        const device = this.device;
        for (const report of buildFrameReports(frame)) {
          await device.write(report);
        }
        this.framesSent++;
      }
    } catch (err) {
      this._handleDeviceError(err);
    } finally {
      this.sending = false;
    }
  }

  _handleDeviceError(err) {
    if (!this.device) return;
    console.error('[Display] Device error, reconnecting:', err.message);
    this.lastError = err.message;
    const device = this.device;
    this.device = null;
    this.pendingFrame = null;
    device.close().catch(() => {});
    this._scheduleReconnect();
    this._emitStatus();
  }

  _scheduleReconnect(delayOverride) {
    if (!this.wantConnected || this.reconnectTimer) return;
    // Exponential backoff: 1s, 2s, 4s ... capped at 30s
    const delay = delayOverride ?? Math.min(MAX_RECONNECT_DELAY_MS, 1000 * 2 ** this.reconnectAttempts);
    this.reconnectAttempts++;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, delay);
  }

  _clearReconnect() {
    clearTimeout(this.reconnectTimer);
    this.reconnectTimer = null;
  }

  /** System is going to sleep: release the device but remember to come back. */
  async suspend() {
    const wanted = this.wantConnected;
    await this.disconnect();
    this.wantConnected = wanted;
  }

  /** System woke up: reconnect after a short delay to let USB settle. */
  resume() {
    if (!this.wantConnected || this.connected) return;
    this.reconnectAttempts = 0;
    this._clearReconnect();
    this._scheduleReconnect(2000);
  }

  /** Frames sent/dropped since the last call. */
  takeStats() {
    const stats = { sent: this.framesSent, dropped: this.framesDropped };
    this.framesSent = 0;
    this.framesDropped = 0;
    return stats;
  }
}

module.exports = { DisplayDevice, buildFrameReports, buildInitReport, VENDOR_ID, PRODUCT_ID };
