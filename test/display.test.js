const test = require('node:test');
const assert = require('node:assert');
const { buildFrameReports, buildInitReport } = require('../src/main/display');

test('init report has magic bytes and report ID', () => {
  const init = buildInitReport();
  assert.strictEqual(init.length, 513);
  assert.deepStrictEqual([...init.subarray(0, 5)], [0x00, 0xDA, 0xDB, 0xDC, 0xDD]);
  assert.strictEqual(init[13], 0x01);
});

test('frame header carries size, resolution and the first 492 bytes', () => {
  const jpeg = Buffer.alloc(2000);
  for (let i = 0; i < jpeg.length; i++) jpeg[i] = i % 251;
  const reports = buildFrameReports(jpeg);

  // 492 bytes in the header, then ceil(1508 / 512) = 3 chunks
  assert.strictEqual(reports.length, 4);
  for (const r of reports) {
    assert.strictEqual(r.length, 513);
    assert.strictEqual(r[0], 0x00);
  }
  const header = reports[0];
  assert.deepStrictEqual([...header.subarray(1, 5)], [0xDA, 0xDB, 0xDC, 0xDD]);
  assert.strictEqual(header[5], 0x02);
  assert.deepStrictEqual([...header.subarray(9, 13)], [0x00, 0x05, 0xE0, 0x01]);
  assert.strictEqual(header[13], 0x02);
  assert.strictEqual(header.readUInt32LE(17), 2000);

  const reassembled = Buffer.concat([header.subarray(21), ...reports.slice(1).map((r) => r.subarray(1))]);
  assert.deepStrictEqual(reassembled.subarray(0, 2000), jpeg);
  assert.ok(reassembled.subarray(2000).every((b) => b === 0), 'last chunk is zero padded');
});

test('small frames fit in the header report', () => {
  assert.strictEqual(buildFrameReports(Buffer.alloc(492)).length, 1);
  assert.strictEqual(buildFrameReports(Buffer.alloc(493)).length, 2);
});
