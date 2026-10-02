/**
 * Sensor polling: combines HWiNFO readings with CPU/RAM/network stats and
 * publishes a snapshot every poll.
 */

const { HWiNFOReader, extractMetrics, findReading, METRICS } = require('./hwinfo');
const { CpuSampler, NetworkSampler, memoryStats } = require('./system-stats');

const POLL_INTERVAL_MS = 500;
// Lower = smoother but slower to react. 15% new value, 85% previous.
const SMOOTHING_FACTOR = 0.15;

class SensorService {
  constructor() {
    this.hwinfo = new HWiNFOReader();
    this.cpu = new CpuSampler();
    this.net = new NetworkSampler();
    this.hwinfoConnected = false;
    this.lastReadings = [];
    this.smoothed = {};
    this.snapshot = {};
    this.listeners = new Set();
    this.timer = null;
  }

  start() {
    if (this.timer) return;
    this.poll();
    this.timer = setInterval(() => this.poll(), POLL_INTERVAL_MS);
  }

  stop() {
    clearInterval(this.timer);
    this.timer = null;
    this.hwinfo.disconnect();
  }

  onUpdate(listener) {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  _smooth(key, raw) {
    const prev = this.smoothed[key];
    const value = prev > 0 ? prev * (1 - SMOOTHING_FACTOR) + raw * SMOOTHING_FACTOR : raw;
    this.smoothed[key] = value;
    return value;
  }

  poll() {
    let hw = null;
    try {
      const readings = this.hwinfo.readAll();
      if (readings) {
        this.lastReadings = readings;
        hw = extractMetrics(readings);
      }
    } catch (err) {
      this.hwinfo.lastError = err.message;
    }

    if (!!hw !== this.hwinfoConnected) {
      this.hwinfoConnected = !!hw;
      console.log(hw ? '[Sensors] Connected to HWiNFO' : `[Sensors] HWiNFO unavailable: ${this.hwinfo.lastError}`);
    }

    const net = this.net.sample();
    const data = {
      static: 50,
      cpu_percent: this.cpu.sample(),
      ...memoryStats(),
      net_upload: net.upload,
      net_download: net.download,
    };
    for (const key of Object.keys(METRICS)) {
      data[key] = hw ? this._smooth(key, hw[key]) : 0;
    }

    this.snapshot = data;
    const status = this.status();
    for (const listener of this.listeners) listener(data, status);
  }

  status() {
    return {
      hwinfo: this.hwinfoConnected,
      error: this.hwinfoConnected ? null : this.hwinfo.lastError,
    };
  }

  /** Detailed report for the Diagnose Sensors dialog. */
  diagnose() {
    const matches = {};
    for (const [key, def] of Object.entries(METRICS)) {
      const r = findReading(this.lastReadings, def.patterns, def.type);
      matches[key] = r ? { sensor: r.sensor, label: r.label, value: r.value, unit: r.unit } : null;
    }
    return {
      status: this.status(),
      values: this.snapshot,
      matches,
      readings: this.hwinfoConnected ? this.lastReadings : [],
    };
  }
}

module.exports = { SensorService };
