/**
 * Step definitions for Player Controls feature.
 *
 * Maps to: features/player-controls.feature
 * Preserves coverage from: test_ui_buttons.py::TestPlayerControls, TestDiscoverAndClickButtons
 */

import { Given, When, Then } from '@cucumber/cucumber';
import { expect } from 'chai';
import { PyKaraokeWorld } from '../support/world';
import { findElement, SELECTORS } from '../support/selectors';

// ── Individual button clicks ────────────────────────────────────────────

When('the user clicks the play button', async function (this: PyKaraokeWorld) {
  const btn = await findElement(this.browser!, 'playBtn');
  await btn.click();
  // Allow state to settle
  await this.browser!.pause(300);
});

When('the user clicks the stop button', async function (this: PyKaraokeWorld) {
  const btn = await findElement(this.browser!, 'stopBtn');
  await btn.click();
  await this.browser!.pause(300);
});

When('the user clicks the next track button', async function (this: PyKaraokeWorld) {
  const btn = await findElement(this.browser!, 'nextBtn');
  await btn.click();
  await this.browser!.pause(300);
});

When('the user clicks the previous track button', async function (this: PyKaraokeWorld) {
  const btn = await findElement(this.browser!, 'prevBtn');
  await btn.click();
  await this.browser!.pause(300);
});

Then('the app should remain stable', async function (this: PyKaraokeWorld) {
  // Verify the app container is still present (no crash blanked the page)
  const apps = await this.browser!.$$(SELECTORS.app);
  expect(apps.length).to.equal(1, 'App container should still be present after interaction');
});

// ── Volume control ──────────────────────────────────────────────────────

When('the user sets the volume slider to {int}', async function (this: PyKaraokeWorld, value: number) {
  const slider = await findElement(this.browser!, 'volumeSlider');
  await this.browser!.execute(
    (sel: string, val: number) => {
      const el = document.querySelector(sel) as HTMLInputElement;
      if (el) {
        el.value = String(val);
        el.dispatchEvent(new Event('input', { bubbles: true }));
      }
    },
    SELECTORS.volumeSlider,
    value,
  );
  await this.browser!.pause(300);
});

Then('the volume display should show {string}', async function (this: PyKaraokeWorld, expected: string) {
  const el = await findElement(this.browser!, 'volumeValue');
  const text = await el.getText();
  expect(text).to.include(expected);
});

// ── Comprehensive button click test ─────────────────────────────────────

Then('every visible button should be clickable without crashing the app', async function (this: PyKaraokeWorld) {
  const buttons = await this.browser!.$$('button');
  expect(buttons.length).to.be.greaterThan(0, 'No buttons found on the page');

  let clickedCount = 0;

  for (const btn of buttons) {
    const isVisible = await btn.isDisplayed();
    if (!isVisible) continue;

    // Dismiss settings modal if it overlays the page
    try {
      await this.browser!.execute(() => {
        const modal = document.getElementById('settings-modal');
        if (modal && modal.style.display !== 'none') {
          modal.style.display = 'none';
        }
      });
    } catch {
      // Ignore
    }

    // Dismiss alerts from previous clicks
    try {
      await this.browser!.dismissAlert();
    } catch {
      // No alert present
    }

    // Re-check visibility after dismissing overlays
    const stillVisible = await btn.isDisplayed();
    if (!stillVisible) continue;

    await btn.click();
    await this.browser!.pause(300);

    // Verify no crash
    const apps = await this.browser!.$$(SELECTORS.app);
    const btnId = await btn.getAttribute('id') || await btn.getText();
    expect(apps.length).to.equal(1, `Page crashed after clicking "${btnId}"`);

    clickedCount++;
  }

  expect(clickedCount).to.be.at.least(5, `Only clicked ${clickedCount} buttons`);
});
