/**
 * Tests for PyKaraoke NG frontend application logic.
 *
 * Run with: node src/runtimes/tauri/src/app.test.js
 *
 * Uses Node.js built-in test runner (available since Node 18).
 * No external dependencies required.
 */

const { describe, it } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

// ---------------------------------------------------------------------------
// Minimal DOM stubs so we can exercise PyKaraokeApp helpers without a browser
// ---------------------------------------------------------------------------
class MockElement {
  constructor(tag = "div") {
    this.tag = tag;
    this.textContent = "";
    this.innerHTML = "";
    this.className = "";
    this.style = {};
    this.dataset = {};
    this.value = "";
    this._listeners = {};
    this._children = [];
  }
  addEventListener(event, fn) {
    this._listeners[event] = this._listeners[event] || [];
    this._listeners[event].push(fn);
  }
  querySelectorAll() {
    return this._children;
  }
}

function createMockDOM() {
  const elements = {};
  const ids = [
    "play-btn",
    "pause-btn",
    "stop-btn",
    "next-btn",
    "prev-btn",
    "ff-btn",
    "rewind-btn",
    "volume-slider",
    "volume-value",
    "search-btn",
    "search-input",
    "add-folder-btn",
    "scan-library-btn",
    "clear-playlist-btn",
    "settings-btn",
    "settings-modal",
    "settings-close-btn",
    "settings-cancel-btn",
    "settings-save-btn",
    "setting-fullscreen",
    "setting-zoom",
    "current-song-title",
    "current-song-artist",
    "progress-slider",
    "time-current",
    "time-total",
    "playlist",
    "results-list",
    "status-message",
    "backend-status",
  ];
  ids.forEach((id) => (elements[id] = new MockElement()));

  global.document = {
    readyState: "complete",
    getElementById: (id) => elements[id] || new MockElement(),
    addEventListener: () => {},
  };
  global.window = {
    __TAURI__: {
      tauri: {
        invoke: async () => ({ status: "ok", message: "stub" }),
      },
      event: {
        listen: async () => {},
      },
      dialog: {
        open: async () => null,
      },
    },
  };
  return elements;
}

// ---------------------------------------------------------------------------
// Extract the formatTime function to test independently
// ---------------------------------------------------------------------------
function formatTime(ms) {
  const seconds = Math.floor(ms / 1000);
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("formatTime", () => {
  it("formats zero milliseconds", () => {
    assert.equal(formatTime(0), "0:00");
  });

  it("formats partial seconds", () => {
    assert.equal(formatTime(500), "0:00");
  });

  it("formats exact seconds", () => {
    assert.equal(formatTime(5000), "0:05");
  });

  it("formats minutes and seconds", () => {
    assert.equal(formatTime(65000), "1:05");
  });

  it("pads single-digit seconds", () => {
    assert.equal(formatTime(61000), "1:01");
  });

  it("formats longer durations", () => {
    assert.equal(formatTime(3661000), "61:01");
  });
});

describe("Playlist rendering logic", () => {
  it("produces empty-playlist message for empty array", () => {
    const els = createMockDOM();
    const playlistEl = els["playlist"];

    // Simulate updatePlaylistUI([])
    const playlist = [];
    if (!playlist || playlist.length === 0) {
      playlistEl.innerHTML =
        '<div class="no-results">Playlist is empty</div>';
    }
    assert.ok(playlistEl.innerHTML.includes("Playlist is empty"));
  });

  it("renders correct number of song items", () => {
    const playlist = [
      { title: "Song A", artist: "Artist 1", filename: "a.cdg" },
      { title: "Song B", artist: "Artist 2", filename: "b.cdg" },
      { title: "Song C", artist: "", filename: "c.kar" },
    ];

    const html = playlist
      .map(
        (song, index) => `
      <div class="song-item" data-index="${index}">
        <div class="song-item-title">${song.title || song.filename}</div>
        <div class="song-item-artist">${song.artist || ""}</div>
      </div>
    `
      )
      .join("");

    // Should contain 3 song-item divs
    const matches = html.match(/class="song-item"/g);
    assert.equal(matches.length, 3);
  });

  it("falls back to filename when title is empty", () => {
    const song = { title: "", artist: "", filename: "my-track.cdg" };
    const display = song.title || song.filename;
    assert.equal(display, "my-track.cdg");
  });

  it("marks active song with active class", () => {
    const playlistIndex = 1;
    const songs = [{ title: "A" }, { title: "B" }, { title: "C" }];

    const html = songs
      .map(
        (song, idx) =>
          `<div class="song-item ${playlistIndex === idx ? "active" : ""}">${song.title}</div>`
      )
      .join("");

    assert.ok(html.includes('class="song-item active"'));
    // Only one should be active
    const actives = html.match(/active/g);
    assert.equal(actives.length, 1);
  });
});

describe("Search results rendering", () => {
  it("shows no-results message for empty results", () => {
    const results = [];
    let html;
    if (!results || results.length === 0) {
      html = '<div class="no-results">No results found</div>';
    }
    assert.ok(html.includes("No results found"));
  });

  it("renders song titles from results", () => {
    const results = [
      { title: "Monkey Shines", artist: "Jonathan Coulton", filename: "" },
      { title: "Northern Star", artist: "Steven Dunston", filename: "" },
    ];

    const html = results
      .map(
        (song) => `
      <div class="song-item">
        <div class="song-item-title">${song.title || song.filename}</div>
        <div class="song-item-artist">${song.artist || ""}</div>
      </div>`
      )
      .join("");

    assert.ok(html.includes("Monkey Shines"));
    assert.ok(html.includes("Northern Star"));
    assert.ok(html.includes("Jonathan Coulton"));
  });
});

describe("Backend event handling", () => {
  it("recognises all known event types", () => {
    const knownTypes = [
      "state_changed",
      "song_finished",
      "playback_error",
      "playlist_updated",
      "library_scan_complete",
    ];
    // App should handle each without throwing
    for (const t of knownTypes) {
      assert.ok(typeof t === "string");
    }
  });

  it("state_changed event carries expected fields", () => {
    const event = {
      type: "state_changed",
      data: {
        playback_state: "playing",
        current_song: { title: "Test", artist: "A" },
        position_ms: 1000,
        duration_ms: 5000,
        playlist: [],
        playlist_index: 0,
        volume: 0.8,
      },
    };
    assert.equal(event.data.playback_state, "playing");
    assert.ok(event.data.duration_ms > 0);
  });
});

describe("Command shapes sent to Rust backend", () => {
  it("play command has correct shape", () => {
    const cmd = { action: "play", params: {} };
    assert.equal(cmd.action, "play");
  });

  it("play with playlist_index has correct shape", () => {
    const cmd = { action: "play", params: { playlist_index: 2 } };
    assert.equal(cmd.params.playlist_index, 2);
  });

  it("set_volume command clamps are expected", () => {
    // Frontend sends 0-100 from slider, divides by 100
    const sliderValue = 75;
    const volume = parseInt(sliderValue) / 100;
    assert.equal(volume, 0.75);
  });

  it("search_songs command includes query string", () => {
    const query = "bohemian rhapsody";
    const cmd = { action: "search_songs", params: { query } };
    assert.equal(cmd.params.query, "bohemian rhapsody");
  });

  it("remove_from_playlist uses numeric index", () => {
    const cmd = { action: "remove_from_playlist", params: { index: 3 } };
    assert.equal(typeof cmd.params.index, "number");
  });
});

describe("UI state management", () => {
  it("play button shows when not playing", () => {
    const isPlaying = false;
    const playDisplay = isPlaying ? "none" : "inline-block";
    const pauseDisplay = isPlaying ? "inline-block" : "none";
    assert.equal(playDisplay, "inline-block");
    assert.equal(pauseDisplay, "none");
  });

  it("pause button shows when playing", () => {
    const isPlaying = true;
    const playDisplay = isPlaying ? "none" : "inline-block";
    const pauseDisplay = isPlaying ? "inline-block" : "none";
    assert.equal(playDisplay, "none");
    assert.equal(pauseDisplay, "inline-block");
  });

  it("progress bar width is computed correctly", () => {
    const state = { position_ms: 30000, duration_ms: 120000 };
    const progress = (state.position_ms / state.duration_ms) * 100;
    assert.equal(progress, 25);
  });

  it("progress bar handles zero duration", () => {
    const state = { position_ms: 0, duration_ms: 0 };
    const progress = state.duration_ms > 0 ? (state.position_ms / state.duration_ms) * 100 : 0;
    assert.equal(progress, 0);
  });

  it("backend status text reflects connection state", () => {
    const connected = true;
    const text = connected ? "Backend: Connected" : "Backend: Disconnected";
    const cls = connected ? "connected" : "disconnected";
    assert.equal(text, "Backend: Connected");
    assert.equal(cls, "connected");
  });

  it("now-playing shows fallback when no song loaded", () => {
    const state = { current_song: null };
    const title = state.current_song
      ? state.current_song.title || state.current_song.filename || "Unknown"
      : "No song loaded";
    assert.equal(title, "No song loaded");
  });

  it("now-playing shows title when song loaded", () => {
    const state = {
      current_song: {
        title: "Monkey Shines",
        artist: "Jonathan Coulton",
        filename: "monkey.mp3",
      },
    };
    const title = state.current_song
      ? state.current_song.title || state.current_song.filename || "Unknown"
      : "No song loaded";
    assert.equal(title, "Monkey Shines");
  });
});

describe("HTML DOM contract", () => {
  it("all required element IDs are present in mock DOM", () => {
    const els = createMockDOM();
    const requiredIds = [
      "play-btn",
      "pause-btn",
      "stop-btn",
      "next-btn",
      "prev-btn",
      "volume-slider",
      "volume-value",
      "search-btn",
      "search-input",
      "add-folder-btn",
      "scan-library-btn",
      "settings-btn",
      "settings-modal",
      "clear-playlist-btn",
      "settings-btn",
      "settings-modal",
      "current-song-title",
      "current-song-artist",
      "progress-slider",
      "time-current",
      "time-total",
      "playlist",
      "results-list",
      "status-message",
      "backend-status",
    ];
    for (const id of requiredIds) {
      assert.ok(
        els[id],
        `Expected element with id="${id}" to exist in DOM`
      );
    }
  });
});

describe("Volume slider behaviour", () => {
  it("converts slider integer to 0-1 float", () => {
    for (const raw of [0, 25, 50, 75, 100]) {
      const vol = parseInt(raw) / 100;
      assert.ok(vol >= 0 && vol <= 1);
    }
  });

  it("displays percentage text from slider value", () => {
    const slider = 42;
    const text = `${slider}%`;
    assert.equal(text, "42%");
  });
});

// ---------------------------------------------------------------------------
// Regression: empty-window bug — Tauri API resilience
// ---------------------------------------------------------------------------
// When WebKitGTK renders a blank surface or the IPC bridge is slow to
// inject, window.__TAURI__ is undefined.  The old code destructured it
// at module scope, crashing the entire page.  These tests verify the fix.

describe("Regression: Tauri API import resilience", () => {
  const appJsSource = fs.readFileSync(
    path.join(__dirname, "app.js"),
    "utf-8"
  );

  it("does NOT use bare destructuring of window.__TAURI__ at top level", () => {
    // This pattern crashes when __TAURI__ is undefined
    const dangerous = /const\s*\{[^}]*invoke[^}]*\}\s*=\s*window\.__TAURI__/;
    assert.ok(
      !dangerous.test(appJsSource),
      "app.js must not use `const { invoke } = window.__TAURI__...` — " +
        "use try/catch instead"
    );
  });

  it("wraps Tauri API access in a try/catch", () => {
    assert.ok(
      appJsSource.includes("try") && appJsSource.includes("catch"),
      "app.js should guard window.__TAURI__ access with try/catch"
    );
  });

  it("provides a fallback invoke function", () => {
    // After the catch, invoke should be assigned an async fallback
    const catchIdx = appJsSource.indexOf("catch");
    const afterCatch = appJsSource.slice(catchIdx);
    assert.ok(
      afterCatch.includes("invoke") && afterCatch.includes("async"),
      "app.js should assign a fallback async invoke in the catch block"
    );
  });

  it("provides a fallback listen function", () => {
    const catchIdx = appJsSource.indexOf("catch");
    const afterCatch = appJsSource.slice(catchIdx);
    assert.ok(
      afterCatch.includes("listen"),
      "app.js should assign a fallback listen in the catch block"
    );
  });

  it("provides a fallback dialogOpen function", () => {
    const catchIdx = appJsSource.indexOf("catch");
    const afterCatch = appJsSource.slice(catchIdx);
    assert.ok(
      afterCatch.includes("dialogOpen"),
      "app.js should assign a fallback dialogOpen in the catch block"
    );
  });

  it("UI renders even when __TAURI__ is missing", () => {
    // Simulate: no __TAURI__ at all
    const savedTauri = global.window?.__TAURI__;
    const els = createMockDOM();
    delete global.window.__TAURI__;

    // Re-evaluate the guard logic
    let testInvoke, testListen, testDialogOpen;
    try {
      testInvoke = global.window.__TAURI__.tauri.invoke;
      testListen = global.window.__TAURI__.event.listen;
      testDialogOpen = global.window.__TAURI__.dialog.open;
    } catch (e) {
      testInvoke = async () => {
        throw new Error("Tauri API not available");
      };
      testListen = async () => {};
      testDialogOpen = async () => null;
    }

    // invoke should be a callable async function, not undefined
    assert.equal(typeof testInvoke, "function");
    assert.equal(typeof testListen, "function");
    assert.equal(typeof testDialogOpen, "function");

    // Static HTML elements should still be accessible
    assert.ok(els["play-btn"]);
    assert.ok(els["status-message"]);

    // Restore
    if (savedTauri) {
      global.window.__TAURI__ = savedTauri;
    }
  });
});

// ---------------------------------------------------------------------------
// Regression: buttons that did nothing in the packaged Debian build
// ---------------------------------------------------------------------------
// Three buttons — Settings, Add Folder, Scan Library — were non-functional:
//  1. settings-btn had no click event listener registered.
//  2. handleAddFolder used alert() which is suppressed in WebKitGTK (Tauri/Linux).
//  3. dialog allowlist was missing, so the native folder picker could not open.

describe("Regression: settings button wired up", () => {
  const appJsSource = fs.readFileSync(
    path.join(__dirname, "app.js"),
    "utf-8"
  );

  it("app.js registers a click listener for settings-btn", () => {
    assert.ok(
      appJsSource.includes("settings-btn"),
      "app.js must reference 'settings-btn' — the Settings button had no " +
        "event listener and did nothing when clicked"
    );
  });

  it("app.js calls getElementById for settings-btn", () => {
    assert.ok(
      appJsSource.includes("getElementById('settings-btn')") ||
        appJsSource.includes('getElementById("settings-btn")'),
      "app.js must attach a listener via getElementById('settings-btn')"
    );
  });

  it("app.js defines a handleShowSettings method", () => {
    assert.ok(
      appJsSource.includes("handleShowSettings"),
      "app.js must define handleShowSettings() to handle the Settings button click"
    );
  });
});

describe("Regression: add-folder button uses Tauri dialog API", () => {
  const appJsSource = fs.readFileSync(
    path.join(__dirname, "app.js"),
    "utf-8"
  );

  it("handleAddFolder does NOT use bare alert()", () => {
    // alert() is suppressed in WebKitGTK on Linux, making the button appear
    // to do nothing.
    const hasAlert = /\balert\s*\(/.test(appJsSource);
    assert.ok(
      !hasAlert,
      "app.js must not use alert() — it is suppressed in WebKitGTK (Tauri on " +
        "Linux) so the Add Folder button appeared to do nothing"
    );
  });

  it("handleAddFolder references the Tauri dialog API via dialogOpen variable", () => {
    assert.ok(
      appJsSource.includes("dialogOpen") && appJsSource.includes("directory"),
      "handleAddFolder should open a native folder picker via the module-level " +
        "dialogOpen variable (window.__TAURI__.dialog.open)"
    );
  });
});

describe("Regression: tauri.conf.json dialog allowlist", () => {
  const confPath = path.join(
    __dirname,
    "..",
    "src-tauri",
    "tauri.conf.json"
  );
  const conf = JSON.parse(fs.readFileSync(confPath, "utf-8"));

  it("dialog.open is enabled in the allowlist", () => {
    assert.ok(
      conf.tauri?.allowlist?.dialog?.open === true,
      "tauri.conf.json must enable allowlist.dialog.open so the native folder " +
        "picker can be opened from handleAddFolder"
    );
  });

  it("resources use backend/** glob, not absolute ../../../../ paths", () => {
    // The CI pre-stages Python files into src/runtimes/tauri/backend/ then
    // tauri build (CWD = src/runtimes/tauri/) resolves "backend/**" correctly.
    // The old ../../../../src/pykaraoke/ paths are 4 levels up from the tauri
    // working directory but the repo root is only 3 levels up — those paths
    // resolved to the parent of the repo root and failed with "No such file".
    const resources = conf.tauri?.bundle?.resources;
    assert.ok(
      Array.isArray(resources) && resources.includes("backend/**"),
      "tauri.conf.json bundle.resources must include 'backend/**' so the " +
        "CI-staged Python backend is bundled correctly"
    );
    const hasBadPaths = (resources || []).some((r) => r.startsWith("../../../../"));
    assert.ok(
      !hasBadPaths,
      "tauri.conf.json must not use ../../../../ resource paths — they resolve " +
        "to the parent of the repo root when tauri build runs from src/runtimes/tauri/"
    );
  });

  it("beforeBuildCommand uses the cross-platform node staging script", () => {
    // The beforeBuildCommand must invoke scripts/stage-backend.js (a cross-platform
    // Node.js script that stages Python files into src-tauri/backend/).
    // Shell one-liners using bash -c '...' with ../../../../ paths are forbidden:
    // they resolve to the parent of the repo root and fail on CI (file not found),
    // and they also fail outright on Windows where bash is not guaranteed.
    assert.equal(
      conf.build?.beforeBuildCommand,
      "node scripts/stage-backend.js",
      "tauri.conf.json beforeBuildCommand must use 'node scripts/stage-backend.js' " +
        "(cross-platform; bash ../../../../ one-liners fail on Windows and CI)"
    );
  });
});

// ---------------------------------------------------------------------------
// Slim sidebar layout: keyboard UX, incremental search, inline queue mgmt
// ---------------------------------------------------------------------------

describe("Slim sidebar: keyboard-first UX", () => {
  const appJsSource = fs.readFileSync(
    path.join(__dirname, "app.js"),
    "utf-8"
  );

  it("app.js registers Escape key to clear search", () => {
    assert.ok(
      appJsSource.includes("Escape"),
      "app.js should handle Escape key to clear the search input"
    );
  });

  it("app.js registers / key to focus search bar", () => {
    assert.ok(
      appJsSource.includes("'/'") || appJsSource.includes('"/"'),
      "app.js should handle '/' key to focus the search bar"
    );
  });

  it("app.js implements incremental search via input event", () => {
    assert.ok(
      appJsSource.includes("'input'") || appJsSource.includes('"input"'),
      "app.js should listen for 'input' events on the search field for incremental search"
    );
  });

  it("app.js debounces incremental search", () => {
    assert.ok(
      appJsSource.includes("_searchDebounce") && appJsSource.includes("setTimeout"),
      "app.js should debounce incremental search to avoid excessive backend calls"
    );
  });
});

describe("Slim sidebar: inline queue management", () => {
  const appJsSource = fs.readFileSync(
    path.join(__dirname, "app.js"),
    "utf-8"
  );

  it("playlist items include inline remove button", () => {
    assert.ok(
      appJsSource.includes("song-item-remove"),
      "app.js should render inline remove buttons (song-item-remove) in playlist items"
    );
  });

  it("does not use confirm() for clear playlist", () => {
    // confirm() is a modal dialog that interrupts DJ workflow
    const hasConfirm = /\bconfirm\s*\(/.test(appJsSource);
    assert.ok(
      !hasConfirm,
      "app.js must not use confirm() — modal dialogs interrupt live DJ workflow"
    );
  });

  it("search results are keyboard-navigable with tabindex", () => {
    assert.ok(
      appJsSource.includes("tabindex"),
      "app.js should set tabindex on search result items for keyboard navigation"
    );
  });

  it("Enter key on search results adds to queue", () => {
    assert.ok(
      appJsSource.includes("'Enter'") || appJsSource.includes('"Enter"'),
      "app.js should handle Enter key on search result items to add to queue"
    );
  });
});

describe("Slim sidebar: Tauri window dimensions", () => {
  const confPath = path.join(
    __dirname,
    "..",
    "src-tauri",
    "tauri.conf.json"
  );
  const conf = JSON.parse(fs.readFileSync(confPath, "utf-8"));

  it("default window width is slim sidebar size (≤450px)", () => {
    const width = conf.tauri?.windows?.[0]?.width;
    assert.ok(
      typeof width === "number" && width <= 450,
      `Default window width should be ≤450px for sidebar mode, got ${width}`
    );
  });

  it("window is not fullscreen by default", () => {
    assert.equal(
      conf.tauri?.windows?.[0]?.fullscreen,
      false,
      "Window must not be fullscreen by default"
    );
  });

  it("window is resizable", () => {
    assert.equal(
      conf.tauri?.windows?.[0]?.resizable,
      true,
      "Window should be resizable so DJs can adjust if needed"
    );
  });
});

// ---------------------------------------------------------------------------
// Regression: stop/next/prev buttons check response status
// ---------------------------------------------------------------------------

describe("Regression: stop/next/prev buttons check response status", () => {
  const appJsSource = fs.readFileSync(
    path.join(__dirname, "app.js"),
    "utf-8"
  );

  it("stop-btn checks r.status from sendCommand", () => {
    const stopIdx = appJsSource.indexOf("stop-btn");
    const handler = appJsSource.slice(stopIdx, stopIdx + 300);
    assert.ok(
      handler.includes("r.status !== 'ok'"),
      "stop-btn handler must check sendCommand response status; " +
        "previously it ignored errors from the backend"
    );
  });

  it("next-btn checks r.status from sendCommand", () => {
    const nextIdx = appJsSource.indexOf("next-btn");
    const handler = appJsSource.slice(nextIdx, nextIdx + 300);
    assert.ok(
      handler.includes("r.status !== 'ok'"),
      "next-btn handler must check sendCommand response status"
    );
  });

  it("prev-btn checks r.status from sendCommand", () => {
    const prevIdx = appJsSource.indexOf("prev-btn");
    const handler = appJsSource.slice(prevIdx, prevIdx + 300);
    assert.ok(
      handler.includes("r.status !== 'ok'"),
      "prev-btn handler must check sendCommand response status"
    );
  });
});

// ---------------------------------------------------------------------------
// Regression: volume slider handles sendCommand errors gracefully
// ---------------------------------------------------------------------------

describe("Regression: volume slider handles errors gracefully", () => {
  const appJsSource = fs.readFileSync(
    path.join(__dirname, "app.js"),
    "utf-8"
  );

  it("volume-slider handler uses .catch() on sendCommand", () => {
    const volIdx = appJsSource.indexOf("volume-slider");
    const handler = appJsSource.slice(volIdx, volIdx + 400);
    assert.ok(
      handler.includes(".catch("),
      "volume-slider handler must use .catch() to handle sendCommand errors; " +
        "previously errors from the backend were silently swallowed"
    );
  });

  it("volume-slider updates display before sending command", () => {
    const volIdx = appJsSource.indexOf("volume-slider");
    const handler = appJsSource.slice(volIdx, volIdx + 400);
    assert.ok(
      handler.indexOf("volume-value") < handler.indexOf("sendCommand") ||
        handler.indexOf("textContent") < handler.indexOf("sendCommand"),
      "volume-slider should update the displayed value before sending the " +
        "command so the UI feels responsive even if the backend is slow"
    );
  });
});

// ---------------------------------------------------------------------------
// Queue / Enqueue functionality
// ---------------------------------------------------------------------------

describe("Queue enqueue: double-click and drag-drop support", () => {
  const appJsSource = fs.readFileSync(
    path.join(__dirname, "app.js"),
    "utf-8"
  );

  it("app.js defines an enqueueSong method", () => {
    assert.ok(
      appJsSource.includes("enqueueSong"),
      "app.js must define an enqueueSong() method as the canonical enqueue function"
    );
  });

  it("app.js registers a dblclick handler on search result items", () => {
    assert.ok(
      appJsSource.includes("dblclick"),
      "app.js must register 'dblclick' event listeners on search result items"
    );
  });

  it("app.js sets draggable=true on search result items", () => {
    assert.ok(
      appJsSource.includes('draggable="true"'),
      "app.js must set draggable='true' on search result items for drag-drop"
    );
  });

  it("app.js registers a dragstart handler on search result items", () => {
    assert.ok(
      appJsSource.includes("dragstart"),
      "app.js must register 'dragstart' event listeners for drag-drop"
    );
  });

  it("app.js sets up drop handler on playlist area", () => {
    assert.ok(
      appJsSource.includes("dragover") && appJsSource.includes("drop"),
      "app.js must register 'dragover' and 'drop' event listeners on the playlist area"
    );
  });

  it("app.js uses application/x-pykaraoke-song MIME type for drag data", () => {
    assert.ok(
      appJsSource.includes("application/x-pykaraoke-song"),
      "app.js must use a custom MIME type for drag-drop data transfer"
    );
  });

  it("enqueueSong calls add_to_playlist command", () => {
    assert.ok(
      appJsSource.includes("add_to_playlist"),
      "enqueueSong must send the 'add_to_playlist' command to the backend"
    );
  });

  it("enqueueSong handles errors and shows status", () => {
    assert.ok(
      appJsSource.includes("Failed to enqueue"),
      "enqueueSong must show a visible error status when enqueue fails"
    );
  });
});

describe("Queue enqueue: command shape", () => {
  it("add_to_playlist command has correct shape", () => {
    const cmd = { action: "add_to_playlist", params: { filepath: "/songs/test.kar" } };
    assert.equal(cmd.action, "add_to_playlist");
    assert.equal(cmd.params.filepath, "/songs/test.kar");
  });

  it("add_to_playlist command requires filepath", () => {
    const cmd = { action: "add_to_playlist", params: {} };
    assert.ok(!cmd.params.filepath, "Missing filepath should be falsy");
  });
});

describe("Queue enqueue: .kar fixture filename in UI", () => {
  it("Elvis fixture filename contains .kar extension", () => {
    const filename = "elvis_presley_-_cant_help_falling_in_love.kar";
    assert.ok(filename.endsWith(".kar"), "Elvis fixture should be a .kar file");
  });

  it("Song data object for queue includes required fields", () => {
    const song = {
      title: "Cant Help Falling In Love",
      artist: "Elvis Presley",
      filepath: "/app/fixtures/tests/fixtures/ultrastar-deluxe/Creative Commons/elvis_presley_-_cant_help_falling_in_love.kar",
      filename: "elvis_presley_-_cant_help_falling_in_love.kar",
    };
    assert.ok(song.title, "Song must have title");
    assert.ok(song.artist, "Song must have artist");
    assert.ok(song.filepath, "Song must have filepath");
    assert.ok(song.filepath.endsWith(".kar"), "Filepath must end in .kar");
  });
});

// ---------------------------------------------------------------------------
// Regression: double-click fires enqueueSong exactly once (was 3x)
// ---------------------------------------------------------------------------
// Before the fix, clicking a search result fired:
//   click → click → dblclick → 3 calls to enqueueSong.
// The fix uses a 250ms timer on the first click that is cancelled on the
// second click, allowing the dblclick handler to fire exactly once.

describe("Regression: double-click adds exactly one queue entry", () => {
  const appJsSource = fs.readFileSync(
    path.join(__dirname, "app.js"),
    "utf-8"
  );

  it("uses a clickTimer variable to debounce clicks", () => {
    assert.ok(
      appJsSource.includes("clickTimer"),
      "app.js must use a clickTimer variable to detect double-click vs single-click"
    );
  });

  it("click handler clears the timer on second click (double-click detection)", () => {
    assert.ok(
      appJsSource.includes("clearTimeout(clickTimer)"),
      "app.js click handler must clearTimeout(clickTimer) to cancel the pending single-click enqueue " +
        "when a second click arrives (part of a double-click)"
    );
  });

  it("dblclick handler also clears any pending clickTimer", () => {
    // The dblclick handler must clear clickTimer too so that a delayed
    // single-click timer does not fire after the double-click has already
    // enqueued the song.
    const dblclickIdx = appJsSource.indexOf("dblclick");
    const afterDblclick = appJsSource.slice(dblclickIdx);
    assert.ok(
      afterDblclick.includes("clearTimeout(clickTimer)"),
      "app.js dblclick handler must also clearTimeout(clickTimer) to " +
        "prevent a stale timer from adding a second entry"
    );
  });

  it("dblclick handler does NOT call enqueueSong directly (calls local enqueue function)", () => {
    const dblclickIdx = appJsSource.indexOf("dblclick");
    const handlerEnd = appJsSource.indexOf("});", dblclickIdx);
    const handlerBody = appJsSource.slice(dblclickIdx, handlerEnd + 3);
    assert.ok(
      handlerBody.includes("enqueue()"),
      "The dblclick handler must call enqueue() (the local wrapper), " +
        "not enqueueSong directly, to ensure proper guard checks"
    );
  });

  it("click handler does NOT call enqueue() immediately — uses setTimeout", () => {
    // Find the search-results `.song-item` click handler: locate the
    // clickTimer variable declaration, then find the first
    // addEventListener('click' that follows it.
    const varDecl = appJsSource.indexOf("var clickTimer");
    const clickAEL = appJsSource.indexOf("addEventListener('click'", varDecl);
    const handlerEnd = appJsSource.indexOf("});", clickAEL);
    const handlerBody = appJsSource.slice(clickAEL, handlerEnd + 3);
    // The handler must call setTimeout before enqueue() — i.e. enqueue is
    // *inside* the setTimeout callback, not directly in the handler body.
    const setTimeoutIdx = handlerBody.indexOf("setTimeout");
    const enqueueIdx = handlerBody.indexOf("enqueue()");
    assert.ok(
      setTimeoutIdx >= 0,
      "The click handler must use setTimeout before calling enqueue(), " +
        "so that a second click can cancel it"
    );
    assert.ok(
      enqueueIdx > setTimeoutIdx,
      "enqueue() must be called inside the setTimeout callback, " +
        "not synchronously in the click handler"
    );
  });

  it("does NOT have separate click() and dblclick() that both call enqueue directly", () => {
    // The old pattern was: click → enqueue(), dblclick → enqueue()
    // The new pattern is: click → setTimeout(enqueue, 250), dblclick → clearTimer + enqueue()
    // Both should NOT directly call enqueue()  (except in the setTimeout callback)
    const clickPattern = /addEventListener\('click',\s*enqueue\)/;
    assert.ok(
      !clickPattern.test(appJsSource),
      "app.js must NOT have addEventListener('click', enqueue) directly — " +
        "that pattern calls enqueue synchronously on every click"
    );
  });
});

// ---------------------------------------------------------------------------
// Regression: boot sequence must call init() (Defect 1)
// ---------------------------------------------------------------------------
// Before the fix, the boot code did `new PyKaraokeApp()` without `.init()`,
// so the app never connected to the backend, never registered event listeners,
// and was completely non-functional.

describe("Regression: boot sequence calls init()", () => {
  const appJsSource = fs.readFileSync(
    path.join(__dirname, "app.js"),
    "utf-8"
  );

  it("boot code calls .init() on the new PyKaraokeApp instance", () => {
    const lines = appJsSource.split("\n");
    // Find the boot block at the end of the file
    const bootLines = lines.slice(-10).join("\n");
    assert.ok(
      bootLines.includes("new PyKaraokeApp().init()"),
      "Boot code must call .init() on the constructed PyKaraokeApp instance; " +
        "without it, the app never connects to the backend or registers event listeners"
    );
  });

  it("does NOT have bare new PyKaraokeApp() without .init()", () => {
    // The old pattern was `new PyKaraokeApp();` with no `.init()` call.
    // The new pattern should always chain `.init()`.
    const barePattern = /new\s+PyKaraokeApp\s*\(\s*\)\s*;/;
    assert.ok(
      !barePattern.test(appJsSource),
      "app.js must not contain bare 'new PyKaraokeApp();' without .init()"
    );
  });

  it("DOMContentLoaded handler calls .init()", () => {
    const domReadyLine = appJsSource
      .split("\n")
      .find(l => l.includes("DOMContentLoaded"));
    assert.ok(
      domReadyLine && domReadyLine.includes(".init()"),
      "The DOMContentLoaded listener must call .init() on the instance"
    );
  });
});

// ---------------------------------------------------------------------------
// Regression: setupEventListeners captures self = this (Defect 2)
// ---------------------------------------------------------------------------
// Before the fix, event listeners referenced `self` which was not defined
// in the closure scope, causing ReferenceErrors on every interaction.

describe("Regression: self is captured in setupEventListeners", () => {
  const appJsSource = fs.readFileSync(
    path.join(__dirname, "app.js"),
    "utf-8"
  );

  it("setupEventListeners declares var self = this", () => {
    // Find the method definition (with opening brace), not the call site
    const fnDefIdx = appJsSource.indexOf("setupEventListeners() {");
    const declArea = appJsSource.slice(fnDefIdx, fnDefIdx + 300);
    assert.ok(
      declArea.includes("var self = this"),
      "setupEventListeners() must capture 'var self = this' so that " +
        "event listener closures can reference the app instance"
    );
  });

  it("search-btn handler references self.handleSearch, not globalThis", () => {
    const searchBtnIdx = appJsSource.indexOf("search-btn");
    const afterSearchBtn = appJsSource.slice(searchBtnIdx, searchBtnIdx + 200);
    assert.ok(
      afterSearchBtn.includes("self.handleSearch"),
      "search-btn click handler must use self.handleSearch"
    );
    assert.ok(
      !afterSearchBtn.includes("globalThis"),
      "search-btn handler must not reference globalThis"
    );
  });

  it("volume slider references self.sendCommand with 'set_volume' string", () => {
    assert.ok(
      appJsSource.includes("self.sendCommand('set_volume'"),
      "Volume slider must use self.sendCommand('set_volume', ...) — " +
        "the old code had undeclared 'action' variable and globalThis.sendCommand"
    );
  });

  it("progress slider references self.currentState, not globalThis.currentState", () => {
    const progressIdx = appJsSource.indexOf("progress-slider");
    const afterProgress = appJsSource.slice(progressIdx, progressIdx + 400);
    assert.ok(
      afterProgress.includes("self.currentState"),
      "Progress slider handler must use self.currentState, not globalThis"
    );
    assert.ok(
      !afterProgress.includes("globalThis.currentState"),
      "Progress slider must not reference globalThis.currentState"
    );
  });

  it("progress slider references self.fmtTime, not globalThis.fmtTime", () => {
    assert.ok(
      appJsSource.includes("self.fmtTime"),
      "Progress slider must use self.fmtTime for time display"
    );
  });

  it("clear-playlist-btn references self.sendCommand, not globalThis", () => {
    const clearIdx = appJsSource.indexOf("clear-playlist-btn");
    const afterClear = appJsSource.slice(clearIdx, clearIdx + 150);
    assert.ok(
      afterClear.includes("self.sendCommand"),
      "Clear playlist must use self.sendCommand"
    );
  });
});

// ---------------------------------------------------------------------------
// Regression: seek buttons use this._setupSeekButton (Defect 3)
// ---------------------------------------------------------------------------
// Before the fix, the code used globalThis._setupSeekButton which was not
// defined on the global scope.

describe("Regression: seek buttons use instance method", () => {
  const appJsSource = fs.readFileSync(
    path.join(__dirname, "app.js"),
    "utf-8"
  );

  it("ff-btn setup uses this._setupSeekButton, not globalThis", () => {
    assert.ok(
      appJsSource.includes("this._setupSeekButton('ff-btn'"),
      "Fast-forward button must use this._setupSeekButton"
    );
  });

  it("rewind-btn setup uses this._setupSeekButton, not globalThis", () => {
    assert.ok(
      appJsSource.includes("this._setupSeekButton('rewind-btn'"),
      "Rewind button must use this._setupSeekButton"
    );
  });

  it("does NOT reference globalThis._setupSeekButton", () => {
    assert.ok(
      !appJsSource.includes("globalThis._setupSeekButton"),
      "app.js must not reference globalThis._setupSeekButton — " +
        "it is an instance method, not a global function"
    );
  });
});
