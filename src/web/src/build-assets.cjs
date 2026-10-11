#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");

const WEB = path.resolve(__dirname, "..");
const DIST = path.resolve(WEB, "dist");
const SRC_ROOT = path.resolve(WEB);
const ASSETS = path.resolve(SRC_ROOT, "_assets");
const WHEEL = path.resolve(SRC_ROOT, "_wheel");

function copyDir(src, dest) {
  fs.mkdirSync(dest, { recursive: true });
  for (const name of fs.readdirSync(src)) {
    const s = path.join(src, name);
    const d = path.join(dest, name);
    const st = fs.statSync(s);
    if (st.isDirectory()) {
      copyDir(s, d);
    } else if (st.isFile()) {
      fs.copyFileSync(s, d);
    }
  }
}

function main() {
  fs.mkdirSync(DIST, { recursive: true });

  // Engine wheel
  if (fs.existsSync(WHEEL)) {
    copyDir(WHEEL, path.resolve(DIST, "_wheel"));
  }

  // Vendor runtime
  if (fs.existsSync(ASSETS)) {
    copyDir(ASSETS, path.resolve(DIST, "_assets"));
  }

  console.log("Copied non-aggregated assets into", DIST);
}

main();
