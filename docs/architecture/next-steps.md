# Open Work

[← Home](../index.md) · [Developer Guide](../developers.md)

---

## Resolved

The following former blockers have been addressed:

- ✅ **Python 3 compatibility** — all Python 2 syntax removed (`types.StringType`, `unicode()`, `raise X, msg`, bare `except:`, etc.)
- ✅ **Artist–title filename parsing** — `FilenameParser` handles "Artist - Title" and legacy dash formats
- ✅ **DIVX/XVID scanning** — `.divx` and `.xvid` added to `MpgExtensions`
- ✅ **ZIP inner-path parsing** — `SongStruct` now uses `ZipStoredName` for artist/title extraction
- ✅ **Security hardening** — `shell=True` removed from subprocess calls; `eval()` replaced with `ast.literal_eval()`

## Open Work

### Integration

- [ ] End-to-end playback test with real media files
- [ ] Bidirectional IPC — async response handling in Tauri
- [ ] Native folder-picker dialog via Tauri plugin
- [ ] Bundle Python backend for distribution (PyInstaller or embedded interpreter)

### Features

- [ ] WebSocket transport (replace polling with push events)
- [ ] Settings UI in the Tauri frontend
- [ ] Lyrics display panel
- [ ] Key / tempo shifting
- [ ] Drag-and-drop playlist reordering
- [ ] Personal playlists (legacy issue #1)
- [ ] Scan-failure logging (legacy issue #11)
- [ ] Scan exclusion filters (legacy issue #13)

### Quality

- [ ] Increase test coverage for `database.py` and `manager.py`
- [ ] Address remaining low-severity SonarQube issues (import-star, old-style formatting)
- [ ] Add type hints across core modules
