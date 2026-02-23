#
# Copyright (C) 2010 Kelvin Lawson (kelvinl@users.sourceforge.net)
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

"""This module is the Python implementation of the auxiliary classes
and functions which have been moved into C for performance reasons.
On the off-chance a C compiler is not available or not reliable for
some reason, you can use this implementation instead."""

import pygame

try:
    import Numeric as N
except ImportError:
    import numpy.oldnumeric as N

# CDG Command Code
CDG_COMMAND = 0x09

# CDG Instruction Codes
CDG_INST_MEMORY_PRESET = 1
CDG_INST_BORDER_PRESET = 2
CDG_INST_TILE_BLOCK = 6
CDG_INST_SCROLL_PRESET = 20
CDG_INST_SCROLL_COPY = 24
CDG_INST_DEF_TRANSP_COL = 28
CDG_INST_LOAD_COL_TBL_0_7 = 30
CDG_INST_LOAD_COL_TBL_8_15 = 31
CDG_INST_TILE_BLOCK_XOR = 38

# Bitmask for all CDG fields
CDG_MASK = 0x3F

# This is the size of the display as defined by the CDG specification.
# The pixels in this region can be painted, and scrolling operations
# rotate through this number of pixels.
CDG_FULL_WIDTH = 300
CDG_FULL_HEIGHT = 216

# This is the size of the array that we operate on.  We add an
# additional border on the right and bottom edge of 6 and 12 pixels,
# respectively, to allow for display shifting.  (It's not clear from
# the spec which colour should be visible when the display is shifted
# to the right or down.  We say it should be the border colour.)

# This is the size of the screen that is actually intended to be
# visible.  It is the center area of CDG_FULL.  The remaining border
# area surrounding it is not meant to be visible.
CDG_DISPLAY_WIDTH = 288
CDG_DISPLAY_HEIGHT = 192

# Screen tile positions
# The viewable area of the screen (288x192) is divided into
# 24 tiles (6x4 of 49x51 each). This is used to only update
# those tiles which have changed on every screen update,
# thus reducing the CPU load of screen updates. A bitmask of
# tiles requiring update is held in CdgPlayer.UpdatedTiles.
# This stores each of the 4 columns in separate bytes, with 6 bits used
# to represent the 6 rows.
TILES_PER_ROW = 6
TILES_PER_COL = 4
TILE_WIDTH = CDG_DISPLAY_WIDTH // TILES_PER_ROW
TILE_HEIGHT = CDG_DISPLAY_HEIGHT // TILES_PER_COL

COLOUR_TABLE_SIZE = 16


class CdgPacket:
    """This class just represents a single 24-byte packet read from
    the CDG stream.  It's not used outside this module."""

    def __init__(self, packet_data):
        self.command = packet_data[0]
        self.instruction = packet_data[1]
        self.data = packet_data[4:20]


class CdgPacketReader:
    """This class does the all work of reading packets from the CDG
    file, and evaluating them to fill in pixels in a Numeric array.
    Its public interface is in five methods."""

    # In this class, we are aggressive with the use of the leading
    # double underscore, Python's convention to indicate private
    # members.  We do this to clearly delineate the private data and
    # methods from the public data and methods, since only the public
    # members are of interest to the C port of this class.  (Though,
    # in practice, the C port follows this class structure quite
    # closely, including duplicating the private members.)

    def __init__(self, cdg_data, mapper_surface):
        self.__cdg_data = cdg_data
        self.__cdg_data_pos = 0

        # This is just for the purpose of mapping colors.
        self.__mapper_surface = mapper_surface

        self.rewind()

    def rewind(self):
        """Rewinds the stream to the beginning, and resets all
        internal state in preparation for decoding the tiles
        again."""

        self.__cdg_data_pos = 0

        # Initialise the colour table. Set a default value for any
        # CDG files that don't actually load the colour table
        # before doing something with it.
        default_colour = 0
        self.__cdg_colour_table = [default_colour] * COLOUR_TABLE_SIZE

        self.__just_cleared_colour_index = -1
        self.__cdg_preset_colour_index = -1
        self.__cdg_border_colour_index = -1
        # Support only one transparent colour
        # Note: Currently unused - reserved for future overlay support on movie files
        self._cdg_transparent_colour = -1

        # These values are used to implement screen shifting.  The CDG
        # specification allows the entire screen to be shifted, up to
        # 5 pixels right and 11 pixels down.  This shift is persistent
        # until it is reset to a different value.  In practice, this
        # is used in conjunction with scrolling (which always jumps in
        # integer blocks of 6x12 pixels) to perform
        # one-pixel-at-a-time scrolls.
        self.__h_offset = 0
        self.__v_offset = 0

        # Build a 306x228 array for the pixel indeces, including border area
        self.__cdg_pixel_colours = N.zeros((CDG_FULL_WIDTH, CDG_FULL_HEIGHT))

        # Build a 306x228 array for the actual RGB values. This will
        # be changed by the various commands, and blitted to the
        # screen now and again. But the border area will not be
        # blitted, only the central 288x192 area.
        self.__cdg_surfarray = N.zeros((CDG_FULL_WIDTH, CDG_FULL_HEIGHT))

        # Start with all tiles requiring update
        self.__updated_tiles = 0xFFFFFFFF

    def mark_tiles_dirty(self):
        """Marks all the tiles dirty, so that the next call to
        GetDirtyTiles() will return the complete list of tiles."""

        self.__updated_tiles = 0xFFFFFFFF

    def get_dirty_tiles(self):
        """Returns a list of (row, col) tuples, corresponding to all
        of the currently-dirty tiles.  Then resets the list of dirty
        tiles to empty."""

        tiles = []
        if self.__updated_tiles != 0:
            for col in range(TILES_PER_COL):
                for row in range(TILES_PER_ROW):
                    if self.__updated_tiles & ((1 << row) << (col * 8)):
                        tiles.append((row, col))

        self.__updated_tiles = 0
        return tiles

    def get_border_colour(self):
        """Returns the current border colour, as a mapped integer
        ready to apply to the surface.  Returns None if the border
        colour has not yet been specified by the CDG stream."""

        if self.__cdg_border_colour_index == -1:
            return None
        return self.__cdg_colour_table[self.__cdg_border_colour_index]

    def do_packets(self, num_packets):
        """Reads numPackets 24-byte packets from the CDG stream, and
        processes their instructions on the internal tables stored
        within this object.  Returns True on success, or False when
        the end-of-file has been reached and no more packets can be
        processed."""

        for i in range(num_packets):
            # Extract the nexxt packet
            packd = self.__get_next_packet()
            if not packd:
                # No more packets.  Return False, but only if we
                # reached this condition on the first packet.
                return i != 0

            self.__cdg_packet_process(packd)

        return True

    def fill_tile(self, surface, row, col):
        """Fills in the pixels on the indicated one-tile surface
        (which must be a TILE_WIDTH x TILE_HEIGHT sized surface) with
        the pixels from the indicated tile."""

        # Calculate the row & column starts/ends
        row_start = 6 + self.__h_offset + (row * TILE_WIDTH)
        row_end = 6 + self.__h_offset + ((row + 1) * TILE_WIDTH)
        col_start = 12 + self.__v_offset + (col * TILE_HEIGHT)
        col_end = 12 + self.__v_offset + ((col + 1) * TILE_HEIGHT)
        pygame.surfarray.blit_array(
            surface, self.__cdg_surfarray[row_start:row_end, col_start:col_end]
        )

    # The remaining methods are all private; they are not part of the
    # public interface.

    # Read the next CDG command from the file (24 bytes each)
    def __get_next_packet(self):
        packet_data = list(map(ord, self.__cdg_data[self.__cdg_data_pos : self.__cdg_data_pos + 24]))
        self.__cdg_data_pos += 24
        if len(packet_data) == 24:
            return CdgPacket(packet_data)
        else:
            self.__cdg_data_pos = len(self.__cdg_data)
            return None

    # Decode and perform the CDG commands in the indicated packet.
    def __cdg_packet_process(self, packd):
        if (packd.command & CDG_MASK) == CDG_COMMAND:
            inst_code = packd.instruction & CDG_MASK
            if inst_code == CDG_INST_MEMORY_PRESET:
                self.__cdg_memory_preset(packd)
            elif inst_code == CDG_INST_BORDER_PRESET:
                self.__cdg_border_preset(packd)
            elif inst_code == CDG_INST_TILE_BLOCK:
                self.__cdg_tile_block_common(packd, xor=0)
            elif inst_code == CDG_INST_SCROLL_PRESET:
                self.__cdg_scroll_preset(packd)
            elif inst_code == CDG_INST_SCROLL_COPY:
                self.__cdg_scroll_copy(packd)
            elif inst_code == CDG_INST_DEF_TRANSP_COL:
                self.__cdg_define_transparent_colour(packd)
            elif inst_code == CDG_INST_LOAD_COL_TBL_0_7:
                self.__cdg_load_colour_table_common(packd, 0)
            elif inst_code == CDG_INST_LOAD_COL_TBL_8_15:
                self.__cdg_load_colour_table_common(packd, 1)
            elif inst_code == CDG_INST_TILE_BLOCK_XOR:
                self.__cdg_tile_block_common(packd, xor=1)
            else:
                # Don't use the error popup, ignore the unsupported command
                error_string = "CDG file may be corrupt, cmd: " + str(inst_code)
                print(error_string)

    # Memory preset (clear the viewable area + border)
    def __cdg_memory_preset(self, packd):
        colour = packd.data[0] & 0x0F

        # The "repeat" flag is nonzero if this is a repeat of a
        # previously-appearing preset command.  (Often a CDG will
        # issue several copies of this command in case one gets
        # corrupted.)

        # We could ignore the entire command if repeat is nonzero, but
        # our data stream is not 100% reliable, since it might have
        # come from a bad rip.  So we should honor every preset
        # command; but we shouldn't waste CPU time clearing the screen
        # repeatedly, needlessly.  So we store a flag indicating the
        # last color that we just cleared to, and don't bother
        # clearing again if it hasn't changed.

        if colour == self.__just_cleared_colour_index:
            return
        self.__just_cleared_colour_index = colour

        # Our new interpretation of CD+G Revealed is that memory preset
        # commands should also change the border
        self.__cdg_preset_colour_index = colour
        self.__cdg_border_colour_index = self.__cdg_preset_colour_index

        # Note that this may be done before any load colour table
        # commands by some CDGs. So the load colour table itself
        # actual recalculates the RGB values for all pixels when
        # the colour table changes.

        # Set the border colour for every pixel. Must be stored in
        # the pixel colour table indeces array, as well as
        # the screen RGB surfarray.

        # NOTE: The preset area--that is, the visible area--starts at
        # (6, 12) and extends to pixel (294, 204).  The border area is
        # the two stripes of 6 pixels on the left and right of the
        # screen, and the stripes of 12 pixels on the top and bottom
        # of the screen.

        # The most efficient way of setting the values in a Numeric
        # array, is to create a zero array and do addition on the
        # the border and preset slices.
        self.__cdg_pixel_colours = N.zeros([CDG_FULL_WIDTH, CDG_FULL_HEIGHT])
        self.__cdg_pixel_colours[:, :] = self.__cdg_pixel_colours[:, :] + colour

        # Now set the border and preset colour in our local surfarray.
        # This will be blitted next time there is a screen update.
        self.__cdg_surfarray = N.zeros([CDG_FULL_WIDTH, CDG_FULL_HEIGHT])
        self.__cdg_surfarray[:, :] = self.__cdg_surfarray[:, :] + self.__cdg_colour_table[colour]

        self.__updated_tiles = 0xFFFFFFFF

    # Border Preset (clear the border area only)
    def __cdg_border_preset(self, packd):
        colour = packd.data[0] & 0x0F
        if colour == self.__cdg_border_colour_index:
            return

        self.__cdg_border_colour_index = colour

        # See cdgMemoryPreset() for a description of what's going on.
        # In this case we are only clearing the border area.

        # Set up the border area of the pixel colours array
        self.__cdg_pixel_colours[:, :12] = N.zeros([CDG_FULL_WIDTH, 12])
        self.__cdg_pixel_colours[:, :12] = (
            self.__cdg_pixel_colours[:, :12] + self.__cdg_border_colour_index
        )
        self.__cdg_pixel_colours[:, -12:] = N.zeros([CDG_FULL_WIDTH, 12])
        self.__cdg_pixel_colours[:, -12:] = (
            self.__cdg_pixel_colours[:, -12:] + self.__cdg_border_colour_index
        )
        self.__cdg_pixel_colours[:6, 12:-12] = N.zeros([6, CDG_FULL_HEIGHT - 24])
        self.__cdg_pixel_colours[:6, 12:-12] = (
            self.__cdg_pixel_colours[:6, 12:-12] + self.__cdg_border_colour_index
        )
        self.__cdg_pixel_colours[-6:, 12:-12] = N.zeros([6, CDG_FULL_HEIGHT - 24])
        self.__cdg_pixel_colours[-6:, 12:-12] = (
            self.__cdg_pixel_colours[-6:, 12:-12] + self.__cdg_border_colour_index
        )

        # Now that we have set the PixelColours, apply them to
        # the Surfarray.
        lookup_table = N.array(self.__cdg_colour_table)
        self.__cdg_surfarray.flat[:] = N.take(lookup_table, N.ravel(self.__cdg_pixel_colours))

    # CDG Scroll Command - Set the scrolled in area with a fresh colour
    def __cdg_scroll_preset(self, packd):
        self.__cdg_scroll_common(packd, copy=False)

    # CDG Scroll Command - Wrap the scrolled out area into the opposite side
    def __cdg_scroll_copy(self, packd):
        self.__cdg_scroll_common(packd, copy=True)

    # Common function to handle the actual pixel scroll for Copy and Preset
    def __cdg_scroll_common(self, packd, copy):
        # Decode the scroll command parameters
        data_block = packd.data
        colour = data_block[0] & 0x0F
        h_scroll = data_block[1] & 0x3F
        v_scroll = data_block[2] & 0x3F
        h_s_cmd = (h_scroll & 0x30) >> 4
        h_offset = h_scroll & 0x07
        v_s_cmd = (v_scroll & 0x30) >> 4
        v_offset = v_scroll & 0x0F

        # Scroll Vertical - Calculate number of pixels
        v_scroll_pixels = self._calc_vertical_scroll(v_s_cmd)

        # Scroll Horizontal- Calculate number of pixels
        h_scroll_pixels = self._calc_horizontal_scroll(h_s_cmd)

        if h_offset != self.__h_offset or v_offset != self.__v_offset:
            # Changing the screen shift.
            self.__h_offset = min(h_offset, 5)
            self.__v_offset = min(v_offset, 11)
            self.__updated_tiles = 0xFFFFFFFF

        if h_scroll_pixels == 0 and v_scroll_pixels == 0:
            return

        # Perform the actual scroll.
        if copy:
            self.__apply_scroll_copy(v_scroll_pixels, h_scroll_pixels)
        else:
            self.__apply_scroll_preset(v_scroll_pixels, h_scroll_pixels, colour)

        # Now that we have scrolled the PixelColours, apply them to
        # the Surfarray.
        lookup_table = N.array(self.__cdg_colour_table)
        self.__cdg_surfarray.flat[:] = N.take(lookup_table, N.ravel(self.__cdg_pixel_colours))
        self.__updated_tiles = 0xFFFFFFFF

    @staticmethod
    def _calc_vertical_scroll(v_s_cmd):
        """Return signed vertical scroll pixels (positive=up, negative=down)."""
        if v_s_cmd == 2:
            return 12
        elif v_s_cmd == 1:
            return -12
        return 0

    @staticmethod
    def _calc_horizontal_scroll(h_s_cmd):
        """Return signed horizontal scroll pixels (positive=left, negative=right)."""
        if h_s_cmd == 2:
            return 6
        elif h_s_cmd == 1:
            return -6
        return 0

    def __apply_scroll_copy(self, v_scroll_pixels, h_scroll_pixels):
        """Copy-scroll: wrap the scrolled-out area into the opposite side."""
        if v_scroll_pixels > 0:
            self.__cdg_pixel_colours = N.concatenate(
                (
                    self.__cdg_pixel_colours[:, v_scroll_pixels:],
                    self.__cdg_pixel_colours[:, :v_scroll_pixels],
                ),
                1,
            )
        elif v_scroll_pixels < 0:
            px = -v_scroll_pixels
            self.__cdg_pixel_colours = N.concatenate(
                (
                    self.__cdg_pixel_colours[:, -px:],
                    self.__cdg_pixel_colours[:, :-px],
                ),
                1,
            )
        elif h_scroll_pixels > 0:
            self.__cdg_pixel_colours = N.concatenate(
                (
                    self.__cdg_pixel_colours[h_scroll_pixels:, :],
                    self.__cdg_pixel_colours[:h_scroll_pixels, :],
                ),
                0,
            )
        elif h_scroll_pixels < 0:
            px = -h_scroll_pixels
            self.__cdg_pixel_colours = N.concatenate(
                (
                    self.__cdg_pixel_colours[-px:, :],
                    self.__cdg_pixel_colours[:-px, :],
                ),
                0,
            )

    def __apply_scroll_preset(self, v_scroll_pixels, h_scroll_pixels, colour):
        """Preset-scroll: fill the scrolled-in area with a fresh colour."""
        if v_scroll_pixels > 0:
            copy_block_colour_index = N.zeros([CDG_FULL_WIDTH, v_scroll_pixels]) + colour
            self.__cdg_pixel_colours = N.concatenate(
                (self.__cdg_pixel_colours[:, v_scroll_pixels:], copy_block_colour_index), 1
            )
        elif v_scroll_pixels < 0:
            px = -v_scroll_pixels
            copy_block_colour_index = N.zeros([CDG_FULL_WIDTH, px]) + colour
            self.__cdg_pixel_colours = N.concatenate(
                (copy_block_colour_index, self.__cdg_pixel_colours[:, :-px]), 1
            )
        elif h_scroll_pixels > 0:
            copy_block_colour_index = N.zeros([h_scroll_pixels, CDG_FULL_HEIGHT]) + colour
            self.__cdg_pixel_colours = N.concatenate(
                (self.__cdg_pixel_colours[h_scroll_pixels:, :], copy_block_colour_index), 0
            )
        elif h_scroll_pixels < 0:
            px = -h_scroll_pixels
            copy_block_colour_index = N.zeros([px, CDG_FULL_HEIGHT]) + colour
            self.__cdg_pixel_colours = N.concatenate(
                (copy_block_colour_index, self.__cdg_pixel_colours[:-px, :]), 0
            )

    # Set one of the colour indeces as transparent. Don't actually do anything with this
    # at the moment, as there is currently no mechanism for overlaying onto a movie file.
    def __cdg_define_transparent_colour(self, packd):
        data_block = packd.data
        colour = data_block[0] & 0x0F
        self._cdg_transparent_colour = colour

    # Load the RGB value for colours 0..7 or 8..15 in the lookup table
    def __cdg_load_colour_table_common(self, packd, table):
        if table == 0:
            colour_table_start = 0
        else:
            colour_table_start = 8
        for i in range(8):
            colour_entry = (packd.data[2 * i] & CDG_MASK) << 8
            colour_entry = colour_entry + (packd.data[(2 * i) + 1] & CDG_MASK)
            colour_entry = ((colour_entry & 0x3F00) >> 2) | (colour_entry & 0x003F)
            red = ((colour_entry & 0x0F00) >> 8) * 17
            green = ((colour_entry & 0x00F0) >> 4) * 17
            blue = (colour_entry & 0x000F) * 17
            self.__cdg_colour_table[i + colour_table_start] = self.__mapper_surface.map_rgb(
                red, green, blue
            )
        # Redraw the entire screen using the new colour table. We still use the
        # same colour indeces (0 to 15) at each pixel but these may translate to
        # new RGB colours. This handles CDGs that preset the screen before actually
        # loading the colour table. It is done in our local RGB surfarray.

        # Do this with the Numeric module operation take() which can replace all
        # values in an array by alternatives from a lookup table. This is ideal as
        # we already have an array of colour indeces (0 to 15). We can create a
        # new RGB surfarray from that by doing take() which translates the 0-15
        # into an RGB colour and stores them in the RGB surfarray.
        lookup_table = N.array(self.__cdg_colour_table)
        self.__cdg_surfarray.flat[:] = N.take(lookup_table, N.ravel(self.__cdg_pixel_colours))

        # An alternative way of doing the above - was found to be very slightly slower.
        # self.__cdg_surfarray.flat[:] =  map(self.__cdg_colour_table.__getitem__, self.__cdg_pixel_colours.flat)

        # Update the screen for any colour changes
        self.__updated_tiles = 0xFFFFFFFF

    # Set the colours for a 12x6 tile. The main CDG command for display data
    def __cdg_tile_block_common(self, packd, xor):
        # Decode the command parameters
        data_block = packd.data
        if data_block[1] & 0x20:
            # I don't know why, but some disks seem to stick an extra
            # bit here to mean "ignore this command".
            return

        colour0 = data_block[0] & 0x0F
        colour1 = data_block[1] & 0x0F

        column_index = (data_block[2] & 0x1F) * 12
        row_index = (data_block[3] & 0x3F) * 6

        # Sanity check the x,y offset read from the CDG in case a
        # corrupted CDG sends us outside of our array bounds
        if column_index > (CDG_FULL_HEIGHT - 12):
            column_index = CDG_FULL_HEIGHT - 12
        if row_index > (CDG_FULL_WIDTH - 6):
            row_index = CDG_FULL_WIDTH - 6

        self.__update_tile_mask(row_index, column_index)

        # Set the pixel array for each of the pixels in the 12x6 tile.
        self.__set_tile_pixels(data_block, row_index, column_index, colour0, colour1, xor)

        # Now the screen has some data on it, so a subsequent clear
        # should be respected.
        self.__just_cleared_colour_index = -1

    def __update_tile_mask(self, row_index, column_index):
        """Update the tile bitmask for the affected screen region."""
        first_row = max((row_index - 6 - self.__h_offset) / TILE_WIDTH, 0)
        last_row = (row_index - 1 - self.__h_offset) / TILE_WIDTH

        first_col = max((column_index - 12 - self.__v_offset) / TILE_HEIGHT, 0)
        last_col = (column_index - 1 - self.__v_offset) / TILE_HEIGHT

        for col in range(first_col, last_col + 1):
            for row in range(first_row, last_row + 1):
                self.__updated_tiles |= (1 << row) << (col * 8)

    def __set_tile_pixels(self, data_block, row_index, column_index, colour0, colour1, xor):
        """Set pixel colours for a 12x6 tile region."""
        for i in range(12):
            byte = data_block[4 + i] & 0x3F
            for j in range(6):
                pixel = (byte >> (5 - j)) & 0x01
                new_col = self.__resolve_pixel_colour(
                    pixel, colour0, colour1, xor, row_index + j, column_index + i
                )
                self.__cdg_surfarray[(row_index + j), (column_index + i)] = self.__cdg_colour_table[
                    new_col
                ]
                self.__cdg_pixel_colours[(row_index + j), (column_index + i)] = new_col

    def __resolve_pixel_colour(self, pixel, colour0, colour1, xor, row, col):
        """Determine the final colour index for a single pixel."""
        if xor:
            xor_col = colour1 if pixel else colour0
            current_colour_index = self.__cdg_pixel_colours[row, col]
            return current_colour_index ^ xor_col
        return colour1 if pixel else colour0
