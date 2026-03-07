/**
 * Step definitions for Playlist Management feature.
 *
 * Maps to: features/playlist-management.feature
 * Preserves coverage from: test_ui_buttons.py::TestClearPlaylist
 */

import { When, Then } from '@cucumber/cucumber';
import { expect } from 'chai';
import { PyKaraokeWorld } from '../support/world';
import { findElement, SELECTORS } from '../support/selectors';

When('the user clicks the clear queue button', async function (this: PyKaraokeWorld) {
  const btn = await findElement(this.browser!, 'clearPlaylistBtn');
  await btn.click();
  await this.browser!.pause(300);
});
