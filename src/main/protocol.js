/**
 * The `te://` protocol.
 *
 *   te://app/<path>          bundled renderer files
 *   te://local/<encoded abs> user media files (images, GIFs, videos)
 *
 * Serving both from one origin keeps canvases untainted, so frames that
 * include user images can still be encoded to JPEG for the display.
 */

const fs = require('fs');
const path = require('path');
const { Readable } = require('stream');
const { protocol } = require('electron');
const { isSafePath } = require('./validation');

const SCHEME = 'te';
const RENDERER_ROOT = path.join(__dirname, '..', 'renderer');

const MIME_TYPES = {
  '.html': 'text/html',
  '.js': 'text/javascript',
  '.css': 'text/css',
  '.json': 'application/json',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.bmp': 'image/bmp',
  '.webp': 'image/webp',
  '.ico': 'image/x-icon',
  '.mp4': 'video/mp4',
  '.m4v': 'video/mp4',
  '.webm': 'video/webm',
  '.mkv': 'video/x-matroska',
  '.mov': 'video/quicktime',
  '.avi': 'video/x-msvideo',
};

const LOCAL_MEDIA = new Set(['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.mp4', '.m4v', '.webm', '.mkv', '.mov', '.avi']);

function registerSchemePrivileges() {
  protocol.registerSchemesAsPrivileged([{
    scheme: SCHEME,
    privileges: { standard: true, secure: true, supportFetchAPI: true, stream: true, corsEnabled: true },
  }]);
}

function notFound() {
  return new Response('Not found', { status: 404 });
}

/** Serve a file, honoring Range requests so <video> can seek and loop. */
function serveFile(filePath, request) {
  let stat;
  try {
    stat = fs.statSync(filePath);
  } catch {
    return notFound();
  }
  if (!stat.isFile()) return notFound();

  const type = MIME_TYPES[path.extname(filePath).toLowerCase()] || 'application/octet-stream';
  const range = /^bytes=(\d*)-(\d*)$/.exec(request.headers.get('range') || '');
  if (range && stat.size > 0) {
    let start = range[1] === '' ? stat.size - Number(range[2]) : Number(range[1]);
    let end = range[1] !== '' && range[2] !== '' ? Number(range[2]) : stat.size - 1;
    start = Math.max(0, start);
    end = Math.min(end, stat.size - 1);
    if (start > end) {
      return new Response(null, { status: 416, headers: { 'Content-Range': `bytes */${stat.size}` } });
    }
    return new Response(Readable.toWeb(fs.createReadStream(filePath, { start, end })), {
      status: 206,
      headers: {
        'Content-Type': type,
        'Content-Length': String(end - start + 1),
        'Content-Range': `bytes ${start}-${end}/${stat.size}`,
        'Accept-Ranges': 'bytes',
      },
    });
  }

  return new Response(Readable.toWeb(fs.createReadStream(filePath)), {
    headers: { 'Content-Type': type, 'Content-Length': String(stat.size), 'Accept-Ranges': 'bytes' },
  });
}

function handleProtocol() {
  protocol.handle(SCHEME, (request) => {
    const url = new URL(request.url);

    if (url.host === 'app') {
      const filePath = path.normalize(path.join(RENDERER_ROOT, decodeURIComponent(url.pathname)));
      if (!filePath.startsWith(RENDERER_ROOT + path.sep)) return notFound();
      return serveFile(filePath, request);
    }

    if (url.host === 'local') {
      const requested = decodeURIComponent(url.pathname.slice(1));
      const check = isSafePath(requested);
      if (!check.safe || !path.isAbsolute(requested)) return notFound();
      if (!LOCAL_MEDIA.has(path.extname(requested).toLowerCase())) return notFound();
      return serveFile(check.resolved, request);
    }

    return notFound();
  });
}

module.exports = { registerSchemePrivileges, handleProtocol, SCHEME };
