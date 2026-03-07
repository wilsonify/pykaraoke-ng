# BDD End-to-End Tests for PyKaraoke NG

## Overview

This directory contains executable BDD specifications for the PyKaraoke NG
Tauri desktop application.  Feature files are written in Gherkin and executed
by [Cucumber.js](https://cucumber.io/docs/installation/javascript/) with
[WebdriverIO](https://webdriver.io/) as the browser automation driver.

## Structure

```
e2e/
├── features/               # Gherkin feature files (executable documentation)
│   ├── application-startup.feature
│   ├── main-window-ui.feature
│   ├── navigation.feature
│   ├── player-controls.feature
│   ├── song-search.feature
│   ├── library-management.feature
│   ├── playlist-management.feature
│   ├── settings-persistence.feature
│   ├── error-handling.feature
│   ├── tauri-packaging.feature
│   └── database-scan.feature
├── steps/                  # Step definitions (thin, delegate to support)
│   ├── application-startup.steps.ts
│   ├── main-window-ui.steps.ts
│   ├── navigation.steps.ts
│   ├── player-controls.steps.ts
│   ├── song-search.steps.ts
│   ├── library-management.steps.ts
│   ├── playlist-management.steps.ts
│   ├── settings-persistence.steps.ts
│   ├── error-handling.steps.ts
│   ├── tauri-packaging.steps.ts
│   └── database-scan.steps.ts
├── support/                # Test infrastructure
│   ├── world.ts            # Shared context (World) for each scenario
│   ├── hooks.ts            # Before/After lifecycle hooks
│   ├── app-lifecycle.ts    # Browser launch/close/reset
│   ├── selectors.ts        # Resilient element selectors
│   ├── logging.ts          # Screenshot capture, structured logging
│   └── mocks.ts            # API mocking (connected/disconnected)
├── reports/                # Auto-generated test reports & screenshots
├── cucumber.js             # Local development config
├── cucumber.ci.js          # CI config (fail-fast, structured reports)
├── package.json
├── tsconfig.json
└── README.md
```

## Quick Start

```bash
cd src/runtimes/tauri/e2e

# Install dependencies
npm install

# Start the application under test (in another terminal)
cd ../../../..
docker compose --profile e2e up -d

# Run BDD tests
npm run test:e2e

# Run in CI mode (fail-fast, JSON + HTML reports)
npm run test:e2e:ci

# Watch mode (re-runs on file changes)
npm run test:e2e:watch
```

## Environment Variables

| Variable        | Default                         | Description                          |
| --------------- | ------------------------------- | ------------------------------------ |
| `E2E_APP_URL`   | `http://localhost:3000`         | URL of the application under test    |
| `SELENIUM_URL`  | (local ChromeDriver)            | Remote Selenium hub URL              |

## Design Principles

1. **Feature files are executable documentation** – readable by non-developers.
2. **Step definitions are thin** – they delegate to support utilities.
3. **Selectors are centralised** in `support/selectors.ts` for resilience.
4. **No hardcoded timeouts** – use `waitUntil` with polling intervals.
5. **Mocks isolate from production APIs** – `support/mocks.ts` intercepts fetch.
6. **Screenshots on failure** are auto-captured and attached to reports.

## Coverage Mapping

The BDD features preserve all test intent from the original Python e2e tests:

| Original Python Test                                    | BDD Feature                     |
| ------------------------------------------------------- | ------------------------------- |
| `test_ui_buttons.py::TestBackendConnection`             | `application-startup.feature`   |
| `test_ui_buttons.py::TestDiscoverAndClickButtons`       | `player-controls.feature`       |
| `test_ui_buttons.py::TestPlayerControls`                | `player-controls.feature`       |
| `test_ui_buttons.py::TestSearchFlow`                    | `song-search.feature`           |
| `test_ui_buttons.py::TestClearPlaylist`                 | `playlist-management.feature`   |
| `test_ui_buttons.py::TestSettingsModal`                 | `settings-persistence.feature`  |
| `test_ui_buttons.py::TestAddFolder`                     | `library-management.feature`    |
| `test_tauri_packaging.py::TestWebKitDmabufWorkaround`   | `tauri-packaging.feature`       |
| `test_tauri_packaging.py::TestBackendPathResolution`    | `tauri-packaging.feature`       |
| `test_tauri_packaging.py::TestTauriBundleResources`     | `tauri-packaging.feature`       |
| `test_tauri_packaging.py::TestJavaScriptApiResilience`  | `tauri-packaging.feature`       |
| `test_end_to_end.py::test_end_to_end_database_scan...` | `database-scan.feature`         |
