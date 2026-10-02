/** Gradient stop editor dialog. */

import { h, showModal } from './dom.js';

const PRESETS = [
  ['Green → Red', [[0, '#00ff96'], [1, '#ff4444']]],
  ['Traffic light', [[0, '#00ff96'], [0.5, '#ffcc00'], [1, '#ff3232']]],
  ['Cool', [[0, '#00c8ff'], [1, '#c864ff']]],
  ['Fire', [[0, '#ffcc00'], [0.5, '#ff6a00'], [1, '#ff0040']]],
  ['Ice', [[0, '#ffffff'], [1, '#00a2ff']]],
];

export function gradientCss(stops) {
  const sorted = [...(stops || [])].sort((a, b) => a[0] - b[0]);
  if (!sorted.length) return '#444';
  if (sorted.length === 1) return sorted[0][1];
  return `linear-gradient(to right, ${sorted.map(([p, c]) => `${c} ${Math.round(p * 100)}%`).join(', ')})`;
}

/** Open the editor; resolves with new stops or null if cancelled. */
export async function editGradient(initialStops) {
  let stops = structuredClone(initialStops || PRESETS[0][1]);
  const preview = h('div', { className: 'gradient-bar' });
  const list = h('div', { className: 'stop-list' });

  const redraw = () => {
    preview.style.background = gradientCss(stops);
    list.replaceChildren(...stops.map((stop, i) => {
      const color = h('input', { type: 'color', className: 'color-input', value: stop[1], oninput: () => { stop[1] = color.value; preview.style.background = gradientCss(stops); } });
      const pos = h('input', { type: 'range', min: 0, max: 100, className: 'range', value: Math.round(stop[0] * 100), oninput: () => {
        stop[0] = Number(pos.value) / 100;
        posLabel.textContent = `${pos.value}%`;
        preview.style.background = gradientCss(stops);
      } });
      const posLabel = h('span', { className: 'range-value' }, `${Math.round(stop[0] * 100)}%`);
      const remove = h('button', { className: 'btn icon', title: 'Remove stop', disabled: stops.length <= 2, onclick: () => { stops.splice(i, 1); redraw(); } }, '✕');
      return h('div', { className: 'stop-row' }, color, pos, posLabel, remove);
    }));
  };

  const addStop = () => {
    const sorted = [...stops].sort((a, b) => a[0] - b[0]);
    // Insert in the widest gap.
    let best = 0;
    for (let i = 1; i < sorted.length - 1; i++) if (sorted[i + 1][0] - sorted[i][0] > sorted[best + 1][0] - sorted[best][0]) best = i;
    const pos = sorted.length > 1 ? (sorted[best][0] + sorted[best + 1][0]) / 2 : 0.5;
    stops.push([pos, sorted[best]?.[1] || '#ffffff']);
    redraw();
  };

  const presetButtons = PRESETS.map(([name, presetStops]) => h('button', {
    className: 'preset-swatch',
    title: name,
    style: { background: gradientCss(presetStops) },
    onclick: () => { stops = structuredClone(presetStops); redraw(); },
  }));

  redraw();
  const result = await showModal({
    title: 'Edit Gradient',
    width: 440,
    body: h('div', { className: 'gradient-editor' },
      preview,
      h('div', { className: 'subheading' }, 'Presets'),
      h('div', { className: 'button-row wrap' }, presetButtons),
      h('div', { className: 'subheading' }, 'Color stops'),
      list,
      h('button', { className: 'btn', onclick: addStop }, '＋ Add stop')),
    buttons: [{ label: 'Cancel', value: null }, { label: 'Apply', value: 'ok', primary: true }],
  });
  return result === 'ok' ? stops.sort((a, b) => a[0] - b[0]) : null;
}
