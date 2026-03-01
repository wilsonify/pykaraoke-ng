/**
 * Cucumber hooks – Before/After scenario lifecycle management.
 *
 * Manages browser sessions, state cleanup, and failure diagnostics.
 */

import { Before, After, BeforeAll, AfterAll, Status } from '@cucumber/cucumber';
import { PyKaraokeWorld } from './world';
import { launchBrowser, closeBrowser, navigateToApp, ensureReportsDir } from './app-lifecycle';
import { captureScreenshot, dumpPageSource, collectConsoleLogs, logInfo, logError } from './logging';
import { restoreFetch } from './mocks';

BeforeAll(async function () {
  ensureReportsDir();
  logInfo('BDD E2E test suite starting');
});

AfterAll(async function () {
  logInfo('BDD E2E test suite complete');
});

/**
 * Before each scenario: launch a fresh browser and navigate to the app.
 */
Before(async function (this: PyKaraokeWorld) {
  this.browser = await launchBrowser();
  this.backendDisconnected = false;
  this.errors = [];
  this.screenshots = [];
  await navigateToApp(this.browser, this.appUrl);
});

/**
 * Before scenarios tagged @requires-python or @requires-selenium:
 * These run outside the browser, so skip browser setup.
 */
Before({ tags: '@requires-python' }, async function (this: PyKaraokeWorld) {
  // These scenarios use Python subprocess and Selenium directly,
  // not through our WebdriverIO session.  The browser opened by the
  // default Before hook is still available if needed.
});

/**
 * After each scenario: capture diagnostics on failure, then close browser.
 */
After(async function (this: PyKaraokeWorld, scenario) {
  if (this.browser) {
    // On failure: screenshot + page source + console logs
    if (scenario.result?.status === Status.FAILED) {
      const name = scenario.pickle.name;
      logError(`Scenario FAILED: ${name}`);

      const screenshotPath = await captureScreenshot(this.browser, name);
      if (screenshotPath) {
        this.screenshots.push(screenshotPath);
        // Attach screenshot to Cucumber report
        const screenshotData = require('fs').readFileSync(screenshotPath);
        this.attach(screenshotData, 'image/png');
      }

      await dumpPageSource(this.browser, name);

      const consoleLogs = await collectConsoleLogs(this.browser);
      if (consoleLogs.length > 0) {
        this.attach(consoleLogs.join('\n'), 'text/plain');
        logError(`Console logs:\n${consoleLogs.join('\n')}`);
      }
    }

    // Restore any mocked fetch before closing
    try {
      await restoreFetch(this.browser);
    } catch {
      // Browser may already be closed
    }

    await closeBrowser(this.browser);
    this.browser = null;
  }
});
