"""CD+G auxiliary utilities.

Canonical location for CDG auxiliary processing functions. The code
currently lives in :mod:`pykaraoke.players.cdg_aux` and is re-exported
here for the new layered architecture.
"""

from pykaraoke.players.cdg_aux import (  # noqa: F401
    CDG_COMMAND,
    CDG_DISPLAY_HEIGHT,
    CDG_DISPLAY_WIDTH,
    CDG_FULL_HEIGHT,
    CDG_FULL_WIDTH,
    CDG_INST_BORDER_PRESET,
    CDG_INST_DEF_TRANSP_COL,
    CDG_INST_LOAD_COL_TBL_0_7,
    CDG_INST_LOAD_COL_TBL_8_15,
    CDG_INST_MEMORY_PRESET,
    CDG_INST_SCROLL_COPY,
    CDG_INST_SCROLL_PRESET,
    CDG_INST_TILE_BLOCK,
    CDG_INST_TILE_BLOCK_XOR,
    CDG_MASK,
    COLOUR_TABLE_SIZE,
    TILE_HEIGHT,
    TILE_WIDTH,
    CdgPacketReader,
)

__all__ = [
    "CDG_COMMAND",
    "CDG_DISPLAY_HEIGHT",
    "CDG_DISPLAY_WIDTH",
    "CDG_FULL_HEIGHT",
    "CDG_FULL_WIDTH",
    "CDG_INST_BORDER_PRESET",
    "CDG_INST_DEF_TRANSP_COL",
    "CDG_INST_LOAD_COL_TBL_0_7",
    "CDG_INST_LOAD_COL_TBL_8_15",
    "CDG_INST_MEMORY_PRESET",
    "CDG_INST_SCROLL_COPY",
    "CDG_INST_SCROLL_PRESET",
    "CDG_INST_TILE_BLOCK",
    "CDG_INST_TILE_BLOCK_XOR",
    "CDG_MASK",
    "COLOUR_TABLE_SIZE",
    "CdgPacketReader",
    "TILE_HEIGHT",
    "TILE_WIDTH",
]
