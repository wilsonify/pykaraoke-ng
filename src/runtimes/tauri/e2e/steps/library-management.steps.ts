/**
 * Step definitions for Library Management feature.
 *
 * Maps to: features/library-management.feature
 * Preserves coverage from: test_ui_buttons.py::TestSearchFlow::test_scan_library,
 *                           test_ui_buttons.py::TestAddFolder
 */

import { When, Then } from '@cucumber/cucumber';
import { expect } from 'chai';
import { PyKaraokeWorld } from '../support/world';
import { findElement, SELECTORS } from '../support/selectors';

When('the user clicks the scan library button', async function (this: PyKaraokeWorld) {
  const btn = await findElement(this.browser!, 'scanLibraryBtn');
  await btn.click();
  await this.browser!.pause(1000);
});

Then('the status bar should indicate scanning activity', async function (this: PyKaraokeWorld) {
  const el = await findElement(this.browser!, 'statusMessage');
  const text = await el.getText();
  const hasScanning = text.toLowerCase().includes('scan') || text.includes('Backend');
  expect(hasScanning).to.be.true;
});

When('the user enters {string} in the folder input', async function (this: PyKaraokeWorld, path: string) {
  const input = await findElement(this.browser!, 'folderInput');
  await input.clearValue();
  await input.setValue(path);
});

When('the user clicks the add folder button', async function (this: PyKaraokeWorld) {
  const btn = await findElement(this.browser!, 'addFolderBtn');
  await btn.click();
  await this.browser!.pause(1000);
});

Then('the status bar should confirm the folder was added or show an error', async function (this: PyKaraokeWorld) {
  const el = await findElement(this.browser!, 'statusMessage');
  const text = await el.getText();
  const valid = text.includes('Folder added') || text.includes('Error');
  expect(valid).to.be.true;
});

When('the user clears the folder input', async function (this: PyKaraokeWorld) {
  const input = await findElement(this.browser!, 'folderInput');
  await input.clearValue();
});

Then('the status bar should display {string}', async function (this: PyKaraokeWorld, expected: string) {
  const el = await findElement(this.browser!, 'statusMessage');
  await this.browser!.waitUntil(
    async () => {
      const text = await el.getText();
      return text.includes(expected);
    },
    { timeout: 5000, timeoutMsg: `Status bar should contain "${expected}"`, interval: 250 },
  );
});
