import { rgba, autoColor } from '../color.js';
import { formatValue } from '../constants.js';
import { fontString, measure } from '../draw-utils.js';

const ARC_WIDTH = 15;
const START = (135 * Math.PI) / 180;
const SPAN = (270 * Math.PI) / 180;

export default {
  type: 'circle_gauge',
  name: 'Circle Gauge',
  defaults: { radius: 120, x: 200, y: 240, text: 'GAUGE' },

  draw(ctx, el, env) {
    const value = env.displayValue(el);
    const fraction = Math.max(0, Math.min(100, value)) / 100;
    // The arc sits just inside the radius so the gauge fits its bounds.
    const r = Math.max(1, el.radius - ARC_WIDTH / 2);
    const { x, y } = el;

    ctx.save();
    ctx.lineWidth = ARC_WIDTH;
    ctx.lineCap = el.gauge_rounded_ends ? 'round' : 'butt';

    ctx.strokeStyle = rgba(el.background_color, el.background_color_opacity);
    ctx.beginPath();
    ctx.arc(x, y, r, START, START + SPAN);
    ctx.stroke();

    if (fraction > 0) {
      if (el.gradient_fill) {
        // Conic gradient mapped onto the 270° sweep; colors follow arc position.
        const grad = ctx.createConicGradient(START, x, y);
        const stops = [...el.gradient_stops].sort((a, b) => a[0] - b[0]);
        for (const [pos, color] of stops) grad.addColorStop(pos * 0.75, color);
        // Hold the end colors past the sweep so rounded caps don't pick up the wrap-around.
        grad.addColorStop(0.8, stops[stops.length - 1][1]);
        grad.addColorStop(0.9, stops[0][1]);
        grad.addColorStop(1, stops[0][1]);
        ctx.strokeStyle = grad;
        ctx.globalAlpha = el.color_opacity / 100;
      } else {
        const color = el.auto_color_change ? autoColor(el.color, value, el.source) : el.color;
        ctx.strokeStyle = rgba(color, el.color_opacity);
      }
      ctx.beginPath();
      ctx.arc(x, y, r, START, START + SPAN * fraction);
      ctx.stroke();
      ctx.globalAlpha = 1;
    }

    // Value text, centered slightly above the middle.
    ctx.font = fontString(el.font_family, el.font_size, el.font_bold, el.font_italic);
    ctx.fillStyle = rgba(el.text_color, el.text_color_opacity);
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(formatValue(value, el.source, el.temp_hide_unit), x, y - 10);

    // Label below the value.
    ctx.font = fontString(el.label_font_family, el.label_font_size, el.label_font_bold, el.label_font_italic);
    ctx.fillStyle = rgba(el.label_text_color, el.text_color_opacity);
    const m = measure(ctx, el.text);
    ctx.textBaseline = 'alphabetic';
    ctx.fillText(el.text, x, y + el.radius / 3 + m.ascent);
    ctx.restore();
  },
};
