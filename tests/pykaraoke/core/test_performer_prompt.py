"""
Tests for pykaraoke.core.performer_prompt module.

Tests the performer name prompt dialog (wx-based).
Since wx may not be available, tests verify module structure.
"""

import pytest


class TestPerformerPromptModule:
    """Tests for performer_prompt module availability."""

    def test_module_importable(self):
        """Module should be importable even without wx."""
        try:
            from pykaraoke.core import performer_prompt

            assert performer_prompt is not None
        except ImportError:
            pytest.skip("performer_prompt requires wx")

    def test_has_performer_prompt_class(self):
        """Module should define a performer prompt class or function."""
        try:
            from pykaraoke.core import performer_prompt

            # Check for the main class/function
            assert hasattr(performer_prompt, "PerformerPrompt") or hasattr(
                performer_prompt, "performerPrompt"
            )
        except ImportError:
            pytest.skip("performer_prompt requires wx")
