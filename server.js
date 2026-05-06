const { createServer } = require("http");
const { readFileSync, existsSync } = require("fs");
const { join, extname } = require("path");

const PORT = process.env.PORT || 3000;
const OUT_DIR = join(__dirname, "out");

const MIME_TYPES = {
  ".html": "text/html",
  ".css": "text/css",
  ".js": "application/javascript",
  ".json": "application/json",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".ico": "image/x-icon",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
  ".txt": "text/plain",
};

function serve(res, filePath, status = 200) {
  try {
    const content = readFileSync(filePath);
    const ext = extname(filePath);
    res.writeHead(status, {
      "Content-Type": MIME_TYPES[ext] || "application/octet-stream",
      "Cache-Control": ext === ".html" ? "no-cache" : "public, max-age=31536000, immutable",
    });
    res.end(content);
  } catch {
    res.writeHead(404, { "Content-Type": "text/html" });
    res.end(readFileSync(join(OUT_DIR, "404.html")));
  }
}

createServer((req, res) => {
  const url = new URL(req.url, `http://localhost:${PORT}`);
  let pathname = url.pathname;

  // Health check
  if (pathname === "/healthz") {
    res.writeHead(200, { "Content-Type": "application/json" });
    return res.end(JSON.stringify({ status: "ok" }));
  }

  // Try exact file match (for assets like _next/*, images, etc.)
  const exactPath = join(OUT_DIR, pathname);
  if (existsSync(exactPath) && !require("fs").statSync(exactPath).isDirectory()) {
    return serve(res, exactPath);
  }

  // Try .html extension (for routes like /blockers -> /blockers.html)
  const htmlPath = join(OUT_DIR, pathname + ".html");
  if (existsSync(htmlPath)) {
    return serve(res, htmlPath);
  }

  // Try index.html inside directory (for /blockers/ -> /blockers/index.html)
  const indexPath = join(OUT_DIR, pathname, "index.html");
  if (existsSync(indexPath)) {
    return serve(res, indexPath);
  }

  // Fallback to index.html for client-side routing
  serve(res, join(OUT_DIR, "index.html"));
}).listen(PORT, () => {
  console.log(`Scrum Master Agent running on port ${PORT}`);
});
