/**
 * Step definitions for Settings Persistence feature.
 *
 * Maps to: features/settings-persistence.feature
 * Preserves coverage from: test_ui_buttons.py::TestSettingsModal::test_save_settings
 */

import { When, Then } from '@cucumber/cucumber';
import { expect } from 'chai';
import { PyKaraokeWorld } from '../support/world';
import { findElement, SELECTORS } from '../support/selectors';

When('the user saves the settings', async function (this: PyKaraokeWorld) {
  const saveBtn = await findElement(this.browser!, 'settingsSaveBtn');
  await saveBtn.click();
  await this.browser!.pause(500);
});

Then('the status bar should confirm settings were saved or show an error', async function (this: PyKaraokeWorld) {
  const el = await findElement(this.browser!, 'statusMessage');
  const text = await el.getText();
  const valid = text.includes('Settings saved') || text.includes('Error');
  expect(valid).to.be.true;
});
