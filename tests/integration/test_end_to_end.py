import os
import shutil
import subprocess
from pathlib import Path

import pytest


def _find_python2():
    for candidate in ("python2", "python2.7"):
        path = shutil.which(candidate)
        if path:
            return path
    return None


def _python2_can_import(python2_path, module_name):
    try:
        subprocess.run(
            [python2_path, "-c", f"import {module_name}"],
            check=True,
            capture_output=True,
            text=True,
        )
        return True
    except Exception:
        return False


def _run_db_scan_with_python2(repo_root, songs_dir, out_dir, env):
    helper = Path(out_dir) / "scan_with_pykdb.py"
    helper.write_text(
        """
import os
import sys

repo_root = os.environ['REPO_ROOT']
sys.path.insert(0, repo_root)

import pykdb

class DummyYielder(pykdb.AppYielder):
    def Yield(self):
        return None

class DummyBusy(pykdb.BusyCancelDialog):
    def __init__(self):
        pykdb.BusyCancelDialog.__init__(self)
    def Show(self):
        return None
    def SetProgress(self, label, progress):
        return None
    def Destroy(self):
        return None

song_db = pykdb.SongDB()

song_db.Settings.FolderList = [os.environ['SONGS_DIR']]
# Keep the scan small and deterministic for tests
song_db.Settings.ReadTitlesTxt = False
song_db.Settings.LookInsideZips = False
song_db.Settings.CheckHashes = False

song_db.BuildSearchDatabase(DummyYielder(), DummyBusy())

song_db.SaveSettings()
song_db.SaveDatabase()

report_path = os.path.join(os.environ['OUT_DIR'], 'scan_report.html')
with open(report_path, 'w') as f:
    f.write('<!doctype html>')
    f.write('<html><head><meta charset="utf-8">')
    f.write('<title>PyKaraoke Scan Report</title>')
    f.write('</head><body>')
    f.write('<h1>PyKaraoke Scan Report</h1>')
    f.write('<ul>')
    for song in song_db.FullSongList:
        f.write('<li>{}</li>'.format(song.DisplayFilename))
    f.write('</ul>')
    f.write('</body></html>')

print(report_path)
""".strip()
        + "\n"
    )

    result = subprocess.run(
        [env["PYTHON2"], str(helper)],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return result.stdout.strip()


def test_end_to_end_database_scan_and_report(tmp_path):
    """
    End-to-end flow:
    1) Create a karaoke file on disk.
    2) Run the real database scan (via python2) to pick it up.
    3) Generate an HTML report of scanned songs.
    4) Use Selenium to verify the report lists the song.
    """

    python2_path = _find_python2()
    if not python2_path:
        pytest.skip("python2 not available; PyKaraoke core is Python 2.x")

    if not _python2_can_import(python2_path, "pygame"):
        pytest.skip("pygame not available for python2; required by pykdb")

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
    env["PYTHON2"] = python2_path
    env["REPO_ROOT"] = str(repo_root)
    env["SONGS_DIR"] = str(songs_dir)
    env["OUT_DIR"] = str(out_dir)
    env["PYKARAOKE_DIR"] = str(out_dir / "pykaraoke_home")
    env["PYKARAOKE_TEMP_DIR"] = str(out_dir / "pykaraoke_tmp")
    env["PYTHONPATH"] = str(repo_root)

    report_path = _run_db_scan_with_python2(repo_root, songs_dir, out_dir, env)
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
