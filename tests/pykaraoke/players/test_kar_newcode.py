"""
Targeted tests for kar.py new/changed code lines.

Covers:
- Lyrics.recordText with @T (title) → text_type = TEXT_TITLE (line 333)
- Lyrics.recordText with @I (info)  → text_type = TEXT_INFO  (line 336)
- LyricSyllable appended with text_type variable (line 345)
"""

import sys
from unittest.mock import MagicMock

import pytest

from tests.conftest import install_pygame_mock

install_pygame_mock()

from pykaraoke.players.kar import Lyrics, LyricSyllable, TEXT_TITLE, TEXT_INFO, TEXT_LYRIC


class TestLyricsRecordTextType:
    """Tests the text_type variable rename (type → text_type) in recordText."""

    def test_record_text_title(self):
        """@T prefix → text_type = TEXT_TITLE (line 333)."""
        lyrics = Lyrics()
        lyrics.recordText(100, "@TSong Title")
        assert len(lyrics.list) == 1
        syl = lyrics.list[0]
        assert syl.type == TEXT_TITLE
        assert syl.text == "Song Title"
        assert syl.click == 100

    def test_record_text_info(self):
        """@I prefix → text_type = TEXT_INFO (line 336)."""
        lyrics = Lyrics()
        lyrics.recordText(200, "@IArtist Name")
        assert len(lyrics.list) == 1
        syl = lyrics.list[0]
        assert syl.type == TEXT_INFO
        assert syl.text == "Artist Name"
        assert syl.click == 200

    def test_record_text_title_multiline(self):
        """@T with newlines creates multiple syllables, all TEXT_TITLE (line 345)."""
        lyrics = Lyrics()
        lyrics.recordText(300, "@TLine One\nLine Two")
        assert len(lyrics.list) == 2
        for syl in lyrics.list:
            assert syl.type == TEXT_TITLE

    def test_record_text_info_multiline(self):
        """@I with newlines creates multiple syllables, all TEXT_INFO."""
        lyrics = Lyrics()
        lyrics.recordText(400, "@IFirst\nSecond\nThird")
        assert len(lyrics.list) == 3
        for syl in lyrics.list:
            assert syl.type == TEXT_INFO

    def test_record_text_unknown_at_prefix_ignored(self):
        """@X (unknown) is ignored entirely."""
        lyrics = Lyrics()
        lyrics.recordText(500, "@XSomething")
        assert len(lyrics.list) == 0

    def test_record_text_regular_lyric(self):
        """Normal text → TEXT_LYRIC (default)."""
        lyrics = Lyrics()
        lyrics.recordText(600, "Hello world")
        assert len(lyrics.list) == 1
        assert lyrics.list[0].type == TEXT_LYRIC
        assert lyrics.list[0].text == "Hello world"

    def test_record_text_empty_ignored(self):
        """Empty text is ignored."""
        lyrics = Lyrics()
        lyrics.recordText(700, "")
        assert len(lyrics.list) == 0

    def test_record_text_line_break(self):
        """/ prefix → line break."""
        lyrics = Lyrics()
        lyrics.recordText(800, "/next line")
        assert len(lyrics.list) == 1
        assert lyrics.list[0].text == "next line"

    def test_record_text_paragraph_break(self):
        r"""\ prefix → paragraph break."""
        lyrics = Lyrics()
        lyrics.recordText(900, "\\new paragraph")
        assert len(lyrics.list) == 1
        assert lyrics.list[0].text == "new paragraph"
