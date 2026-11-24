import { createReadStream, existsSync, statSync } from "node:fs";
import { createServer } from "node:http";
import { extname, join, normalize, resolve, sep } from "node:path";

const configuredRoot = process.env.A11Y_VIEWER_DIR;
const buildRoot = resolve("../../../target/dx/sl-viewer");
const root = resolve(
  configuredRoot ??
    (existsSync(join(buildRoot, "release/web/public/index.html"))
      ? join(buildRoot, "release/web/public")
      : join(buildRoot, "debug/web/public")),
);
const port = Number(process.env.A11Y_VIEWER_PORT ?? 4173);
const types = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".wasm": "application/wasm",
};

if (!existsSync(join(root, "index.html"))) {
  throw new Error(`viewer build not found at ${root}; run dx build first`);
}

createServer((request, response) => {
  const requestUrl = new URL(request.url, `http://${request.headers.host}`);
  const pathname = decodeURIComponent(requestUrl.pathname);

  // Root-route tests exercise the canonical demo fixture. Production web
  // builds intentionally fetch the loopback daemon instead, while explicit
  // fixture routes below retain their individual error and splash states.
  if (pathname === "/" && !requestUrl.search) {
    response.writeHead(302, { Location: "/?fixture=demo" }).end();
    return;
  }

  const requested = resolve(root, `.${normalize(pathname)}`);
  if (requested !== root && !requested.startsWith(`${root}${sep}`)) {
    response.writeHead(403).end("Forbidden");
    return;
  }

  let file = requested;
  if (existsSync(file) && statSync(file).isDirectory()) {
    file = join(file, "index.html");
  }
  if (!existsSync(file)) {
    response.writeHead(404).end("Not found");
    return;
  }

  response.writeHead(200, {
    "Cache-Control": "no-store",
    "Content-Type": types[extname(file)] ?? "application/octet-stream",
  });
  createReadStream(file).pipe(response);
}).listen(port, "127.0.0.1", () => {
  console.log(`Serving sl-viewer from ${root} at http://127.0.0.1:${port}`);
});
