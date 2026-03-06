"""Performer prompt and performer-related domain logic.

Canonical location for the performer request dialog. The implementation
currently lives in :mod:`pykaraoke.core.performer_prompt` and is
re-exported here so that callers can start migrating to the new
layered import path::

    from pykaraoke.domain.performer import PerformerPrompt
"""

try:
    from pykaraoke.core.performer_prompt import PerformerPrompt  # noqa: F401

    __all__ = ["PerformerPrompt"]
except ImportError:
    # wx may not be installed; the module is still importable
    __all__ = []
