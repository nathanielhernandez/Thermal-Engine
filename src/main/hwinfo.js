/**
 * HWiNFO shared memory reader.
 *
 * Requires HWiNFO to be running with "Shared Memory Support" enabled.
 * Layout reference: https://www.hwinfo.com/forum/threads/shared-memory-layout.5149/
 *
 * The parsing functions are pure (they take a Uint8Array) so they can be unit
 * tested without HWiNFO; only HWiNFOReader touches the Win32 API.
 */

const SHARED_MEM_NAME = 'Global\\HWiNFO_SENS_SM2';
const FILE_MAP_READ = 0x0004;
const SIGNATURE_ACTIVE = 0x53695748; // "HWiS"
const SIGNATURE_DEAD = 0x44414544; // "DEAD" - HWiNFO stopped sharing (e.g. 12-hour free limit)

const HEADER_SIZE = 44;
const STRING_LEN = 128;
const UNIT_LEN = 16;

const SENSOR_TYPE = {
  NONE: 0, TEMP: 1, VOLT: 2, FAN: 3, CURRENT: 4, POWER: 5, CLOCK: 6, USAGE: 7, OTHER: 8,
};

// For each metric: the reading type and label patterns tried in priority order.
const METRICS = {
  cpu_temp: { type: SENSOR_TYPE.TEMP, patterns: ['CPU Package', 'CPU (Tctl/Tdie)', 'CPU Tctl/Tdie', 'Tctl/Tdie', 'CPU Die', 'CPU', 'Core 0'] },
  cpu_clock: { type: SENSOR_TYPE.CLOCK, patterns: ['Core 0 Clock', 'CPU Core 0', 'Core Clock', 'CPU Clock'], integer: true },
  cpu_power: { type: SENSOR_TYPE.POWER, patterns: ['CPU Package Power', 'CPU Power', 'Package Power', 'CPU PPT'] },
  gpu_temp: { type: SENSOR_TYPE.TEMP, patterns: ['GPU Temperature', 'GPU Hot Spot', 'GPU Core'] },
  gpu_percent: { type: SENSOR_TYPE.USAGE, patterns: ['GPU Core Load', 'GPU Usage', 'GPU Load', 'GPU Utilization'] },
  gpu_clock: { type: SENSOR_TYPE.CLOCK, patterns: ['GPU Clock', 'GPU Core Clock'], integer: true },
  gpu_memory_clock: { type: SENSOR_TYPE.CLOCK, patterns: ['GPU Memory Clock', 'Memory Clock'], integer: true },
  gpu_memory_percent: { type: SENSOR_TYPE.USAGE, patterns: ['GPU Memory Usage', 'GPU Memory Load', 'GPU Memory Allocated'] },
  gpu_power: { type: SENSOR_TYPE.POWER, patterns: ['GPU Power', 'GPU Total Power', 'GPU Board Power', 'GPU Chip Power'] },
};

function readCString(bytes, offset, maxLen) {
  let end = offset;
  const limit = Math.min(offset + maxLen, bytes.length);
  while (end < limit && bytes[end] !== 0) end++;
  return Buffer.from(bytes.buffer, bytes.byteOffset + offset, end - offset).toString('utf8').trim();
}

function parseHeader(bytes) {
  if (bytes.length < HEADER_SIZE) return null;
  const dv = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  return {
    signature: dv.getUint32(0, true),
    version: dv.getUint32(4, true),
    revision: dv.getUint32(8, true),
    pollTime: Number(dv.getBigUint64(12, true)),
    sensorOffset: dv.getUint32(20, true),
    sensorSize: dv.getUint32(24, true),
    sensorCount: dv.getUint32(28, true),
    readingOffset: dv.getUint32(32, true),
    readingSize: dv.getUint32(36, true),
    readingCount: dv.getUint32(40, true),
  };
}

/** Total number of bytes needed to read every sensor and reading. */
function totalSize(header) {
  return Math.max(
    HEADER_SIZE,
    header.sensorOffset + header.sensorSize * header.sensorCount,
    header.readingOffset + header.readingSize * header.readingCount,
  );
}

/** Parse every reading from a full shared memory snapshot. */
function parseReadings(bytes, header) {
  const dv = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);

  const sensorNames = [];
  for (let i = 0; i < header.sensorCount; i++) {
    const o = header.sensorOffset + i * header.sensorSize;
    sensorNames.push(readCString(bytes, o + 8, STRING_LEN));
  }

  const readings = [];
  for (let i = 0; i < header.readingCount; i++) {
    const o = header.readingOffset + i * header.readingSize;
    if (o + 316 > bytes.length) break;
    const sensorIndex = dv.getUint32(o + 4, true);
    const labelOrig = readCString(bytes, o + 12, STRING_LEN);
    const labelUser = readCString(bytes, o + 12 + STRING_LEN, STRING_LEN);
    readings.push({
      type: dv.getUint32(o, true),
      sensor: sensorNames[sensorIndex] || 'Unknown',
      label: labelUser || labelOrig,
      unit: readCString(bytes, o + 12 + STRING_LEN * 2, UNIT_LEN),
      value: dv.getFloat64(o + 12 + STRING_LEN * 2 + UNIT_LEN, true),
    });
  }
  return readings;
}

/** Find the first reading of `type` whose sensor or label contains a pattern (in pattern order). */
function findReading(readings, patterns, type) {
  for (const pattern of patterns) {
    const p = pattern.toLowerCase();
    for (const r of readings) {
      if (type != null && r.type !== type) continue;
      if (r.sensor.toLowerCase().includes(p) || r.label.toLowerCase().includes(p)) return r;
    }
  }
  return null;
}

/** Map parsed readings to the ThermalEngine sensor keys. */
function extractMetrics(readings) {
  const result = {};
  for (const [key, def] of Object.entries(METRICS)) {
    const r = findReading(readings, def.patterns, def.type);
    const value = r ? r.value : 0;
    result[key] = def.integer ? Math.trunc(value) : value;
  }
  return result;
}

class HWiNFOReader {
  constructor() {
    this.handle = null;
    this.view = null;
    this.lastError = null;
    this._api = null;
  }

  _loadApi() {
    if (this._api) return this._api;
    const koffi = require('koffi');
    const k32 = koffi.load('kernel32.dll');
    this._api = {
      koffi,
      OpenFileMappingW: k32.func('void* __stdcall OpenFileMappingW(uint32_t access, bool inherit, const char16_t *name)'),
      MapViewOfFile: k32.func('void* __stdcall MapViewOfFile(void *handle, uint32_t access, uint32_t offsetHigh, uint32_t offsetLow, size_t size)'),
      UnmapViewOfFile: k32.func('bool __stdcall UnmapViewOfFile(void *addr)'),
      CloseHandle: k32.func('bool __stdcall CloseHandle(void *handle)'),
    };
    return this._api;
  }

  connect() {
    if (process.platform !== 'win32') {
      this.lastError = 'HWiNFO is only available on Windows';
      return false;
    }
    try {
      const api = this._loadApi();
      const handle = api.OpenFileMappingW(FILE_MAP_READ, false, SHARED_MEM_NAME);
      if (!handle) {
        this.lastError = 'HWiNFO shared memory not found. Is HWiNFO running with Shared Memory Support enabled?';
        return false;
      }
      const view = api.MapViewOfFile(handle, FILE_MAP_READ, 0, 0, 0);
      if (!view) {
        api.CloseHandle(handle);
        this.lastError = 'MapViewOfFile failed';
        return false;
      }
      this.handle = handle;
      this.view = view;
      this.lastError = null;
      return true;
    } catch (err) {
      this.lastError = err.message;
      return false;
    }
  }

  disconnect() {
    if (!this._api) return;
    if (this.view) this._api.UnmapViewOfFile(this.view);
    if (this.handle) this._api.CloseHandle(this.handle);
    this.view = null;
    this.handle = null;
  }

  get connected() {
    return this.view != null;
  }

  /** Copy the shared memory and return all readings, or null if unavailable. */
  readAll() {
    if (!this.connected && !this.connect()) return null;
    const { koffi } = this._api;
    const header = parseHeader(koffi.decode(this.view, 'uint8_t', HEADER_SIZE));
    if (!header || header.signature !== SIGNATURE_ACTIVE) {
      this.lastError = header && header.signature === SIGNATURE_DEAD
        ? 'HWiNFO stopped sharing sensor data (free version 12-hour limit). Restart HWiNFO.'
        : 'Invalid HWiNFO shared memory signature';
      // Drop the stale mapping so the next poll re-opens it after HWiNFO restarts.
      this.disconnect();
      return null;
    }
    const bytes = koffi.decode(this.view, 'uint8_t', totalSize(header));
    return parseReadings(bytes, header);
  }
}

module.exports = {
  HWiNFOReader,
  parseHeader,
  parseReadings,
  totalSize,
  findReading,
  extractMetrics,
  METRICS,
  SENSOR_TYPE,
  SIGNATURE_ACTIVE,
  SIGNATURE_DEAD,
};
