#
# Copyright (C) 2010  Kelvin Lawson (kelvinl@users.sourceforge.net)
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

"""This module defines the class PykPlayer, which is a base class used
by the modules pykar.py, pycdg.py, and pympg.py.  This collects
together some common interfaces used by these different
implementations for different types of Karaoke files."""

import os
import sys

import pygame

from pykaraoke.config.constants import (
    ENV_GP2X,
    ENV_WINDOWS,
    GP2X_BUTTON_L,
    GP2X_BUTTON_LEFT,
    GP2X_BUTTON_R,
    GP2X_BUTTON_RIGHT,
    GP2X_BUTTON_SELECT,
    GP2X_BUTTON_START,
    STATE_CAPTURING,
    STATE_CLOSED,
    STATE_CLOSING,
    STATE_INIT,
    STATE_NOT_PLAYING,
    STATE_PAUSED,
    STATE_PLAYING,
)
from pykaraoke.config.environment import env
from pykaraoke.core.manager import manager

# Constant for the sync delay message (avoiding literal duplication)
_SYNC_MSG = "sync %s"


class PykPlayer:
    def __init__(self, song, song_db, error_notify_callback=None, done_callback=None, window_title=None):
        """The first parameter, song, may be either a database.SongStruct
        instance, or it may be a filename."""

        if song_db is None:
            from pykaraoke.core import database

            song_db = database.globalSongDB
            song_db.load_settings(None)
        self.song_db = song_db

        # Set the global command-line options if they have not already
        # been set.
        if manager.options is None:
            parser = self.setup_options()
            (manager.options, args) = parser.parse_args()
            manager.apply_options(self.song_db)

            if song is None:
                if len(args) != 1:
                    parser.print_help()
                    sys.exit(2)
                song = args[0]

        # Unfortunately, we can't capture sound when dumping.  There
        # are two reasons for this.  (1) pymedia doesn't currently
        # support multiplexing audio with a video stream, so when
        # you're dumping an mpeg file, it has to be video-only.  (2)
        # pygame doesn't provide a way for us to programmatically
        # convert a midi file to sound samples anyway--all you can do
        # with a midi file is route it through the speakers.

        # So, for these reasons, we always just disable sound when
        # dumping images or movies.
        if manager.options.dump:
            manager.options.nomusic = True

        if isinstance(song, str):
            # We were given a filename.  Convert it to a SongStruct.
            song = self.song_db.makeSongStruct(song)

        # Store the parameters
        self.song = song
        self.window_title = window_title

        # And look up the actual files corresponding to this SongStruct.
        self.song_datas = song.get_song_datas()
        if window_title is None:
            self.window_title = song.display_filename

        # Caller can register a callback by which we
        # print out error information, use stdout if none registered
        if error_notify_callback:
            self.error_notify_callback = error_notify_callback
        else:
            self.error_notify_callback = self.__default_error_print

        # Caller can register a callback by which we
        # let them know when the song is finished
        if done_callback:
            self.song_finished_callback = done_callback
        else:
            self.song_finished_callback = None

        self.state = STATE_INIT
        self.internal_offset_time = 0

        # These values are used to keep track of the current position
        # through the song based on pygame's get_ticks() interface.
        # It's used only when get_pos() cannot be used or is
        # unreliable for some reason.
        self.play_time = 0
        self.play_start_time = 0
        self.play_frame = 0

        # self.play_start_time is valid while State == STATE_PLAYING; it
        # indicates the get_ticks() value at which the song started
        # (adjusted for any pause intervals that occurred during
        # play).  self.play_time is valid while State != STATE_PLAYING;
        # it indicates the total number of ticks (milliseconds) that
        # have elapsed in the song so far.

        # self.play_frame starts at 0 and increments once for each
        # frame.  It's not very meaningful, except in STATE_CAPTURING
        # mode.

        # Keep track of the set of modifier buttons that are held
        # down.  This is currently used only for the GP2X interface.
        self.shoulder_l_held = False
        self.shoulder_r_held = False

        # Set this true if the player can zoom font sizes.
        self.supports_font_zoom = False

    # The following methods are part of the public API and intended to
    # be exported from this class.

    def validate(self):
        """Returns True if the karaoke file appears to be playable
        and contains lyrics, or False otherwise."""

        return self.do_validate()

    def play(self):
        self.do_play()

        if manager.options.dump:
            self.setup_dump()
        else:
            self.play_start_time = pygame.time.get_ticks()
            self.state = STATE_PLAYING

    # pause the song - Use pause() again to unpause
    def pause(self):
        if self.state == STATE_PLAYING:
            self.do_pause()
            self.play_time = pygame.time.get_ticks() - self.play_start_time
            self.state = STATE_PAUSED
        elif self.state == STATE_PAUSED:
            self.do_unpause()
            self.play_start_time = pygame.time.get_ticks() - self.play_time
            self.state = STATE_PLAYING

    # close the whole thing down
    def close(self):
        self.state = STATE_CLOSING

    # you must call play() to restart. Blocks until pygame is initialised
    def rewind(self):
        self.do_rewind()
        self.play_time = 0
        self.play_start_time = 0
        self.play_frame = 0
        self.state = STATE_NOT_PLAYING

    # stop the song and go back to the start. As you would
    # expect stop to do on a CD player. play() restarts from
    # the beginning
    def stop(self):
        self.rewind()

    # Get the song length (in seconds)
    def get_length(self):
        error_string = "get_length() not supported"
        self.error_notify_callback(error_string)
        return None

    # Get the current time (in milliseconds).
    def get_pos(self):
        if self.state == STATE_PLAYING:
            return pygame.time.get_ticks() - self.play_start_time
        else:
            return self.play_time

    def setup_options(self, usage=None):
        """Initialise and return optparse OptionParser object,
        suitable for parsing the command line options to this
        application."""

        if usage is None:
            usage = "%prog [options] <Karaoke file>"

        return manager.setup_options(usage, self.song_db)

    # Below methods are internal.

    def setup_dump(self):
        # Capture the output as a sequence of numbered frame images.
        self.play_time = 0
        self.play_start_time = 0
        self.play_frame = 0
        self.state = STATE_CAPTURING

        self.dump_frame_rate = manager.options.dump_fps
        if not self.dump_frame_rate:
            raise ValueError("dump_fps must be specified for frame dumping")

        filename = manager.options.dump
        base, ext = os.path.splitext(filename)
        ext_lower = ext.lower()

        self.dump_encoder = None
        if ext_lower == ".mpg":
            # Use pymedia to convert frames to an mpeg2 stream
            # on-the-fly.
            import pymedia.video.vcodec as vcodec

            self.dump_file = open(filename, "wb")
            frame_rate = int(self.dump_frame_rate * 100 + 0.5)
            self.dump_frame_rate = float(frame_rate) / 100.0

            params = {
                "type": 0,
                "gop_size": 12,
                "frame_rate_base": 125,
                "max_b_frames": 0,
                "height": manager.options.size_y,
                "width": manager.options.size_x,
                "frame_rate": frame_rate,
                "deinterlace": 0,
                "bitrate": 9800000,
                "id": vcodec.getCodecID("mpeg2video"),
            }
            self.dump_encoder = vcodec.Encoder(params)
            return

        # Don't dump a video file; dump a sequence of frames instead.
        self.dump_ppm = ext_lower == ".ppm" or ext_lower == ".pnm"
        self.dump_append = False

        # Convert the filename to a pattern.
        if "#" in filename:
            hash_pos = filename.index("#")
            end = hash_pos
            while end < len(filename) and filename[end] == "#":
                end += 1
            count = end - hash_pos
            filename = filename[:hash_pos] + "%0" + str(count) + "d" + filename[end:]
        else:
            # There's no hash in the filename.
            if self.dump_ppm:
                # We can dump a series of frames all to the same file,
                # if we're dumping ppm frames.  Mjpegtools likes this.
                self.dump_append = True
                try:
                    os.remove(filename)
                except OSError:
                    pass
            else:
                # Implicitly append a frame number.
                filename = base + "%04d" + ext

        self.dump_filename = filename

    def do_frame_dump(self):
        if self.dump_encoder:
            import pymedia.video.vcodec as vcodec

            ss = pygame.image.tostring(manager.surface, "RGB")
            bmp_frame = vcodec.VFrame(
                vcodec.formats.PIX_FMT_RGB24, manager.surface.get_size(), (ss, None, None)
            )
            yuv_frame = bmp_frame.convert(vcodec.formats.PIX_FMT_YUV420P)
            d = self.dump_encoder.encode(yuv_frame)
            self.dump_file.write(d.data)
            return

        if self.dump_append:
            filename = self.dump_filename
        else:
            filename = self.dump_filename % self.play_frame
            print(filename)

        if self.dump_ppm:
            # Dump a PPM file.  We do PPM by hand since pygame
            # doesn't support it directly, but it's so easy and
            # useful.

            w, h = manager.surface.get_size()
            if self.dump_append:
                f = open(filename, "ab")
            else:
                f = open(filename, "wb")
            f.write("P6\n%s %s 255\n" % (w, h))
            f.write(pygame.image.tostring(manager.surface, "RGB"))

        else:
            # Ask pygame to dump the file.  We trust that pygame knows
            # how to store an image in the requested format.
            pygame.image.save(manager.surface, filename)

    def do_validate(self):
        return True

    def do_play(self):
        # Abstract method - subclasses implement actual playback logic
        pass

    def do_pause(self):
        # Abstract method - subclasses implement pause functionality
        pass

    def do_unpause(self):
        # Abstract method - subclasses implement resume from pause
        pass

    def do_rewind(self):
        # Abstract method - subclasses implement rewind to beginning
        pass

    def do_stuff(self):
        # Override this in a derived class to do some useful per-frame
        # activity.
        # Common handling code for a close request or if the
        # pygame window was quit
        if self.state == STATE_CLOSING:
            if manager.display:
                manager.display.fill((0, 0, 0))
                pygame.display.flip()
            self.shutdown()

        elif self.state == STATE_CAPTURING:
            # We are capturing a video file.
            self.do_frame_dump()

            # Set the frame time for the next frame.
            self.play_time = 1000.0 * self.play_frame / self.dump_frame_rate

        self.play_frame += 1

    def do_resize(self, new_size):
        # This will be called internally whenever the window is
        # resized for any reason, either due to an application resize
        # request being processed, or due to the user dragging the
        # window handles.
        pass

    def do_resize_begin(self):
        # This will be called internally before the screen is resized
        # by pykmanager and do_resize() is called. Not all players need
        # to do anything here.
        pass

    def do_resize_end(self):
        # This will be called internally after the screen is resized
        # by pykmanager and do_resize() is called. Not all players need
        # to do anything here.
        pass

    def handle_event(self, event):
        if event.type == pygame.USEREVENT:
            self.close()
        elif event.type == pygame.KEYDOWN:
            self._handle_key_down(event)
        elif event.type == pygame.QUIT:
            self.close()
        elif env == ENV_GP2X and event.type == pygame.JOYBUTTONDOWN:
            self._handle_joy_button_down(event)
        elif env == ENV_GP2X and event.type == pygame.JOYBUTTONUP:
            self._handle_joy_button_up(event)

    def _handle_key_down(self, event):
        """Handle keyboard events, extracted to reduce cognitive complexity."""
        if event.key == pygame.K_ESCAPE:
            self.close()
        elif event.key in (pygame.K_PAUSE, pygame.K_p):
            self.pause()
        elif event.key in (pygame.K_BACKSPACE, pygame.K_DELETE):
            self.rewind()
            self.play()
        elif self.state == STATE_PLAYING and event.mod & (pygame.KMOD_LCTRL | pygame.KMOD_RCTRL):
            self._handle_ctrl_arrow(event)

        if self.supports_font_zoom:
            self._handle_font_zoom_key(event)

    def _handle_ctrl_arrow(self, event):
        """Handle ctrl+arrow keys for sync delay adjustment."""
        if event.key == pygame.K_RIGHT:
            manager.settings.sync_delay_ms += 250
            print(_SYNC_MSG % manager.settings.sync_delay_ms)
        elif event.key == pygame.K_LEFT:
            manager.settings.sync_delay_ms -= 250
            print(_SYNC_MSG % manager.settings.sync_delay_ms)
        elif event.key == pygame.K_DOWN:
            manager.settings.sync_delay_ms = 0
            print(_SYNC_MSG % manager.settings.sync_delay_ms)

    def _handle_font_zoom_key(self, event):
        """Handle font zoom keyboard shortcuts."""
        if event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
            manager.zoom_font(1.0 / 0.9)
        elif event.key in (pygame.K_MINUS, pygame.K_UNDERSCORE, pygame.K_KP_MINUS):
            manager.zoom_font(0.9)

    def _handle_joy_button_down(self, event):
        """Handle GP2X joystick button down events."""
        if event.button == GP2X_BUTTON_SELECT:
            self.close()
        elif event.button == GP2X_BUTTON_START:
            self.pause()
        elif event.button == GP2X_BUTTON_L:
            self.shoulder_l_held = True
        elif event.button == GP2X_BUTTON_R:
            self.shoulder_r_held = True

        if self.supports_font_zoom and self.shoulder_l_held:
            if event.button == GP2X_BUTTON_RIGHT:
                manager.zoom_font(1.0 / 0.9)
            elif event.button == GP2X_BUTTON_LEFT:
                manager.zoom_font(0.9)

    def _handle_joy_button_up(self, event):
        """Handle GP2X joystick button up events."""
        if event.button == GP2X_BUTTON_L:
            self.shoulder_l_held = False
        elif event.button == GP2X_BUTTON_R:
            self.shoulder_r_held = False

    def shutdown(self):
        # This will be called by the pykManager to shut down the thing
        # immediately.

        # If the caller gave us a callback, let them know we're finished
        if self.state != STATE_CLOSED:
            self.state = STATE_CLOSED
            if self.song_finished_callback is not None:
                self.song_finished_callback()

    def __default_error_print(self, error_string):
        print(error_string)

    def find_pygame_font(self, font_data, font_size):
        """Returns a pygame.Font selected by this data."""
        if not font_data.size:
            # The font names a specific filename.
            filename = font_data.name
            if os.path.sep not in filename:
                filename = os.path.join(manager.FontPath, filename)
            return pygame.font.Font(filename, font_size)

        # The font names a system font.
        point_size = int(font_data.size * font_size / 10.0 + 0.5)
        return pygame.font.SysFont(
            font_data.name, point_size, bold=font_data.bold, italic=font_data.italic
        )
