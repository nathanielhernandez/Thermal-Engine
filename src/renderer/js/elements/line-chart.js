import { rgba } from '../color.js';
import { formatValue } from '../constants.js';
import { fontString } from '../draw-utils.js';

const MAX_HISTORY = 100;
const SAMPLE_INTERVAL_MS = 50;

// History is keyed by element name so it survives undo/redo (which recreates element objects).
const histories = new Map();

function record(el, now) {
  let h = histories.get(el.name);
  if (!h) {
    h = { values: [], last: 0 };
    histories.set(el.name, h);
  }
  if (now - h.last >= SAMPLE_INTERVAL_MS) {
    h.values.push(Number(el.value) || 0);
    if (h.values.length > MAX_HISTORY) h.values.shift();
    h.last = now;
  }
  return h.values;
}

/** Catmull-Rom spline through `points` with `steps` interpolated points per segment. */
export function catmullRom(points, steps = 8) {
  if (points.length < 3) return points;
  const pts = [points[0], ...points, points[points.length - 1]];
  const out = [];
  for (let i = 1; i < pts.length - 2; i++) {
    const [p0, p1, p2, p3] = [pts[i - 1], pts[i], pts[i + 1], pts[i + 2]];
    for (let s = 0; s < steps; s++) {
      const t = s / steps;
      const t2 = t * t;
      const t3 = t2 * t;
      const f = (a, b, c, d) => 0.5 * ((2 * b) + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t2 + (-a + 3 * b - 3 * c + d) * t3);
      out.push([f(p0[0], p1[0], p2[0], p3[0]), f(p0[1], p1[1], p2[1], p3[1])]);
    }
  }
  out.push(pts[pts.length - 2]);
  return out;
}

export default {
  type: 'line_chart',
  name: 'Line Chart',
  defaults: {
    x: 100, y: 100, width: 300, height: 100, color: '#00ff96', background_color: '#1a1a2e',
    source: 'cpu_percent', value: 50, text: 'CPU', font_size: 14,
    show_background: true, show_label: true, show_gradient: true, line_thickness: 2, smooth: false,
  },

  draw(ctx, el, env) {
    const { x, y, width: w, height: h } = el;
    ctx.save();

    if (el.show_background) {
      ctx.fillStyle = rgba(el.background_color, el.background_color_opacity);
      ctx.fillRect(x, y, w, h);
      ctx.strokeStyle = 'rgb(60, 60, 80)';
      ctx.lineWidth = 1;
      ctx.strokeRect(x + 0.5, y + 0.5, w - 1, h - 1);
    }

    const history = record(el, env.perfNow);
    const count = Math.min(history.length, Math.floor(w / 3));
    if (count >= 2) {
      const slice = history.slice(-count);
      let points = slice.map((v, i) => [
        x + (i / (count - 1)) * w,
        y + h - (Math.max(0, Math.min(100, v)) / 100) * h,
      ]);
      if (el.smooth) points = catmullRom(points);

      if (el.show_gradient) {
        const grad = ctx.createLinearGradient(x, y, x, y + h);
        grad.addColorStop(0, rgba(el.color, (100 / 255) * el.color_opacity));
        grad.addColorStop(1, rgba(el.color, (20 / 255) * el.color_opacity));
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.moveTo(points[0][0], y + h);
        for (const [px, py] of points) ctx.lineTo(px, py);
        ctx.lineTo(points[points.length - 1][0], y + h);
        ctx.closePath();
        ctx.fill();
      }

      const color = rgba(el.color, el.color_opacity);
      ctx.strokeStyle = color;
      ctx.lineWidth = el.line_thickness;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      ctx.beginPath();
      points.forEach(([px, py], i) => (i ? ctx.lineTo(px, py) : ctx.moveTo(px, py)));
      ctx.stroke();

      const [lx, ly] = points[points.length - 1];
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(lx, ly, Math.max(3, el.line_thickness + 1), 0, Math.PI * 2);
      ctx.fill();
    }

    if (el.show_label) {
      ctx.font = fontString(el.font_family, el.font_size, el.font_bold, el.font_italic);
      ctx.fillStyle = el.use_custom_text_color
        ? rgba(el.text_color, el.text_color_opacity)
        : rgba(el.color, el.color_opacity);
      ctx.textAlign = 'left';
      ctx.textBaseline = 'top';
      ctx.fillText(`${el.text}: ${formatValue(el.value, el.source, el.temp_hide_unit)}`, x + 5, y + 2);
    }
    ctx.restore();
  },
};
