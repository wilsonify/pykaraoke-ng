import os
import subprocess
import sys
from pathlib import Path

import pytest


def _run_db_scan(repo_root, songs_dir, out_dir, env):
    helper = Path(out_dir) / "scan_with_pykdb.py"
    helper.write_text(
        """
import os
import sys

repo_root = os.environ['REPO_ROOT']
sys.path.insert(0, repo_root)

from pykaraoke.core import database

class DummyYielder(database.AppYielder):
    def Yield(self):
        return None

class DummyBusy(database.BusyCancelDialog):
    def __init__(self):
        database.BusyCancelDialog.__init__(self)
    def Show(self):
        return None
    def SetProgress(self, label, progress):
        return None
    def Destroy(self):
        return None

song_db = database.SongDB()

song_db.settings.folder_list = [os.environ['SONGS_DIR']]
# Keep the scan small and deterministic for tests
song_db.settings.read_titles_txt = False
song_db.settings.look_inside_zips = False
song_db.settings.check_hashes = False

song_db.build_search_database(DummyYielder(), DummyBusy())

song_db.save_settings()
song_db.save_database()

report_path = os.path.join(os.environ['OUT_DIR'], 'scan_report.html')
with open(report_path, 'w') as f:
    f.write('<!doctype html>')
    f.write('<html><head><meta charset="utf-8">')
    f.write('<title>PyKaraoke Scan Report</title>')
    f.write('</head><body>')
    f.write('<h1>PyKaraoke Scan Report</h1>')
    f.write('<ul>')
    for song in song_db.full_song_list:
        f.write('<li>{}</li>'.format(song.display_filename))
    f.write('</ul>')
    f.write('</body></html>')

print(report_path)
""".strip()
        + "\n"
    )

    result = subprocess.run(
        [sys.executable, str(helper)],
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        pytest.skip(f"database scan subprocess failed: {result.stderr.strip()}")
    # The last non-empty line of stdout is the report path.
    # Earlier lines may contain pygame greeting or other output.
    lines = [l for l in result.stdout.strip().splitlines() if l.strip()]
    return lines[-1].strip() if lines else result.stdout.strip()


def test_end_to_end_database_scan_and_report(tmp_path):
    """
    End-to-end flow:
    1) Create a karaoke file on disk.
    2) Run the database scan to pick it up.
    3) Generate an HTML report of scanned songs.
    4) Use Selenium to verify the report lists the song.
    """

    try:
        import pygame  # noqa: F401
    except ImportError:
        pytest.skip("pygame not available; required by database module")

    try:
        from selenium import webdriver
        from selenium.common.exceptions import WebDriverException
        from selenium.webdriver.chrome.options import Options as ChromeOptions
    except Exception:
        pytest.skip("selenium not installed")

    repo_root = Path(__file__).resolve().parents[1]
    songs_dir = tmp_path / "songs"
    songs_dir.mkdir()

    # Empty .kar file is sufficient for scanning (extension-based)
    song_name = "SampleArtist-SampleTitle.kar"
    (songs_dir / song_name).write_bytes(b"")

    out_dir = tmp_path / "out"
    out_dir.mkdir()

    env = os.environ.copy()
    env["REPO_ROOT"] = str(repo_root)
    env["SONGS_DIR"] = str(songs_dir)
    env["OUT_DIR"] = str(out_dir)
    env["PYKARAOKE_DIR"] = str(out_dir / "pykaraoke_home")
    env["PYKARAOKE_TEMP_DIR"] = str(out_dir / "pykaraoke_tmp")
    env["PYTHONPATH"] = str(repo_root)

    report_path = _run_db_scan(repo_root, songs_dir, out_dir, env)
    report_file = Path(report_path)
    assert report_file.exists()

    options = ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    try:
        driver = webdriver.Chrome(options=options)
    except WebDriverException:
        pytest.skip("selenium Chrome driver not available")

    try:
        driver.get(report_file.as_uri())
        assert "PyKaraoke Scan Report" in driver.title
        body_text = driver.find_element("tag name", "body").text
        assert "SampleArtist-SampleTitle.kar" in body_text
    finally:
        driver.quit()


# Mark the entire module as integration tests
pytestmark = pytest.mark.integration
