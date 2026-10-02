import { rgba, autoColor } from '../color.js';
import { formatValue } from '../constants.js';
import { fontString, measure, drawTextCentered, roundRectPath } from '../draw-utils.js';

const TEXT_GAP_SIDE = 10;
const TEXT_GAP_VERTICAL = 16;

function textParts(el, value) {
  const valueText = formatValue(value, el.source, el.temp_hide_unit);
  const valuePart = {
    text: valueText,
    font: fontString(el.font_family, el.font_size, el.font_bold, el.font_italic),
    color: rgba(el.text_color, el.text_color_opacity),
  };
  const labelPart = (text) => ({
    text,
    font: fontString(el.label_font_family, el.label_font_size, el.label_font_bold, el.label_font_italic),
    color: rgba(el.label_text_color, el.text_color_opacity),
  });
  switch (el.bar_text_mode) {
    case 'full': return [labelPart(`${el.text} `), valuePart];
    case 'value_only': return [valuePart];
    case 'label_only': return [labelPart(el.text)];
    default: return [];
  }
}

function drawText(ctx, el, value) {
  const parts = textParts(el, value);
  if (!parts.length) return;
  for (const part of parts) {
    ctx.font = part.font;
    Object.assign(part, measure(ctx, part.text));
  }
  const total = parts.reduce((sum, p) => sum + p.width, 0);
  const maxHeight = Math.max(...parts.map((p) => p.height));
  const { x, y, width: w, height: h } = el;

  let startX = x + (w - total) / 2;
  let centerY = y + h / 2;
  switch (el.bar_text_position) {
    case 'left': startX = x - total - TEXT_GAP_SIDE; break;
    case 'right': startX = x + w + TEXT_GAP_SIDE; break;
    case 'top': centerY = y - TEXT_GAP_VERTICAL - maxHeight / 2; break;
    case 'bottom': centerY = y + h + TEXT_GAP_VERTICAL + maxHeight / 2; break;
    default: break;
  }

  let cursor = startX;
  for (const part of parts) {
    ctx.font = part.font;
    ctx.fillStyle = part.color;
    cursor += drawTextCentered(ctx, part.text, cursor, centerY);
  }
}

function drawBorder(ctx, el, cornerRadius) {
  const bw = el.bar_border_width;
  const half = bw / 2;
  const [offset, sizeAdjust, radiusAdjust] = {
    inside: [half, -bw, -half],
    outside: [-half, bw, half],
  }[el.bar_border_position] || [0, 0, 0];

  ctx.strokeStyle = rgba(el.bar_border_color, el.bar_border_opacity);
  ctx.lineWidth = bw;
  roundRectPath(
    ctx,
    el.x + offset,
    el.y + offset,
    el.width + sizeAdjust,
    el.height + sizeAdjust,
    el.rounded_corners ? Math.max(0, cornerRadius + radiusAdjust) : 0,
  );
  ctx.stroke();
}

export default {
  type: 'bar_gauge',
  name: 'Bar Gauge',
  defaults: { width: 300, height: 30, x: 100, y: 100, text: 'BAR' },

  draw(ctx, el, env) {
    const value = env.displayValue(el);
    const fraction = Math.max(0, Math.min(100, value)) / 100;
    const { x, y, width: w, height: h } = el;
    const cornerRadius = el.rounded_corners ? h / 2 : 0;

    ctx.save();
    ctx.fillStyle = rgba(el.background_color, el.background_color_opacity);
    roundRectPath(ctx, x, y, w, h, cornerRadius);
    ctx.fill();

    const fillWidth = w * fraction;
    if (fillWidth > 0) {
      if (el.gradient_fill) {
        // Gradient spans the full bar so colors reflect the absolute level.
        const grad = ctx.createLinearGradient(x, y, x + w, y);
        for (const [pos, color] of el.gradient_stops) grad.addColorStop(pos, color);
        ctx.fillStyle = grad;
        ctx.globalAlpha = el.color_opacity / 100;
      } else {
        const color = el.auto_color_change ? autoColor(el.color, value, el.source) : el.color;
        ctx.fillStyle = rgba(color, el.color_opacity);
      }
      roundRectPath(ctx, x, y, fillWidth, h, Math.min(cornerRadius, fillWidth / 2));
      ctx.fill();
      ctx.globalAlpha = 1;
    }

    if (el.bar_border) drawBorder(ctx, el, cornerRadius);
    drawText(ctx, el, value);
    ctx.restore();
  },
};
