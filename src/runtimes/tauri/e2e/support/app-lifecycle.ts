/**
 * App lifecycle management – start, stop, reset the application under test.
 *
 * Manages the WebdriverIO browser session and ensures each scenario starts
 * from a clean state.
 */

import { remote, Browser, RemoteOptions } from 'webdriverio';
import * as fs from 'fs';
import * as path from 'path';

/** Default WebdriverIO capabilities for headless Chrome. */
function buildBrowserOptions(): RemoteOptions {
  const seleniumUrl = process.env.SELENIUM_URL || 'http://localhost:4444/wd/hub';
  const isRemote = !!process.env.SELENIUM_URL;

  const chromeArgs = [
    '--headless=new',
    '--disable-gpu',
    '--no-sandbox',
    '--disable-dev-shm-usage',
    '--window-size=400,800',
  ];

  if (isRemote) {
    return {
      hostname: new URL(seleniumUrl).hostname,
      port: parseInt(new URL(seleniumUrl).port, 10) || 4444,
      path: new URL(seleniumUrl).pathname,
      capabilities: {
        browserName: 'chrome',
        'goog:chromeOptions': { args: chromeArgs },
      },
      logLevel: 'warn',
    };
  }

  return {
    capabilities: {
      browserName: 'chrome',
      'goog:chromeOptions': { args: chromeArgs },
    },
    logLevel: 'warn',
  };
}

/** Start a new browser session. */
export async function launchBrowser(): Promise<Browser<'async'>> {
  const opts = buildBrowserOptions();
  const browser = await remote(opts);
  // Set a generous implicit wait so selectors retry until the DOM is ready.
  // Prefer explicit waits in step definitions for fine-grained control.
  await browser.setTimeout({ implicit: 5000 });
  return browser;
}

/** Navigate the browser to the application URL. */
export async function navigateToApp(browser: Browser<'async'>, url: string): Promise<void> {
  await browser.url(url);
}

/** Close the browser session. */
export async function closeBrowser(browser: Browser<'async'> | null): Promise<void> {
  if (browser) {
    try {
      await browser.deleteSession();
    } catch {
      // Session may already be closed
    }
  }
}

/** Reset application state between scenarios (clear local storage, navigate fresh). */
export async function resetAppState(browser: Browser<'async'>, url: string): Promise<void> {
  try {
    await browser.execute(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
  } catch {
    // May fail if no page is loaded yet
  }
  await browser.url(url);
}

/**
 * Ensure the reports directory exists.
 */
export function ensureReportsDir(): string {
  const reportsDir = path.resolve(__dirname, '..', 'reports');
  if (!fs.existsSync(reportsDir)) {
    fs.mkdirSync(reportsDir, { recursive: true });
  }
  return reportsDir;
}
