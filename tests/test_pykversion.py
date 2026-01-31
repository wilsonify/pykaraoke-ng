"""Unit tests for pykversion module."""

import re
import pytest


class TestVersionString:
    """Test version string format and values."""

    def test_version_string_exists(self):
        """Version string constant should be defined."""
        from pykversion import PYKARAOKE_VERSION_STRING

        assert PYKARAOKE_VERSION_STRING is not None

    def test_version_string_is_string(self):
        """Version string should be a string type."""
        from pykversion import PYKARAOKE_VERSION_STRING

        assert isinstance(PYKARAOKE_VERSION_STRING, str)

    def test_version_string_not_empty(self):
        """Version string should not be empty."""
        from pykversion import PYKARAOKE_VERSION_STRING

        assert len(PYKARAOKE_VERSION_STRING) > 0

    def test_version_string_format(self):
        """Version string should follow semantic versioning format (X.Y.Z)."""
        from pykversion import PYKARAOKE_VERSION_STRING

        # Match patterns like "0.7.5", "1.0.0", "2.10.3", etc.
        pattern = r"^\d+\.\d+\.\d+(-\w+)?$"
        assert re.match(pattern, PYKARAOKE_VERSION_STRING), (
            f"Version string '{PYKARAOKE_VERSION_STRING}' does not match "
            "expected format X.Y.Z or X.Y.Z-suffix"
        )

    def test_version_string_parseable(self):
        """Version string components should be parseable as integers."""
        from pykversion import PYKARAOKE_VERSION_STRING

        # Handle potential suffixes like "-beta"
        base_version = PYKARAOKE_VERSION_STRING.split("-")[0]
        parts = base_version.split(".")

        assert len(parts) == 3, "Version should have exactly 3 parts"

        for i, part in enumerate(parts):
            try:
                value = int(part)
                assert value >= 0, f"Version part {i} should be non-negative"
            except ValueError:
                pytest.fail(f"Version part '{part}' is not a valid integer")

    def test_version_major_minor_patch_extractable(self):
        """Should be able to extract major, minor, patch from version."""
        from pykversion import PYKARAOKE_VERSION_STRING

        base_version = PYKARAOKE_VERSION_STRING.split("-")[0]
        major, minor, patch = [int(x) for x in base_version.split(".")]

        # Sanity checks
        assert major >= 0
        assert minor >= 0
        assert patch >= 0


class TestVersionComparison:
    """Test version comparison utilities (if needed for refactoring)."""

    def test_version_tuple_creation(self):
        """Version can be converted to tuple for comparison."""
        from pykversion import PYKARAOKE_VERSION_STRING

        base_version = PYKARAOKE_VERSION_STRING.split("-")[0]
        version_tuple = tuple(int(x) for x in base_version.split("."))

        assert len(version_tuple) == 3
        assert all(isinstance(v, int) for v in version_tuple)

    def test_version_is_at_least_0_7_5(self):
        """Current version should be at least 0.7.5 (known version)."""
        from pykversion import PYKARAOKE_VERSION_STRING

        base_version = PYKARAOKE_VERSION_STRING.split("-")[0]
        version_tuple = tuple(int(x) for x in base_version.split("."))

        assert version_tuple >= (0, 7, 5), "Version should be at least 0.7.5"
