// Native panel resolution. Frames sent to the device are always this size.
export const DISPLAY_WIDTH = 1280;
export const DISPLAY_HEIGHT = 480;

/**
 * How the panel is mounted. Themes are designed upright on a canvas of
 * `width` x `height`; each frame is rotated by `rotation` degrees
 * (clockwise) to fit the panel's native landscape frame.
 */
export const ORIENTATIONS = {
  landscape: { label: 'Landscape', rotation: 0, width: DISPLAY_WIDTH, height: DISPLAY_HEIGHT },
  portrait: { label: 'Portrait', rotation: 90, width: DISPLAY_HEIGHT, height: DISPLAY_WIDTH },
  landscape_inverted: { label: 'Landscape (inverted)', rotation: 180, width: DISPLAY_WIDTH, height: DISPLAY_HEIGHT },
  portrait_inverted: { label: 'Portrait (inverted)', rotation: 270, width: DISPLAY_HEIGHT, height: DISPLAY_WIDTH },
};

export const DEFAULT_ORIENTATION = 'landscape';

export function getOrientation(name) {
  return ORIENTATIONS[name] || ORIENTATIONS[DEFAULT_ORIENTATION];
}

/**
 * Map a point on the upright theme canvas to native panel pixels.
 * Used by the frame rotation and its tests.
 */
export function canvasToPanel(orientation, x, y) {
  const { rotation, width, height } = getOrientation(orientation);
  switch (rotation) {
    case 90: return { x: height - y, y: x };
    case 180: return { x: width - x, y: height - y };
    case 270: return { x: y, y: width - x };
    default: return { x, y };
  }
}

// Format: [source_id, display name, unit type, unit symbol]
export const DATA_SOURCES_CATEGORIZED = {
  Static: [
    ['static', 'Static Value', 'percent', '%'],
  ],
  CPU: [
    ['cpu_percent', 'CPU Utilization', 'percent', '%'],
    ['cpu_temp', 'CPU Temperature', 'temp', '°C'],
    ['cpu_clock', 'CPU Clock Speed', 'clock', 'MHz'],
    ['cpu_power', 'CPU Power', 'power', 'W'],
  ],
  GPU: [
    ['gpu_percent', 'GPU Utilization', 'percent', '%'],
    ['gpu_temp', 'GPU Temperature', 'temp', '°C'],
    ['gpu_clock', 'GPU Clock Speed', 'clock', 'MHz'],
    ['gpu_memory_percent', 'GPU Memory', 'percent', '%'],
    ['gpu_memory_clock', 'GPU Memory Clock', 'clock', 'MHz'],
    ['gpu_power', 'GPU Power', 'power', 'W'],
  ],
  Memory: [
    ['ram_percent', 'RAM Usage', 'percent', '%'],
    ['ram_used', 'RAM Used', 'size', 'GB'],
    ['ram_available', 'RAM Available', 'size', 'GB'],
  ],
  Network: [
    ['net_upload', 'Upload Speed', 'speed', 'MB/s'],
    ['net_download', 'Download Speed', 'speed', 'MB/s'],
  ],
};

export const SOURCE_UNITS = Object.fromEntries(
  Object.values(DATA_SOURCES_CATEGORIZED).flat()
    .map(([id, name, type, symbol]) => [id, { name, type, symbol }]),
);

export const TEMP_SOURCES = new Set(['cpu_temp', 'gpu_temp']);

/** Format a sensor value with its unit, e.g. "45°C" or "1.2MB/s". */
export function formatValue(value, source, hideTempUnit = false) {
  const unit = SOURCE_UNITS[source] || { symbol: '%', type: 'percent' };
  const v = Number(value) || 0;
  switch (unit.type) {
    case 'temp':
      return `${v.toFixed(0)}${hideTempUnit ? '°' : unit.symbol}`;
    case 'size':
    case 'speed':
      return `${v.toFixed(1)}${unit.symbol}`;
    default:
      return `${v.toFixed(0)}${unit.symbol}`;
  }
}
