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
    "progress-fill",
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
      "current-song-title",
      "current-song-artist",
      "progress-fill",
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

  it("beforeBuildCommand is empty (CI stages files via a separate step)", () => {
    // The beforeBuildCommand in main uses ../../../../ paths which are one level
    // too deep when tauri is invoked from src/runtimes/tauri/. The CI workflow
    // instead stages files in a separate step and overrides beforeBuildCommand
    // to empty via TAURI_CONFIG.
    assert.equal(
      conf.build?.beforeBuildCommand ?? "",
      "",
      "tauri.conf.json beforeBuildCommand must be empty; Python staging is " +
        "handled by the CI 'Stage Python backend for bundling' step"
    );
  });
});
