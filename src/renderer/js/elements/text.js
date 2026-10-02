import { rgba } from '../color.js';
import { formatValue } from '../constants.js';
import { fontString, measure, formatClock } from '../draw-utils.js';

/** Draw single-line text aligned within the element box, optionally clipped to it. */
export function drawBoxText(ctx, el, text) {
  ctx.save();
  if (el.clip) {
    ctx.beginPath();
    ctx.rect(el.x, el.y, el.width, el.height);
    ctx.clip();
  }
  ctx.font = fontString(el.font_family, el.font_size, el.font_bold, el.font_italic);
  ctx.fillStyle = rgba(el.color, el.color_opacity);
  const m = measure(ctx, text);
  let x = el.x + (el.width - m.width) / 2;
  if (el.text_align === 'left') x = el.x;
  else if (el.text_align === 'right') x = el.x + el.width - m.width;
  // Center the font box vertically, like the original Qt layout.
  const baseline = el.y + (el.height + m.height) / 2 - m.descent;
  ctx.textAlign = 'left';
  ctx.textBaseline = 'alphabetic';
  ctx.fillText(text, x, baseline);
  ctx.restore();
}

export const textElement = {
  type: 'text',
  name: 'Text',
  defaults: { x: 100, y: 100, text: 'Text Label', font_size: 36, width: 200, height: 50 },

  draw(ctx, el) {
    let text = el.text;
    if (el.source && el.source !== 'static') {
      const valueText = formatValue(el.value, el.source, el.temp_hide_unit);
      text = el.text ? `${el.text}: ${valueText}` : valueText;
    }
    drawBoxText(ctx, el, text);
  },
};

export const clockElement = {
  type: 'clock',
  name: 'Digital Clock',
  defaults: { x: 100, y: 100, font_size: 48, width: 200, height: 60 },

  draw(ctx, el, env) {
    drawBoxText(ctx, el, formatClock(env.now, el));
  },
};
