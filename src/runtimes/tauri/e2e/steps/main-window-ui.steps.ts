/**
 * Step definitions for Main Window UI Elements feature.
 *
 * Maps to: features/main-window-ui.feature
 * Preserves coverage from: test_ui_buttons.py::TestBackendConnection::test_app_element_present
 */

import { Then } from '@cucumber/cucumber';
import { expect } from 'chai';
import { PyKaraokeWorld } from '../support/world';
import { findElement, waitForVisible, isDisplayed, SELECTORS } from '../support/selectors';

Then('the search input should be visible', async function (this: PyKaraokeWorld) {
  await waitForVisible(this.browser!, 'searchInput');
});

Then('the search button should be visible', async function (this: PyKaraokeWorld) {
  await waitForVisible(this.browser!, 'searchBtn');
});

Then('the play button should be visible', async function (this: PyKaraokeWorld) {
  await waitForVisible(this.browser!, 'playBtn');
});

Then('the stop button should be visible', async function (this: PyKaraokeWorld) {
  await waitForVisible(this.browser!, 'stopBtn');
});

Then('the next track button should be visible', async function (this: PyKaraokeWorld) {
  await waitForVisible(this.browser!, 'nextBtn');
});

Then('the previous track button should be visible', async function (this: PyKaraokeWorld) {
  await waitForVisible(this.browser!, 'prevBtn');
});

Then('the volume slider should be visible', async function (this: PyKaraokeWorld) {
  await waitForVisible(this.browser!, 'volumeSlider');
});

Then('the settings button should be visible', async function (this: PyKaraokeWorld) {
  await waitForVisible(this.browser!, 'settingsBtn');
});

Then('the now-playing title should show {string}', async function (this: PyKaraokeWorld, expected: string) {
  const el = await findElement(this.browser!, 'currentSongTitle');
  const text = await el.getText();
  expect(text).to.include(expected);
});

Then('the time display should show {string}', async function (this: PyKaraokeWorld, expected: string) {
  const el = await findElement(this.browser!, 'timeCurrent');
  const text = await el.getText();
  expect(text).to.include(expected);
});

Then('the queue section should be visible', async function (this: PyKaraokeWorld) {
  await waitForVisible(this.browser!, 'playlist');
});

Then('the queue should display {string}', async function (this: PyKaraokeWorld, expected: string) {
  const el = await findElement(this.browser!, 'playlist');
  await this.browser!.waitUntil(
    async () => {
      const text = await el.getText();
      return text.toLowerCase().includes(expected.toLowerCase());
    },
    { timeout: 5000, timeoutMsg: `Queue did not display "${expected}"`, interval: 250 },
  );
});

Then('the clear queue button should be visible', async function (this: PyKaraokeWorld) {
  await waitForVisible(this.browser!, 'clearPlaylistBtn');
});
