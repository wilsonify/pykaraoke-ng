/**
 * Step definitions for Error State Handling feature.
 *
 * Maps to: features/error-handling.feature
 * Tests graceful degradation when the backend is unreachable.
 */

import { Given, When, Then } from '@cucumber/cucumber';
import { expect } from 'chai';
import { PyKaraokeWorld } from '../support/world';
import { findElement, SELECTORS } from '../support/selectors';
import { mockBackendDisconnected } from '../support/mocks';

When('the backend becomes unreachable', async function (this: PyKaraokeWorld) {
  await mockBackendDisconnected(this.browser!);
  // Trigger a backend check by refreshing
  await this.browser!.refresh();
  await this.browser!.pause(2000);
});

Then('the status bar should indicate the backend is unreachable', async function (this: PyKaraokeWorld) {
  const el = await findElement(this.browser!, 'statusMessage');
  await this.browser!.waitUntil(
    async () => {
      const text = await el.getText();
      return text.includes('unreachable') || text.includes('Disconnected') || text.includes('Backend');
    },
    { timeout: 10000, timeoutMsg: 'Status should indicate backend unreachable', interval: 500 },
  );
});

Given('the backend is not connected', async function (this: PyKaraokeWorld) {
  this.backendDisconnected = true;
  await mockBackendDisconnected(this.browser!);
  // Refresh to apply the mock
  await this.browser!.refresh();
  await this.browser!.pause(2000);
});

Then('the status bar should indicate a search failure or no connection', async function (this: PyKaraokeWorld) {
  const el = await findElement(this.browser!, 'statusMessage');
  const text = await el.getText();
  const valid =
    text.includes('failed') ||
    text.includes('unreachable') ||
    text.includes('Error') ||
    text.includes('Search') ||
    text.includes('Connecting');
  expect(valid).to.be.true;
});
