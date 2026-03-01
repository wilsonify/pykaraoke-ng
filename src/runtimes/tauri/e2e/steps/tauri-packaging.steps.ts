/**
 * Step definitions for Tauri Packaging Integrity feature.
 *
 * Maps to: features/tauri-packaging.feature
 * Preserves coverage from: test_tauri_packaging.py (all classes)
 *
 * These are static-analysis checks that read source files directly,
 * no running application needed.
 */

import { Given, Then } from '@cucumber/cucumber';
import { expect } from 'chai';
import * as fs from 'fs';
import * as path from 'path';

// Resolve paths relative to the e2e directory
const TAURI_DIR = path.resolve(__dirname, '..', '..');
const RUST_MAIN = path.join(TAURI_DIR, 'src-tauri', 'src', 'main.rs');
const TAURI_CONF = path.join(TAURI_DIR, 'src-tauri', 'tauri.conf.json');
const APP_JS = path.join(TAURI_DIR, 'src', 'app.js');

let rustSource: string;
let tauriConf: any;
let appJsSource: string;

Given('the Tauri source files are available', function () {
  expect(fs.existsSync(RUST_MAIN), `main.rs not found at ${RUST_MAIN}`).to.be.true;
  rustSource = fs.readFileSync(RUST_MAIN, 'utf-8');
});

Given('the Tauri configuration file is available', function () {
  expect(fs.existsSync(TAURI_CONF), `tauri.conf.json not found at ${TAURI_CONF}`).to.be.true;
  tauriConf = JSON.parse(fs.readFileSync(TAURI_CONF, 'utf-8'));
});

Given('the frontend source files are available', function () {
  expect(fs.existsSync(APP_JS), `app.js not found at ${APP_JS}`).to.be.true;
  appJsSource = fs.readFileSync(APP_JS, 'utf-8');
});

// ── WebKitGTK DMA-BUF workaround ───────────────────────────────────────

Then('main.rs should set WEBKIT_DISABLE_DMABUF_RENDERER', function () {
  expect(rustSource).to.include('WEBKIT_DISABLE_DMABUF_RENDERER',
    'main.rs must set WEBKIT_DISABLE_DMABUF_RENDERER to prevent blank windows on Linux');
});

Then('the workaround should be Linux-only', function () {
  const dmabufIdx = rustSource.indexOf('WEBKIT_DISABLE_DMABUF_RENDERER');
  const preceding = rustSource.slice(Math.max(0, dmabufIdx - 300), dmabufIdx);
  expect(preceding).to.include('target_os = "linux"',
    'WEBKIT_DISABLE_DMABUF_RENDERER should be gated behind #[cfg(target_os = "linux")]');
});

Then('the workaround should respect existing environment values', function () {
  const hasCheck = rustSource.includes('is_err()') || rustSource.includes('is_ok()');
  expect(hasCheck).to.be.true;
});

Then('the workaround should be applied before the Tauri builder starts', function () {
  const dmabufPos = rustSource.indexOf('WEBKIT_DISABLE_DMABUF_RENDERER');
  const builderPos = rustSource.indexOf('tauri::Builder::default()');
  expect(dmabufPos).to.be.lessThan(builderPos,
    'WEBKIT_DISABLE_DMABUF_RENDERER must be set before tauri::Builder::default()');
});

// ── Backend path resolution ─────────────────────────────────────────────

Then('main.rs should try at least {int} candidate paths for backend.py', function (minCount: number) {
  const matches = rustSource.match(/\.join\("backend\.py"\)/g) || [];
  expect(matches.length).to.be.at.least(minCount,
    `main.rs should try at least ${minCount} candidate paths for backend.py`);
});

Then('main.rs should check path existence before use', function () {
  expect(rustSource).to.include('.exists()',
    'main.rs should check .exists() on candidate paths');
});

Then('main.rs should use resource_dir for bundled installs', function () {
  expect(rustSource).to.include('resource_dir',
    'main.rs must use resource_dir() to locate bundled resources');
});

// ── Tauri bundle configuration ──────────────────────────────────────────

Then('the bundle should declare resources', function () {
  const resources = tauriConf?.tauri?.bundle?.resources;
  expect(resources).to.be.an('array').that.is.not.empty;
});

Then('backend.py should be reachable via bundled resources', function () {
  const resources = tauriConf.tauri.bundle.resources;
  const hasBackendGlob = resources.some((r: string) => r.includes('backend') && r.includes('**'));
  const hasBackendLiteral = resources.some((r: string) => r.includes('backend.py'));
  expect(hasBackendGlob || hasBackendLiteral).to.be.true;
});

Then('the beforeBuildCommand should stage the backend', function () {
  const beforeBuild = tauriConf?.build?.beforeBuildCommand || '';
  expect(beforeBuild).to.not.be.empty;
  // Should reference the staging script
  expect(beforeBuild).to.include('stage-backend');
});

// ── JavaScript API resilience ───────────────────────────────────────────

Then('app.js should not destructure window.__TAURI__ at top level', function () {
  const dangerous = /const\s*\{[^}]*invoke[^}]*\}\s*=\s*window\.__TAURI__/;
  expect(dangerous.test(appJsSource)).to.be.false;
});

Then('app.js should wrap Tauri API access in try-catch', function () {
  expect(appJsSource).to.include('try');
  expect(appJsSource).to.include('catch');
});

Then('app.js should provide a fallback invoke function', function () {
  expect(appJsSource).to.include('invoke');
  expect(appJsSource).to.include('async');
});
