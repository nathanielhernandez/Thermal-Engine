const test = require('node:test');
const assert = require('node:assert');
const { sumPhysicalCounters, IF_ROW_SIZE } = require('../src/main/system-stats');

function row(buf, index, flags, inOctets, outOctets) {
  const o = 8 + index * IF_ROW_SIZE;
  buf[o + 1152] = flags;
  buf.writeBigUInt64LE(inOctets, o + 1208);
  buf.writeBigUInt64LE(outOctets, o + 1280);
}

test('only counts physical adapters, skipping filter and virtual rows', () => {
  const buf = Buffer.alloc(8 + 4 * IF_ROW_SIZE);
  row(buf, 0, 0b101, 1000n, 100n); // hardware NIC
  row(buf, 1, 0b011, 1000n, 100n); // filter driver bound to the same NIC
  row(buf, 2, 0b000, 5000n, 500n); // virtual adapter (VPN/loopback)
  row(buf, 3, 0b10101, 300n, 30n); // second hardware NIC (Wi-Fi)
  const totals = sumPhysicalCounters(new Uint8Array(buf.buffer, buf.byteOffset, buf.byteLength), 4);
  assert.deepStrictEqual(totals, { in: 1300n, out: 130n });
});
