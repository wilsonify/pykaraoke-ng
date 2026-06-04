"""Tests for UI layout ordering in index.html.

Defect 2: Search box should appear after folder/library management.
Defect 3: Playback progress should appear after queue management.
"""

import os
from html.parser import HTMLParser


class _LayoutParser(HTMLParser):
    """Parse index.html into ordered sections."""

    def __init__(self):
        super().__init__()
        self.sections = []
        self._current_section_id = None
        self._ids_in_section = []
        self._inside_main = False
        self._inside_summary = False
        self._main_depth = 0

    def _section_id(self, attrs):
        for k, v in attrs:
            if k == "id":
                return v
            if k == "class":
                for cls in v.split():
                    if cls.endswith("-section"):
                        return cls
        return None

    def handle_starttag(self, tag, attrs):
        id_ = self._section_id(attrs)
        if tag == "div" and id_:
            if id_ == "main-container" or "main-container" in (dict(attrs).get("class", "") or ""):
                self._inside_main = True
                self._main_depth = 1
            elif self._inside_main and id_:
                if self._current_section_id is not None:
                    self.sections.append((self._current_section_id, self._ids_in_section))
                self._current_section_id = id_
                self._ids_in_section = []
        if self._inside_main and tag == "div":
            self._main_depth += 1
        if tag == "summary":
            self._inside_summary = True

    def handle_endtag(self, tag):
        if self._inside_main and tag == "div":
            self._main_depth -= 1
            if self._main_depth == 0:
                self._inside_main = False
                if self._current_section_id is not None:
                    self.sections.append((self._current_section_id, self._ids_in_section))
                    self._current_section_id = None
                    self._ids_in_section = []

    def handle_data(self, data):
        if self._inside_summary:
            stripped = data.strip()
            if stripped and self._current_section_id:
                self._ids_in_section.append(stripped)
            self._inside_summary = False


def _read_html():
    path = os.path.join(
        os.path.dirname(__file__),
        "..", "..",
        "src", "runtimes", "tauri", "src", "index.html"
    )
    with open(path, encoding="utf-8") as f:
        return f.read()


class _ElementFinder(HTMLParser):
    def __init__(self):
        super().__init__()
        self._tag_stack = []
        self._id_order = []
        self._capture_ids = True

    def handle_starttag(self, tag, attrs):
        self._tag_stack.append(tag)
        attrs_dict = dict(attrs)
        id_ = attrs_dict.get("id")
        if id_ and self._capture_ids:
            self._id_order.append(id_)

    def handle_endtag(self, tag):
        if self._tag_stack and self._tag_stack[-1] == tag:
            self._tag_stack.pop()


class TestDefect2SearchBoxPlacement:
    """Search controls should appear after folder/library management."""

    def find_elements_by_id(self):
        html = _read_html()
        finder = _ElementFinder()
        finder.feed(html)
        return finder._id_order

    def test_add_folder_before_search_controls(self):
        """Add Folder and Scan Library should appear before search input."""
        ids = self.find_elements_by_id()
        add_folder_idx = ids.index("add-folder-btn")
        scan_idx = ids.index("scan-library-btn")
        search_idx = ids.index("search-input")
        assert add_folder_idx < search_idx, (
            "Add Folder button must appear before search input"
        )
        assert scan_idx < search_idx, (
            "Scan Library button must appear before search input"
        )

    def test_add_folder_before_search_button(self):
        ids = self.find_elements_by_id()
        add_idx = ids.index("add-folder-btn")
        search_btn_idx = ids.index("search-btn")
        assert add_idx < search_btn_idx, (
            "Add Folder button must appear before search button"
        )

    def test_folder_input_before_search_input(self):
        ids = self.find_elements_by_id()
        folder_input_idx = ids.index("folder-input")
        search_input_idx = ids.index("search-input")
        assert folder_input_idx < search_input_idx, (
            "Folder input must appear before search input"
        )

    def test_scan_library_before_search_input(self):
        ids = self.find_elements_by_id()
        scan_idx = ids.index("scan-library-btn")
        search_input_idx = ids.index("search-input")
        assert scan_idx < search_input_idx, (
            "Scan Library must appear before search input"
        )


class TestDefect3PlaybackProgressPlacement:
    """Playback progress should appear after queue management."""

    def find_elements_by_id(self):
        html = _read_html()
        finder = _ElementFinder()
        finder.feed(html)
        return finder._id_order

    def test_queue_before_progress_bar(self):
        """Queue section must appear before the progress bar."""
        ids = self.find_elements_by_id()
        playlist_idx = ids.index("playlist")
        progress_idx = ids.index("progress-slider")
        assert playlist_idx < progress_idx, (
            "Playlist/Queue must appear before progress bar"
        )

    def test_queue_before_time_display(self):
        ids = self.find_elements_by_id()
        playlist_idx = ids.index("playlist")
        time_current_idx = ids.index("time-current")
        assert playlist_idx < time_current_idx, (
            "Playlist must appear before time display"
        )

    def test_clear_playlist_before_progress(self):
        ids = self.find_elements_by_id()
        clear_idx = ids.index("clear-playlist-btn")
        progress_idx = ids.index("progress-slider")
        assert clear_idx < progress_idx, (
            "Clear playlist button must appear before progress bar"
        )

    def test_search_results_before_queue(self):
        ids = self.find_elements_by_id()
        results_idx = ids.index("results-list")
        playlist_idx = ids.index("playlist")
        assert results_idx < playlist_idx, (
            "Search results must appear before queue"
        )

    def test_full_expected_ordering(self):
        """Verify the complete expected order of major sections."""
        ids = self.find_elements_by_id()
        expected_ids = [
            "folder-input", "add-folder-btn",
            "scan-library-btn",
            "search-input", "search-btn",
            "results-list",
            "clear-playlist-btn", "playlist",
            "progress-slider", "time-current", "time-total",
        ]
        positions = []
        for eid in expected_ids:
            if eid in ids:
                positions.append(ids.index(eid))
        for i in range(1, len(positions)):
            assert positions[i] > positions[i - 1], (
                f"Element {expected_ids[i]} appears before {expected_ids[i - 1]}, "
                f"but expected reverse order"
            )


class TestResponsiveLayout:
    """Verify the layout uses flexbox correctly for responsive design."""

    def _read_css(self):
        path = os.path.join(
            os.path.dirname(__file__),
            "..", "..",
            "src", "runtimes", "tauri", "src", "styles.css"
        )
        with open(path, encoding="utf-8") as f:
            return f.read()

    def test_main_container_uses_flex_column(self):
        """#app should use flex column layout for vertical stacking."""
        css = self._read_css()
        assert "#app" in css
        assert "flex-direction: column" in css or "flex-direction:column" in css.replace(" ", ""), (
            "#app must use flex-direction: column"
        )

    def test_main_container_full_height(self):
        """#app should fill the viewport height."""
        css = self._read_css()
        app_section = css[css.index("#app"):]
        assert "height: 100vh" in app_section or '"100vh"' in css, (
            "#app should use height: 100vh"
        )

    def test_status_bar_at_bottom(self):
        """.status-bar should be pinned to bottom."""
        css = self._read_css()
        assert ".status-bar" in css
        assert "flex-shrink: 0" in css[css.index(".status-bar"):].split("}")[0], (
            "Status bar should use flex-shrink: 0 to stay at bottom"
        )

    def test_main_container_scrollable(self):
        """.main-container should scroll when content overflows."""
        css = self._read_css()
        main_idx = css.index(".main-container")
        main_section = css[main_idx:css.index("}", main_idx) + 1]
        assert "overflow-y" in main_section, (
            "main-container should have overflow-y property"
        )

    def test_sidebar_max_width(self):
        """Body should have a max-width to prevent wide layout."""
        css = self._read_css()
        body_block = css[css.index("body {"):css.index("}", css.index("body {")) + 1]
        assert "max-width" in body_block, (
            "Body should have a max-width constraint"
        )


class TestTabOrderAndAccessibility:
    """Keyboard navigation and tab order for the main UI."""

    def find_elements_by_id(self):
        html = _read_html()
        finder = _ElementFinder()
        finder.feed(html)
        return finder._id_order

    def test_tab_order_starts_with_folder_input(self):
        """First focusable element should be the folder input."""
        ids = self.find_elements_by_id()
        first_focusable = None
        focusable_ids = [
            "folder-input", "add-folder-btn",
            "scan-library-btn",
            "search-input", "search-btn",
            "clear-playlist-btn",
            "prev-btn", "play-btn", "pause-btn",
            "stop-btn", "next-btn",
            "volume-slider",
        ]
        for fid in focusable_ids:
            if fid in ids:
                first_focusable = fid
                break
        assert first_focusable == "folder-input", (
            f"First focusable element should be folder-input, got {first_focusable}"
        )

    def test_tab_order_search_before_results(self):
        """Search input should come before results list in tab order."""
        ids = self.find_elements_by_id()
        search_idx = ids.index("search-input")
        results_idx = ids.index("results-list")
        assert search_idx < results_idx, (
            "Search input must appear before results list for logical tab flow"
        )

    def test_tab_order_results_before_queue(self):
        """Results list should come before queue for logical workflow."""
        ids = self.find_elements_by_id()
        results_idx = ids.index("results-list")
        playlist_idx = ids.index("playlist")
        assert results_idx < playlist_idx, (
            "Results must appear before queue for logical tab flow"
        )

    def test_tab_order_queue_before_playback(self):
        """Queue should come before playback controls for logical workflow."""
        ids = self.find_elements_by_id()
        playlist_idx = ids.index("playlist")
        play_idx = ids.index("play-btn")
        assert playlist_idx < play_idx, (
            "Queue must appear before playback controls for logical tab flow"
        )
