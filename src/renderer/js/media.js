/**
 * Loading and caching of user media: images, animated GIFs and the video
 * background. Files are served through te://local so canvases stay untainted.
 */

export function localUrl(filePath) {
  return `te://local/${encodeURIComponent(filePath)}`;
}

const listeners = new Set();
/** Called when any media finishes loading so the scene can be redrawn. */
export function onMediaLoaded(cb) {
  listeners.add(cb);
}
function notifyLoaded() {
  for (const cb of listeners) cb();
}

// ---------------------------------------------------------------------------
// Images

const images = new Map();

/** Returns { image, error } once loaded, or null while loading. */
export function getImage(filePath) {
  if (!filePath) return { image: null, error: 'No image' };
  let entry = images.get(filePath);
  if (!entry) {
    entry = { image: null, error: null, loaded: false };
    images.set(filePath, entry);
    const img = new Image();
    img.onload = () => {
      entry.image = img;
      entry.loaded = true;
      notifyLoaded();
    };
    img.onerror = () => {
      entry.error = 'Image not found';
      entry.loaded = true;
      notifyLoaded();
    };
    img.src = localUrl(filePath);
  }
  return entry.loaded ? entry : null;
}

/** Load an image and resolve with its natural size (used when choosing a file). */
export function loadImageSize(filePath) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve({ width: img.naturalWidth, height: img.naturalHeight });
    img.onerror = () => reject(new Error('Failed to load image'));
    img.src = localUrl(filePath);
  });
}

// ---------------------------------------------------------------------------
// Animated GIFs (decoded once with WebCodecs ImageDecoder, LRU cached)

const GIF_CACHE_SIZE = 10;
const gifs = new Map();

async function decodeGif(entry, filePath) {
  try {
    const response = await fetch(localUrl(filePath));
    if (!response.ok) throw new Error('File not found');
    const decoder = new ImageDecoder({ data: await response.arrayBuffer(), type: 'image/gif' });
    await decoder.tracks.ready;
    const count = decoder.tracks.selectedTrack.frameCount;
    for (let i = 0; i < count; i++) {
      const { image } = await decoder.decode({ frameIndex: i });
      const durationMs = image.duration ? image.duration / 1000 : 100;
      entry.frames.push({ bitmap: await createImageBitmap(image), duration: durationMs > 0 ? durationMs : 100 });
      image.close();
    }
    decoder.close();
    if (!entry.frames.length) throw new Error('No frames found');
    entry.totalDuration = entry.frames.reduce((sum, f) => sum + f.duration, 0);
  } catch (err) {
    entry.error = err.message;
  }
  entry.loaded = true;
  notifyLoaded();
}

/** Returns the GIF entry ({ frames, totalDuration, error }) once loaded, or null. */
export function getGif(filePath) {
  if (!filePath) return { frames: [], error: 'No GIF' };
  let entry = gifs.get(filePath);
  if (entry) {
    gifs.delete(filePath);
    gifs.set(filePath, entry); // mark most recently used
  } else {
    entry = { frames: [], totalDuration: 0, error: null, loaded: false };
    gifs.set(filePath, entry);
    while (gifs.size > GIF_CACHE_SIZE) {
      const [oldestPath, oldest] = gifs.entries().next().value;
      oldest.frames.forEach((f) => f.bitmap.close());
      gifs.delete(oldestPath);
    }
    decodeGif(entry, filePath);
  }
  return entry.loaded ? entry : null;
}

let gifEpoch = performance.now();
/** Restart GIF timing (e.g. after the system wakes from sleep). */
export function resetGifPlayback() {
  gifEpoch = performance.now();
}

export function gifFrameAt(entry, now = performance.now()) {
  if (entry.frames.length <= 1) return entry.frames[0];
  let t = (now - gifEpoch) % entry.totalDuration;
  for (const frame of entry.frames) {
    if (t < frame.duration) return frame;
    t -= frame.duration;
  }
  return entry.frames[entry.frames.length - 1];
}

// ---------------------------------------------------------------------------
// Video background

export class VideoBackground {
  constructor() {
    this.path = '';
    this.fitMode = 'fit_height';
    this.video = null;
    this.error = null;
    this.onChange = null;
  }

  get enabled() {
    return !!this.path;
  }

  get ready() {
    return this.video && this.video.readyState >= 2;
  }

  load(filePath, fitMode = this.fitMode) {
    this.clear();
    this.path = filePath;
    this.fitMode = fitMode;
    this.error = null;
    const video = document.createElement('video');
    video.muted = true;
    video.loop = true;
    video.playsInline = true;
    video.preload = 'auto';
    video.addEventListener('loadeddata', () => {
      video.play().catch((err) => console.warn('[Video] play() failed:', err.message));
      this.onChange?.();
    });
    video.addEventListener('error', () => {
      this.error = 'This video format is not supported. Try MP4 (H.264) or WebM.';
      this.onChange?.();
    });
    video.src = localUrl(filePath);
    this.video = video;
  }

  clear() {
    if (this.video) {
      this.video.pause();
      this.video.removeAttribute('src');
      this.video.load();
    }
    this.video = null;
    this.path = '';
    this.error = null;
  }

  /** Resume playback (e.g. after sleep). */
  resume() {
    if (this.video && this.video.paused) this.video.play().catch(() => {});
  }

  /** Draw the current frame. Returns false if nothing was drawn. */
  draw(ctx) {
    if (!this.ready) return false;
    const vw = this.video.videoWidth;
    const vh = this.video.videoHeight;
    if (!vw || !vh) return false;
    const { width: cw, height: ch } = ctx.canvas;
    const aspect = vw / vh;
    let w;
    let h;
    if (this.fitMode === 'fit_width') {
      w = cw;
      h = cw / aspect;
    } else {
      h = ch;
      w = ch * aspect;
    }
    ctx.drawImage(this.video, (cw - w) / 2, (ch - h) / 2, w, h);
    return true;
  }

  toJSON() {
    return { video_path: this.path, fit_mode: this.fitMode, enabled: this.enabled };
  }
}
