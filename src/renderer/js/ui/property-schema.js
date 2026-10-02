/**
 * Which properties each element type shows, grouped into sections.
 * `types` limits a field to some element types; `when(el)` hides it
 * depending on other values.
 */

import { TEMP_SOURCES } from '../constants.js';

const GAUGES = ['circle_gauge', 'bar_gauge'];
const SIZED = ['bar_gauge', 'text', 'rectangle', 'clock', 'image', 'gif', 'line_chart'];
const RADIAL = ['circle_gauge', 'analog_clock'];
const HAS_SOURCE = ['circle_gauge', 'bar_gauge', 'text', 'line_chart'];

export const SECTIONS = [
  {
    title: 'General',
    fields: [
      { kind: 'text', key: 'name', label: 'Name' },
      { kind: 'checkbox', key: 'locked', label: 'Locked' },
    ],
  },
  {
    title: 'Transform',
    fields: [
      { kind: 'pair', label: 'Position', fields: [
        { kind: 'number', key: 'x', prefix: 'X', min: -2000, max: 4000 },
        { kind: 'number', key: 'y', prefix: 'Y', min: -2000, max: 4000 },
      ] },
      { kind: 'pair', label: 'Size', types: SIZED, fields: [
        { kind: 'number', key: 'width', prefix: 'W', min: 1, max: 4000 },
        { kind: 'number', key: 'height', prefix: 'H', min: 1, max: 4000 },
      ] },
      { kind: 'number', key: 'radius', label: 'Radius', types: RADIAL, min: 10, max: 1000 },
    ],
  },
  {
    title: 'Colors',
    fields: [
      { kind: 'checkbox', key: 'gradient_fill', label: 'Gradient fill', types: GAUGES },
      { kind: 'gradient', key: 'gradient_stops', label: 'Gradient', types: GAUGES, when: (el) => el.gradient_fill },
      {
        kind: 'color', key: 'color', opacityKey: 'color_opacity', label: 'Color',
        types: ['circle_gauge', 'bar_gauge', 'text', 'rectangle', 'clock', 'analog_clock', 'line_chart'],
        when: (el) => !(GAUGES.includes(el.type) && el.gradient_fill) && !(el.type === 'rectangle' && el.glass_effect),
      },
      { kind: 'color', key: 'color', label: 'Tint', types: ['rectangle'], when: (el) => el.glass_effect },
      { kind: 'number', key: 'color_opacity', label: 'Opacity', types: ['image', 'gif'], min: 0, max: 100, suffix: '%' },
      { kind: 'color', key: 'background_color', opacityKey: 'background_color_opacity', label: 'Background', types: ['circle_gauge', 'bar_gauge', 'analog_clock', 'line_chart'] },
      { kind: 'checkbox', key: 'bar_border', label: 'Border', types: ['bar_gauge'] },
      { kind: 'color', key: 'bar_border_color', opacityKey: 'bar_border_opacity', label: 'Border color', types: ['bar_gauge'], when: (el) => el.bar_border },
      { kind: 'number', key: 'bar_border_width', label: 'Border width', types: ['bar_gauge'], min: 1, max: 20, when: (el) => el.bar_border },
      { kind: 'select', key: 'bar_border_position', label: 'Border position', types: ['bar_gauge'], when: (el) => el.bar_border, options: [['inside', 'Inside'], ['center', 'Center'], ['outside', 'Outside']] },
    ],
  },
  {
    title: 'Appearance',
    fields: [
      { kind: 'number', key: 'border_radius', label: 'Corner radius', types: ['rectangle'], min: 0, max: 500 },
      { kind: 'checkbox', key: 'glass_effect', label: 'Frosted glass', types: ['rectangle'] },
      { kind: 'number', key: 'glass_blur', label: 'Blur', types: ['rectangle'], min: 1, max: 50, when: (el) => el.glass_effect },
      { kind: 'number', key: 'glass_opacity', label: 'Tint opacity', types: ['rectangle'], min: 0, max: 100, suffix: '%', when: (el) => el.glass_effect },
    ],
  },
  {
    title: 'Text',
    fields: [
      { kind: 'select', key: 'bar_text_mode', label: 'Show', types: ['bar_gauge'], options: [['full', 'Label + value'], ['value_only', 'Value only'], ['label_only', 'Label only'], ['none', 'Nothing']] },
      { kind: 'select', key: 'bar_text_position', label: 'Position', types: ['bar_gauge'], when: (el) => el.bar_text_mode !== 'none', options: [['top', 'Top'], ['bottom', 'Bottom'], ['left', 'Left'], ['right', 'Right'], ['inside', 'Inside']] },
      { kind: 'text', key: 'text', label: 'Text', types: ['text', 'line_chart'] },
      { kind: 'subheading', label: 'Value', types: GAUGES },
      { kind: 'font', label: 'Font', types: ['circle_gauge', 'bar_gauge', 'text', 'clock', 'analog_clock', 'line_chart'] },
      { kind: 'color', key: 'text_color', opacityKey: 'text_color_opacity', label: 'Text color', types: ['circle_gauge', 'bar_gauge', 'analog_clock'] },
      { kind: 'checkbox', key: 'use_custom_text_color', label: 'Custom text color', types: ['line_chart'] },
      { kind: 'color', key: 'text_color', opacityKey: 'text_color_opacity', label: 'Text color', types: ['line_chart'], when: (el) => el.use_custom_text_color },
      { kind: 'align', key: 'text_align', label: 'Align', types: ['text', 'clock'] },
      { kind: 'checkbox', key: 'clip', label: 'Clip to box', types: ['text', 'clock'] },
      { kind: 'subheading', label: 'Label', types: GAUGES },
      { kind: 'text', key: 'text', label: 'Label', types: GAUGES },
      { kind: 'font', label: 'Font', prefix: 'label_', types: GAUGES },
      { kind: 'color', key: 'label_text_color', label: 'Label color', types: GAUGES },
    ],
  },
  {
    title: 'Data',
    fields: [
      { kind: 'source', key: 'source', label: 'Source', types: HAS_SOURCE },
      { kind: 'number', key: 'value', label: 'Preview value', types: HAS_SOURCE, min: 0, max: 10000, step: 1, when: (el) => el.source === 'static' },
      { kind: 'checkbox', key: 'temp_hide_unit', label: 'Show ° only', types: HAS_SOURCE, when: (el) => TEMP_SOURCES.has(el.source) },
    ],
  },
  {
    title: 'Media',
    fields: [
      { kind: 'file', key: 'image_path', label: 'Image', media: 'image', types: ['image'] },
      { kind: 'checkbox', key: 'scale_proportionally', label: 'Keep aspect ratio', types: ['image'] },
      { kind: 'file', key: 'gif_path', label: 'GIF', media: 'gif', types: ['gif'] },
      { kind: 'select', key: 'scale_mode', label: 'Scaling', types: ['gif'], options: [['fit', 'Fit'], ['fill', 'Fill'], ['stretch', 'Stretch']] },
    ],
  },
  {
    title: 'Options',
    fields: [
      { kind: 'checkbox', key: 'auto_color_change', label: 'Warning colors', types: GAUGES, when: (el) => !el.gradient_fill },
      { kind: 'checkbox', key: 'animate_gauge', label: 'Animate changes', types: GAUGES },
      { kind: 'checkbox', key: 'gauge_rounded_ends', label: 'Rounded ends', types: ['circle_gauge'] },
      { kind: 'checkbox', key: 'rounded_corners', label: 'Rounded corners', types: ['bar_gauge'] },
      { kind: 'checkbox', key: 'show_background', label: 'Background', types: ['line_chart'] },
      { kind: 'checkbox', key: 'show_label', label: 'Label', types: ['line_chart'] },
      { kind: 'checkbox', key: 'show_gradient', label: 'Fill under line', types: ['line_chart'] },
      { kind: 'checkbox', key: 'smooth', label: 'Smooth line', types: ['line_chart'] },
      { kind: 'number', key: 'line_thickness', label: 'Line thickness', types: ['line_chart'], min: 1, max: 20 },
      { kind: 'select', key: 'time_format', label: 'Format', types: ['clock'], options: [['24h', '24-hour'], ['12h', '12-hour']] },
      { kind: 'checkbox', key: 'show_am_pm', label: 'AM/PM', types: ['clock'], when: (el) => el.time_format === '12h' },
      { kind: 'checkbox', key: 'show_seconds', label: 'Seconds', types: ['clock'] },
      { kind: 'checkbox', key: 'show_leading_zero', label: 'Leading zero', types: ['clock'] },
      { kind: 'select', key: 'clock_face_style', label: 'Face', types: ['analog_clock'], options: [['numbers', 'Numbers'], ['ticks', 'Ticks'], ['none', 'None']] },
      { kind: 'checkbox', key: 'show_seconds_hand', label: 'Seconds hand', types: ['analog_clock'] },
      { kind: 'checkbox', key: 'show_clock_border', label: 'Border', types: ['analog_clock'] },
      { kind: 'checkbox', key: 'smooth_animation', label: 'Smooth sweep', types: ['analog_clock'] },
    ],
  },
];

export function fieldApplies(field, el) {
  return !field.types || field.types.includes(el.type);
}

export function fieldVisible(field, el) {
  return fieldApplies(field, el) && (!field.when || field.when(el));
}
