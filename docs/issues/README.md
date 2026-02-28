# Legacy PyKaraoke Issues

This directory contains documentation of issues from the original PyKaraoke project (https://github.com/kelvinlawson/pykaraoke).

## Files

- **[legacy-issues.md](legacy-issues.md)** - Complete documentation of all 18 open issues from the original project
- **[webkit-dmabuf-empty-window.md](webkit-dmabuf-empty-window.md)** - Empty window on launch due to WebKitGTK DMA-BUF failure (fixed)
- **[deb-buttons-not-working.md](deb-buttons-not-working.md)** - Add Folder, Scan Library, and Settings buttons do nothing in packaged .deb (fixed)

## Summary

The original PyKaraoke project had 18 open issues at the time of forking. These issues are preserved for historical reference and to guide future development of PyKaraoke-NG.

### Issue Categories

- **Feature Requests**: 11 issues
  - Personal playlists (#1)
  - Pitch-shifting (#2)
  - Lyrics preview window (#3)
  - Tempo-shifting (#4)
  - Custom filename parsing (#5)
  - Additional video extensions (#6)
  - Database path reallocation (#7)
  - Database backup/restore (#8)
  - Professional KJ features (#9)
  - Scan failure logging (#11)
  - Scan exclusion filters (#13)

- **Bugs**: 4 issues
  - MIDI without lyrics crash (#10)
  - Kamikaze mode double prompt (#12)
  - Artist-Title parsing issues (#14)
  - MIDI playback failures (#16)

- **Installation/Platform**: 3 issues
  - wxPython dependency renamed (#18)
  - GP2X platform relevance (#21)
  - Ubuntu 22 Python 3 compatibility (#22)

### Status in PyKaraoke-NG

**Resolved**:
- #6: `.divx` and `.xvid` added to `MpgExtensions`
- #14: `FilenameParser` handles "Artist - Title" and legacy dash formats; regression tests in place
- #18, #21, #22: Platform and dependency issues resolved through modernization (Python 3.13+, wxPython removed, GP2X dropped)

**Partially Addressed** (regression tests exist, edge cases remain):
- #5: ZIP inner-path parsing uses `ZipStoredName`; filenames without a delimiter are marked as known-ambiguous
- #16: MIDI playback — Python 3 byte-string handling fixed; needs testing with real `.mid` files

**High Priority**:
- #7, #8: Database path reallocation and backup/restore
- #11: Scan failure logging
- #13: Scan exclusion filters

**Future Consideration**:
- #1: Personal playlists
- #2, #4: Pitch and tempo shifting
- #9: Professional KJ features
- #10: MIDI without lyrics crash handling

## Contributing

If you're interested in addressing any of these legacy issues in PyKaraoke-NG, please:

1. Check if the issue is still relevant given the architectural changes
2. Open a new issue in the PyKaraoke-NG repository
3. Reference the original issue number from this documentation
4. Propose a solution that fits the modern Tauri-based architecture
