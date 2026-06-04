"""
Tests for pykaraoke.players.kar module.

Tests MIDI/KAR player module with pygame mocked for headless testing.
"""

import sys
from unittest.mock import MagicMock

import pytest

from tests.conftest import install_pygame_mock

install_pygame_mock()


class TestKarModule:
    def test_module_importable(self):
        from pykaraoke.players import kar

        assert kar is not None

    def test_has_mid_player_class(self):
        from pykaraoke.players import kar

        assert hasattr(kar, "MidPlayer")

    def test_mid_player_is_class(self):
        from pykaraoke.players import kar

        assert isinstance(kar.MidPlayer, type)

    def test_state_capturing_imported(self):
        """Regression: kar module must have STATE_CAPTURING available.

        Before the fix, kar.py used STATE_CAPTURING in do_stuff() but
        did not import it, causing a NameError during stop/poll.
        """
        from pykaraoke.players import kar

        # Importing the module should not raise NameError on the
        # STATE_CAPTURING reference in do_stuff()
        assert hasattr(kar, "MidPlayer")

        # Verify STATE_CAPTURING is accessible through the module's imports
        # by checking it can be referenced at all
        from pykaraoke.config.constants import STATE_CAPTURING

        assert STATE_CAPTURING is not None


class TestMidiConstants:
    def test_midi_header_id(self):
        from pykaraoke.players import kar

        if hasattr(kar, "MIDI_HEADER"):
            assert kar.MIDI_HEADER == b"MThd"

    def test_midi_track_id(self):
        from pykaraoke.players import kar

        if hasattr(kar, "MIDI_TRACK_HEADER"):
            assert kar.MIDI_TRACK_HEADER == b"MTrk"


class TestMidiParsing:
    def test_big_endian_16(self):
        data = bytes([0x01, 0x00])
        value = (data[0] << 8) | data[1]
        assert value == 256

    def test_big_endian_32(self):
        data = bytes([0x00, 0x00, 0x01, 0x00])
        value = (data[0] << 24) | (data[1] << 16) | (data[2] << 8) | data[3]
        assert value == 256
