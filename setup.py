#!/usr/bin/env python
# ******************************************************************************
# ****                                                                      ****
# **** Copyright (C) 2010  Kelvin Lawson (kelvinl@users.sourceforge.net)    ****
# **** Copyright (C) 2010  PyKaraoke Development Team                       ****
# ****                                                                      ****
# **** This library is free software; you can redistribute it and/or        ****
# **** modify it under the terms of the GNU Lesser General Public           ****
# **** License as published by the Free Software Foundation; either         ****
# **** version 2.1 of the License, or (at your option) any later version.   ****
# ****                                                                      ****
# **** This library is distributed in the hope that it will be useful,      ****
# **** but WITHOUT ANY WARRANTY; without even the implied warranty of       ****
# **** MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU    ****
# **** Lesser General Public License for more details.                      ****
# ****                                                                      ****
# **** You should have received a copy of the GNU Lesser General Public     ****
# **** License along with this library; if not, write to the                ****
# **** Free Software Foundation, Inc.                                       ****
# **** 59 Temple Place, Suite 330                                           ****
# **** Boston, MA  02111-1307  USA                                          ****
# ******************************************************************************

import glob
import sys
from distutils.command.build_ext import build_ext
from distutils.core import Extension, setup

import wxversion

import pykversion
from pykenv import *

wxversion.ensureMinimal("2.6")

# These are the data files that should be installed for all systems,
# including Windows.

data_files = [
    (
        "share/pykaraoke/icons",
        [
            "icons/audio_16.png",
            "icons/folder_close_16.png",
            "icons/folder_open_16.png",
            "icons/microphone.ico",
            "icons/microphone.png",
            "icons/pykaraoke.xpm",
            "icons/splash.png",
        ],
    ),
    (
        "share/pykaraoke/fonts",
        [
            "fonts/DejaVuSans.ttf",
            "fonts/DejaVuSansCondensed.ttf",
            "fonts/DejaVuSansCondensed-Bold.ttf",
        ],
    ),
]

# These data files only make sense on Unix-like systems.
if env != ENV_WINDOWS:
    data_files += [
        (
            "bin",
            [
                "install/pykaraoke",
                "install/pykaraoke_mini",
                "install/pycdg",
                "install/pykar",
                "install/pympg",
                "install/cdg2mpg",
            ],
        ),
        ("share/applications", ["install/pykaraoke.desktop", "install/pykaraoke_mini.desktop"]),
    ]

# These are the basic keyword arguments we will pass to distutil's
# setup() function.
cmdclass = {}
setupArgs = {
    "name": "pykaraoke",
    "version": pykversion.PYKARAOKE_VERSION_STRING,
    "description": "PyKaraoke = CD+G/MPEG/KAR Karaoke Player",
    "maintainer": "Kelvin Lawson",
    "maintainer_email": "kelvin@kibosh.org",
    "url": "https://www.kibosh.org/pykaraoke",
    "license": "LGPL",
    "long_description": "PyKaraoke - CD+G/MPEG/KAR Karaoke Player",
    "py_modules": [
        "pycdgAux",
        "pycdg",
        "pykaraoke_mini",
        "pykaraoke",
        "pykar",
        "pykconstants",
        "pykdb",
        "pykenv",
        "pykmanager",
        "pykplayer",
        "pykversion",
        "pympg",
        "performer_prompt",
    ],
    "ext_modules": [Extension("_pycdgAux", ["_pycdgAux.c"], libraries=["SDL"])],
    "data_files": data_files,
    "cmdclass": cmdclass,
    "classifiers": [
        "Development Status :: 5 - Production/Stable",
        "Environment :: X11 Applications",
        "Environment :: Win32 (MS Windows)",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX",
        "Programming Language :: Python",
        "Topic :: Games/Entertainment",
        "Topic :: Multimedia :: Sound/Audio :: Players",
    ],
}


# Let's extend build_ext so we can allow the user to specify
# explicitly the location of the SDL installation (or we can try to
# guess where it might be.)
class my_build_ext(build_ext):
    user_options = build_ext.user_options
    user_options += [
        (
            "sdl-location=",
            None,
            "Specify the path to the SDL source directory, assuming sdl_location/include and sdl_location/lib exist beneath that.  (Otherwise, use --include-dirs and --library-dirs.)",
        ),
    ]

    def initialize_options(self):
        build_ext.initialize_options(self)
        self.sdl_location = None

    def finalize_options(self):
        build_ext.finalize_options(self)
        if self.sdl_location is None:
            # The default SDL location.  This is useful only if your
            # SDL source is installed under a common root, with
            # sdl_loc/include and sdl_loc/lib directories beneath that
            # root.  This is the standard way that SDL is distributed
            # on Windows, but not on Unix.  For a different
            # configuration, just specify --include-dirs and
            # --library-dirs separately.

            if env == ENV_WINDOWS:
                # For a default location on Windows, look around for SDL
                # in the current directory.
                sdl_dirs = glob.glob("SDL*")

                # Sort them in order, so that the highest-numbered version
                # will (probably) fall to the end.
                sdl_dirs.sort()

                for dir in sdl_dirs:
                    if os.path.isdir(os.path.join(dir, "include")):
                        self.sdl_location = dir

        if self.sdl_location is not None:
            # Now append the system paths.
            self.include_dirs.append(os.path.join(self.sdl_location, "include"))
            self.library_dirs.append(os.path.join(self.sdl_location, "lib"))

            # Also put the lib dir on the PATH, so Windows can find SDL.dll.
            if env == ENV_WINDOWS:
                libdir = os.path.join(self.sdl_location, "lib")
                os.environ["PATH"] = "%s;%s" % (libdir, os.environ["PATH"])


cmdclass["build_ext"] = my_build_ext

setup(**setupArgs)
