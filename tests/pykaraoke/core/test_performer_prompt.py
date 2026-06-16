"""
Tests for pykaraoke.core.performer_prompt module.

Tests the performer name prompt dialog (wx-based).
Uses a wx mock so no wx runtime is needed.
"""

import sys
from unittest.mock import MagicMock, PropertyMock, patch

import pytest


@pytest.fixture(autouse=True)
def mock_wx():
    """Provide a mock wx module so performer_prompt can be imported

    without wxPython installed.  The mock supplies the module-level
    names that performer_prompt.py references (Dialog, StaticText,
    TextCtrl, NewId, etc.) so the import succeeds and the class can
    be inspected structurally.
    """
    if "wx" in sys.modules:
        yield
        return

    wx = MagicMock()
    wx.ID_ANY = -1
    wx.TE_PROCESS_ENTER = 0x100
    wx.HORIZONTAL = 4
    wx.VERTICAL = 8
    wx.ALL = 1
    wx.OK = 510
    wx.CANCEL = 511
    wx.ID_OK = 510
    wx.ID_CANCEL = 511
    wx.EVT_BUTTON = type("EVT_BUTTON", (), {})()
    wx.OK = 510

    # Mock Dialog class
    dialog_mock = MagicMock()
    type(dialog_mock).PerformerText = PropertyMock()
    type(dialog_mock).PerformerID = PropertyMock()
    type(dialog_mock).PerformerTxtCtrl = PropertyMock()
    type(dialog_mock).PerformerSizer = PropertyMock()
    type(dialog_mock).ButtonSizer = PropertyMock()
    type(dialog_mock).MainSizer = PropertyMock()
    type(dialog_mock).performer = PropertyMock()
    wx.Dialog = MagicMock(return_value=dialog_mock)
    wx.StaticText = MagicMock()
    wx.NewId = MagicMock(return_value=42)
    wx.TextCtrl = MagicMock()
    wx.BoxSizer = MagicMock()

    sys.modules["wx"] = wx
    yield

    # Restore if we injected — harmless if it wasn't there before
    if "wx" in sys.modules and isinstance(sys.modules["wx"], MagicMock):
        del sys.modules["wx"]


class TestPerformerPromptModule:
    """Tests for performer_prompt module availability."""

    def test_module_importable(self):
        """Module should be importable even without wx."""
        from pykaraoke.core import performer_prompt

        assert performer_prompt is not None

    def test_has_performer_prompt_class(self):
        """Module should define a performer prompt class or function."""
        from pykaraoke.core import performer_prompt

        assert hasattr(performer_prompt, "PerformerPrompt") or hasattr(
            performer_prompt, "performerPrompt"
        )
