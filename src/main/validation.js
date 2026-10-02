/**
 * Validation for theme/preset files and user-supplied file names.
 */

const path = require('path');

const ORIENTATIONS = new Set(['landscape', 'portrait', 'landscape_inverted', 'portrait_inverted']);
const HEX_COLOR = /^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})$/;
const RESERVED_NAMES = new Set([
  'CON', 'PRN', 'AUX', 'NUL',
  ...Array.from({ length: 9 }, (_, i) => `COM${i + 1}`),
  ...Array.from({ length: 9 }, (_, i) => `LPT${i + 1}`),
]);

function isValidColor(color) {
  return typeof color === 'string' && HEX_COLOR.test(color);
}

/** Reject paths with null bytes or `..` segments. */
function isSafePath(filePath) {
  if (!filePath || typeof filePath !== 'string') return { safe: false, error: 'Empty path' };
  if (filePath.includes('\0')) return { safe: false, error: 'Null byte in path' };
  if (filePath.replace(/\\/g, '/').split('/').some((part) => part === '..' || part === '...')) {
    return { safe: false, error: 'Path traversal detected' };
  }
  return { safe: true, resolved: path.resolve(filePath) };
}

function isSafeFilename(filename) {
  if (!filename) return { safe: false, error: 'Empty filename' };
  if (/[/\\]/.test(filename)) return { safe: false, error: 'Filename contains path separator' };
  if (filename.includes('\0')) return { safe: false, error: 'Null byte in filename' };
  const reserved = /[<>:"|?*]/.exec(filename);
  if (reserved) return { safe: false, error: `Reserved character '${reserved[0]}' in filename` };
  if (RESERVED_NAMES.has(path.parse(filename).name.toUpperCase())) return { safe: false, error: 'Reserved filename' };
  return { safe: true };
}

function sanitizePresetName(name) {
  if (!name) return 'preset';
  // eslint-disable-next-line no-control-regex
  const sanitized = String(name).replace(/[<>:"/\\|?*\x00-\x1f]/g, '').slice(0, 50).trim();
  return sanitized || 'preset';
}

function validateElement(element, index) {
  const errors = [];
  const prefix = `Element ${index}`;
  if (!element || typeof element !== 'object' || Array.isArray(element)) return [`${prefix}: must be an object`];

  if (!('type' in element)) errors.push(`${prefix}: missing 'type'`);
  else if (typeof element.type !== 'string') errors.push(`${prefix}: 'type' must be a string`);

  for (const field of ['x', 'y', 'width', 'height', 'radius', 'font_size', 'value']) {
    if (!(field in element)) continue;
    const val = element[field];
    if (typeof val !== 'number' || Number.isNaN(val)) errors.push(`${prefix}: '${field}' must be numeric`);
    else if (val < -10000 || val > 10000) errors.push(`${prefix}: '${field}' out of range`);
  }

  for (const field of ['color', 'background_color']) {
    if (element[field] && !isValidColor(element[field])) errors.push(`${prefix}: invalid '${field}' format`);
  }

  for (const field of ['image_path', 'gif_path']) {
    if (!element[field]) continue;
    const check = isSafePath(element[field]);
    if (!check.safe) errors.push(`${prefix}: ${field}: ${check.error}`);
  }

  for (const field of ['name', 'text', 'font_family', 'source']) {
    if (!(field in element)) continue;
    if (typeof element[field] !== 'string') errors.push(`${prefix}: '${field}' must be a string`);
    else if (element[field].length > 500) errors.push(`${prefix}: '${field}' too long`);
  }
  return errors;
}

/** Validate theme JSON. Returns { valid, errors }. */
function validateTheme(data) {
  const errors = [];
  if (!data || typeof data !== 'object' || Array.isArray(data)) return { valid: false, errors: ['Root must be an object'] };

  const allowed = new Set(['name', 'background_color', 'orientation', 'display_width', 'display_height', 'elements', 'video_background']);
  for (const key of Object.keys(data)) {
    if (!allowed.has(key)) errors.push(`Unknown key: ${key}`);
  }

  if ('name' in data) {
    if (typeof data.name !== 'string') errors.push("'name' must be a string");
    else if (data.name.length > 100) errors.push("'name' too long (max 100 chars)");
  }
  if ('background_color' in data && !isValidColor(data.background_color)) errors.push("Invalid 'background_color' format");
  if ('orientation' in data && !ORIENTATIONS.has(data.orientation)) errors.push("Invalid 'orientation' value");

  for (const dim of ['display_width', 'display_height']) {
    if (dim in data && (!Number.isInteger(data[dim]) || data[dim] < 0 || data[dim] > 10000)) errors.push(`Invalid '${dim}' value`);
  }

  if ('elements' in data) {
    if (!Array.isArray(data.elements)) errors.push("'elements' must be a list");
    else data.elements.forEach((el, i) => errors.push(...validateElement(el, i)));
  }

  if ('video_background' in data) {
    const vb = data.video_background;
    if (!vb || typeof vb !== 'object' || Array.isArray(vb)) errors.push("'video_background' must be an object");
    else if (vb.video_path) {
      const check = isSafePath(vb.video_path);
      if (!check.safe) errors.push(`video_background path: ${check.error}`);
    }
  }

  return { valid: errors.length === 0, errors };
}

module.exports = { validateTheme, isValidColor, isSafePath, isSafeFilename, sanitizePresetName };
