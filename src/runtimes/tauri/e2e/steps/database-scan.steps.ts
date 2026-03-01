/**
 * Step definitions for Database Scan and Report feature.
 *
 * Maps to: features/database-scan.feature
 * Preserves coverage from: test_end_to_end.py::test_end_to_end_database_scan_and_report
 *
 * NOTE: This scenario requires Python + Selenium (Chrome) to be available.
 * It is tagged @requires-python @requires-selenium and may be skipped
 * in environments without those dependencies.
 */

import { Given, When, Then } from '@cucumber/cucumber';
import { expect } from 'chai';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';
import { execSync } from 'child_process';

let tempDir: string;
let songsDir: string;
let outDir: string;
let reportPath: string;

Given('a temporary songs directory with a file {string}', function (filename: string) {
  tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'pykaraoke-e2e-'));
  songsDir = path.join(tempDir, 'songs');
  outDir = path.join(tempDir, 'out');
  fs.mkdirSync(songsDir, { recursive: true });
  fs.mkdirSync(outDir, { recursive: true });

  // Create an empty .kar file (extension-based detection)
  fs.writeFileSync(path.join(songsDir, filename), '');
});

When('the database scan runs against the songs directory', function () {
  const repoRoot = path.resolve(__dirname, '..', '..', '..', '..', '..', '..');
  const scanScript = path.join(outDir, 'scan_with_pykdb.py');

  // Write the scan helper script (matches test_end_to_end.py logic)
  fs.writeFileSync(
    scanScript,
    `
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
`.trim() + '\\n',
  );

  const env = {
    ...process.env,
    REPO_ROOT: repoRoot,
    SONGS_DIR: songsDir,
    OUT_DIR: outDir,
    PYKARAOKE_DIR: path.join(outDir, 'pykaraoke_home'),
    PYKARAOKE_TEMP_DIR: path.join(outDir, 'pykaraoke_tmp'),
    PYTHONPATH: repoRoot,
  };

  try {
    const output = execSync(`python3 ${scanScript}`, {
      env,
      encoding: 'utf-8',
      timeout: 30000,
    });
    const lines = output.trim().split('\\n').filter((l: string) => l.trim());
    reportPath = lines[lines.length - 1].trim();
  } catch (err: any) {
    // TODO: Handle environments where pygame is not available
    throw new Error(`Database scan failed: ${err.stderr || err.message}`);
  }
});

Then('an HTML report should be generated', function () {
  expect(fs.existsSync(reportPath), `Report not found at ${reportPath}`).to.be.true;
});

Then('the report title should be {string}', function (expectedTitle: string) {
  const content = fs.readFileSync(reportPath, 'utf-8');
  expect(content).to.include(`<title>${expectedTitle}</title>`);
});

Then('the report should list {string}', function (expectedEntry: string) {
  const content = fs.readFileSync(reportPath, 'utf-8');
  expect(content).to.include(expectedEntry);
});
