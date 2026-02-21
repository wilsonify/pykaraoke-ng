# Legacy PyKaraoke Issues

This document captures all open issues from the original PyKaraoke project (https://github.com/kelvinlawson/pykaraoke/issues). These issues are preserved for historical reference and to guide future development of PyKaraoke-NG.

**Note**: PyKaraoke-NG has undergone significant architectural changes, including:
- Migration from wxPython GUI to Tauri-based modern web interface
- Python 3 modernization
- Code quality improvements via SonarQube

## Table of Contents
- [Feature Requests](#feature-requests)
- [Bugs](#bugs)
- [Installation/Platform Issues](#installationplatform-issues)

---

## Feature Requests

### Issue #1: Save Personal Singer Playlists
**Opened**: Jun 19, 2011  
**Author**: kelvinlawson  
**Status**: Open (Legacy)

**Description**: Allow singers to save personal playlists of their favourite songs.

**PyKaraoke-NG Status**: Not implemented. Could be considered for the Tauri GUI implementation.

---

### Issue #2: Pitch-shifting
**Opened**: Jun 20, 2011  
**Author**: kelvinlawson  
**Status**: Open (Legacy)

**Description**: Already in progress in gstreamer branch. Needs to be merged into master with the following changes:
- Fall back to Pygame for audio if pygst is not available (vital on platforms that do not support pygst, potentially GP2X) and saves us from mandating that pygst is always installed.
- Windows pygst pitch-shifting is not currently working, so needs to be fixed or do not attempt to use pygst/pitch-shifting on Windows platform (even if pygst is available).
- Do not show the pitch-shifting buttons in pykaraoke.py if pygst not in use.

**Comments**:
- chazzmac (Jan 24, 2014): Asked about 3-year delay
- kelvinlawson (Jan 28, 2014): Noted this is community-driven since he doesn't personally use pitch-shifting. Happy to accept patches. Suggested users can clone and use the gstreamer branch directly.

**PyKaraoke-NG Status**: Not implemented. Would require integration with modern audio processing libraries if added to Tauri interface.

---

### Issue #3: Lyrics Preview Window
**Opened**: Jun 20, 2011  
**Author**: kelvinlawson  
**Status**: Open (Legacy)

**Description**: Already in progress in gstreamer branch, needs to be merged into master with the following changes:
- Make sure that it does not break all supported platforms.
- In particular, make sure that there are no Wx dependencies introduced for platforms that use only pykaraoke_mini (e.g. GP2X). At the moment it looks like the gstreamer branch has introduced a dependency on Wx which could affect pykaraoke_mini platforms that have no Wx installed. (To be confirmed).

**PyKaraoke-NG Status**: Not applicable - wxPython GUI has been removed. A preview window could be implemented in the Tauri GUI.

---

### Issue #4: Tempo-Shifting
**Opened**: Jun 20, 2011  
**Author**: kelvinlawson  
**Status**: Open (Legacy)

**Description**: This is a work-in-progress in gstreamer branch, but is not yet working. Once working needs to be merged into master, including making sure that it works on all platforms, and disabling it if pygst is not available or tempo-shifting is not working on the platform.

**PyKaraoke-NG Status**: Not implemented. Would require integration with modern audio processing libraries if added to Tauri interface.

---

### Issue #5: Custom pattern for song structure filter
**Opened**: Jun 27, 2011  
**Author**: kelvinlawson  
**Status**: Open (Legacy)

**Description**: Feature request from Sourceforge tracker. User had a zip archive with structured KAR files in the following way: `language/artist/song.kar`

Version 0.7.4 did not parse it properly. User provided a quick fix:

```python
if ZipStoredName:
    ZipSplit = ZipStoredName.rpartition(".")[0]
    self.Title = ZipSplit.rpartition("/")[2]
    self.Artist = ZipSplit.rpartition("/")[0].rpartition("/")[2]
    self.DisplayFilename = os.path.basename(ZipStoredName)
    if isinstance(self.DisplayFilename, types.StringType):
        self.DisplayFilename = self.DisplayFilename.decode(settings.ZipfileCoding)
```

User noted that a proper fix would require much more programming.

**Reference**: Original Sourceforge tracker: http://sourceforge.net/tracker/?func=detail&atid=695884&aid=3324428&group_id=123242

**PyKaraoke-NG Status**: Needs investigation. The database parsing logic may have changed significantly.

---

### Issue #6: Scan DIVX and XVID Extensions
**Opened**: Sep 19, 2011  
**Author**: kelvinlawson (originally submitted by SF user softbilly)  
**Status**: Open (Legacy)

**Description**: When scanning for songs in the selected folders it should be possible to search also for divx and xvid extensions and not only avi.

**PyKaraoke-NG Status**: Needs investigation. Video file extension scanning should be reviewed in the current codebase.

---

### Issue #7: Reallocate file links in database
**Opened**: Sep 19, 2011  
**Author**: kelvinlawson (originally submitted by SF user softbilly)  
**Status**: Open (Legacy)

**Description**: Imagine media files were scanned from folder e.g. `D:\Myfiles\some subfolder structure` and database was edited with information like artist etc. Now the files are moved to `C:\MyKaraoke\some subfolder structure`. It should be possible to reallocate the files. Change root of file links in database.

**PyKaraoke-NG Status**: Not implemented. This would be a useful feature for database management.

---

### Issue #8: Backup and restore library
**Opened**: Sep 19, 2011  
**Author**: kelvinlawson (originally submitted by SF user softbilly)  
**Status**: Open (Legacy)

**Description**: It should be possible to backup and restore the song database. Talking about the list of artists and songs and the link to the media file (cdg + mp3 or avi) and not the media files themselves. This would be another feature.

**PyKaraoke-NG Status**: Not implemented. Database backup/restore would be a valuable feature.

---

### Issue #9: KJ Features
**Opened**: Sep 19, 2011  
**Author**: kelvinlawson  
**Status**: Open (Legacy)

**Description**: Various KJ (Karaoke Jockey) feature requests:
- Key change functionality
- Countdown timer
- DJ preview screen

**PyKaraoke-NG Status**: Not implemented. These professional KJ features could be considered for future development.

---

### Issue #11: Log files that failed during scan
**Opened**: Dec 5, 2011  
**Author**: SlashQuit  
**Status**: Open (Legacy)

**Description**: Feature request to log failed files during scan with reasons for failure.

**PyKaraoke-NG Status**: Not implemented. Better error logging would be valuable for troubleshooting.

---

### Issue #13: Scan exclusion filter
**Opened**: Dec 5, 2011  
**Author**: SlashQuit  
**Status**: Open (Legacy)

**Description**: Feature request for scan exclusion filter (e.g., exclude Vocal, Gospel, Spanish categories).

**PyKaraoke-NG Status**: Not implemented. Could be useful for large song collections.

---

## Bugs

### Issue #10: Unresponsive after playing MIDI without lyrics
**Opened**: Nov 5, 2011  
**Author**: kelvinlawson  
**Status**: Open (Legacy)

**Description**: Application becomes unresponsive after playing MIDI file without lyrics. Error: AttributeError

**PyKaraoke-NG Status**: Needs verification. The player architecture has changed significantly.

---

### Issue #12: Kamikaze mode double performer prompt
**Opened**: Dec 5, 2011  
**Author**: SlashQuit  
**Status**: Open (Legacy)

**Description**: Bug in Kamikaze mode - double performer prompt appears.

**PyKaraoke-NG Status**: Needs investigation. Kamikaze mode functionality needs to be verified in current codebase.

---

### Issue #14: Artist-Title parsing fails with certain filenames
**Opened**: Dec 11, 2011  
**Author**: SlashQuit  
**Status**: Open (Legacy)

**Description**: Artist-Title parsing fails with dashes in paths/names. User provided detailed parsing logic suggestions.

Example problematic cases:
- Files with multiple dashes
- Dashes in directory paths vs. filenames
- Need for smarter parsing logic

**PyKaraoke-NG Status**: Needs investigation. File parsing logic should be reviewed and tested with various filename formats.

---

### Issue #16: Sound playback fails with MIDI files
**Opened**: Jan 3, 2014  
**Author**: silverdev  
**Status**: Open (Legacy)

**Description**: MIDI playback fails silently - no sound but lyrics display correctly.

**PyKaraoke-NG Status**: Needs verification. MIDI support should be tested in current implementation.

---

## Installation/Platform Issues

### Issue #18: Renamed libwxgtk-python dependency
**Opened**: Mar 24, 2015  
**Author**: fnk0c  
**Status**: Open (Legacy)

**Description**: libwxgtk-python dependency was renamed to python-wxgtk2.8 - documentation needs update.

**PyKaraoke-NG Status**: Not applicable - wxPython GUI has been completely removed in favor of Tauri.

---

### Issue #21: GP2X still relevant?
**Opened**: Dec 27, 2017  
**Author**: AThomsen  
**Status**: Open (Legacy)

**Description**: Question about whether GP2X platform support is still relevant.

**Comments**: 3 comments discussing platform support and whether to maintain GP2X compatibility.

**PyKaraoke-NG Status**: GP2X support has been removed. PyKaraoke-NG focuses on modern platforms (Windows, macOS, Linux desktop).

---

### Issue #22: Installation on Ubuntu 22
**Opened**: May 22, 2023  
**Author**: firux88  
**Status**: Open (Legacy)

**Description**: Installation problems on Ubuntu 22 - Python 3 compatibility issues with dependencies.

**PyKaraoke-NG Status**: PyKaraoke-NG has been fully updated for Python 3.13+ compatibility. Installation issues should be resolved.

---

## Notes for PyKaraoke-NG Development

### High Priority
- **Issue #14**: File parsing improvements for artist/title extraction
- **Issue #16**: MIDI playback testing and fixes
- **Issue #22**: Ensure Python 3 compatibility (already done)

### Medium Priority
- **Issue #7**: Database path reallocation tool
- **Issue #8**: Database backup/restore functionality
- **Issue #13**: Scan exclusion filters

### Low Priority (Nice to Have)
- **Issue #1**: Personal playlists
- **Issue #2, #4**: Pitch/tempo shifting (requires audio processing research)
- **Issue #9**: Professional KJ features
- **Issue #11**: Enhanced error logging

### Not Applicable
- **Issue #3**: Lyrics preview (can be reimplemented in Tauri)
- **Issue #18**: wxPython dependency (removed)
- **Issue #21**: GP2X support (deprecated)

### Needs Investigation
- **Issue #5**: Custom filename parsing patterns
- **Issue #6**: DIVX/XVID extension support
- **Issue #10**: MIDI without lyrics crash
- **Issue #12**: Kamikaze mode double prompt
