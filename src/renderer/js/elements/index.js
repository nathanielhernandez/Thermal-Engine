/**
 * Element type registry.
 *
 * Each element type is a module exporting:
 *   type      unique id stored in theme files
 *   name      display name
 *   defaults  default properties for new elements
 *   draw(ctx, element, env)  renders at display resolution (1280x480)
 *
 * To add an element type, create a module here and add it to TYPES.
 */

import circleGauge from './circle-gauge.js';
import barGauge from './bar-gauge.js';
import { textElement, clockElement } from './text.js';
import rectangle from './rectangle.js';
import analogClock from './analog-clock.js';
import { imageElement, gifElement } from './media-elements.js';
import lineChart from './line-chart.js';

const TYPES = [circleGauge, barGauge, textElement, rectangle, clockElement, analogClock, imageElement, gifElement, lineChart];

const registry = new Map(TYPES.map((t) => [t.type, t]));

export function getElementType(type) {
  return registry.get(type);
}

export function elementTypes() {
  return TYPES;
}
