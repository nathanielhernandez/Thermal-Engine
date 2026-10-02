/**
 * Theme element data model. Elements are plain objects so they serialize
 * straight to the same JSON format the Python version used.
 */

import { getElementType } from './elements/index.js';

const GAUGE_TYPES = new Set(['circle_gauge', 'bar_gauge']);

/** Defaults for every element property, matching the original ThemeElement. */
function baseDefaults(type) {
  const color = '#00ff96';
  return {
    type,
    name: '',
    x: 100,
    y: 100,
    width: 200,
    height: 50,
    radius: 100,
    border_radius: 0,
    glass_effect: false,
    glass_blur: 10,
    glass_opacity: 50,
    color,
    color_opacity: 100,
    background_color: '#1a1a2e',
    background_color_opacity: 100,
    use_custom_text_color: false,
    text_color: GAUGE_TYPES.has(type) ? '#ffffff' : color,
    text_color_opacity: 100,
    text: 'Label',
    font_size: 32,
    font_family: 'Arial',
    font_bold: false,
    font_italic: false,
    text_align: 'center',
    clip: false,
    source: 'static',
    value: 50,
    image_path: '',
    scale_proportionally: true,
    aspect_ratio: 1.0,
    show_background: true,
    show_label: true,
    show_gradient: true,
    line_thickness: 2,
    smooth: false,
    rounded_corners: false,
    gradient_fill: false,
    gradient_stops: [[0.0, '#00ff96'], [1.0, '#ff4444']],
    bar_text_mode: 'full',
    bar_text_position: type === 'bar_gauge' ? 'top' : 'inside',
    bar_border: false,
    bar_border_width: 2,
    bar_border_color: '#ffffff',
    bar_border_opacity: 100,
    bar_border_position: 'center',
    auto_color_change: false,
    animate_gauge: false,
    animation_speed: 0.05,
    gauge_rounded_ends: false,
    label_font_size: GAUGE_TYPES.has(type) ? 24 : 16,
    label_font_family: 'Arial',
    label_font_bold: false,
    label_font_italic: false,
    label_text_color: color,
    gif_path: '',
    scale_mode: 'fit',
    time_format: '24h',
    show_am_pm: true,
    show_seconds: true,
    show_leading_zero: true,
    show_seconds_hand: true,
    show_clock_border: true,
    clock_face_style: 'numbers',
    smooth_animation: true,
    group: null,
    locked: false,
    temp_hide_unit: false,
  };
}

const KNOWN_KEYS = Object.keys(baseDefaults('text'));

/**
 * Build a complete element from (possibly partial) saved data.
 * Defaults that depend on other values (like text color) follow the
 * provided `color`, as in the original implementation.
 */
export function normalizeElement(data) {
  const type = typeof data.type === 'string' ? data.type : 'text';
  const defaults = baseDefaults(type);
  if ('color' in data) {
    if (!GAUGE_TYPES.has(type)) defaults.text_color = data.color;
    defaults.label_text_color = data.color;
  }
  const element = { ...defaults };
  for (const key of KNOWN_KEYS) {
    if (key in data && data[key] !== undefined) element[key] = data[key];
  }
  element.gradient_stops = normalizeStops(element.gradient_stops);
  if (!element.name) element.name = `${type}_${Math.random().toString(36).slice(2, 8)}`;
  return element;
}

function normalizeStops(stops) {
  if (!Array.isArray(stops) || !stops.length) return [[0, '#00ff96'], [1, '#ff4444']];
  return stops
    .filter((s) => Array.isArray(s) && s.length >= 2)
    .map(([pos, color]) => [Math.max(0, Math.min(1, Number(pos) || 0)), String(color)]);
}

/** Create a new element of `type` with editor defaults and a unique name. */
export function createElement(type, existingElements = [], props = {}) {
  const typeDef = getElementType(type);
  const element = normalizeElement({ type, ...(typeDef?.defaults || {}), ...props });
  element.name = uniqueName(type, existingElements);
  return element;
}

export function uniqueName(base, existingElements) {
  const names = new Set(existingElements.map((e) => e.name));
  let i = 1;
  while (names.has(`${base}_${i}`)) i++;
  return `${base}_${i}`;
}

export function cloneElement(element) {
  return structuredClone(element);
}

export function serializeElement(element) {
  const out = {};
  for (const key of KNOWN_KEYS) out[key] = element[key];
  return out;
}

/** Element bounds in display pixels: { x, y, w, h }. */
export function elementBounds(el) {
  if (el.type === 'circle_gauge' || el.type === 'analog_clock') {
    return { x: el.x - el.radius, y: el.y - el.radius, w: el.radius * 2, h: el.radius * 2 };
  }
  if (el.width > 0 && el.height > 0) return { x: el.x, y: el.y, w: el.width, h: el.height };
  return { x: el.x, y: el.y, w: 100, h: 50 };
}

export function isRadial(el) {
  return el.type === 'circle_gauge' || el.type === 'analog_clock';
}

/**
 * Keep group members contiguous (in the position of the group's first
 * member) so the layer list and render order always agree.
 */
export function normalizeGroups(elements) {
  const result = [];
  const placed = new Set();
  for (const el of elements) {
    if (placed.has(el)) continue;
    if (el.group) {
      for (const member of elements) {
        if (member.group === el.group) {
          result.push(member);
          placed.add(member);
        }
      }
    } else {
      result.push(el);
      placed.add(el);
    }
  }
  return result;
}
