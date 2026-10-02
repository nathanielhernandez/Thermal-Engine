/** Application dialogs: preferences, sensor diagnostics and HWiNFO setup help. */

import { SOURCE_UNITS, formatValue } from '../constants.js';
import { h, showModal } from './dom.js';

export async function showPreferences() {
  const settings = await window.te.settings.all();
  const checkbox = (key, label) => {
    const input = h('input', { type: 'checkbox', checked: !!settings[key] });
    return { key, input, row: h('label', { className: 'check' }, input, h('span', {}, label)) };
  };
  const boxes = [
    checkbox('launch_at_login', 'Launch at Windows startup'),
    checkbox('launch_minimized', 'Start minimized to system tray'),
    checkbox('minimize_to_tray', 'Minimize to system tray instead of taskbar'),
    checkbox('close_to_tray', 'Close button minimizes to tray'),
  ];
  const quality = h('input', { type: 'range', min: 40, max: 100, value: settings.jpeg_quality ?? 80, className: 'range' });
  const qualityLabel = h('span', { className: 'range-value' }, `${quality.value}`);
  quality.addEventListener('input', () => { qualityLabel.textContent = quality.value; });

  const result = await showModal({
    title: 'Preferences',
    width: 420,
    body: h('div', { className: 'prefs' },
      h('div', { className: 'subheading' }, 'Startup'), boxes[0].row, boxes[1].row,
      h('div', { className: 'subheading' }, 'Behavior'), boxes[2].row, boxes[3].row,
      h('div', { className: 'subheading' }, 'Display'),
      h('div', { className: 'field' }, h('label', { className: 'field-label' }, 'JPEG quality'), h('div', { className: 'field-control' }, quality, qualityLabel)),
      h('p', { className: 'hint' }, 'Lower quality sends frames faster; 80 is a good balance.')),
    buttons: [{ label: 'Cancel', value: null }, { label: 'Save', value: 'ok', primary: true }],
  });
  if (result !== 'ok') return null;
  for (const { key, input } of boxes) {
    if (input.checked !== !!settings[key]) await window.te.settings.set(key, input.checked);
  }
  const q = Number(quality.value);
  if (q !== settings.jpeg_quality) await window.te.settings.set('jpeg_quality', q);
  return window.te.settings.all();
}

export async function showDiagnostics() {
  const report = await window.te.sensors.diagnose();
  const status = report.status.hwinfo
    ? h('div', { className: 'status-line ok' }, '● Connected to HWiNFO')
    : h('div', { className: 'status-line bad' }, `● HWiNFO not connected — ${report.status.error || 'unknown error'}`);

  const valueRows = Object.entries(report.values)
    .filter(([key]) => key in SOURCE_UNITS && key !== 'static')
    .map(([key, value]) => {
      const match = report.matches[key];
      const source = match ? `${match.sensor} / ${match.label}` : (key in report.matches ? '— not found —' : 'Windows');
      return h('tr', {}, h('td', {}, SOURCE_UNITS[key].name), h('td', { className: 'num' }, formatValue(value, key)), h('td', { className: 'muted' }, source));
    });

  const filter = h('input', { type: 'search', className: 'text-input', placeholder: 'Filter readings…' });
  const readingsBody = h('tbody');
  const drawReadings = () => {
    const q = filter.value.toLowerCase();
    readingsBody.replaceChildren(...report.readings
      .filter((r) => !q || `${r.sensor} ${r.label}`.toLowerCase().includes(q))
      .slice(0, 500)
      .map((r) => h('tr', {}, h('td', { className: 'muted' }, r.sensor), h('td', {}, r.label), h('td', { className: 'num' }, `${r.value.toFixed(1)} ${r.unit}`))));
  };
  filter.addEventListener('input', drawReadings);
  drawReadings();

  await showModal({
    title: 'Sensor Diagnostics',
    width: 720,
    body: h('div', { className: 'diagnostics' },
      status,
      report.status.hwinfo ? null : hwinfoInstructions(),
      h('div', { className: 'subheading' }, 'Current values'),
      h('table', { className: 'data-table' }, h('tbody', {}, valueRows)),
      report.readings.length ? h('details', {},
        h('summary', {}, `All HWiNFO readings (${report.readings.length})`),
        filter,
        h('div', { className: 'table-scroll' }, h('table', { className: 'data-table' }, readingsBody))) : null),
  });
}

function hwinfoInstructions() {
  return h('ol', { className: 'instructions' },
    h('li', {}, 'Download and install ', h('a', { href: 'https://www.hwinfo.com/download/', target: '_blank' }, 'HWiNFO'), ' (free).'),
    h('li', {}, 'Run HWiNFO in "Sensors-only" mode.'),
    h('li', {}, 'Open Settings (gear icon) and check "Shared Memory Support".'),
    h('li', {}, 'Keep HWiNFO running. Thermal Engine connects automatically.'));
}

export function showHwinfoHelp() {
  return showModal({
    title: 'HWiNFO Required for Sensor Data',
    width: 520,
    body: h('div', {},
      h('p', {}, 'Thermal Engine reads CPU and GPU temperatures, clocks and power from HWiNFO, a free hardware monitoring tool. CPU usage, RAM and network work without it.'),
      hwinfoInstructions(),
      h('p', { className: 'hint' }, 'Tip: set HWiNFO to start with Windows and minimize to the tray. The free version stops sharing data after 12 hours; restart HWiNFO to resume.')),
  });
}
