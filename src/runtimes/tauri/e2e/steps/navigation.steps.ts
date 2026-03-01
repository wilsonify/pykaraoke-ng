/**
 * Step definitions for Navigation Flow feature.
 *
 * Maps to: features/navigation.feature
 * Preserves coverage from: test_ui_buttons.py::TestSettingsModal
 */

import { Given, When, Then } from '@cucumber/cucumber';
import { expect } from 'chai';
import { PyKaraokeWorld } from '../support/world';
import { findElement, waitForVisible, waitForNotVisible, SELECTORS } from '../support/selectors';

// ── Library section collapse/expand ─────────────────────────────────────

When('the user collapses the library section', async function (this: PyKaraokeWorld) {
  const details = await this.browser!.$(SELECTORS.libraryDetails);
  // Click the <summary> to collapse
  const summary = await details.$('summary');
  // Only collapse if currently open
  const isOpen = await details.getAttribute('open');
  if (isOpen !== null) {
    await summary.click();
  }
});

When('the user expands the library section', async function (this: PyKaraokeWorld) {
  const details = await this.browser!.$(SELECTORS.libraryDetails);
  const summary = await details.$('summary');
  const isOpen = await details.getAttribute('open');
  if (isOpen === null) {
    await summary.click();
  }
});

Then('the folder input should not be visible', async function (this: PyKaraokeWorld) {
  // After collapsing, the folder input inside <details> should be hidden
  const folderInput = await this.browser!.$(SELECTORS.folderInput);
  await this.browser!.waitUntil(
    async () => !(await folderInput.isDisplayed()),
    { timeout: 3000, timeoutMsg: 'Folder input should be hidden after collapse' },
  );
});

Then('the folder input should be visible', async function (this: PyKaraokeWorld) {
  await waitForVisible(this.browser!, 'folderInput');
});

// ── Settings modal ──────────────────────────────────────────────────────

When('the user opens the settings modal', async function (this: PyKaraokeWorld) {
  const btn = await findElement(this.browser!, 'settingsBtn');
  await btn.click();
  await waitForVisible(this.browser!, 'settingsModal');
});

Then('the settings modal should be visible', async function (this: PyKaraokeWorld) {
  await waitForVisible(this.browser!, 'settingsModal');
});

Then('the fullscreen setting should be present', async function (this: PyKaraokeWorld) {
  const el = await findElement(this.browser!, 'settingFullscreen');
  const exists = await el.isExisting();
  expect(exists).to.be.true;
});

Then('the zoom mode setting should be present', async function (this: PyKaraokeWorld) {
  const el = await findElement(this.browser!, 'settingZoom');
  const exists = await el.isExisting();
  expect(exists).to.be.true;
});

When('the user closes the settings modal via cancel', async function (this: PyKaraokeWorld) {
  const cancelBtn = await findElement(this.browser!, 'settingsCancelBtn');
  await cancelBtn.click();
});

Then('the settings modal should not be visible', async function (this: PyKaraokeWorld) {
  await waitForNotVisible(this.browser!, 'settingsModal');
});

// ── Keyboard shortcuts ──────────────────────────────────────────────────

Given('the search input does not have focus', async function (this: PyKaraokeWorld) {
  // Click on the app body to remove focus from search
  const app = await findElement(this.browser!, 'app');
  await app.click();
});

When('the user presses the {string} key', async function (this: PyKaraokeWorld, key: string) {
  await this.browser!.keys(key);
});

Then('the search input should have focus', async function (this: PyKaraokeWorld) {
  await this.browser!.waitUntil(
    async () => {
      const activeId = await this.browser!.execute(() => document.activeElement?.id);
      return activeId === 'search-input';
    },
    { timeout: 3000, timeoutMsg: 'Search input should have focus' },
  );
});

Given('the search input contains {string}', async function (this: PyKaraokeWorld, text: string) {
  const input = await findElement(this.browser!, 'searchInput');
  await input.clearValue();
  await input.setValue(text);
});

When('the user presses the Escape key', async function (this: PyKaraokeWorld) {
  await this.browser!.keys('Escape');
});

Then('the search input should be empty', async function (this: PyKaraokeWorld) {
  const input = await findElement(this.browser!, 'searchInput');
  await this.browser!.waitUntil(
    async () => {
      const value = await input.getValue();
      return value === '';
    },
    { timeout: 3000, timeoutMsg: 'Search input should be empty after Escape' },
  );
});
