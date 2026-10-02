import { rgba } from '../color.js';
import { roundRectPath } from '../draw-utils.js';

let scratch = null;
function scratchCanvas(w, h) {
  if (!scratch) scratch = new OffscreenCanvas(w, h);
  if (scratch.width < w) scratch.width = w;
  if (scratch.height < h) scratch.height = h;
  const ctx = scratch.getContext('2d');
  ctx.clearRect(0, 0, scratch.width, scratch.height);
  return { canvas: scratch, ctx };
}

/** Frosted glass: blur whatever is already drawn beneath, then tint it. */
function drawGlass(ctx, el) {
  const { x, y, width: w, height: h } = el;
  const blur = Math.max(0, el.glass_blur);
  if (w > 0 && h > 0 && blur > 0) {
    // Copy a padded region so the blur doesn't pull in transparent edges.
    const pad = Math.ceil(blur * 2);
    const sx = Math.max(0, Math.floor(x - pad));
    const sy = Math.max(0, Math.floor(y - pad));
    const sw = Math.min(ctx.canvas.width - sx, Math.ceil(w + pad * 2));
    const sh = Math.min(ctx.canvas.height - sy, Math.ceil(h + pad * 2));
    if (sw > 0 && sh > 0) {
      const tmp = scratchCanvas(sw, sh);
      tmp.ctx.drawImage(ctx.canvas, sx, sy, sw, sh, 0, 0, sw, sh);
      ctx.save();
      roundRectPath(ctx, x, y, w, h, el.border_radius);
      ctx.clip();
      ctx.filter = `blur(${blur}px)`;
      ctx.drawImage(tmp.canvas, 0, 0, sw, sh, sx, sy, sw, sh);
      ctx.restore();
    }
  }

  ctx.save();
  roundRectPath(ctx, x, y, w, h, el.border_radius);
  ctx.fillStyle = rgba(el.color, el.glass_opacity);
  ctx.fill();
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.16)';
  ctx.lineWidth = 1;
  ctx.stroke();
  ctx.restore();
}

export default {
  type: 'rectangle',
  name: 'Rectangle',
  defaults: { width: 200, height: 100, x: 100, y: 100, border_radius: 0, glass_effect: false, glass_blur: 10, glass_opacity: 50 },

  draw(ctx, el) {
    if (el.glass_effect) {
      drawGlass(ctx, el);
      return;
    }
    ctx.save();
    ctx.fillStyle = rgba(el.color, el.color_opacity);
    roundRectPath(ctx, el.x, el.y, el.width, el.height, el.border_radius);
    ctx.fill();
    ctx.restore();
  },
};
