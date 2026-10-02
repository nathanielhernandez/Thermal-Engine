const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');
const { validateTheme, isSafePath, isSafeFilename, sanitizePresetName } = require('../src/main/validation');

test('bundled presets are valid', () => {
  const dir = path.join(__dirname, '..', 'presets');
  for (const file of fs.readdirSync(dir).filter((f) => f.endsWith('.json'))) {
    const result = validateTheme(JSON.parse(fs.readFileSync(path.join(dir, file), 'utf8')));
    assert.ok(result.valid, `${file}: ${result.errors.join(', ')}`);
  }
});

test('rejects malformed themes', () => {
  assert.strictEqual(validateTheme([]).valid, false);
  assert.strictEqual(validateTheme({ extra: 1 }).valid, false);
  assert.strictEqual(validateTheme({ background_color: 'red' }).valid, false);
  assert.strictEqual(validateTheme({ elements: [{ x: 1 }] }).valid, false);
  assert.strictEqual(validateTheme({ elements: [{ type: 'text', x: '5' }] }).valid, false);
  assert.strictEqual(validateTheme({ elements: [{ type: 'image', image_path: 'C:\\a\\..\\b.png' }] }).valid, false);
  assert.strictEqual(validateTheme({ name: 'ok', elements: [{ type: 'text', x: 5, color: '#fff' }] }).valid, true);
  assert.strictEqual(validateTheme({ orientation: 'portrait_inverted', display_width: 480, display_height: 1280 }).valid, true);
  assert.strictEqual(validateTheme({ orientation: 'sideways' }).valid, false);
});

test('path and filename checks', () => {
  assert.strictEqual(isSafePath('C:\\Users\\me\\pic.png').safe, true);
  assert.strictEqual(isSafePath('../secret').safe, false);
  assert.strictEqual(isSafePath('a\0b').safe, false);
  assert.strictEqual(isSafeFilename('My Theme.json').safe, true);
  assert.strictEqual(isSafeFilename('a/b.json').safe, false);
  assert.strictEqual(isSafeFilename('CON.json').safe, false);
  assert.strictEqual(isSafeFilename('what?.json').safe, false);
  assert.strictEqual(sanitizePresetName('  a<b>:c  '), 'abc');
  assert.strictEqual(sanitizePresetName('///'), 'preset');
});
