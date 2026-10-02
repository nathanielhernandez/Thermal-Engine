/**
 * CPU, RAM and network statistics that don't need HWiNFO.
 */

const os = require('os');

const GiB = 1024 ** 3;
const MiB = 1024 ** 2;

// MIB_IF_ROW2 layout (iphlpapi.h), 1352 bytes per row; MIB_IF_TABLE2 rows start at offset 8.
const IF_ROW_SIZE = 1352;
const IF_TABLE_HEADER = 8;
const IF_ROW_FLAGS = 1152; // InterfaceAndOperStatusFlags bitfield
const IF_ROW_IN_OCTETS = 1208;
const IF_ROW_OUT_OCTETS = 1280;
const IF_FLAG_HARDWARE = 0x1;
const IF_FLAG_FILTER = 0x2;

class CpuSampler {
  constructor(historySize = 5) {
    this.prev = this._snapshot();
    this.history = [];
    this.historySize = historySize;
  }

  _snapshot() {
    let idle = 0;
    let total = 0;
    for (const cpu of os.cpus()) {
      const t = cpu.times;
      idle += t.idle;
      total += t.user + t.nice + t.sys + t.idle + t.irq;
    }
    return { idle, total };
  }

  /** CPU utilization since the last sample, averaged over the last few samples. */
  sample() {
    const now = this._snapshot();
    const dTotal = now.total - this.prev.total;
    const dIdle = now.idle - this.prev.idle;
    this.prev = now;
    if (dTotal > 0) {
      this.history.push(Math.max(0, Math.min(100, (1 - dIdle / dTotal) * 100)));
      if (this.history.length > this.historySize) this.history.shift();
    }
    if (!this.history.length) return 0;
    return this.history.reduce((a, b) => a + b, 0) / this.history.length;
  }
}

/** Sums byte counters over physical network adapters (filter/virtual rows would double count). */
class NetworkSampler {
  constructor() {
    this.api = null;
    this.prev = null;
    this.prevTime = 0;
    if (process.platform === 'win32') {
      try {
        const koffi = require('koffi');
        const lib = koffi.load('iphlpapi.dll');
        this.api = {
          koffi,
          GetIfTable2: lib.func('uint32_t __stdcall GetIfTable2(_Out_ void **table)'),
          FreeMibTable: lib.func('void __stdcall FreeMibTable(void *mem)'),
        };
      } catch (err) {
        console.error('[Stats] Network counters unavailable:', err.message);
      }
    }
  }

  _readCounters() {
    if (!this.api) return null;
    const { koffi, GetIfTable2, FreeMibTable } = this.api;
    const out = [null];
    if (GetIfTable2(out) !== 0 || !out[0]) return null;
    try {
      const count = koffi.decode(out[0], 'uint32_t');
      const bytes = koffi.decode(out[0], 'uint8_t', IF_TABLE_HEADER + count * IF_ROW_SIZE);
      return sumPhysicalCounters(bytes, count);
    } finally {
      FreeMibTable(out[0]);
    }
  }

  /** Upload/download rate in MB/s since the last sample. */
  sample() {
    const counters = this._readCounters();
    const now = Date.now();
    let upload = 0;
    let download = 0;
    if (counters && this.prev) {
      const dt = (now - this.prevTime) / 1000;
      if (dt > 0) {
        // Counters can reset when an adapter goes down; ignore negative deltas.
        upload = Math.max(0, Number(counters.out - this.prev.out)) / dt / MiB;
        download = Math.max(0, Number(counters.in - this.prev.in)) / dt / MiB;
      }
    }
    if (counters) {
      this.prev = counters;
      this.prevTime = now;
    }
    return { upload, download };
  }
}

function sumPhysicalCounters(bytes, count) {
  const dv = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  let totalIn = 0n;
  let totalOut = 0n;
  for (let i = 0; i < count; i++) {
    const o = IF_TABLE_HEADER + i * IF_ROW_SIZE;
    const flags = bytes[o + IF_ROW_FLAGS];
    if (!(flags & IF_FLAG_HARDWARE) || (flags & IF_FLAG_FILTER)) continue;
    totalIn += dv.getBigUint64(o + IF_ROW_IN_OCTETS, true);
    totalOut += dv.getBigUint64(o + IF_ROW_OUT_OCTETS, true);
  }
  return { in: totalIn, out: totalOut };
}

function memoryStats() {
  const total = os.totalmem();
  const available = os.freemem();
  const used = total - available;
  return {
    ram_percent: (used / total) * 100,
    ram_used: used / GiB,
    ram_available: available / GiB,
  };
}

module.exports = { CpuSampler, NetworkSampler, memoryStats, sumPhysicalCounters, IF_ROW_SIZE };
