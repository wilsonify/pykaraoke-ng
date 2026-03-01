/**
 * BDD World – shared context passed between step definitions within a scenario.
 *
 * Holds the browser instance, app state, and helper references so that
 * step definitions remain thin and delegate to support utilities.
 */

import { World, IWorldOptions, setWorldConstructor } from '@cucumber/cucumber';
import { Browser, RemoteOptions } from 'webdriverio';

export interface AppWorld extends World {
  /** WebdriverIO browser instance for the current scenario. */
  browser: Browser<'async'> | null;

  /** The base URL of the running application under test. */
  appUrl: string;

  /** Whether the backend should be mocked as unreachable for this scenario. */
  backendDisconnected: boolean;

  /** Collected error messages during this scenario. */
  errors: string[];

  /** Screenshot paths captured during this scenario (for debugging). */
  screenshots: string[];
}

export class PyKaraokeWorld extends World implements AppWorld {
  browser: Browser<'async'> | null = null;
  appUrl: string;
  backendDisconnected = false;
  errors: string[] = [];
  screenshots: string[] = [];

  constructor(options: IWorldOptions) {
    super(options);
    // Configurable via environment variable; defaults to docker-compose UI service
    this.appUrl = process.env.E2E_APP_URL || 'http://localhost:3000';
  }
}

setWorldConstructor(PyKaraokeWorld);
