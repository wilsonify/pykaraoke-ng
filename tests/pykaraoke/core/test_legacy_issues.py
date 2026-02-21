"""Regression tests for legacy issues tracked in docs/issues/legacy-issues.md.

These tests capture expected behavior for known legacy issues.
Tests that can now pass are plain asserts; tests that expose remaining
work-in-progress are marked with ``pytest.mark.xfail``.
"""

import pytest

from pykaraoke.core.database import SettingsStruct, SongDB, SongStruct


def _settings_with_filename_type(file_name_type):
    settings = SettingsStruct()
    settings.CdgDeriveSongInformation = True
    settings.CdgFileNameType = file_name_type
    return settings


def test_issue14_parses_title_with_extra_dashes_type0():
    """Issue #14: Extra dashes in title should not break parsing (type 0).

    The new FilenameParser joins all parts after disc-track-artist with
    dashes, so 'SC1234-05-Artist-Title-With-Dashes.cdg' correctly yields
    artist='Artist' and title='Title-With-Dashes'.
    """
    settings = _settings_with_filename_type(0)  # Disc-Track-Artist-Title
    filepath = "SC1234-05-Artist-Title-With-Dashes.cdg"

    song = SongStruct(filepath, settings)

    assert song.Artist == "Artist"
    assert song.Title == "Title-With-Dashes"


@pytest.mark.xfail(
    reason="Issue #14: Ambiguous dash-only filenames like 'AC-DC-Back-In-Black' "
           "cannot be reliably split without a space-dash-space separator. "
           "Parser treats first part as artist, rest as title.",
    strict=True,
)
def test_issue14_parses_artist_with_dashes_type3():
    """Issue #14: Dashes in artist names should be preserved (type 3).

    Without a space-dash-space separator the parser cannot distinguish
    where the artist name ends and the title begins.
    'AC-DC-Back-In-Black.cdg' → artist='AC', title='DC-Back-In-Black'
    rather than artist='AC-DC', title='Back-In-Black'.
    """
    settings = _settings_with_filename_type(3)  # Artist-Title
    filepath = "AC-DC-Back-In-Black.cdg"

    song = SongStruct(filepath, settings)

    # Ideal (currently unachievable without heuristics / lookup table):
    assert song.Artist == "AC-DC"
    assert song.Title == "Back-In-Black"


def test_issue14_space_dash_separator_works():
    """Issue #14: When the filename uses ' - ' the parser handles it well."""
    settings = _settings_with_filename_type(3)  # Artist-Title
    filepath = "AC-DC - Back In Black.cdg"

    song = SongStruct(filepath, settings)

    assert song.Artist == "AC-DC"
    assert song.Title == "Back In Black"


@pytest.mark.xfail(
    reason="Issue #5: ZipStoredName inner path 'English/Queen/Bohemian Rhapsody.kar' "
           "yields basename 'Bohemian Rhapsody.kar' which has no dash separator, "
           "so parsing falls back to title-only. Full nested-path extraction is not yet implemented.",
    strict=True,
)
def test_issue5_zip_stored_name_parsing_uses_inner_path():
    """Issue #5: Zip member paths should be parsed for artist/title."""
    settings = _settings_with_filename_type(3)  # Artist-Title

    song = SongStruct(
        "/tmp/Archive.zip",
        settings,
        ZipStoredName="English/Queen/Bohemian Rhapsody.kar",
        DatabaseAdd=True,
    )

    assert song.Artist == "Queen"
    assert song.Title == "Bohemian Rhapsody"


def test_issue5_zip_stored_name_with_dash_separator():
    """Issue #5: When the zip member uses 'Artist - Title.ext' it parses OK."""
    settings = _settings_with_filename_type(3)  # Artist-Title

    song = SongStruct(
        "/tmp/Archive.zip",
        settings,
        ZipStoredName="English/Queen - Bohemian Rhapsody.kar",
    )

    assert song.Artist == "Queen"
    assert song.Title == "Bohemian Rhapsody"


def test_issue6_divx_xvid_extensions_should_scan():
    """Issue #6: DIVX and XVID extensions should be recognized."""
    song_db = SongDB()

    assert song_db.IsExtensionValid(".divx") is True
    assert song_db.IsExtensionValid(".xvid") is True