const test = require('node:test');
const assert = require('node:assert');
const {
  parseHeader, parseReadings, totalSize, extractMetrics, SENSOR_TYPE, SIGNATURE_ACTIVE, SIGNATURE_DEAD,
} = require('../src/main/hwinfo');

const SENSOR_SIZE = 264;
const READING_SIZE = 460; // newer HWiNFO versions use larger elements than the 316-byte base layout

/** Build a fake HWiNFO shared memory block. */
function buildSharedMemory(sensors, readings, signature = SIGNATURE_ACTIVE) {
  const sensorOffset = 44;
  const readingOffset = sensorOffset + sensors.length * SENSOR_SIZE;
  const buf = Buffer.alloc(readingOffset + readings.length * READING_SIZE);
  buf.writeUInt32LE(signature, 0);
  buf.writeUInt32LE(2, 4);
  buf.writeBigUInt64LE(2000n, 12);
  buf.writeUInt32LE(sensorOffset, 20);
  buf.writeUInt32LE(SENSOR_SIZE, 24);
  buf.writeUInt32LE(sensors.length, 28);
  buf.writeUInt32LE(readingOffset, 32);
  buf.writeUInt32LE(READING_SIZE, 36);
  buf.writeUInt32LE(readings.length, 40);
  sensors.forEach((name, i) => buf.write(name, sensorOffset + i * SENSOR_SIZE + 8, 'utf8'));
  readings.forEach((r, i) => {
    const o = readingOffset + i * READING_SIZE;
    buf.writeUInt32LE(r.type, o);
    buf.writeUInt32LE(r.sensor, o + 4);
    buf.write(r.label, o + 12, 'utf8');
    if (r.userLabel) buf.write(r.userLabel, o + 140, 'utf8');
    buf.write(r.unit || '', o + 268, 'utf8');
    buf.writeDoubleLE(r.value, o + 284);
  });
  return new Uint8Array(buf.buffer, buf.byteOffset, buf.byteLength);
}

const SENSORS = ['CPU [#0]: AMD Ryzen 7 7800X3D', 'GPU [#0]: NVIDIA GeForce RTX 4080'];
const READINGS = [
  { type: SENSOR_TYPE.TEMP, sensor: 0, label: 'CPU (Tctl/Tdie)', unit: '°C', value: 61.5 },
  { type: SENSOR_TYPE.CLOCK, sensor: 0, label: 'Core 0 Clock (perf #1)', unit: 'MHz', value: 4850.7 },
  { type: SENSOR_TYPE.POWER, sensor: 0, label: 'CPU Package Power', unit: 'W', value: 72.25 },
  { type: SENSOR_TYPE.TEMP, sensor: 1, label: 'GPU Temperature', unit: '°C', value: 48 },
  { type: SENSOR_TYPE.USAGE, sensor: 1, label: 'GPU Core Load', unit: '%', value: 37 },
  { type: SENSOR_TYPE.CLOCK, sensor: 1, label: 'GPU Clock', unit: 'MHz', value: 2610.2 },
  { type: SENSOR_TYPE.CLOCK, sensor: 1, label: 'GPU Memory Clock', unit: 'MHz', value: 1400.9 },
  { type: SENSOR_TYPE.USAGE, sensor: 1, label: 'GPU Memory Usage', unit: '%', value: 22.5 },
  { type: SENSOR_TYPE.POWER, sensor: 1, label: 'GPU Power', userLabel: 'GPU Board Power', unit: 'W', value: 210 },
];

test('parses header and readings with element sizes from the header', () => {
  const bytes = buildSharedMemory(SENSORS, READINGS);
  const header = parseHeader(bytes);
  assert.strictEqual(header.signature, SIGNATURE_ACTIVE);
  assert.strictEqual(header.readingCount, READINGS.length);
  assert.strictEqual(totalSize(header), bytes.length);

  const readings = parseReadings(bytes, header);
  assert.strictEqual(readings.length, READINGS.length);
  assert.deepStrictEqual(readings[0], { type: SENSOR_TYPE.TEMP, sensor: SENSORS[0], label: 'CPU (Tctl/Tdie)', unit: '°C', value: 61.5 });
  // User-defined labels take precedence over original labels.
  assert.strictEqual(readings[8].label, 'GPU Board Power');
});

test('maps readings to ThermalEngine sensor keys', () => {
  const bytes = buildSharedMemory(SENSORS, READINGS);
  const metrics = extractMetrics(parseReadings(bytes, parseHeader(bytes)));
  assert.deepStrictEqual(metrics, {
    cpu_temp: 61.5,
    cpu_clock: 4850,
    cpu_power: 72.25,
    gpu_temp: 48,
    gpu_percent: 37,
    gpu_clock: 2610,
    gpu_memory_clock: 1400,
    gpu_memory_percent: 22.5,
    gpu_power: 210,
  });
});

test('missing readings report 0', () => {
  const bytes = buildSharedMemory(['CPU'], [READINGS[0]]);
  const metrics = extractMetrics(parseReadings(bytes, parseHeader(bytes)));
  assert.strictEqual(metrics.cpu_temp, 61.5);
  assert.strictEqual(metrics.gpu_temp, 0);
  assert.strictEqual(metrics.gpu_clock, 0);
});

test('recognizes the DEAD signature HWiNFO writes when sharing stops', () => {
  const header = parseHeader(buildSharedMemory(SENSORS, READINGS, SIGNATURE_DEAD));
  assert.strictEqual(header.signature, SIGNATURE_DEAD);
});
