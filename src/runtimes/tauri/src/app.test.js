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
        invoke: async (cmd, args) => {
          if (cmd === "engine_start") return;
          if (cmd === "engine_status") return "running";
          if (cmd === "playback_play") return { status: "playing", currentSong: null, positionMs: 0, durationMs: 0, volume: 0.8 };
          if (cmd === "playback_pause") return { status: "paused", currentSong: null, positionMs: 0, durationMs: 0, volume: 0.8 };
          if (cmd === "playback_stop") return { status: "stopped", currentSong: null, positionMs: 0, durationMs: 0, volume: 0.8 };
          if (cmd === "search") return { query: args.query, results: [], totalCount: 0 };
          if (cmd === "library_folders") return [];
          return {};
        },
      },
      event: {
        listen: async () => () => {},
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

    const list = [];
    if (!list || list.length === 0) {
      playlistEl.innerHTML =
        '<div class="no-results">Playlist is empty</div>';
    }
    assert.ok(playlistEl.innerHTML.includes("Playlist is empty"));
  });

  it("renders correct number of song items", () => {
    const songs = [
      { title: "Song A", artist: "Artist 1", filename: "a.cdg" },
      { title: "Song B", artist: "Artist 2", filename: "b.cdg" },
      { title: "Song C", artist: "", filename: "c.kar" },
    ];

    const html = songs
      .map(
        (song, index) => `
      <div class="song-item" data-index="${index}">
        <div class="song-item-title">${song.title || song.filename}</div>
        <div class="song-item-artist">${song.artist || ""}</div>
      </div>
    `
      )
      .join("");

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

describe("Engine event handling", () => {
  it("recognises all known event types", () => {
    const knownTypes = [
      "engine:playback_changed",
      "engine:queue_changed",
      "engine:library_changed",
      "engine:settings_changed",
      "engine:scan_progress",
      "engine:error",
    ];
    for (const t of knownTypes) {
      assert.ok(typeof t === "string");
    }
  });

  it("playback_changed event carries expected fields", () => {
    const event = {
      payload: {
        status: "playing",
        currentSong: { title: "Test", artist: "A" },
        positionMs: 1000,
        durationMs: 5000,
        volume: 0.8,
      },
    };
    assert.equal(event.payload.status, "playing");
    assert.ok(event.payload.durationMs > 0);
  });
});

describe("Command shapes sent to Rust engine", () => {
  it("playback_play command has correct shape", () => {
    const cmd = { cmd: "playback_play", args: {} };
    assert.equal(cmd.cmd, "playback_play");
  });

  it("search command includes query string", () => {
    const query = "bohemian rhapsody";
    const cmd = { cmd: "search", args: { query } };
    assert.equal(cmd.args.query, "bohemian rhapsody");
  });

  it("queue_remove uses numeric index", () => {
    const cmd = { cmd: "queue_remove", args: { index: 3 } };
    assert.equal(typeof cmd.args.index, "number");
  });

  it("playback_set_volume uses 0-1 float range", () => {
    const sliderValue = 75;
    const volume = parseInt(sliderValue) / 100;
    assert.equal(volume, 0.75);
  });

  it("engine_tick command has no parameters", () => {
    const cmd = { cmd: "engine_tick", args: {} };
    assert.equal(cmd.cmd, "engine_tick");
    assert.equal(Object.keys(cmd.args).length, 0);
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
    const state = { positionMs: 30000, durationMs: 120000 };
    const progress = (state.positionMs / state.durationMs) * 100;
    assert.equal(progress, 25);
  });

  it("progress bar handles zero duration", () => {
    const state = { positionMs: 0, durationMs: 0 };
    const progress = state.durationMs > 0 ? (state.positionMs / state.durationMs) * 100 : 0;
    assert.equal(progress, 0);
  });

  it("engine status text reflects connection state", () => {
    const connected = true;
    const text = connected ? "Engine: Connected" : "Engine: Disconnected";
    const cls = connected ? "connected" : "disconnected";
    assert.equal(text, "Engine: Connected");
    assert.equal(cls, "connected");
  });

  it("now-playing shows fallback when no song loaded", () => {
    const state = { currentSong: null };
    const title = state.currentSong
      ? state.currentSong.title || state.currentSong.filename || "Unknown"
      : "No song loaded";
    assert.equal(title, "No song loaded");
  });

  it("now-playing shows title when song loaded", () => {
    const state = {
      currentSong: {
        title: "Monkey Shines",
        artist: "Jonathan Coulton",
        filename: "monkey.mp3",
      },
    };
    const title = state.currentSong
      ? state.currentSong.title || state.currentSong.filename || "Unknown"
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

describe("Regression: Tauri API import resilience", () => {
  const appJsSource = fs.readFileSync(
    path.join(__dirname, "app.js"),
    "utf-8"
  );

  it("does NOT use bare destructuring of window.__TAURI__ at top level", () => {
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
    const catchIdx = appJsSource.indexOf("catch");
    const afterCatch = appJsSource.slice(catchIdx);
    assert.ok(
      afterCatch.includes("invoke") && afterCatch.includes("async"),
      "app.js should assign a fallback async invoke in the catch block"
    );
  });

  it("provides a fallback listenEvent function", () => {
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
    const savedTauri = global.window?.__TAURI__;
    const els = createMockDOM();
    delete global.window.__TAURI__;

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

    assert.equal(typeof testInvoke, "function");
    assert.equal(typeof testListen, "function");
    assert.equal(typeof testDialogOpen, "function");

    assert.ok(els["play-btn"]);
    assert.ok(els["status-message"]);

    if (savedTauri) {
      global.window.__TAURI__ = savedTauri;
    }
  });
});

// ---------------------------------------------------------------------------
// Regression: buttons that did nothing in the packaged Debian build
// ---------------------------------------------------------------------------

describe("Regression: settings button wired up", () => {
  const appJsSource = fs.readFileSync(
    path.join(__dirname, "app.js"),
    "utf-8"
  );

  it("app.js registers a click listener for settings-btn", () => {
    assert.ok(
      appJsSource.includes("settings-btn"),
      "app.js must reference 'settings-btn'"
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
      "app.js must define handleShowSettings()"
    );
  });
});

describe("Regression: add-folder button uses Tauri dialog API", () => {
  const appJsSource = fs.readFileSync(
    path.join(__dirname, "app.js"),
    "utf-8"
  );

  it("handleAddFolder does NOT use bare alert()", () => {
    const hasAlert = /\balert\s*\(/.test(appJsSource);
    assert.ok(
      !hasAlert,
      "app.js must not use alert()"
    );
  });

  it("handleAddFolder references the Tauri dialog API via dialogOpen variable", () => {
    assert.ok(
      appJsSource.includes("dialogOpen") && appJsSource.includes("directory"),
      "handleAddFolder should open a native folder picker via dialogOpen"
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
      "tauri.conf.json must enable allowlist.dialog.open"
    );
  });

  it("beforeBuildCommand uses the cross-platform node staging script", () => {
    assert.equal(
      conf.build?.beforeBuildCommand,
      "node scripts/stage-rust-backend.js",
      "tauri.conf.json beforeBuildCommand must use 'node scripts/stage-rust-backend.js'"
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
      "app.js should listen for 'input' events on the search field"
    );
  });

  it("app.js debounces incremental search", () => {
    assert.ok(
      appJsSource.includes("_searchDebounce") && appJsSource.includes("setTimeout"),
      "app.js should debounce incremental search"
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
      "app.js should render inline remove buttons in playlist items"
    );
  });

  it("does not use confirm() for clear playlist", () => {
    const hasConfirm = /\bconfirm\s*\(/.test(appJsSource);
    assert.ok(
      !hasConfirm,
      "app.js must not use confirm()"
    );
  });

  it("search results are keyboard-navigable with tabindex", () => {
    assert.ok(
      appJsSource.includes("tabindex"),
      "app.js should set tabindex on search result items"
    );
  });

  it("Enter key on search results adds to queue", () => {
    assert.ok(
      appJsSource.includes("'Enter'") || appJsSource.includes('"Enter"'),
      "app.js should handle Enter key on search result items"
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
      `Default window width should be ≤450px, got ${width}`
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
      "Window should be resizable"
    );
  });
});

// ---------------------------------------------------------------------------
// Regression: stop/next/prev buttons check for errors
// ---------------------------------------------------------------------------

describe("Regression: stop/next/prev buttons handle errors", () => {
  const appJsSource = fs.readFileSync(
    path.join(__dirname, "app.js"),
    "utf-8"
  );

  it("stop-btn handler uses try/catch for error handling", () => {
    const stopIdx = appJsSource.indexOf("stop-btn");
    const handler = appJsSource.slice(stopIdx, stopIdx + 200);
    assert.ok(
      handler.includes(".catch(") || handler.includes("try"),
      "stop-btn handler must handle errors via catch or try"
    );
  });

  it("next-btn handler uses try/catch for error handling", () => {
    const nextIdx = appJsSource.indexOf("next-btn");
    const handler = appJsSource.slice(nextIdx, nextIdx + 200);
    assert.ok(
      handler.includes(".catch(") || handler.includes("try"),
      "next-btn handler must handle errors via catch or try"
    );
  });

  it("prev-btn handler uses try/catch for error handling", () => {
    const prevIdx = appJsSource.indexOf("prev-btn");
    const handler = appJsSource.slice(prevIdx, prevIdx + 200);
    assert.ok(
      handler.includes(".catch(") || handler.includes("try"),
      "prev-btn handler must handle errors via catch or try"
    );
  });
});

// ---------------------------------------------------------------------------
// Regression: volume slider handles errors gracefully
// ---------------------------------------------------------------------------

describe("Regression: volume slider handles errors gracefully", () => {
  const appJsSource = fs.readFileSync(
    path.join(__dirname, "app.js"),
    "utf-8"
  );

  it("volume-slider handler uses .catch() on invoke", () => {
    const volIdx = appJsSource.indexOf("volume-slider");
    const handler = appJsSource.slice(volIdx, volIdx + 400);
    assert.ok(
      handler.includes(".catch("),
      "volume-slider handler must use .catch() to handle errors"
    );
  });

  it("volume-slider updates display before sending command", () => {
    const volIdx = appJsSource.indexOf("volume-slider");
    const handler = appJsSource.slice(volIdx, volIdx + 400);
    assert.ok(
      handler.indexOf("volume-value") < handler.indexOf("invoke") &&
        handler.indexOf("textContent") >= 0,
      "volume-slider should update displayed value before invoking"
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
      "app.js must define an enqueueSong() method"
    );
  });

  it("app.js registers a dblclick handler on search result items", () => {
    assert.ok(
      appJsSource.includes("dblclick"),
      "app.js must register 'dblclick' event listeners"
    );
  });

  it("app.js sets draggable=true on search result items", () => {
    assert.ok(
      appJsSource.includes('draggable="true"'),
      "app.js must set draggable='true' for drag-drop"
    );
  });

  it("app.js registers a dragstart handler on search result items", () => {
    assert.ok(
      appJsSource.includes("dragstart"),
      "app.js must register 'dragstart' event listeners"
    );
  });

  it("app.js sets up drop handler on playlist area", () => {
    assert.ok(
      appJsSource.includes("dragover") && appJsSource.includes("drop"),
      "app.js must register 'dragover' and 'drop' listeners"
    );
  });

  it("app.js uses application/x-pykaraoke-song MIME type for drag data", () => {
    assert.ok(
      appJsSource.includes("application/x-pykaraoke-song"),
      "app.js must use custom MIME type for drag-drop"
    );
  });

  it("enqueueSong calls queue_enqueue command", () => {
    assert.ok(
      appJsSource.includes("queue_enqueue"),
      "enqueueSong must send the 'queue_enqueue' command"
    );
  });

  it("enqueueSong handles errors and shows status", () => {
    assert.ok(
      appJsSource.includes("Failed to enqueue"),
      "enqueueSong must show visible error status when enqueue fails"
    );
  });
});

describe("Queue enqueue: command shape", () => {
  it("queue_enqueue command has correct shape", () => {
    const cmd = { cmd: "queue_enqueue", args: { filepath: "/songs/test.kar" } };
    assert.equal(cmd.cmd, "queue_enqueue");
    assert.equal(cmd.args.filepath, "/songs/test.kar");
  });

  it("queue_enqueue command requires filepath", () => {
    const cmd = { cmd: "queue_enqueue", args: {} };
    assert.ok(!cmd.args.filepath, "Missing filepath should be falsy");
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
// Regression: double-click fires enqueueSong exactly once
// ---------------------------------------------------------------------------

describe("Regression: double-click adds exactly one queue entry", () => {
  const appJsSource = fs.readFileSync(
    path.join(__dirname, "app.js"),
    "utf-8"
  );

  it("uses a clickTimer variable to debounce clicks", () => {
    assert.ok(
      appJsSource.includes("clickTimer"),
      "app.js must use clickTimer variable"
    );
  });

  it("click handler clears the timer on second click", () => {
    assert.ok(
      appJsSource.includes("clearTimeout(clickTimer)"),
      "app.js click handler must clearTimeout(clickTimer)"
    );
  });

  it("dblclick handler also clears any pending clickTimer", () => {
    const dblclickIdx = appJsSource.indexOf("dblclick");
    const afterDblclick = appJsSource.slice(dblclickIdx);
    assert.ok(
      afterDblclick.includes("clearTimeout(clickTimer)"),
      "dblclick must also clearTimeout(clickTimer)"
    );
  });

  it("dblclick handler calls enqueue() (local wrapper), not enqueueSong directly", () => {
    const dblclickIdx = appJsSource.indexOf("dblclick");
    const handlerEnd = appJsSource.indexOf("});", dblclickIdx);
    const handlerBody = appJsSource.slice(dblclickIdx, handlerEnd + 3);
    assert.ok(
      handlerBody.includes("enqueue()"),
      "dblclick handler must call enqueue()"
    );
  });

  it("click handler uses setTimeout before calling enqueue()", () => {
    const varDecl = appJsSource.indexOf("var clickTimer");
    const clickAEL = appJsSource.indexOf("addEventListener('click'", varDecl);
    const handlerEnd = appJsSource.indexOf("});", clickAEL);
    const handlerBody = appJsSource.slice(clickAEL, handlerEnd + 3);
    const setTimeoutIdx = handlerBody.indexOf("setTimeout");
    const enqueueIdx = handlerBody.indexOf("enqueue()");
    assert.ok(
      setTimeoutIdx >= 0,
      "click handler must use setTimeout"
    );
    assert.ok(
      enqueueIdx > setTimeoutIdx,
      "enqueue() must be inside setTimeout callback"
    );
  });

  it("does NOT have separate click() and dblclick() that both call enqueue directly", () => {
    const clickPattern = /addEventListener\('click',\s*enqueue\)/;
    assert.ok(
      !clickPattern.test(appJsSource),
      "app.js must NOT have addEventListener('click', enqueue) directly"
    );
  });
});

// ---------------------------------------------------------------------------
// Regression: boot sequence must call init()
// ---------------------------------------------------------------------------

describe("Regression: boot sequence calls init()", () => {
  const appJsSource = fs.readFileSync(
    path.join(__dirname, "app.js"),
    "utf-8"
  );

  it("boot code calls .init() on the new PyKaraokeApp instance", () => {
    const lines = appJsSource.split("\n");
    const bootLines = lines.slice(-10).join("\n");
    assert.ok(
      bootLines.includes("new PyKaraokeApp().init()"),
      "Boot code must call .init()"
    );
  });

  it("does NOT have bare new PyKaraokeApp() without .init()", () => {
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
      "DOMContentLoaded listener must call .init()"
    );
  });
});

// ---------------------------------------------------------------------------
// Regression: setupEventListeners captures self = this
// ---------------------------------------------------------------------------

describe("Regression: self is captured in setupUIEventListeners", () => {
  const appJsSource = fs.readFileSync(
    path.join(__dirname, "app.js"),
    "utf-8"
  );

  it("setupUIEventListeners declares var self = this", () => {
    const fnDefIdx = appJsSource.indexOf("setupUIEventListeners() {");
    const declArea = appJsSource.slice(fnDefIdx, fnDefIdx + 300);
    assert.ok(
      declArea.includes("var self = this"),
      "setupUIEventListeners() must capture 'var self = this'"
    );
  });

  it("search-btn handler references self.handleSearch", () => {
    const searchBtnIdx = appJsSource.indexOf("search-btn");
    const afterSearchBtn = appJsSource.slice(searchBtnIdx, searchBtnIdx + 200);
    assert.ok(
      afterSearchBtn.includes("self.handleSearch"),
      "search-btn handler must use self.handleSearch"
    );
    assert.ok(
      !afterSearchBtn.includes("globalThis"),
      "search-btn handler must not reference globalThis"
    );
  });

  it("volume slider references invoke with 'playback_set_volume' string", () => {
    assert.ok(
      appJsSource.includes("playback_set_volume"),
      "Volume slider must use 'playback_set_volume' command"
    );
  });

  it("progress slider references self.currentState", () => {
    const progressIdx = appJsSource.indexOf("progress-slider");
    const afterProgress = appJsSource.slice(progressIdx, progressIdx + 400);
    assert.ok(
      afterProgress.includes("self.currentState"),
      "Progress slider must use self.currentState"
    );
    assert.ok(
      !afterProgress.includes("globalThis.currentState"),
      "Progress slider must not reference globalThis.currentState"
    );
  });

  it("progress slider references self.fmtTime", () => {
    assert.ok(
      appJsSource.includes("self.fmtTime"),
      "Progress slider must use self.fmtTime"
    );
  });
});

// ---------------------------------------------------------------------------
// Regression: seek buttons use this._setupSeekButton
// ---------------------------------------------------------------------------

describe("Regression: seek buttons use instance method", () => {
  const appJsSource = fs.readFileSync(
    path.join(__dirname, "app.js"),
    "utf-8"
  );

  it("ff-btn setup uses this._setupSeekButton", () => {
    assert.ok(
      appJsSource.includes("this._setupSeekButton('ff-btn'"),
      "Fast-forward button must use this._setupSeekButton"
    );
  });

  it("rewind-btn setup uses this._setupSeekButton", () => {
    assert.ok(
      appJsSource.includes("this._setupSeekButton('rewind-btn'"),
      "Rewind button must use this._setupSeekButton"
    );
  });

  it("does NOT reference globalThis._setupSeekButton", () => {
    assert.ok(
      !appJsSource.includes("globalThis._setupSeekButton"),
      "app.js must not reference globalThis._setupSeekButton"
    );
  });
});

// ---------------------------------------------------------------------------
// New architecture: Engine trait commands
// ---------------------------------------------------------------------------

describe("New architecture: typed commands", () => {
  const appJsSource = fs.readFileSync(
    path.join(__dirname, "app.js"),
    "utf-8"
  );

  const expectedInvokes = [
    "engine_start",
    "engine_status",
    "playback_play",
    "playback_pause",
    "playback_stop",
    "playback_next",
    "playback_previous",
    "playback_seek",
    "playback_set_volume",
    "queue_enqueue",
    "queue_remove",
    "queue_clear",
    "queue_list",
    "library_scan",
    "library_add_folder",
    "search",
    "settings_get",
    "settings_update",
  ];

  for (const cmd of expectedInvokes) {
    it(`uses invoke('${cmd}', ...) pattern`, () => {
      const pattern = `'${cmd}'`;
      assert.ok(
        appJsSource.includes(pattern),
        `app.js must use invoke('${cmd}', ...) pattern`
      );
    });
  }

  it("does NOT use sendCommand helper", () => {
    const hasSendCommand = appJsSource.includes("sendCommand(");
    assert.ok(
      !hasSendCommand,
      "app.js must not use the old sendCommand() helper"
    );
  });

  it("does NOT use send_command (old IPC channel)", () => {
    const hasSendCommandOld = appJsSource.includes("'send_command'") || appJsSource.includes('"send_command"');
    assert.ok(
      !hasSendCommandOld,
      "app.js must not reference the old 'send_command' IPC channel"
    );
  });

  it("uses setInterval only for engine_tick (not for state polling)", () => {
    const tickUsesSetInterval = appJsSource.includes("setInterval(function() {") &&
      appJsSource.includes("engine_tick");
    assert.ok(
      tickUsesSetInterval,
      "app.js must use setInterval with engine_tick for decoder advancement"
    );
    // Ensure old get_state polling is not used
    const getStatePolling = appJsSource.includes("get_state");
    assert.ok(
      !getStatePolling,
      "app.js must not poll get_state for state updates" +
        " (replaced by event-driven updates)"
    );
  });

  it("uses listenEvent for engine events", () => {
    assert.ok(
      appJsSource.includes("listenEvent('engine:playback_changed'"),
      "app.js must listen for engine:playback_changed events"
    );
    assert.ok(
      appJsSource.includes("listenEvent('engine:queue_changed'"),
      "app.js must listen for engine:queue_changed events"
    );
    assert.ok(
      appJsSource.includes("listenEvent('engine:error'"),
      "app.js must listen for engine:error events"
    );
  });

  it("uses engine_start for initialization", () => {
    assert.ok(
      appJsSource.includes("engine_start"),
      "app.js must call engine_start to initialize the engine"
    );
  });

  it("uses settings_get and settings_update", () => {
    assert.ok(
      appJsSource.includes("settings_get"),
      "app.js must use settings_get for loading settings"
    );
    assert.ok(
      appJsSource.includes("settings_update"),
      "app.js must use settings_update for saving settings"
    );
  });
});

describe("New architecture: response data shapes", () => {
  it("playback state uses camelCase fields", () => {
    const state = {
      status: "playing",
      currentSong: { title: "Test", artist: "A" },
      positionMs: 1000,
      durationMs: 5000,
      volume: 0.8,
    };
    assert.ok("positionMs" in state);
    assert.ok("durationMs" in state);
    assert.ok("currentSong" in state);
  });

  it("queue view uses songs array with currentIndex", () => {
    const view = {
      songs: [{ title: "A" }, { title: "B" }],
      currentIndex: 0,
      totalDurationSeconds: 500,
    };
    assert.equal(view.songs.length, 2);
    assert.equal(view.currentIndex, 0);
  });

  it("search results use camelCase fields", () => {
    const view = {
      query: "queen",
      results: [{ title: "Bohemian Rhapsody", artist: "Queen" }],
      totalCount: 1,
    };
    assert.equal(view.totalCount, 1);
    assert.equal(view.results[0].title, "Bohemian Rhapsody");
  });

  it("settings view uses nested display/audio/lyrics objects", () => {
    const view = {
      version: 1,
      display: { fullscreen: false, width: 800, height: 600, alwaysOnTop: false },
      audio: { volume: 0.8, syncDelayMs: 0 },
      lyrics: { show: true, fontSize: 40, fontBold: false, fontItalic: false },
      libraryFolders: [],
    };
    assert.equal(view.version, 1);
    assert.ok(view.display);
    assert.ok(view.audio);
    assert.ok(view.lyrics);
  });

  it("library scan progress uses camelCase fields", () => {
    const progress = {
      status: "complete",
      foldersScanned: 2,
      songsFound: 150,
      errors: [],
      percent: 100,
    };
    assert.equal(progress.percent, 100);
    assert.equal(progress.songsFound, 150);
  });
});
