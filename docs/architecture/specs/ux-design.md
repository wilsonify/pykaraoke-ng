# UX Design Specification — Slim Sidebar DJ Utility Panel

> **Audience:** All contributors (frontend, UX, design)
> **Governance:** [constitution.md](constitution.md) §2
> **Version:** 1.0.0
> **Last updated:** 2026-02-28

---

## 1. Design Philosophy

PyKaraoke-NG exists to serve a working DJ running a live event. Every design
decision flows from this constraint:

> The DJ's primary software must remain visible.
> PyKaraoke-NG occupies the remaining sliver of screen.

The original PyKaraoke delivered exactly this — a narrow, practical window for
searching and queueing karaoke songs while continuing a DJ set. Modern karaoke
applications consume 80–90% of screen real estate, breaking this workflow.

PyKaraoke-NG restores the original posture: a **professional utility panel**,
not a media consumption app.

---

## 2. Target Persona

### The Working DJ

| Attribute            | Detail                                                    |
|----------------------|-----------------------------------------------------------|
| **Role**             | Live-event DJ running karaoke as part of a broader set    |
| **Environment**      | Laptop screen (13–16 in.), often in low-light venues      |
| **Primary software** | DJ tools (Audacious, VirtualDJ, Mixxx) — must stay visible|
| **Time pressure**    | Constant — patrons queue requests between songs           |
| **Interaction style**| Keyboard-dominant, occasional mouse/trackpad              |
| **Tolerance for friction** | Near zero — every extra click costs time           |
| **Screen budget**    | 300–450 px wide strip, full screen height                 |

### Persona Anti-Patterns (NOT our user)

- Casual listener browsing a music library at home.
- Touch-screen kiosk user selecting songs.
- Music enthusiast wanting album art and visualizations.
- First-time user who needs onboarding wizards.

---

## 3. Layout Architecture

### 3.1 Single Vertical Column

All primary UI elements are arranged in a **single vertical column**, flowing
top → bottom. There are no horizontal panel splits in the default layout.

```
┌─────────────────────────┐  ← Fixed top
│  🔍 Search bar          │
├─────────────────────────┤
│  ▼ Filters (collapse)   │
├─────────────────────────┤  ← Scrollable region begins
│  Search results          │
│  ┌─────────────────────┐│
│  │ Song - Artist       ││
│  │ Song - Artist       ││
│  │ Song - Artist       ││
│  │ ...                 ││
│  └─────────────────────┘│
├─────────────────────────┤
│  ▶ Now Playing (compact)│
│    Title — Artist        │
│    ▶ ⏸ ⏭  ───●───  🔊  │
├─────────────────────────┤
│  Queue (3 songs)         │
│  ┌─────────────────────┐│
│  │ 1. Song — Artist  ✕ ││
│  │ 2. Song — Artist  ✕ ││
│  │ 3. Song — Artist  ✕ ││
│  └─────────────────────┘│
├─────────────────────────┤  ← Scrollable region ends
│  Status bar              │  ← Fixed bottom
└─────────────────────────┘
```

### 3.2 Dimensional Constraints

| Property            | Value          | Rationale                              |
|---------------------|----------------|----------------------------------------|
| Default width       | 380 px         | Fits beside DJ software on 1366 px+    |
| Minimum width       | 300 px         | Functional limit — text truncation ok  |
| Maximum width       | 450 px         | Prevents creeping screen dominance     |
| Default height      | 100% viewport  | Uses full vertical space               |
| Minimum height      | 500 px         | Ensures queue + now-playing visible    |
| Horizontal resize   | Allowed (300–450 px range) | User can tune to preference  |
| Full-width toggle   | Opt-in only    | Must be an explicit user action        |

### 3.3 Alignment Rules

- All primary controls are **left-aligned**.
- No center-aligned headings, titles, or controls.
- Right-alignment is permitted only for inline secondary actions
  (e.g., a remove button at the end of a queue row).
- All text is left-aligned.

### 3.4 Fixed vs. Scrollable Regions

| Region          | Behaviour    | Rationale                              |
|-----------------|--------------|----------------------------------------|
| Search bar      | Fixed top    | Always accessible, never scrolls away  |
| Filters         | Collapsible  | Hidden by default; toggled inline       |
| Results + Queue | Scrollable   | Main content area scrolls vertically   |
| Now Playing     | Sticky/fixed | Always visible for transport control   |
| Status bar      | Fixed bottom | Connection status always visible       |

---

## 4. Vertical Flow Order

Elements appear in this exact order, top to bottom. No reordering.

| Order | Element                | Purpose                                      |
|-------|------------------------|----------------------------------------------|
| 1     | **Search bar**         | Text input for incremental song search        |
| 2     | **Search filters**     | Collapsible: filter by format, artist, etc.   |
| 3     | **Search results**     | Scrollable list of matching songs             |
| 4     | **Now Playing**        | Current song info + minimal transport controls|
| 5     | **Queue**              | Ordered list of upcoming songs                |
| 6     | **Playback controls**  | Volume, progress (integrated into Now Playing)|
| 7     | **Status bar**         | Backend status, connection indicator          |

---

## 5. Interaction Design

### 5.1 Keyboard-First UX

Every primary workflow must be keyboard-accessible:

| Key              | Action                                    |
|------------------|-------------------------------------------|
| `/` or `Ctrl+K`  | Focus search bar                          |
| `↑` / `↓`       | Navigate search results or queue          |
| `Enter`          | Add selected result to queue              |
| `Esc`            | Clear search / deselect / close filters   |
| `Space`          | Play / Pause                              |
| `Ctrl+→`        | Skip to next song                         |
| `Delete`         | Remove selected item from queue           |
| `Ctrl+↑/↓`     | Reorder selected item in queue            |
| `Tab`            | Move focus between sections               |

### 5.2 Search Behaviour

- **Incremental filtering:** Results update as the user types. No "Search"
  button.
- **Debounce:** 100–150 ms debounce to avoid excessive re-renders.
- **Minimum query length:** 1 character (single-char artist names exist).
- **Empty state:** Show recent songs or "Type to search" hint.
- **No pagination:** Virtual scrolling for large result sets. The user
  scrolls continuously.

### 5.3 Queue Management

- **Add:** Press Enter on a search result, or click the `+` icon.
- **Remove:** Inline `✕` button per row, or `Delete` key.
- **Reorder:** Drag-and-drop, or `Ctrl+↑/↓` keyboard shortcuts.
- **Auto-advance:** When a song ends, the next queued song starts
  automatically.
- **Empty queue:** Show "Queue empty — search to add songs" hint.

### 5.4 Prohibited Interaction Patterns

These patterns are **banned** because they break the DJ workflow:

| Pattern                       | Why it's banned                              |
|-------------------------------|----------------------------------------------|
| Modal dialogs                 | Block the entire window, require dismissal   |
| Full-screen overlays          | Obscure the queue and now-playing state       |
| Confirmation dialogs for      | Slows down rapid queue management            |
| queue add/remove              |                                               |
| Multi-step wizards            | Too slow for live performance                 |
| Mandatory settings screens    | Should never block the primary workflow        |
| Splash screens                | Waste time on every launch                    |
| Auto-expanding to full width  | Steals screen from DJ software               |
| Horizontal tab bars           | Waste vertical space, introduce mode switching|

---

## 6. Visual Design

### 6.1 Typography

| Element        | Size   | Weight  | Notes                            |
|----------------|--------|---------|----------------------------------|
| Song title     | 13 px  | 500     | Primary text in lists            |
| Artist name    | 12 px  | 400     | Secondary text, muted color      |
| Section header | 11 px  | 700     | ALL CAPS, letter-spacing +0.5 px |
| Status text    | 11 px  | 400     | Muted, fixed bottom              |
| Search input   | 14 px  | 400     | Slightly larger for visibility   |

### 6.2 Spacing

| Property              | Value   | Notes                              |
|-----------------------|---------|------------------------------------|
| Section gap           | 4 px    | Between major vertical sections    |
| List item height      | 32 px   | Compact but tappable               |
| List item padding     | 4px 8px | Horizontal padding for text        |
| Search bar height     | 36 px   | Fixed input height                 |
| Inner section padding | 8 px    | Padding inside section containers  |

### 6.3 Color Scheme

Dark theme by default (DJs work in low-light environments):

| Role                | Variable               | Value (dark)  |
|---------------------|------------------------|---------------|
| Background          | `--bg-primary`         | `#0f0f11`     |
| Surface             | `--bg-surface`         | `#1a1a2e`     |
| Text primary        | `--text-primary`       | `#e4e4e7`     |
| Text muted          | `--text-muted`         | `#71717a`     |
| Accent              | `--color-accent`       | `#6366f1`     |
| Now playing highlight| `--color-now-playing` | `#22c55e`     |
| Danger (remove)     | `--color-danger`       | `#ef4444`     |
| Border              | `--border-subtle`      | `#27272a`     |

### 6.4 Visual Anti-Patterns

| ❌ Avoid                          | ✅ Instead                              |
|-----------------------------------|-----------------------------------------|
| Hero banners or splash images     | Jump straight to search bar             |
| Large album art thumbnails        | Small (24 px) or no thumbnails          |
| Animated transitions > 150 ms     | Instant or near-instant transitions     |
| Drop shadows and elevation layers | Flat design with subtle borders         |
| Rounded corners > 4 px            | Sharp or minimal rounding               |
| Marketing copy or branding areas  | Functional elements only                |

---

## 7. Component Hierarchy

### 7.1 Current State (to be refactored)

The current frontend is a single `index.html` with a two-panel horizontal
flexbox layout (`#main-content` splits into `.left-panel` and `.right-panel`)
and a monolithic `app.js` class. This violates the single-column constraint.

### 7.2 Target Component Hierarchy

```
<App>
  <SlimSidebarLayout>           ← Root layout: vertical flex, max-width 450px
    <SearchBar />               ← Fixed top, always visible
    <SearchFilters />           ← Collapsible, hidden by default
    <SearchResults />           ← Scrollable list, virtual scrolling
    <NowPlaying />              ← Sticky section: song info + transport
    <Queue />                   ← Scrollable list with reorder + remove
    <StatusBar />               ← Fixed bottom: connection status
  </SlimSidebarLayout>
</App>
```

### 7.3 Component Responsibilities

| Component          | Responsibility                                         |
|--------------------|--------------------------------------------------------|
| `SlimSidebarLayout`| Enforces vertical stacking, max-width, fixed regions   |
| `SearchBar`        | Text input, keyboard shortcuts, focus management       |
| `SearchFilters`    | Toggle-able filter chips (format, artist, etc.)        |
| `SearchResults`    | Virtual-scrolling list of search matches               |
| `NowPlaying`       | Current song display + play/pause/skip + progress bar  |
| `Queue`            | Ordered list with drag-reorder and inline remove       |
| `StatusBar`        | Backend status indicator, connection health            |

---

## 8. CSS / Layout Rules

### 8.1 Root Layout

```css
/* SlimSidebarLayout */
#app {
  display: flex;
  flex-direction: column;
  width: 100vw;
  max-width: 450px;
  min-width: 300px;
  height: 100vh;
  overflow: hidden;
  font-family: system-ui, -apple-system, sans-serif;
}
```

### 8.2 Prohibited CSS Patterns

| ❌ Prohibited                              | Why                                     |
|--------------------------------------------|-----------------------------------------|
| `flex-direction: row` on main layout       | Breaks vertical flow                    |
| `width: 100%` without `max-width`          | Allows full-screen expansion            |
| `margin: 0 auto` on containers             | Centers content instead of left-aligning|
| `text-align: center` on primary controls   | Violates left-alignment rule            |
| `position: fixed` without containment      | Can overflow the slim window            |
| `min-width` > 450 px on any element        | Forces the window wider than sidebar    |

### 8.3 Scrolling Strategy

- The **search results** and **queue** sections share a single scrollable
  container (`overflow-y: auto`).
- The **search bar** and **status bar** are outside the scrollable container
  (fixed top/bottom).
- The **now-playing** section uses `position: sticky` to stay visible as
  the user scrolls through results/queue.
- No horizontal scroll anywhere. Text truncation with ellipsis for long
  song titles.

---

## 9. Window Configuration (Tauri)

The Tauri window configuration must enforce the slim sidebar defaults:

```json
{
  "windows": [{
    "fullscreen": false,
    "resizable": true,
    "title": "PyKaraoke NG",
    "width": 380,
    "height": 768,
    "minWidth": 300,
    "minHeight": 500,
    "maxWidth": 450,
    "decorations": true,
    "alwaysOnTop": false
  }]
}
```

Key changes from current config (1024 × 768):
- Default width: 1024 → **380**
- Added `minWidth: 300`, `maxWidth: 450`
- Added `minHeight: 500`

---

## 10. Responsive Behaviour

### 10.1 Within the Sidebar Range (300–450 px)

- All elements stack vertically.
- Song titles truncate with ellipsis.
- Artist names appear on a second line if needed, or truncate.
- Transport controls use icon-only buttons (no text labels).
- Queue items show: number, title (truncated), remove button.

### 10.2 Wide Mode (opt-in only, > 450 px)

If the user explicitly removes the max-width constraint (via a toggle or
window resize override):

- Search results may show additional columns (duration, format).
- Song details may expand inline.
- This mode is **not the default** and must never activate automatically.

### 10.3 Narrow Mode (< 300 px)

- Not officially supported.
- Elements may clip or wrap. This is acceptable — the user has chosen an
  unusably narrow width.

---

## 11. Performance Budgets

| Metric                          | Budget   |
|---------------------------------|----------|
| Time from launch to usable UI   | < 500 ms |
| Time from keypress to results   | < 200 ms |
| Search result render (100 items)| < 50 ms  |
| Queue reorder visual feedback   | < 16 ms  |
| Memory footprint (idle)         | < 50 MB  |

---

## 12. Migration Path from Current UI

### Phase 1: Layout Restructure
1. Replace the two-panel horizontal flexbox with single vertical column.
2. Move now-playing and queue below search results.
3. Enforce `max-width: 450px` on the root container.
4. Update Tauri window defaults.

### Phase 2: Compact Controls
1. Reduce padding, margins, and font sizes per §6.
2. Replace full-width transport controls with icon-only compact bar.
3. Remove or collapse the settings modal into an inline section.

### Phase 3: Keyboard Navigation
1. Implement focus management across sections.
2. Add keyboard shortcut handlers per §5.1.
3. Add search debounce and incremental filtering.

### Phase 4: Polish
1. Virtual scrolling for large song libraries.
2. Drag-to-reorder for queue.
3. Status bar and connection health indicator.

---

## 13. DJ Workflow Optimizations

### 13.1 Quick Queue

A DJ handling rapid requests needs to:
1. Hear a request → type the first few letters.
2. See matching songs instantly.
3. Press Enter to queue.
4. Move on in < 3 seconds total.

The UI must support this **3-second add** workflow without any confirmation
dialogs, page transitions, or mode changes.

### 13.2 Glanceable State

At any moment, the DJ must be able to glance at the sidebar and immediately
know:
- What song is currently playing (and how far along it is).
- How many songs are in the queue.
- What the next song is.

This information must be visible **without scrolling** when the queue has
≤ 5 items.

### 13.3 Emergency Skip

During a live event, sometimes a song must be stopped immediately (wrong
track, technical issue, audience reaction). The skip/stop action must be:
- One click or one keypress.
- Visible without scrolling.
- Not gated behind a confirmation dialog.

---

## 14. Accessibility Notes

- All interactive elements must be keyboard-reachable via Tab.
- Focus indicators must be visible (2 px solid accent color).
- Contrast ratios must meet WCAG AA (4.5:1 for text, 3:1 for UI).
- Screen reader labels for icon-only buttons (e.g., `aria-label="Skip"`).
- The dark theme is the default, but a light theme toggle is acceptable
  for accessibility.

---

## 15. Cross-References

- **Constitution §2:** Target Audience and Design Posture
- **Constitution §2.3:** UX Invariants (binding constraints)
- **Build-system invariants:** Window config changes must pass CI
- **Feature spec:** `specs/features/NNN-slim-sidebar-layout/`
