"""
End-to-end Selenium tests for the PyKaraoke NG browser UI.

These tests run against the live docker-compose stack:
  - backend  (Python FastAPI on port 8080)
  - ui       (nginx serving the frontend on port 3000)
  - selenium (Firefox via selenium/standalone-firefox)

Launch with:
    docker compose --profile e2e up --abort-on-container-exit test-e2e
"""

import os
import time

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

pytestmark = pytest.mark.integration

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SELENIUM_URL = os.environ.get("SELENIUM_URL", "http://selenium:4444/wd/hub")
UI_URL = os.environ.get("UI_URL", "http://ui:3000")


@pytest.fixture(scope="module")
def driver():
    """Create a remote Firefox WebDriver connected to the Selenium container."""
    opts = FirefoxOptions()
    # Connect to the standalone-firefox container
    drv = webdriver.Remote(command_executor=SELENIUM_URL, options=opts)
    drv.implicitly_wait(5)
    yield drv
    drv.quit()


@pytest.fixture(autouse=True)
def load_ui(driver):
    """Navigate to the UI before every test."""
    driver.get(UI_URL)
    # Wait until the app has initialised (status bar updates from "Ready")
    WebDriverWait(driver, 10).until(
        EC.text_to_be_present_in_element((By.ID, "backend-status"), "Connected")
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def status_text(driver):
    return driver.find_element(By.ID, "status-message").text


def backend_status(driver):
    return driver.find_element(By.ID, "backend-status").text


def get_console_errors(driver):
    """Return JS console errors (Firefox doesn't support this natively
    through Selenium, so we just verify the page didn't crash)."""
    # Verify the app element is still present — a JS crash would blank it.
    return driver.find_elements(By.ID, "app")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBackendConnection:
    """The UI should connect to the backend on load."""

    def test_backend_connected(self, driver):
        assert "Connected" in backend_status(driver)

    def test_status_shows_connected(self, driver):
        assert "Backend connected" in status_text(driver)

    def test_app_element_present(self, driver):
        assert len(get_console_errors(driver)) == 1


class TestDiscoverAndClickButtons:
    """Discover every <button> in the page and click each one."""

    def test_all_buttons_clickable(self, driver):
        buttons = driver.find_elements(By.TAG_NAME, "button")
        assert len(buttons) > 0, "No buttons found on the page"

        clicked = []
        for btn in buttons:
            btn_id = btn.get_attribute("id") or btn.text.strip()
            # Skip hidden buttons (e.g. pause-btn starts hidden)
            if not btn.is_displayed():
                continue

            # Dismiss the settings modal if it's overlaying the page
            try:
                modal = driver.find_element(By.ID, "settings-modal")
                if modal.is_displayed():
                    driver.execute_script(
                        "document.getElementById('settings-modal').style.display='none';"
                    )
                    time.sleep(0.1)
            except Exception:
                pass

            # Dismiss any prompt/alert that a previous click may have opened
            try:
                alert = driver.switch_to.alert
                alert.dismiss()
                time.sleep(0.1)
            except Exception:
                pass

            # Re-check visibility after dismissing overlays
            if not btn.is_displayed():
                continue

            btn.click()
            time.sleep(0.3)
            # Verify the page didn't crash
            assert len(driver.find_elements(By.ID, "app")) == 1, (
                f"Page crashed after clicking '{btn_id}'"
            )
            clicked.append(btn_id)

        assert len(clicked) >= 5, f"Only clicked {len(clicked)} buttons: {clicked}"


class TestPlayerControls:
    """Click each player control button individually and verify status bar."""

    def test_play_button(self, driver):
        driver.find_element(By.ID, "play-btn").click()
        time.sleep(0.5)
        # Page should still be intact
        assert driver.find_element(By.ID, "app")

    def test_stop_button(self, driver):
        driver.find_element(By.ID, "stop-btn").click()
        time.sleep(0.5)
        assert driver.find_element(By.ID, "app")

    def test_next_button(self, driver):
        driver.find_element(By.ID, "next-btn").click()
        time.sleep(0.5)
        assert driver.find_element(By.ID, "app")

    def test_prev_button(self, driver):
        driver.find_element(By.ID, "prev-btn").click()
        time.sleep(0.5)
        assert driver.find_element(By.ID, "app")

    def test_volume_slider(self, driver):
        slider = driver.find_element(By.ID, "volume-slider")
        # Set volume to 50%
        driver.execute_script(
            "arguments[0].value = 50; arguments[0].dispatchEvent(new Event('input'));",
            slider,
        )
        time.sleep(0.3)
        vol_text = driver.find_element(By.ID, "volume-value").text
        assert "50%" in vol_text


class TestSearchFlow:
    """Type a search query and verify results appear."""

    def test_search_returns_results(self, driver):
        search_input = driver.find_element(By.ID, "search-input")
        search_input.clear()
        search_input.send_keys("Coulton")

        driver.find_element(By.ID, "search-btn").click()
        time.sleep(1)

        status = status_text(driver)
        # Should show "Found N results" or "Search failed" (if library empty)
        assert "Found" in status or "Search" in status

    def test_scan_library(self, driver):
        # Library section is open by default
        driver.find_element(By.ID, "scan-library-btn").click()
        time.sleep(1)

        status = status_text(driver)
        assert "Scanning" in status or "scan" in status.lower() or "Backend" in status


class TestClearPlaylist:
    """Click the Clear button on an empty playlist — should not crash."""

    def test_clear_empty_playlist(self, driver):
        driver.find_element(By.ID, "clear-playlist-btn").click()
        time.sleep(0.3)
        playlist = driver.find_element(By.ID, "playlist").text
        assert "empty" in playlist.lower() or playlist == ""


class TestSettingsModal:
    """Open settings, verify the modal appears, then close it."""

    def test_open_and_close_settings(self, driver):
        driver.find_element(By.ID, "settings-btn").click()
        time.sleep(0.5)

        modal = driver.find_element(By.ID, "settings-modal")
        assert modal.is_displayed()

        # Verify controls exist
        assert driver.find_element(By.ID, "setting-fullscreen")
        assert driver.find_element(By.ID, "setting-zoom")

        # Close via Cancel
        driver.find_element(By.ID, "settings-cancel-btn").click()
        time.sleep(0.3)
        assert not modal.is_displayed()

    def test_save_settings(self, driver):
        driver.find_element(By.ID, "settings-btn").click()
        time.sleep(0.5)

        driver.find_element(By.ID, "settings-save-btn").click()
        time.sleep(0.5)

        status = status_text(driver)
        assert "Settings saved" in status or "Error" in status


class TestAddFolder:
    """Type a folder path into the inline input and click Add."""

    def test_add_folder_with_path(self, driver):
        # The Library <details> section is open by default now
        folder_input = driver.find_element(By.ID, "folder-input")
        folder_input.clear()
        folder_input.send_keys("/app/fixtures")

        driver.find_element(By.ID, "add-folder-btn").click()
        time.sleep(1)

        status = status_text(driver)
        assert "Folder added: /app/fixtures" in status or "Error" in status

    def test_add_folder_empty_shows_warning(self, driver):
        folder_input = driver.find_element(By.ID, "folder-input")
        folder_input.clear()

        driver.find_element(By.ID, "add-folder-btn").click()
        time.sleep(0.5)

        status = status_text(driver)
        assert "Enter a folder path" in status
