/**
 * Scene renderer. Draws a theme at display resolution; the same frame is
 * shown in the editor (scaled) and sent to the LCD.
 */

import { DISPLAY_WIDTH, DISPLAY_HEIGHT } from './constants.js';
import { getElementType } from './elements/index.js';

const animated = new WeakMap();

/**
 * Ease gauge values toward their target. Time-based so the motion looks the
 * same at any frame rate (tuned to match the original per-frame easing at 60fps).
 */
function animateValue(el, dt) {
  const target = Number(el.value) || 0;
  if (!el.animate_gauge) {
    animated.delete(el);
    return target;
  }
  const current = animated.get(el);
  if (current === undefined) {
    animated.set(el, target);
    return target;
  }
  const diff = target - current;
  if (Math.abs(diff) < 0.001) {
    animated.set(el, target);
    return target;
  }
  const frames = Math.min(dt * 60, 10);
  const t = Math.min(1, Math.abs(diff) / 50);
  const speed = Math.min(0.9, (el.animation_speed || 0.05) * (1 + t * 2));
  let step = diff * (1 - (1 - speed) ** frames);
  const minStep = 0.05 * frames;
  if (Math.abs(step) < minStep) step = Math.sign(diff) * Math.min(minStep, Math.abs(diff));
  const next = current + step;
  animated.set(el, next);
  return next;
}

export function createRenderEnv() {
  return { now: new Date(), perfNow: performance.now(), dt: 0, values: new WeakMap() };
}

/** Advance time-dependent state (clock, animations) for a new frame. */
export function advanceEnv(env, elements) {
  const perfNow = performance.now();
  env.dt = env.perfNow ? Math.max(0, (perfNow - env.perfNow) / 1000) : 0;
  env.perfNow = perfNow;
  env.now = new Date();
  for (const el of elements) env.values.set(el, animateValue(el, env.dt));
  env.displayValue = (el) => (env.values.has(el) ? env.values.get(el) : Number(el.value) || 0);
  return env;
}

/**
 * Render `scene` ({ backgroundColor, elements, video }) into ctx.
 * Elements at the start of the list are in front, so draw back to front.
 */
export function renderScene(ctx, scene, env) {
  ctx.save();
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.globalAlpha = 1;
  ctx.filter = 'none';
  ctx.fillStyle = scene.backgroundColor;
  ctx.fillRect(0, 0, DISPLAY_WIDTH, DISPLAY_HEIGHT);
  if (scene.video?.enabled) scene.video.draw(ctx);

  for (let i = scene.elements.length - 1; i >= 0; i--) {
    const el = scene.elements[i];
    const type = getElementType(el.type);
    if (!type) continue;
    try {
      type.draw(ctx, el, env);
    } catch (err) {
      console.error(`[Render] ${el.type} "${el.name}" failed:`, err);
    }
  }
  ctx.restore();
}
