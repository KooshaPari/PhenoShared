#!/usr/bin/env node
// Vercel serverless entrypoint: serves static files from dist/
// Also handles SPA fallback for client-side routing
import { createServer } from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { join, extname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = fileURLToPath(new URL('.', import.meta.url));
const DIST = join(__dirname, 'dist');
const INDEX = join(DIST, 'index.html');

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.css':  'text/css; charset=utf-8',
  '.js':   'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg':  'image/svg+xml',
  '.png':  'image/png',
  '.jpg':  'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.gif':  'image/gif',
  '.ico':  'image/x-icon',
  '.txt':  'text/plain; charset=utf-8',
  '.xml':  'application/xml; charset=utf-8',
  '.woff': 'font/woff',
  '.woff2':'font/woff2',
  '.ttf':  'font/ttf',
  '.eot':  'application/vnd.ms-fontobject',
  '.cast': 'application/octet-stream',
};

async function serveFile(res, filePath) {
  try {
    const stats = await stat(filePath);
    if (!stats.isFile()) return false;
    const ext = extname(filePath).toLowerCase();
    const ct = MIME[ext] || 'application/octet-stream';
    const body = await readFile(filePath);
    res.writeHead(200, {
      'Content-Type': ct,
      'Content-Length': body.length,
      'Cache-Control': 'public, max-age=0, must-revalidate',
    });
    res.end(body);
    return true;
  } catch {
    return false;
  }
}

const server = createServer(async (req, res) => {
  try {
    const url = new URL(req.url, 'http://localhost');
    const pathname = decodeURIComponent(url.pathname);

    // Try exact file in dist/
    const filePath = join(DIST, pathname);
    if (await serveFile(res, filePath)) return;

    // SPA fallback: serve index.html for non-file routes
    if (await serveFile(res, INDEX)) return;

    // 404
    res.writeHead(404, { 'Content-Type': 'text/plain' });
    res.end('Not found');
  } catch (err) {
    console.error('Server error:', err);
    res.writeHead(500, { 'Content-Type': 'text/plain' });
    res.end('Internal server error');
  }
});

export default server;
