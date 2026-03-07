/**
 * Logging and diagnostics – structured failure logging and screenshot capture.
 */

import * as fs from 'fs';
import * as path from 'path';
import { Browser } from 'webdriverio';
import { ensureReportsDir } from './app-lifecycle';

/**
 * Capture a screenshot and save it to the reports directory.
 * Returns the file path of the saved screenshot.
 */
export async function captureScreenshot(
  browser: Browser<'async'>,
  scenarioName: string,
): Promise<string> {
  const reportsDir = ensureReportsDir();
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const safeName = scenarioName.replace(/[^a-zA-Z0-9_-]/g, '_').substring(0, 80);
  const filename = `screenshot-${safeName}-${timestamp}.png`;
  const filepath = path.join(reportsDir, filename);

  try {
    await browser.saveScreenshot(filepath);
    logInfo(`Screenshot saved: ${filepath}`);
    return filepath;
  } catch (err) {
    logError(`Failed to capture screenshot: ${err}`);
    return '';
  }
}

/**
 * Collect browser console logs (where supported).
 */
export async function collectConsoleLogs(
  browser: Browser<'async'>,
): Promise<string[]> {
  try {
    const logs = await browser.getLogs('browser');
    return logs.map((entry: any) => `[${entry.level}] ${entry.message}`);
  } catch {
    // Not all drivers support log collection
    return [];
  }
}

/**
 * Structured info log to stdout.
 */
export function logInfo(message: string): void {
  const ts = new Date().toISOString();
  console.log(`[E2E ${ts}] INFO: ${message}`);
}

/**
 * Structured error log to stderr.
 */
export function logError(message: string): void {
  const ts = new Date().toISOString();
  console.error(`[E2E ${ts}] ERROR: ${message}`);
}

/**
 * Structured warning log to stderr.
 */
export function logWarn(message: string): void {
  const ts = new Date().toISOString();
  console.warn(`[E2E ${ts}] WARN: ${message}`);
}

/**
 * Dump full page source to a file for post-mortem analysis.
 */
export async function dumpPageSource(
  browser: Browser<'async'>,
  scenarioName: string,
): Promise<string> {
  const reportsDir = ensureReportsDir();
  const safeName = scenarioName.replace(/[^a-zA-Z0-9_-]/g, '_').substring(0, 80);
  const filename = `pagesource-${safeName}.html`;
  const filepath = path.join(reportsDir, filename);

  try {
    const source = await browser.getPageSource();
    fs.writeFileSync(filepath, source, 'utf-8');
    logInfo(`Page source saved: ${filepath}`);
    return filepath;
  } catch (err) {
    logError(`Failed to dump page source: ${err}`);
    return '';
  }
}
