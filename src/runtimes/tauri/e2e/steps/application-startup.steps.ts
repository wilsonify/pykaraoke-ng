/**
 * Step definitions for Application Startup feature.
 *
 * Maps to: features/application-startup.feature
 * Preserves coverage from: test_ui_buttons.py::TestBackendConnection
 */

import { Given, When, Then } from '@cucumber/cucumber';
import { expect } from 'chai';
import { PyKaraokeWorld } from '../support/world';
import { closeBrowser, launchBrowser, navigateToApp } from '../support/app-lifecycle';
import { findElement, waitForTextContains, SELECTORS } from '../support/selectors';
import { mockBackendConnected } from '../support/mocks';

Given('the application is not running', async function (this: PyKaraokeWorld) {
  // Close any existing browser session to simulate a fresh start
  if (this.browser) {
    await closeBrowser(this.browser);
    this.browser = null;
  }
});

When('the user launches the application', async function (this: PyKaraokeWorld) {
  this.browser = await launchBrowser();
  await mockBackendConnected(this.browser!);
  await navigateToApp(this.browser!, this.appUrl);

  // Wait for the app to initialise: status bar should update from "Ready"
  await this.browser!.waitUntil(
    async () => {
      const el = await this.browser!.$(SELECTORS.backendStatus);
      const text = await el.getText();
      return text.includes('Connected');
    },
    { timeout: 15000, timeoutMsg: 'App did not connect to backend within 15s', interval: 500 },
  );
});

Given('the application is running', async function (this: PyKaraokeWorld) {
  // The Before hook already launched the browser and navigated to the app.
  // Apply mock backend for deterministic behavior.
  if (this.browser) {
    await mockBackendConnected(this.browser);
    // Wait for page to fully load
    await this.browser.waitUntil(
      async () => {
        const el = await this.browser!.$(SELECTORS.app);
        return await el.isExisting();
      },
      { timeout: 10000, timeoutMsg: 'App container not found', interval: 250 },
    );
  }
});

Then('the main window should be visible', async function (this: PyKaraokeWorld) {
  const app = await findElement(this.browser!, 'app');
  const isDisplayed = await app.isDisplayed();
  expect(isDisplayed).to.be.true;
});

Then('the primary action button should be enabled', async function (this: PyKaraokeWorld) {
  const playBtn = await findElement(this.browser!, 'playBtn');
  const isEnabled = await playBtn.isEnabled();
  expect(isEnabled).to.be.true;
});

Then('the backend status should show {string}', async function (this: PyKaraokeWorld, expectedText: string) {
  await waitForTextContains(this.browser!, 'backendStatus', expectedText);
});

Then('the status bar should display {string}', async function (this: PyKaraokeWorld, expectedText: string) {
  await waitForTextContains(this.browser!, 'statusMessage', expectedText);
});

Then('the app container should be present in the DOM', async function (this: PyKaraokeWorld) {
  const app = await findElement(this.browser!, 'app');
  const exists = await app.isExisting();
  expect(exists).to.be.true;
});

Then('no JavaScript crash should have occurred', async function (this: PyKaraokeWorld) {
  // Verify the app element is still present — a JS crash would blank it
  const apps = await this.browser!.$$(SELECTORS.app);
  expect(apps.length).to.equal(1, 'App container should still be present (no JS crash)');
});
