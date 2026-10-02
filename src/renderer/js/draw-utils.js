/** Canvas drawing helpers shared by the element renderers. */

export function fontString(family, size, bold = false, italic = false) {
  const safeFamily = String(family || 'Arial').replace(/["\\]/g, '');
  return `${italic ? 'italic ' : ''}${bold ? 'bold ' : ''}${Math.max(1, size)}px "${safeFamily}", sans-serif`;
}

/** Measure text with the current font. Height uses the font box like Qt's fontMetrics(). */
export function measure(ctx, text) {
  const m = ctx.measureText(text);
  const ascent = m.fontBoundingBoxAscent ?? m.actualBoundingBoxAscent;
  const descent = m.fontBoundingBoxDescent ?? m.actualBoundingBoxDescent;
  return { width: m.width, ascent, descent, height: ascent + descent };
}

/**
 * Draw `text` vertically centered on `centerY` (font box), starting at `x`.
 * Returns the advance width.
 */
export function drawTextCentered(ctx, text, x, centerY) {
  const m = measure(ctx, text);
  ctx.textBaseline = 'alphabetic';
  ctx.textAlign = 'left';
  ctx.fillText(text, x, centerY - m.height / 2 + m.ascent);
  return m.width;
}

export function roundRectPath(ctx, x, y, w, h, r) {
  ctx.beginPath();
  if (r > 0) ctx.roundRect(x, y, w, h, Math.min(r, w / 2, h / 2));
  else ctx.rect(x, y, w, h);
}

/** strftime-style clock text: 24h/12h, optional seconds, AM/PM and leading zero. */
export function formatClock(date, { time_format: format, show_seconds: seconds, show_am_pm: amPm, show_leading_zero: leadingZero }) {
  const pad = (n) => String(n).padStart(2, '0');
  let hours = date.getHours();
  let suffix = '';
  if (format === '12h') {
    suffix = amPm ? (hours < 12 ? ' AM' : ' PM') : '';
    hours = hours % 12 || 12;
  }
  let text = `${pad(hours)}:${pad(date.getMinutes())}`;
  if (seconds) text += `:${pad(date.getSeconds())}`;
  if (!leadingZero && text[0] === '0') text = text.slice(1);
  return text + suffix;
}
