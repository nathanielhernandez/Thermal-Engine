import test from 'node:test';
import assert from 'node:assert';
import fs from 'node:fs';
import { formatValue } from '../src/renderer/js/constants.js';
import { interpolateGradient, rgba, autoColor } from '../src/renderer/js/color.js';
import { normalizeElement, serializeElement, normalizeGroups, createElement } from '../src/renderer/js/model.js';
import { formatClock } from '../src/renderer/js/draw-utils.js';

test('formats values with units', () => {
  assert.strictEqual(formatValue(61.6, 'cpu_temp'), '62°C');
  assert.strictEqual(formatValue(61.6, 'cpu_temp', true), '62°');
  assert.strictEqual(formatValue(4850.4, 'cpu_clock'), '4850MHz');
  assert.strictEqual(formatValue(12.345, 'ram_used'), '12.3GB');
  assert.strictEqual(formatValue(1.26, 'net_download'), '1.3MB/s');
  assert.strictEqual(formatValue(42, 'static'), '42%');
});

test('gradient interpolation and colors', () => {
  const stops = [[0, '#000000'], [1, '#ffffff']];
  assert.strictEqual(interpolateGradient(stops, 0.5), '#808080');
  assert.strictEqual(interpolateGradient(stops, -1), '#000000');
  assert.strictEqual(interpolateGradient([[1, '#ffffff'], [0, '#000000']], 1), '#ffffff');
  assert.strictEqual(rgba('#ff0000', 50), 'rgba(255, 0, 0, 0.5)');
  assert.strictEqual(autoColor('#00ff00', 65, 'cpu_temp'), '#ffcc00');
  assert.strictEqual(autoColor('#00ff00', 65, 'cpu_percent'), '#00ff00');
  assert.strictEqual(autoColor('#00ff00', 95, 'gpu_percent'), '#ff3232');
});

test('round-trips the bundled Default preset', () => {
  const data = JSON.parse(fs.readFileSync(new URL('../presets/Default.json', import.meta.url)));
  for (const raw of data.elements) {
    const out = serializeElement(normalizeElement(raw));
    for (const [key, value] of Object.entries(raw)) assert.deepStrictEqual(out[key], value, `${raw.name}.${key}`);
  }
});

test('fills defaults that follow the element color', () => {
  const text = normalizeElement({ type: 'text', color: '#123456' });
  assert.strictEqual(text.text_color, '#123456');
  const gauge = normalizeElement({ type: 'circle_gauge', color: '#123456' });
  assert.strictEqual(gauge.text_color, '#ffffff');
  assert.strictEqual(gauge.label_text_color, '#123456');
  assert.strictEqual(normalizeElement({ type: 'bar_gauge' }).bar_text_position, 'top');
});

test('creates elements with type defaults and unique names', () => {
  const a = createElement('circle_gauge', []);
  const b = createElement('circle_gauge', [a]);
  assert.strictEqual(a.radius, 120);
  assert.strictEqual(a.name, 'circle_gauge_1');
  assert.strictEqual(b.name, 'circle_gauge_2');
  assert.strictEqual(createElement('line_chart', []).source, 'cpu_percent');
});

test('keeps group members contiguous', () => {
  const [a, b, c, d] = ['a', 'b', 'c', 'd'].map((name) => ({ name, group: null }));
  b.group = 'G';
  d.group = 'G';
  assert.deepStrictEqual(normalizeGroups([a, b, c, d]).map((e) => e.name), ['a', 'b', 'd', 'c']);
});

test('formats clock text', () => {
  const date = new Date(2026, 0, 1, 9, 5, 7);
  const base = { time_format: '24h', show_seconds: true, show_am_pm: true, show_leading_zero: true };
  assert.strictEqual(formatClock(date, base), '09:05:07');
  assert.strictEqual(formatClock(date, { ...base, show_leading_zero: false, show_seconds: false }), '9:05');
  assert.strictEqual(formatClock(new Date(2026, 0, 1, 21, 5, 7), { ...base, time_format: '12h' }), '09:05:07 PM');
  assert.strictEqual(formatClock(new Date(2026, 0, 1, 0, 0, 0), { ...base, time_format: '12h', show_am_pm: false }), '12:00:00');
});
