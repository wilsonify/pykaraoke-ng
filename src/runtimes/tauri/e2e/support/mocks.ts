/**
 * API mocking utilities – intercept fetch calls in the browser to simulate
 * backend states (connected, disconnected, error responses).
 *
 * This allows deterministic testing without reliance on a running backend.
 */

import { Browser } from 'webdriverio';

/**
 * Mock the backend as connected: /health returns 200, commands return ok.
 */
export async function mockBackendConnected(browser: Browser<'async'>): Promise<void> {
  // Inject a service worker or override fetch in the page context
  await browser.execute(() => {
    const originalFetch = window.fetch;

    (window as any).__originalFetch = originalFetch;
    (window as any).__mockBackend = true;

    window.fetch = async function (input: RequestInfo | URL, init?: RequestInit) {
      const url = typeof input === 'string' ? input : input.toString();

      if (url.includes('/health')) {
        return new Response(JSON.stringify({ status: 'ok' }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        });
      }

      if (url.includes('/api/command')) {
        const body = init?.body ? JSON.parse(init.body as string) : {};
        return new Response(
          JSON.stringify({
            status: 'ok',
            message: `Mock response for ${body.action}`,
            data: getMockData(body.action, body.params),
          }),
          {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          },
        );
      }

      return originalFetch.call(window, input, init);
    };

    function getMockData(action: string, params: any): any {
      switch (action) {
        case 'get_state':
          return {
            playback_state: 'stopped',
            current_song: null,
            position_ms: 0,
            duration_ms: 0,
            playlist: [],
            playlist_index: -1,
            volume: 0.75,
          };
        case 'search_songs':
          return { results: [] };
        case 'get_settings':
          return { fullscreen: false, zoom_mode: 'soft' };
        case 'scan_library':
          return { song_count: 0 };
        default:
          return null;
      }
    }
  });
}

/**
 * Mock the backend as disconnected: all fetch calls to backend endpoints reject.
 */
export async function mockBackendDisconnected(browser: Browser<'async'>): Promise<void> {
  await browser.execute(() => {
    const originalFetch = window.fetch;
    (window as any).__originalFetch = originalFetch;
    (window as any).__mockBackend = true;

    window.fetch = async function (input: RequestInfo | URL, init?: RequestInit) {
      const url = typeof input === 'string' ? input : input.toString();

      if (url.includes('/health') || url.includes('/api/')) {
        throw new TypeError('NetworkError: backend unreachable (mocked)');
      }

      return originalFetch.call(window, input, init);
    };
  });
}

/**
 * Restore original fetch if mocks were applied.
 */
export async function restoreFetch(browser: Browser<'async'>): Promise<void> {
  await browser.execute(() => {
    if ((window as any).__originalFetch) {
      window.fetch = (window as any).__originalFetch;
      delete (window as any).__originalFetch;
      delete (window as any).__mockBackend;
    }
  });
}
