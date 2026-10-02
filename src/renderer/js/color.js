/** Color helpers. Colors are stored as hex strings, opacity as 0-100. */

export function parseHex(hex) {
  let h = String(hex || '').replace('#', '');
  if (h.length === 3 || h.length === 4) h = [...h].map((c) => c + c).join('');
  const n = (i) => parseInt(h.slice(i, i + 2), 16);
  if (!/^[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$/.test(h)) return { r: 0, g: 0, b: 0, a: 1 };
  return { r: n(0), g: n(2), b: n(4), a: h.length === 8 ? n(6) / 255 : 1 };
}

/** CSS rgba() string for a hex color with 0-100 opacity. */
export function rgba(hex, opacity = 100) {
  const { r, g, b, a } = parseHex(hex);
  return `rgba(${r}, ${g}, ${b}, ${a * Math.max(0, Math.min(100, opacity)) / 100})`;
}

export function toHex({ r, g, b }) {
  return `#${[r, g, b].map((v) => Math.round(v).toString(16).padStart(2, '0')).join('')}`;
}

/** Color at `position` (0-1) along gradient stops [[pos, hex], ...]. */
export function interpolateGradient(stops, position) {
  if (!stops || !stops.length) return '#00ff96';
  const sorted = [...stops].sort((a, b) => a[0] - b[0]);
  const p = Math.max(0, Math.min(1, position));
  if (p <= sorted[0][0]) return sorted[0][1];
  if (p >= sorted[sorted.length - 1][0]) return sorted[sorted.length - 1][1];
  for (let i = 0; i < sorted.length - 1; i++) {
    const [p1, c1] = sorted[i];
    const [p2, c2] = sorted[i + 1];
    if (p >= p1 && p <= p2) {
      const t = p2 === p1 ? 0 : (p - p1) / (p2 - p1);
      const a = parseHex(c1);
      const b = parseHex(c2);
      return toHex({ r: a.r + t * (b.r - a.r), g: a.g + t * (b.g - a.g), b: a.b + t * (b.b - a.b) });
    }
  }
  return sorted[sorted.length - 1][1];
}

/** Threshold color for gauges with auto color change enabled. */
export function autoColor(baseColor, value, source) {
  const [warn, hot] = String(source).includes('temp') ? [60, 80] : [70, 90];
  if (value < warn) return baseColor;
  if (value < hot) return '#ffcc00';
  return '#ff3232';
}
