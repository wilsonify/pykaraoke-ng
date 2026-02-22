#!/usr/bin/env python

# pympg - MPEG Karaoke Player
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

import shlex
import subprocess
import sys
import threading

import pygame

from pykaraoke.config.constants import (
    ENV_GP2X,
    ENV_POSIX,
    ENV_WINDOWS,
    STATE_CLOSED,
    STATE_CLOSING,
    STATE_INIT,
    STATE_NOT_PLAYING,
    STATE_PAUSED,
    STATE_PLAYING,
)
from pykaraoke.config.environment import env
from pykaraoke.core.manager import manager
from pykaraoke.core.player import PykPlayer

# OVERVIEW
#
# pympg is an MPEG player built using python. It was written for the
# PyKaraoke project but is in fact a general purpose MPEG player that
# could be used in other python projects requiring an MPEG player.
#
# The player uses the pygame library (www.pygame.org), and can therefore
# run on any operating system that runs pygame (currently Linux, Windows
# and OSX).
#
# You can use this file as a standalone player, or together with
# PyKaraoke. PyKaraoke provides a graphical user interface, playlists,
# searchable song database etc.
#
# For those writing a media player or similar project who would like
# MPG support, this module has been designed to be easily incorporated
# into such projects and is released under the LGPL.


# REQUIREMENTS
#
# pympg requires the following to be installed on your system:
# . Python (www.python.org)
# . Pygame (www.pygame.org)


# USAGE INSTRUCTIONS
#
# To start the player, pass the MPEG filename/path on the command line:
#       python pympg.py /songs/theboxer.mpg
#
# You can also incorporate a MPG player in your own projects by
# importing this module. The class MpgPlayer is exported by the
# module. You can import and start it as follows:
#   from pykaraoke.players import mpg
#   player = mpg.MpgPlayer("/songs/theboxer.mpg")
#   player.play()
# If you do this, you must also arrange to call manager.poll()
# from time to time, at least every 100 milliseconds or so, to allow
# the player to do its work.
#
# The class also exports Close(), Pause(), Rewind(), GetPos().
#
# There are two optional parameters to the initialiser, errorNotifyCallback
# and doneCallback:
#
# errorNotifyCallback, if provided, will be used to print out any error
# messages (e.g. song file not found). This allows the module to fit
# together well with GUI playlist managers by utilising the same GUI's
# error popup window mechanism (or similar). If no callback is provided,
# errors are printed to stdout. errorNotifyCallback should take one
# parameter, the error string, e.g.:
#   def errorPopup (ErrorString):
#       msgBox (ErrorString)
#
# doneCallback can be used to register a callback so that the player
# calls you back when the song is finished playing. The callback should
# take no parameters, e.g.:
#   def songFinishedCallback():
#       msgBox ("Song is finished")
#
# To register callbacks, pass the functions in to the initialiser:
#   MpgPlayer ("/songs/theboxer.mpg", errorPopup, songFinishedCallback)
# These parameters are optional and default to None.
#
# If the initialiser fails (e.g. the song file is not present), __init__
# raises an exception.


# IMPLEMENTATION DETAILS
#
# pympg is implemented as a handful of python modules. Pygame provides
# all of the MPEG decoding and display capabilities, and can play an
# MPEG file with just a few lines of code. Hence this module is rather
# small. What it provides on top of the basic pygame features, is a
# player-like class interface with Play, Pause, Rewind etc. It also
# implements a resizable player window.  And, of course, it integrates
# nicely with pykaraoke.py and pykaraoke_mini.py.
#
# Previous implementations ran the player within a thread; this is no
# longer the case.  Instead, it is the caller's responsibility to call
# pycdg.manager.poll() every once in a while to ensure that the player
# gets enough CPU time to do its work.  Ideally, this should be at
# least every 100 milliseconds or so to guarantee good video and audio
# response time.

# Display depth (bits)
DISPLAY_DEPTH = 32

# Check to see if the movie module is available.
try:
    import pygame.movie as movie
except ImportError:
    movie = None


# MpgPlayer Class
class MpgPlayer(PykPlayer):
    # Initialise the player instace
    def __init__(self, song, song_db, error_notify_callback=None, done_callback=None):
        """The first parameter, song, may be either a pykdb.SongStruct
        instance, or it may be a filename."""

        PykPlayer.__init__(self, song, song_db, error_notify_callback, done_callback)

        self.Movie = None

        manager.set_cpu_speed("mpg")

        manager.init_player(self)
        manager.open_display(depth=DISPLAY_DEPTH)

        # Close the mixer while using Movie
        manager.close_audio()

        # Open the Movie module
        filepath = self.song_datas[0].get_filepath()
        if isinstance(filepath, str):
            filepath = filepath.encode(sys.getfilesystemencoding())
        self.Movie = pygame.movie.Movie(filepath)
        self.Movie.set_display(
            manager.display, (0, 0, manager.displaySize[0], manager.displaySize[1])
        )

    def do_play(self):
        self.Movie.play()

    def do_pause(self):
        self.Movie.pause()

    def do_unpause(self):
        self.Movie.play()

    def do_rewind(self):
        self.Movie.stop()
        self.Movie.rewind()

    # Get the movie length (in seconds).
    def get_length(self):
        return self.Movie.get_length()

    # Get the current time (in milliseconds).
    def get_pos(self):
        return self.Movie.get_time() * 1000

    def setup_options(self, usage=None):
        """Initialise and return optparse OptionParser object,
        suitable for parsing the command line options to this
        application."""

        if usage is None:
            usage = "%prog [options] <mpg filename>"
        parser = PykPlayer.setup_options(self, usage=usage)

        # Remove irrelevant options.
        parser.remove_option("--font-scale")

        return parser

    def shutdown(self):
        # This will be called by the pykManager to shut down the thing
        # immediately.
        if self.Movie:
            self.Movie.stop()
        # Must remove the object before using pygame.mixer module again
        self.Movie = None
        PykPlayer.shutdown(self)

    def handle_event(self, event):
        if (
            event.type == pygame.KEYDOWN
            and event.key == pygame.K_RETURN
            and (
                event.mod
                & (pygame.KMOD_LSHIFT | pygame.KMOD_RSHIFT | pygame.KMOD_LMETA | pygame.KMOD_RMETA)
            )
        ):
            # Shift/meta return: start/stop song.  Useful for keybinding apps.
            self.close()
            return

        PykPlayer.handle_event(self, event)

    # Internal. Only called by the pykManager.
    def do_resize(self, new_size):
        # Resize the screen.
        self.Movie.set_display(
            manager.display, (0, 0, manager.displaySize[0], manager.displaySize[1])
        )

    # Internal. Only called by the pykManager.
    def do_resize_begin(self):
        # The Movie player must be paused while resizing otherwise we
        # get Xlib errors. pykmanager will call here before the resize
        # so that we can do it.
        if self.State == STATE_PLAYING:
            self.Movie.pause()

    # Internal. Only called by the pykManager.
    def do_resize_end(self):
        # Called by pykmanager when resizing has finished.
        # We only play if it was playing in the first place.
        if self.State == STATE_PLAYING:
            self.Movie.play()


class ExternalPlayer(PykPlayer):
    """This class is used to invoke an external command and wait for
    it to finish.  It is usually used to play a video file using an
    external player."""

    def __init__(self, song, song_db, error_notify_callback=None, done_callback=None):
        """The first parameter, song, may be either a pykdb.SongStruct
        instance, or it may be a filename."""

        PykPlayer.__init__(self, song, song_db, error_notify_callback, done_callback)

        self.Movie = None

        manager.set_cpu_speed("mpg")
        manager.init_player(self)

        # Close the audio and the display
        manager.close_audio()
        manager.close_display()
        manager.close_cpu_control()

        self.procReturnCode = None
        self.proc = None

    def do_play(self):
        if self.procReturnCode is not None:
            # The movie is done.
            self.__stop()

        if not self.proc:
            self.__start()

    def get_length(self):
        # We cannot fetch the length from arbitrary external players.
        # Return zero-length.
        return 0

    def get_pos(self):
        # Use the default GetPos() which simply checks the time
        # since we started playing. This does not take account
        # for any fast-forward/rewind that may occur in the
        # external player, but we cannot support getting the
        # song position from arbitrary user-supplied players.
        return PykPlayer.get_pos(self)

    def do_stuff(self):
        if self.procReturnCode is not None:
            # The movie is done.
            self.__stop()
            self.close()

        PykPlayer.do_stuff(self)

    def __start(self):
        filepath = self.song_datas[0].get_filepath()

        external = manager.settings.MpgExternal
        if "%" in external:
            # Assume the filename parameter is embedded in the string.
            # Parse the command string into a list to avoid shell injection
            cmd_str = external % {
                "file": filepath,
            }
            # Split the command string into a list for safe subprocess execution
            cmd = shlex.split(cmd_str)

        elif external:
            # No parameter appears to be present; assume the program
            # accepts the filename as the only parameter.
            cmd = [external, filepath]

        # Security: Never use shell=True to prevent command injection (CWE-78)
        # Always pass cmd as a list to subprocess.Popen for safe execution
        if self.procReturnCode is not None:
            raise RuntimeError("Process already running")
        sys.stdout.flush()
        self.proc = subprocess.Popen(cmd, shell=False)
        if manager.settings.MpgExternalThreaded:
            # Wait for it to complete in a thread.
            self.thread = threading.Thread(target=self.__runThread)
            self.thread.start()
        else:
            # Don't wait for it in a thread; wait for it here.
            self.thread = None
            self.__runThread()

    def __stop(self):
        if self.thread:
            self.thread.join()
        self.proc = None
        self.procReturnCode = None
        self.thread = None

    def __runThread(self):
        """This method runs in a sub-thread.  Its job is just to wait
        for the process to finish."""

        try:
            self.procReturnCode = self.proc.wait()
        except OSError:
            self.procReturnCode = -1


# Can be called from the command line with the MPG filepath as parameter
def main():
    player = MpgPlayer(None, None)
    player.play()
    manager.wait_for_player()


if __name__ == "__main__":
    sys.exit(main())
