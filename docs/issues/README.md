# Legacy PyKaraoke Issues

This directory contains documentation of issues from the original PyKaraoke project (https://github.com/kelvinlawson/pykaraoke).

## Files

- **[legacy-issues.md](legacy-issues.md)** - Complete documentation of all 18 open issues from the original project

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
- #18, #21, #22: Platform and dependency issues resolved through modernization
- wxPython GUI completely removed
- Python 3.13+ fully supported
- GP2X support dropped

**High Priority for Investigation**:
- #14: File parsing improvements
- #16: MIDI playback testing

**Medium Priority**:
- #7, #8: Database management features
- #13: Scan filters

**Future Consideration**:
- #1: Personal playlists
- #2, #4: Audio manipulation features
- #9: Professional KJ features

## Contributing

If you're interested in addressing any of these legacy issues in PyKaraoke-NG, please:

1. Check if the issue is still relevant given the architectural changes
2. Open a new issue in the PyKaraoke-NG repository
3. Reference the original issue number from this documentation
4. Propose a solution that fits the modern Tauri-based architecture
