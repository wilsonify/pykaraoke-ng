// Loads the app's inline ES module out of the single-file src/web/index.html.
//
// The app is one self-contained HTML file (UI + CSS + JS + PyScript bridge),
// so the unit tests extract its `<script type="module">` block and import it
// as a module.  Outside a browser `document` is undefined, so only the pure
// helpers run; the DOM wiring at the bottom of the script stays dormant.

import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const htmlPath = resolve(here, '..', '..', 'src', 'web', 'index.html');
const outPath = resolve(here, '.extracted', 'app.mjs');

export async function loadApp() {
  const html = readFileSync(htmlPath, 'utf8');
  const match = html.match(/<script type="module">([\s\S]*?)<\/script>/);
  if (!match) {
    throw new Error('src/web/index.html has no inline <script type="module"> block');
  }
  mkdirSync(dirname(outPath), { recursive: true });
  writeFileSync(outPath, match[1]);
  return import(pathToFileURL(outPath).href);
}
