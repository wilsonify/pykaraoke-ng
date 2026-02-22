"""Regression tests for legacy issues tracked in docs/issues/legacy-issues.md.

These tests capture expected behavior for known legacy issues. They are
intentionally allowed to fail until the corresponding fixes are implemented.
"""

from pykaraoke.core.database import SettingsStruct, SongDB, SongStruct


def _settings_with_filename_type(file_name_type):
    settings = SettingsStruct()
    settings.cdg_derive_song_information = True
    settings.cdg_file_name_type = file_name_type
    return settings


def test_issue14_parses_title_with_extra_dashes_type0():
    """Issue #14: Extra dashes in title should not break parsing (type 0)."""
    settings = _settings_with_filename_type(0)  # Disc-Track-Artist-Title
    filepath = "SC1234-05-Artist-Title-With-Dashes.cdg"

    song = SongStruct(filepath, settings)

    assert song.artist == "Artist"
    assert song.title == "Title-With-Dashes"


def test_issue14_parses_artist_with_dashes_type3():
    """Issue #14: Dashes in artist names should be preserved (type 3)."""
    settings = _settings_with_filename_type(3)  # Artist-Title
    filepath = "AC-DC-Back-In-Black.cdg"

    song = SongStruct(filepath, settings)

    assert song.artist == "AC-DC"
    assert song.title == "Back-In-Black"


def test_issue5_zip_stored_name_parsing_uses_inner_path():
    """Issue #5: Zip member paths should be parsed for artist/title."""
    settings = _settings_with_filename_type(3)  # Artist-Title

    song = SongStruct(
        "/tmp/Archive.zip",
        settings,
        zip_stored_name="English/Queen/Bohemian Rhapsody.kar",
        database_add=True,
    )

    assert song.artist == "Queen"
    assert song.title == "Bohemian Rhapsody"


def test_issue6_divx_xvid_extensions_should_scan():
    """Issue #6: DIVX and XVID extensions should be recognized."""
    song_db = SongDB()

    assert song_db.is_extension_valid(".divx") is True
    assert song_db.is_extension_valid(".xvid") is True