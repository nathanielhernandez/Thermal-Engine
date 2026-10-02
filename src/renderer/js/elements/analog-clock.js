import { rgba, parseHex } from '../color.js';
import { fontString, measure } from '../draw-utils.js';

const DEG = Math.PI / 180;

function hand(ctx, x, y, length, angleDeg, width, color) {
  const a = (angleDeg - 90) * DEG;
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  ctx.lineCap = 'round';
  ctx.beginPath();
  ctx.moveTo(x, y);
  ctx.lineTo(x + length * Math.cos(a), y + length * Math.sin(a));
  ctx.stroke();
}

export default {
  type: 'analog_clock',
  name: 'Analog Clock',
  defaults: { radius: 100, x: 200, y: 240, color: '#ffffff', background_color: '#1a1a2e' },

  draw(ctx, el, env) {
    const { x, y, radius: r } = el;
    const now = env.now;
    const hours = now.getHours() % 12;
    const minutes = now.getMinutes();
    const seconds = now.getSeconds();

    let secondAngle;
    let minuteAngle;
    if (el.smooth_animation) {
      secondAngle = (seconds + now.getMilliseconds() / 1000) * 6;
      minuteAngle = (minutes + seconds / 60) * 6;
    } else {
      secondAngle = seconds * 6;
      minuteAngle = minutes * 6;
    }
    const hourAngle = (hours + minutes / 60) * 30;
    const color = rgba(el.color, el.color_opacity);

    ctx.save();
    // Face
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fillStyle = rgba(el.background_color, el.background_color_opacity);
    ctx.fill();
    if (el.show_clock_border) {
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.stroke();
    }

    // Numbers or ticks
    const textColor = rgba(el.text_color, el.text_color_opacity);
    ctx.font = fontString(el.font_family, el.font_size * 0.8, el.font_bold, el.font_italic);
    for (let i = 0; i < 12; i++) {
      const a = (i * 30 - 90) * DEG;
      if (el.clock_face_style === 'numbers') {
        const text = String(i || 12);
        const m = measure(ctx, text);
        const tr = r * 0.78;
        ctx.fillStyle = textColor;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'alphabetic';
        ctx.fillText(text, x + tr * Math.cos(a), y + tr * Math.sin(a) - m.height / 2 + m.ascent);
      } else if (el.clock_face_style === 'ticks') {
        const major = i % 3 === 0;
        const inner = r * (major ? 0.75 : 0.85);
        const outer = r * 0.95;
        ctx.strokeStyle = textColor;
        ctx.lineWidth = major ? 2 : 1;
        ctx.lineCap = 'butt';
        ctx.beginPath();
        ctx.moveTo(x + inner * Math.cos(a), y + inner * Math.sin(a));
        ctx.lineTo(x + outer * Math.cos(a), y + outer * Math.sin(a));
        ctx.stroke();
      }
    }

    hand(ctx, x, y, r * 0.5, hourAngle, 4, color);
    hand(ctx, x, y, r * 0.7, minuteAngle, 3, color);
    if (el.show_seconds_hand) {
      const alpha = parseHex(el.color).a * el.color_opacity / 100;
      hand(ctx, x, y, r * 0.85, secondAngle, 1.5, `rgba(255, 80, 80, ${alpha})`);
    }

    // Center dot
    ctx.beginPath();
    ctx.arc(x, y, 4, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();
    ctx.restore();
  },
};
