#!/usr/bin/env node
// SPA server: serves index.html for all non-file routes
// Replaces the python3 http.server which doesn't support SPA rewrites
import { createServer } from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { join, extname, isAbsolute } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = fileURLToPath(new URL('.', import.meta.url));
const PORT = process.env.PORT || 8421;
const INDEX = 'index.html';

const MIME = {
  '.html': 'text/html',
  '.css':  'text/css',
  '.js':   'application/javascript',
  '.json': 'application/json',
  '.svg':  'image/svg+xml',
  '.png':  'image/png',
  '.jpg':  'image/jpeg',
  '.ico':  'image/x-icon',
  '.txt':  'text/plain',
};

async function serveFile(res, filePath) {
  try {
    const stats = await stat(filePath);
    if (!stats.isFile()) return false;
    const ext = extname(filePath).toLowerCase();
    const ct = MIME[ext] || 'application/octet-stream';
    const body = await readFile(filePath);
    res.writeHead(200, { 'Content-Type': ct, 'Content-Length': body.length });
    res.end(body);
    return true;
  } catch {
    return false;
  }
}

const server = createServer(async (req, res) => {
  const url = new URL(req.url, `http://localhost:${PORT}`);
  const pathname = decodeURIComponent(url.pathname);
  const filePath = join(__dirname, pathname);

  // Security: stay within project root
  if (!isAbsolute(filePath) || !filePath.startsWith(__dirname)) {
    res.writeHead(403);
    res.end('Forbidden');
    return;
  }

  // Try exact file first
  if (await serveFile(res, filePath)) {
    console.log(`${req.method} 200 ${pathname}`);
    return;
  }

  // SPA rewrite: try index.html sibling for directory or non-file path
  const indexPath = join(__dirname, INDEX);
  if (await serveFile(res, indexPath)) {
    console.log(`${req.method} 200 (SPA) ${pathname} -> /${INDEX}`);
    return;
  }

  console.log(`${req.method} 404 ${pathname}`);
  res.writeHead(404);
  res.end('Not found');
});

server.listen(PORT, '127.0.0.1', () => {
  console.log(`SPA server running at http://127.0.0.1:${PORT}/`);
  console.log('Press Ctrl+C to stop.');
});
