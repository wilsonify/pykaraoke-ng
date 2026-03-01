/**
 * Step definitions for Song Search feature.
 *
 * Maps to: features/song-search.feature
 * Preserves coverage from: test_ui_buttons.py::TestSearchFlow
 */

import { Given, When, Then } from '@cucumber/cucumber';
import { expect } from 'chai';
import { PyKaraokeWorld } from '../support/world';
import { findElement, waitForTextContains, SELECTORS } from '../support/selectors';

Given('the backend is connected', async function (this: PyKaraokeWorld) {
  // Wait for backend connection status
  await this.browser!.waitUntil(
    async () => {
      const el = await this.browser!.$(SELECTORS.backendStatus);
      const text = await el.getText();
      return text.includes('Connected');
    },
    { timeout: 10000, timeoutMsg: 'Backend should show Connected status', interval: 500 },
  );
});

When('the user searches for {string}', async function (this: PyKaraokeWorld, query: string) {
  const input = await findElement(this.browser!, 'searchInput');
  await input.clearValue();
  await input.setValue(query);

  const searchBtn = await findElement(this.browser!, 'searchBtn');
  await searchBtn.click();

  // Wait for the status bar to update from the search action
  await this.browser!.pause(1000);
});

When('the user types {string} in the search input', async function (this: PyKaraokeWorld, text: string) {
  const input = await findElement(this.browser!, 'searchInput');
  await input.clearValue();
  await input.setValue(text);
});

When('the user presses Enter in the search input', async function (this: PyKaraokeWorld) {
  const input = await findElement(this.browser!, 'searchInput');
  await input.addValue('\uE007'); // Enter key
  await this.browser!.pause(1000);
});

Then('the status bar should indicate search results or a search action', async function (this: PyKaraokeWorld) {
  const el = await findElement(this.browser!, 'statusMessage');
  const text = await el.getText();
  // The status should show one of these patterns
  const validPatterns = ['Found', 'Search', 'result', 'Searching'];
  const hasValidStatus = validPatterns.some((pattern) => text.includes(pattern));
  expect(hasValidStatus).to.be.true;
});

Then('the application should send a search request after a short delay', async function (this: PyKaraokeWorld) {
  // The incremental search debounces at ~200ms, so wait and then check status
  await this.browser!.waitUntil(
    async () => {
      const el = await this.browser!.$(SELECTORS.statusMessage);
      const text = await el.getText();
      return text !== 'Ready' && text !== 'Connecting to backend…';
    },
    {
      timeout: 5000,
      timeoutMsg: 'Status bar should update after incremental search',
      interval: 250,
    },
  );
});
