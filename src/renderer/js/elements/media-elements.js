import { getImage, getGif, gifFrameAt } from '../media.js';

function drawPlaceholder(ctx, el, label, error = false) {
  ctx.save();
  ctx.fillStyle = error ? 'rgb(60, 40, 40)' : 'rgb(40, 40, 60)';
  ctx.fillRect(el.x, el.y, el.width, el.height);
  ctx.strokeStyle = error ? 'rgb(150, 100, 100)' : 'rgb(100, 100, 120)';
  ctx.lineWidth = 1;
  ctx.strokeRect(el.x + 0.5, el.y + 0.5, el.width - 1, el.height - 1);
  ctx.fillStyle = ctx.strokeStyle;
  ctx.font = '20px Arial, sans-serif';
  ctx.textBaseline = 'middle';
  ctx.textAlign = 'left';
  ctx.fillText(label.slice(0, 30), el.x + 10, el.y + el.height / 2);
  ctx.restore();
}

/** Draw `source` into the element box using fit / fill / stretch scaling. */
function drawScaled(ctx, source, sw, sh, el, mode) {
  const { x, y, width: w, height: h } = el;
  if (mode === 'stretch') {
    ctx.drawImage(source, x, y, w, h);
  } else if (mode === 'fill') {
    const scale = Math.max(w / sw, h / sh);
    const cw = w / scale;
    const ch = h / scale;
    ctx.drawImage(source, (sw - cw) / 2, (sh - ch) / 2, cw, ch, x, y, w, h);
  } else if (mode === 'fit-top-left') {
    const scale = Math.min(w / sw, h / sh, 1);
    ctx.drawImage(source, x, y, sw * scale, sh * scale);
  } else {
    const scale = Math.min(w / sw, h / sh);
    const dw = sw * scale;
    const dh = sh * scale;
    ctx.drawImage(source, x + (w - dw) / 2, y + (h - dh) / 2, dw, dh);
  }
}

export const imageElement = {
  type: 'image',
  name: 'Image',
  defaults: { width: 200, height: 200, x: 100, y: 100 },

  draw(ctx, el) {
    if (!el.image_path) return drawPlaceholder(ctx, el, 'No Image');
    const entry = getImage(el.image_path);
    if (!entry) return undefined; // still loading
    if (entry.error) return drawPlaceholder(ctx, el, entry.error, true);
    const img = entry.image;
    ctx.save();
    ctx.globalAlpha = el.color_opacity / 100;
    // Proportional images shrink to fit, anchored at the top-left (as before).
    drawScaled(ctx, img, img.naturalWidth, img.naturalHeight, el, el.scale_proportionally ? 'fit-top-left' : 'stretch');
    ctx.restore();
    return undefined;
  },
};

export const gifElement = {
  type: 'gif',
  name: 'GIF Image',
  defaults: { x: 100, y: 100, width: 200, height: 200, gif_path: '', scale_mode: 'fit' },

  draw(ctx, el, env) {
    if (!el.gif_path) return drawPlaceholder(ctx, el, 'No GIF');
    const entry = getGif(el.gif_path);
    if (!entry) return drawPlaceholder(ctx, el, 'Loading GIF...');
    if (entry.error) return drawPlaceholder(ctx, el, entry.error, true);
    const frame = gifFrameAt(entry, env.perfNow);
    ctx.save();
    ctx.globalAlpha = el.color_opacity / 100;
    drawScaled(ctx, frame.bitmap, frame.bitmap.width, frame.bitmap.height, el, el.scale_mode);
    ctx.restore();
    return undefined;
  },
};
