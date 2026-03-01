/**
 * Resilient selectors – helpers for locating UI elements by data-test-id,
 * falling back to element IDs when data attributes are not yet added.
 *
 * Prefer data-test-id attributes in the source HTML.  Until the HTML is
 * updated, these helpers use the existing id= attributes from index.html.
 */

import { Browser, Element } from 'webdriverio';

/** Selector map: logical name → CSS selector.
 *
 * Uses the existing id= attributes from the PyKaraoke NG index.html.
 * If data-test-id attributes are added later, update these selectors.
 */
export const SELECTORS = {
  // Root
  app: '#app',

  // Header
  settingsBtn: '#settings-btn',

  // Search
  searchInput: '#search-input',
  searchBtn: '#search-btn',
  folderInput: '#folder-input',
  addFolderBtn: '#add-folder-btn',
  scanLibraryBtn: '#scan-library-btn',
  libraryDetails: 'details.search-filters',

  // Results
  resultsList: '#results-list',

  // Player
  playBtn: '#play-btn',
  pauseBtn: '#pause-btn',
  stopBtn: '#stop-btn',
  nextBtn: '#next-btn',
  prevBtn: '#prev-btn',
  volumeSlider: '#volume-slider',
  volumeValue: '#volume-value',
  currentSongTitle: '#current-song-title',
  currentSongArtist: '#current-song-artist',
  timeCurrent: '#time-current',
  timeTotal: '#time-total',
  progressFill: '#progress-fill',

  // Queue
  playlist: '#playlist',
  clearPlaylistBtn: '#clear-playlist-btn',

  // Status
  statusMessage: '#status-message',
  backendStatus: '#backend-status',

  // Settings modal
  settingsModal: '#settings-modal',
  settingFullscreen: '#setting-fullscreen',
  settingZoom: '#setting-zoom',
  settingsCancelBtn: '#settings-cancel-btn',
  settingsCloseBtn: '#settings-close-btn',
  settingsSaveBtn: '#settings-save-btn',
} as const;

export type SelectorKey = keyof typeof SELECTORS;

/**
 * Find an element using a logical selector key.
 * Waits for the element to exist before returning.
 */
export async function findElement(
  browser: Browser<'async'>,
  key: SelectorKey,
): Promise<Element<'async'>> {
  const selector = SELECTORS[key];
  const el = await browser.$(selector);
  await el.waitForExist({ timeout: 10000 });
  return el;
}

/**
 * Wait until an element's text contains the expected substring.
 * Uses polling instead of hardcoded timeouts.
 */
export async function waitForTextContains(
  browser: Browser<'async'>,
  key: SelectorKey,
  expected: string,
  timeoutMs = 10000,
): Promise<void> {
  const selector = SELECTORS[key];
  await browser.waitUntil(
    async () => {
      const el = await browser.$(selector);
      const text = await el.getText();
      return text.includes(expected);
    },
    {
      timeout: timeoutMs,
      timeoutMsg: `Expected "${key}" (${selector}) to contain "${expected}" within ${timeoutMs}ms`,
      interval: 250,
    },
  );
}

/**
 * Wait until an element is displayed (visible).
 */
export async function waitForVisible(
  browser: Browser<'async'>,
  key: SelectorKey,
  timeoutMs = 10000,
): Promise<void> {
  const selector = SELECTORS[key];
  const el = await browser.$(selector);
  await el.waitForDisplayed({ timeout: timeoutMs });
}

/**
 * Wait until an element is NOT displayed.
 */
export async function waitForNotVisible(
  browser: Browser<'async'>,
  key: SelectorKey,
  timeoutMs = 10000,
): Promise<void> {
  const selector = SELECTORS[key];
  const el = await browser.$(selector);
  await el.waitForDisplayed({ timeout: timeoutMs, reverse: true });
}

/**
 * Check if an element is currently displayed.
 */
export async function isDisplayed(
  browser: Browser<'async'>,
  key: SelectorKey,
): Promise<boolean> {
  try {
    const selector = SELECTORS[key];
    const el = await browser.$(selector);
    return await el.isDisplayed();
  } catch {
    return false;
  }
}
