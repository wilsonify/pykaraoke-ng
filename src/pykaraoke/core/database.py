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

"""This module provides support for the PyKaraoke song database, as
well as the user's settings file."""

import os
import sys
import time
import zipfile

import pickle
import pygame
from io import BytesIO

from pykaraoke.players import cdg
from pykaraoke.players import kar
from pykaraoke.players import mpg
from pykaraoke.config.constants import (
    ENV_GP2X,
    ENV_WINDOWS,
    STATE_NOT_PLAYING,
)
from pykaraoke.config.environment import env

from hashlib import sha256  # Use SHA-256 instead of MD5 for file hashing (security)

from pykaraoke.core.filename_parser import FileNameType, FilenameParser

# The amount of time to wait, in milliseconds, before yielding to the
# app for windowing updates during a long update process.
YIELD_INTERVAL = 1000

# The maximum number of zip files we will attempt to store in our zip
# file cache.
MAX_ZIP_FILES = 10

# Increment this version number whenever the settings version changes
# (which may not necessarily change with each PyKaraoke release).
# This will force users to re-enter their configuration information.
SETTINGS_VERSION = 6

# Increment this version number whenever the database version changes
# (which will also hopefully be infrequently).
DATABASE_VERSION = 2

# Error message constants (avoiding literal duplication)
_ERR_INVALID_FILE_TYPE = "Invalid type for file: %s!"
_ERR_INVALID_FILENAME_TYPE = "File name type is invalid!"
_TITLES_FILENAME = "titles.txt"


class AppYielder:
    """This is a simple class that knows how to yield control to the
    windowing system every once in a while.  It is passed to functions
    like SearchDatabase and BuildSearchDatabase--tasks which might
    take a while to perform.

    This class is just an abstract base class and does nothing.  Apps
    should subclass it and override do_yield() to make any use from
    it."""

    def __init__(self):
        self.last_yield = pygame.time.get_ticks()

    def consider_yield(self):
        now = pygame.time.get_ticks()
        if now - self.last_yield >= YIELD_INTERVAL:
            self.do_yield()
            self.last_yield = now

    def do_yield(self):
        """Override this method to actually yield control to the
        windowing system."""
        pass


class BusyCancelDialog:
    """This class implements a busy dialog to show a task is
    progressing, and it includes a cancel button the user might click
    on to interrupt the task.  This is just an abstract base class and
    does nothing.  Apps should subclass from it."""

    def __init__(self):
        self.clicked = False

    def show(self):
        # Abstract method - subclasses should override to display the dialog
        pass

    def set_progress(self, label, progress):
        # Abstract method - subclasses should override to update progress display
        pass

    def destroy(self):
        # Abstract method - subclasses should override to clean up dialog resources
        pass


class SongData:
    """This class is returned by SongStruct.get_song_datas(), below.  It
    represents either a song file that exists on disk (and must still
    be read), or it is a song file that was found in a zip archive
    (and its data is available now)."""

    def __init__(self, filename, data):
        self.filename = filename
        self.temp_filename = None
        self.data = data
        self.ext = os.path.splitext(filename)[1].lower()

        # By convention, if data is passed as None to the constructor,
        # that means this file is a true file that exists on disk.  On
        # the other hand, if data is not None, then this is not a true
        # file, and data contains its contents.
        self.trueFile = data is None

    def get_data(self):
        """Returns the actual data of the file.  If the file has not
        yet been read, this will read it and return the data."""

        if self.data is not None:
            # The file has already been read; return that data.
            return self.data

        # The file has not yet been read
        with open(self.filename, "rb") as f:
            self.data = f.read()
        return self.data

    def get_filepath(self):
        """Returns a full pathname to the file.  If the file does not
        exist on disk, this will write it to a temporary file and
        return the name of that file."""

        if self.trueFile:
            # The file exists on disk already; just return its
            # pathname.
            return self.filename

        if not self.temp_filename:
            # The file does not exist on disk already; we have to write it
            # to a temporary file.
            prefix = globalSongDB.create_temp_file_name_prefix()
            basename = os.path.basename(self.filename)
            # Add the tempfile prefix as well as the time to make the
            # filename unique. This works around a bug
            # in pygame.mixer.music on Windows which stops us deleting
            # temp files until another song is loaded, preventing the
            # same song from being played twice in a row.
            self.temp_filename = prefix + str(time.time()) + basename
            with open(self.temp_filename, "wb") as f:
                f.write(self.data)

        return self.temp_filename


# This functor is declared globally.  It is assigned by
# SongDB.SelectSort(), so we can use bisect to search through
# the list also.  This is an ugly hack around the fact that bisect has
# no facility to receive a key parameter, like sort does.
file_sort_key = None


class SongStruct:
    """This corresponds to a single song file entry, e.g. a .kar
    file, or a .mp3/.cdg filename pair.  The file might correspond to
    a physical file on disk, or to a file within a zip file."""

    # Type codes.
    T_KAR = 0
    T_CDG = 1
    T_MPG = 2

    def __init__(
        self, filepath, settings, title=None, artist=None, zip_stored_name=None, database_add=False
    ):
        self.Filepath = filepath  # Full path to file or ZIP file
        self.ZipStoredName = zip_stored_name  # Filename stored in ZIP

        # Assume there will be no title/artist info found
        self.Title = title or ""  # (optional) Title for display in playlist
        self.Artist = artist or ""  # (optional) Artist for display
        self.Disc = ""  # (optional) Disc for display
        self.Track = -1  # (optional) Track for display

        # Check to see if we are deriving song information from the filename
        self._deriveSongInfo(filepath, settings, zip_stored_name, database_add)

        # This is a list of other song files that share the same
        # artist and title data.
        self.sameSongs = []

        # This is a pointer to the TitleStruct object that defined
        # this song file, or None if it was not defined.
        self.titles = None

        # If the file ends in '.', assume we got it via tab-completion
        # on a filename, and it really is meant to end in '.cdg'.
        if self.Filepath != "" and self.Filepath[-1] == ".":
            self.Filepath += "cdg"

        self._resolveDisplayFilename(filepath, settings, zip_stored_name)
        self._resolveType(settings)

    def _deriveSongInfo(self, filepath, settings, zip_stored_name, database_add):
        """Derive title/artist/disc/track from the filename if configured."""
        if not settings.CdgDeriveSongInformation:
            return
        try:
            _parser = FilenameParser(
                file_name_type=FileNameType(settings.CdgFileNameType)
            )
            # When the song lives inside a ZIP, use the inner member
            # path for parsing (directory structure can provide the artist).
            if zip_stored_name:
                _parsed = _parser.parse_zip_path(zip_stored_name)
            else:
                _parsed = _parser.parse(filepath)
            # An empty artist means the filename did not match the
            # configured naming scheme (equivalent to the legacy KeyError).
            if not _parsed.artist:
                raise KeyError(f"Could not parse filename: {filepath}")
            self.Title = _parsed.title
            self.Artist = _parsed.artist
            self.Disc = _parsed.disc
            self.Track = _parsed.track
        except (ValueError, KeyError, IndexError):
            self.Title = os.path.basename(filepath)
            if database_add and settings.ExcludeNonMatchingFilenames:
                raise KeyError("Excluding non-matching file: %s" % self.Title) from None

    def _resolveDisplayFilename(self, filepath, settings, zip_stored_name):
        """Set DisplayFilename from the zip member name or the file path."""
        if zip_stored_name:
            self.DisplayFilename = os.path.basename(zip_stored_name)
            if isinstance(self.DisplayFilename, bytes):
                self.DisplayFilename = self.DisplayFilename.decode(settings.ZipfileCoding)
        else:
            self.DisplayFilename = os.path.basename(filepath)
            if isinstance(self.DisplayFilename, bytes):
                self.DisplayFilename = self.DisplayFilename.decode(settings.FilesystemCoding)

    def _resolveType(self, settings):
        """Determine the song type (KAR, CDG, MPG) from the file extension."""
        self.Type = None
        ext = os.path.splitext(self.DisplayFilename)[1].lower()
        if ext in settings.KarExtensions:
            self.Type = self.T_KAR
        elif ext in settings.CdgExtensions:
            self.Type = self.T_CDG
        elif ext in settings.MpgExtensions:
            self.Type = self.T_MPG
            if ext == ".mpg" or ext == ".mpeg":
                self.MpgType = "mpg"
            else:
                self.MpgType = ext[1:]

    def parse_title(self, filepath, settings):
        """Parses the file path and returns the title of the song. If the filepath cannot be parsed a KeyError exception is thrown. If the settings contains a file naming scheme that we do not support a KeyError exception is thrown."""
        if not settings.CdgDeriveSongInformation:
            return ""

        # Mapping: file_name_type -> (expected_parts, title_index)
        _type_config = {0: (4, 3), 1: (3, 2), 2: (3, 2), 3: (2, 1)}
        config = _type_config.get(settings.CdgFileNameType)
        if config is None:
            raise KeyError(_ERR_INVALID_FILENAME_TYPE)

        expected_parts, title_index = config
        parts = filepath.split("-")
        if len(parts) != expected_parts:
            raise KeyError(_ERR_INVALID_FILE_TYPE % filepath)

        title = parts[title_index].strip()
        return os.path.splitext(title)[0]

    def parse_artist(self, filepath, settings):
        """Parses the filepath and returns the artist of the song."""
        if not settings.CdgDeriveSongInformation:
            return ""

        _artist_index = {0: 2, 1: 1, 2: 1, 3: 0}
        index = _artist_index.get(settings.CdgFileNameType)
        if index is None:
            raise KeyError(_ERR_INVALID_FILENAME_TYPE)

        artist = filepath.split("-")[index]
        if settings.CdgFileNameType == 3:
            artist = os.path.basename(artist)
        return artist.strip()

    def parse_disc(self, filepath, settings):
        """Parses the filepath and returns the disc name of the song."""
        if not settings.CdgDeriveSongInformation:
            return ""

        if settings.CdgFileNameType == 0:  # Disc-Track-Artist-Title.Ext
            disc = filepath.split("-")[0]
        elif settings.CdgFileNameType == 1:  # DiscTrack-Artist-Title.Ext
            disc = filepath[: len(filepath) - 2]
        elif settings.CdgFileNameType == 2:  # Disc-Artist-Title.Ext
            disc = filepath.split("-")[0]
        elif settings.CdgFileNameType == 3:  # Artist-Title.Ext
            return ""
        else:
            raise KeyError(_ERR_INVALID_FILENAME_TYPE)

        return os.path.basename(disc.strip())

    def parse_track(self, filepath, settings):
        """Parses the file path and returns the track for the song."""
        if not settings.CdgDeriveSongInformation:
            return ""

        if settings.CdgFileNameType == 0:  # Disc-Track-Artist-Title.Ext
            return filepath.split("-")[1]
        if settings.CdgFileNameType == 1:  # DiscTrack-Artist-Title.Ext
            return filepath[-2:]
        if settings.CdgFileNameType in (2, 3):  # Disc-Artist-Title or Artist-Title
            return ""
        raise KeyError(_ERR_INVALID_FILENAME_TYPE)

    def make_sort_key(self, text):
        """Returns a suitable key to use for sorting, by lowercasing
        and removing articles from the indicated string."""
        text = text.strip().lower()
        if text:
            # Remove a leading parenthetical phrase.
            if text[0] == "(":
                rparen = text.index(")")
                if rparen != ")":
                    text = text[rparen + 1 :].strip()

        if text:
            # Remove a leading article.
            first_word = text.split()[0]
            if first_word in ["a", "an", "the"]:
                text = text[len(first_word) :].strip()

        return text

    def make_player(self, song_db, error_notify_callback, done_callback):
        """Creates and returns a player of the appropriate type to
        play this file, if possible; or returns None if the file
        cannot be played (in which case, the error_notify_callback will
        have already been called with the error message)."""

        settings = song_db.Settings
        constructor = None

        if self.Type == self.T_CDG:
            constructor = cdg.CdgPlayer
        elif self.Type == self.T_KAR:
            constructor = kar.MidPlayer
        elif self.Type == self.T_MPG:
            if self.MpgType == "mpg" and settings.MpgNative and mpg.movie:
                # Mpg files can be played internally.
                constructor = mpg.MpgPlayer
            else:
                # Other kinds of movies require an external player.
                constructor = mpg.ExternalPlayer
        else:
            ext = os.path.splitext(self.DisplayFilename)[1]
            error_notify_callback("Unsupported file format " + ext)
            return None

        # Try to open the song file.
        try:
            player = constructor(self, song_db, error_notify_callback, done_callback)
        except (RuntimeError, OSError, ImportError) as e:
            error_notify_callback(
                "Error opening file.\n%s\n%s" % (type(e).__name__, str(e))
            )
            return None

        return player

    def get_song_datas(self):
        """Returns a list of SongData objects; see SongData.

        Usually there is only one element in the list: the file named
        by this SongStruct.  In the case of .cdg files, however, there
        may be more tuples; the first tuple will be the file named by
        this SongStruct, and the remaining tuples will correspond to
        other files with the same basenames but different extensions
        (so that the .mp3 or .ogg associated with a cdg file may be
        recovered)."""

        song_datas = []

        if not self.Filepath:
            return song_datas

        if not os.path.exists(self.Filepath):
            error = "No such file: %s" % (self.Filepath)
            raise ValueError(error)

        directory = os.path.dirname(self.Filepath) or "."
        root, _ = os.path.splitext(self.Filepath)
        prefix = os.path.basename(root + ".")

        if self.ZipStoredName:
            song_datas = self._get_song_datas_from_zip(prefix, song_datas)
        else:
            song_datas.append(SongData(self.Filepath, None))

        if self.Type == self.T_CDG:
            self._findMatchingCdgFiles(directory, prefix, song_datas)

        return song_datas

    def _get_song_datas_from_zip(self, prefix, song_datas):
        """Extract song data files from a ZIP archive."""
        zf = globalSongDB.get_zip_file(self.Filepath)
        filelist = [self.ZipStoredName]

        root, ext = os.path.splitext(self.ZipStoredName)
        root, ext = os.path.splitext(self.ZipStoredName)
        zip_prefix = os.path.basename(root + ".")
        prefix = zip_prefix or prefix

        if self.Type == self.T_CDG:
            for name in zf.namelist():
                if name != self.ZipStoredName and name.startswith(prefix):
                    filelist.append(name)

        for file in filelist:
            try:
                data = zf.read(file)
                song_datas.append(SongData(file, data))
            except (KeyError, zipfile.BadZipFile):
                print("Error in ZIP containing ")
        return song_datas

    @staticmethod
    def _decodeByteString(value):
        """Decode a byte-string to str, replacing invalid characters."""
        if isinstance(value, bytes):
            try:
                return value.decode("utf-8")
            except UnicodeDecodeError:
                return value.decode("ascii", "replace")
        return value

    def _findMatchingCdgFiles(self, directory, prefix, song_datas):
        """Find loose files on disk matching the CDG file's basename."""
        for file in os.listdir(directory):
            file = self._decodeByteString(file)
            prefix = self._decodeByteString(prefix)
            if file.startswith(prefix):
                path = os.path.join(directory, file)
                if path != self.Filepath:
                    song_datas.append(SongData(path, None))

    def get_text_colour(self, selected):
        """Returns a suitable colour to use when rendering the text
        of this song line in the pykaraoke_mini song index."""

        if selected:
            fg = (255, 255, 255)

        else:
            # Determine the color of the text.
            fg = (180, 180, 180)
            if self.Type == self.T_KAR:
                # Midi file: color it red.
                fg = (180, 72, 72)

            elif self.Type == self.T_CDG:
                # CDG+MP3: color it blue.
                fg = (72, 72, 180)

            elif self.Type == self.T_MPG:
                # MPEG file: color it yellow.
                fg = (180, 180, 72)

        return fg

    def get_background_colour(self, selected):
        """Returns a suitable colour to use when rendering the
        background of this song line in the pykaraoke_mini song
        index."""

        if not selected:
            bg = (0, 0, 0)

        else:
            if self.Type == self.T_KAR:
                # Midi file: color it red.
                bg = (120, 0, 0)

            elif self.Type == self.T_CDG:
                # CDG+MP3: color it blue.
                bg = (0, 0, 120)

            elif self.Type == self.T_MPG:
                # MPEG file: color it yellow.
                bg = (120, 120, 0)

        return bg

    def get_display_filenames(self):
        """Returns the list of all of the filenames that share the
        same artist/title with this song file.  The list is formatted
        as a single comma-delimited string."""

        if self.sameSongs:
            return ", ".join(f.DisplayFilename for f in self.sameSongs)
        return self.DisplayFilename

    def get_type_sort(self):
        """Defines a sorting order by type, for sorting the sameSongs
        list."""

        # We negate self.Type, so that the sort order is: mpg, cdg,
        # kar.  This means that MPG files have priority over CDG which
        # have priority over KAR, for the purposes of coloring the
        # files in the mini index.
        return (-self.Type, self.DisplayFilename)

    def get_mark_key(self):
        """Returns a key for indexing into markedSongs, for uniquely
        identifying this particular song file."""
        return (self.Filepath, self.ZipStoredName)

    def __lt__(self, other):
        """Define a sorting order between SongStruct objects.  This is
        used in bisect, to quickly search for a SongStruct in a sorted
        list.  It relies on file_sort_key (above) having being filled in
        already."""
        global file_sort_key

        a = file_sort_key(self)
        b = file_sort_key(other)
        if a == b:
            return id(self) < id(other)
        return a < b

    def __eq__(self, other):
        """Define equality between SongStruct objects based on sort key."""
        global file_sort_key
        return file_sort_key(self) == file_sort_key(other) and id(self) == id(other)


class TitleStruct:
    """This represents a single titles.txt file.  Its filename is
    preserved so it can be rewritten later, to modify a title and/or
    artist associated with a song."""

    def __init__(self, filepath, zip_stored_name=None):
        self.Filepath = filepath  # Full path to file or ZIP file
        self.ZipStoredName = zip_stored_name  # Filename stored in ZIP
        self.songs = []

        # This is false unless the titles file has been locally
        # modified and needs to be flushed.
        self.dirty = False

    def read(self, song_db):
        """Reads the titles.txt file, and stores the results in the
        indicated db.  This is intended to be called during db
        scan."""

        if self.ZipStoredName is not None:
            zf = song_db.get_zip_file(self.Filepath)
            unzipped_data = zf.read(self.ZipStoredName)
            sfile = BytesIO(unzipped_data)
            self.__read_titles(song_db, sfile, os.path.join(self.Filepath, self.ZipStoredName))
        else:
            self.__read_titles(song_db, None, self.Filepath)

    def rewrite(self, song_db):
        """Rewrites the titles.txt file with the current data."""
        if self.ZipStoredName is not None:
            sfile = BytesIO()
            self.__write_titles(song_db, sfile, os.path.join(self.Filepath, self.ZipStoredName))
            unzipped_data = sfile.getvalue()
            song_db.drop_zip_file(self.Filepath)
            zf = zipfile.ZipFile(self.Filepath, "a", zipfile.ZIP_DEFLATED)

            # Since the lame Python zipfile.py implementation won't
            # replace an existing file, we have to rename it out of
            # the way.
            self.__rename_zip_element(zf, self.ZipStoredName)

            zf.writestr(self.ZipStoredName, unzipped_data)
            zf.close()
        else:
            self.__write_titles(song_db, None, self.Filepath)

    def __rename_zip_element(self, zf, name1, name2=None):
        """Renames the file within the archive named "name1" to
        "name2".  To avoid major rewriting of the archive, it is
        required that len(name1) == len(name2).

        If name2 is omitted or None, a new, unique name is
        generated based on the old name.
        """

        zinfo = zf.getinfo(name1)
        zf._writecheck(zinfo)

        if name2 is None:
            # Replace the last letters with digits.
            i = 0
            n = str(i)
            name2 = name1[: -len(n)] + n
            while name2 in zf.NameToInfo:
                i += 1
                n = str(i)
                name2 = name1[: -len(n)] + n

        if len(name1) != len(name2):
            raise RuntimeError("Cannot change length of name with rename().")

        filepos = zf.fp.tell()

        zf.fp.seek(zinfo.header_offset + 30, 0)
        zf.fp.write(name2)
        zinfo.filename = name2

        zf.fp.seek(filepos, 0)

    def __read_titles(self, song_db, catalog_file, catalog_pathname):
        self.songs = []
        dirname = os.path.split(catalog_pathname)[0]

        should_close = False
        if catalog_file is None:
            # Open the file for reading in binary mode, since the
            # loop below calls .decode() on each line.
            try:
                catalog_file = open(catalog_pathname, "rb")
                should_close = True
            except (OSError, IOError):
                print("Could not open titles file %s" % (repr(catalog_pathname)))
                return

        try:
            for line in catalog_file:
                self.__process_title_line(line, catalog_pathname, dirname, song_db)
        finally:
            if should_close:
                catalog_file.close()

    def __process_title_line(self, line, catalog_pathname, dirname, song_db):
        """Parse a single line from a titles file and update the song database."""
        try:
            line = line.decode("utf-8").strip()
        except UnicodeDecodeError:
            line = line.decode("utf-8", "replace")
            print("Invalid characters in %s:\n%s" % (repr(catalog_pathname), line))

        if not line:
            return

        parts = line.split("\t")
        if len(parts) == 2:
            filename, title = parts
            artist = ""
        elif len(parts) == 3:
            filename, title, artist = parts
        else:
            print("Invalid line in %s:\n%s" % (repr(catalog_pathname), line))
            return

        # Allow a forward slash in the file to stand in for
        # whatever the OS's path separator is.
        filename = filename.replace("/", os.path.sep)

        pathname = os.path.join(dirname, filename)
        song = song_db.files_by_fullpath.get(pathname, None)
        if song is None:
            print("Unknown file in %s:\n%s" % (repr(catalog_pathname), repr(filename)))
            return

        song.titles = self
        self.songs.append(song)
        song.Title = title.strip()
        song.Artist = artist.strip()
        if song.Title:
            song_db.got_titles = True
        if song.Artist:
            song_db.got_artists = True

    def __make_rel_to(self, filename, rel_to):
        """Returns the filename expressed as a relative path to
        relTo.  Both file paths should be full paths; relTo should
        already have had normcase and normpath applied to it, and
        should end with a slash."""

        filename = os.path.normpath(filename)
        norm = os.path.normcase(filename)
        prefix = os.path.commonprefix((norm, rel_to))

        # The common prefix must end with a slash.
        slash = prefix.rfind(os.sep)
        if slash != -1:
            prefix = prefix[: slash + 1]

        filename = filename[len(prefix) :]
        rel_to = rel_to[len(prefix) :]

        num_slashes = rel_to.count(os.sep)
        if num_slashes > 1:
            backup = ".." + os.sep
            filename = backup * (num_slashes - 1) + filename

        return filename

    def __write_titles(self, song_db, catalog_file, catalog_pathname):
        _dirname = os.path.split(catalog_pathname)[0]

        if catalog_file is None:
            # Open the file for writing.
            try:
                catalog_file = open(catalog_pathname, "w")
            except (OSError, IOError):
                print("Could not rewrite titles file %s" % (repr(catalog_pathname)))
                return

        rel_to = os.path.normcase(os.path.normpath(catalog_pathname))
        if rel_to[-1] != os.sep:
            rel_to += os.sep

        for song in self.songs:
            filename = song.Filepath
            if song.ZipStoredName:
                filename = os.path.join(filename, song.ZipStoredName)

            filename = self.__make_rel_to(filename, rel_to)

            # Use forward slashes instead of the native separator, to
            # make a more platform-independent titles.txt file.
            filename = filename.replace(os.sep, "/")

            line = filename
            if song_db.got_titles or song_db.got_artists:
                line += "\t" + song.Title
            if song_db.got_artists:
                line += "\t" + song.Artist

            line = line.encode("utf-8")
            catalog_file.write(line + "\n")


class FontData:
    """This stores the font description selected by the user.
    Hopefully it is enough information to be used both in wx and in
    pygame to reference a unique font on the system."""

    def __init__(self, name=None, size=None, bold=False, italic=False):
        # name may be either a system font name (if size is not None) or a
        # filename (if size is None).
        self.name = name
        self.size = size
        self.bold = bold
        self.italic = italic

    def __repr__(self):
        if not self.size:
            return "FontData(%s)" % (repr(self.name))
        else:
            return "FontData(%s, %s, %s, %s)" % (
                repr(self.name),
                repr(self.size),
                repr(self.bold),
                repr(self.italic),
            )

    def get_description(self):
        desc = self.name
        if self.size:
            desc += ",%spt" % (self.size)
        if self.bold:
            desc += ",bold"
        if self.italic:
            desc += ",italic"

        return desc


# SettingsStruct used as storage only for settings. The instance
# can be pickled to save all user's settings.
class SettingsStruct:
    # This is the list of the encoding strings we offer the user to
    # select from.  You can also type your own.
    Encodings = [
        "cp1252",
        "iso-8859-1",
        "iso-8859-2",
        "iso-8859-5",
        "iso-8859-7",
        "utf-8",
    ]

    # This is the set of CDG zoom modes.
    Zoom = [
        "quick",
        "int",
        "full",
        "soft",
        "none",
    ]
    ZoomDesc = {
        "quick": "a pixelly scale, maintaining aspect ratio",
        "int": "like quick, reducing artifacts a little",
        "full": "like quick, but stretches to fill the entire window",
        "soft": "a high-quality scale, but may be slow on some hardware",
        "none": "keep the display in its original size",
    }

    # Some audio cards seem to support only a limited set of sample
    # rates.  Here are the suggested offerings.
    SampleRates = [
        48000,
        44100,
        22050,
        11025,
        5512,
    ]

    # A list of possible file name deriving combinations.
    # The combination order is stored and used in the parsing algorithm.
    # Track is assumed to be exactly 2 digits.
    FileNameCombinations = [
        "Disc-Track-Artist-Title",
        "DiscTrack-Artist-Title",
        "Disc-Artist-Title",
        "Artist-Title",
    ]

    def __init__(self):
        self.Version = SETTINGS_VERSION

        # Set the default settings, in case none are stored on disk
        self.folder_list = []
        self.CdgExtensions = [".cdg"]
        self.KarExtensions = [".kar", ".mid"]
        self.MpgExtensions = [".mpg", ".mpeg", ".avi", ".divx", ".xvid"]
        self.IgnoredExtensions = []
        self.look_inside_zips = True
        self.read_titles_txt = True
        self.CheckHashes = False
        self.DeleteIdentical = False
        if env == ENV_WINDOWS:
            self.FilesystemCoding = "cp1252"
        else:
            self.FilesystemCoding = "iso-8859-1"
        self.ZipfileCoding = "cp1252"

        self.WindowSize = (640, 480)  # Size of the window for PyKaraoke
        self.FullScreen = False  # Determines if the karaoke player should be full screen
        self.NoFrame = False  # Determies if the karaoke player should have a window frame.

        # SDL specific parameters; some settings may work better on
        # certain hardware than others
        self.DoubleBuf = True
        self.HardwareSurface = True

        self.PlayerSize = (640, 480)  # Size of the karaoke player
        self.PlayerPosition = None  # Initial position of the karaoke player

        self.SplitVertically = True
        self.AutoPlayList = True  # Enables or disables the auto play on the play-list
        self.DoubleClickPlayList = (
            True  # Enables or disables the double click for playing from the play-list
        )
        self.ClearFromPlayList = (
            True  # Enables or disables clearing the playlist with a right click on the play list
        )
        self.Kamikaze = False  # Enables or disables the kamikaze button
        self.UsePerformerName = False  # Enables or disables the prompting for a performers name.
        self.PlayFromSearchList = (
            True  # Enables or disables the playing of a song from the search list
        )
        self.DisplayArtistTitleCols = False  # Enables or disables display of artist/title columns

        self.SampleRate = 44100
        self.NumChannels = 2
        self.BufferMs = 50
        self.UseMp3Settings = True

        # This value is a time in milliseconds that will be used to
        # shift the time of the lyrics display relative to the video.
        # It is adjusted by the user pressing the left and right
        # arrows during singing, and is persistent during a session.
        # Positive values make the lyrics anticipate the music,
        # negative values delay them.
        self.SyncDelayMs = 0

        # KAR/MID options
        self.KarEncoding = "cp1252"  # Default text encoding in karaoke files
        self.KarFont = FontData("DejaVuSans.ttf")
        self.KarBackgroundColour = (0, 0, 0)
        self.KarReadyColour = (255, 50, 50)
        self.KarSweepColour = (255, 255, 255)
        self.KarInfoColour = (0, 0, 200)
        self.KarTitleColour = (100, 100, 255)
        self.MIDISampleRate = 44100

        # CDG options
        self.CdgZoom = "int"
        self.CdgUseC = True
        self.CdgDeriveSongInformation = (
            False  # Determines if we should parse file names for song information
        )
        self.CdgFileNameType = -1  # The style index we are using for the file name parsing
        self.ExcludeNonMatchingFilenames = (
            False  # Exclude songs from database if can't derive song info
        )

        # MPEG options
        self.MpgNative = True
        self.MpgExternalThreaded = True
        self.MpgExternal = 'mplayer -fs "%(file)s"'

        if env == ENV_WINDOWS:
            self.MpgExternal = '"C:\\Program Files\\Windows Media Player\\wmplayer.exe" "%(file)s" /play /close /fullscreen'
        elif env == ENV_GP2X:
            self.FullScreen = True
            self.PlayerSize = (320, 240)
            self.CdgZoom = "none"
            # Reduce the default sample rate on the GP2x to save time.
            self.MIDISampleRate = 11025
            self.MpgExternal = './mplayer_cmdline "%(file)s"'
            self.MpgExternalThreaded = False
            self.BufferMs = 250

            # Define the CPU speed for various activities.  We're
            # conservative here and avoid overclocking by default.
            # The user can push these values higher if he knows his
            # GP2X can handle it.
            self.CPUSpeed_startup = 240
            self.CPUSpeed_wait = 33
            self.CPUSpeed_menu_idle = 33
            self.CPUSpeed_menu_slow = 100
            self.CPUSpeed_menu_fast = 240
            self.CPUSpeed_load = 240
            self.CPUSpeed_cdg = 200
            self.CPUSpeed_kar = 240
            self.CPUSpeed_mpg = 200


# This is a trivial class used to wrap the song database with a
# version number.
class DBStruct:
    def __init__(self):
        self.Version = DATABASE_VERSION
        pass


# Song database class with methods for building the database, searching etc
class SongDB:
    def __init__(self):
        # Filepaths and titles are stored in a list of SongStruct instances
        self.FullSongList = []

        # This is the same list, with songs of the same artist/title
        # removed.
        self.UniqueSongList = []

        # Here's those lists again, cached into various different
        # sorts.
        self.SortedLists = {}

        # And this is just the currently-active song list, according
        # to selected sort.
        self.song_list = []

        # The list of titles_files we have found in our scan.
        self.titles_files = []

        # A cache of zip files.
        self.zip_files = []

        # Set true if there are local changes to the database that
        # need to be saved to disk.
        self.databaseDirty = False

        # Some databases may omit either or both of titles and
        # artists, relying on filenames instead.
        self.got_titles = False
        self.got_artists = False

        # Create a SettingsStruct instance for storing settings
        # in case none are stored.
        self.Settings = SettingsStruct()

        # All temporary files use this prefix
        self.temp_file_prefix = "00Pykar__"

        self.save_dir = self.get_save_directory()
        self.temp_dir = self.get_temp_directory()
        self.cleanup_temp_files()

    def get_save_directory(self):
        """Returns the directory in which the settings files should
        be saved."""

        # If we have PYKARAOKE_DIR defined, use it.
        save_dir = os.getenv("PYKARAOKE_DIR")
        if save_dir:
            return save_dir

        if env == ENV_GP2X:
            # On the GP2X, just save db files in the root directory.
            # Makes it easier to find them, and avoids directory
            # clutter.
            return "."

        # Without PYKARAOKE_DIR, use ~/.pykaraoke.  Try to figure that
        # out.
        home_dir = self.get_home_directory()
        return os.path.join(home_dir, ".pykaraoke")

    def get_temp_directory(self):
        """Returns the directory in which temporary files should be
        saved."""
        temp_env = os.getenv("PYKARAOKE_TEMP_DIR")
        if temp_env:
            return temp_env

        temp_env = os.getenv("TEMP")
        if temp_env:
            return os.path.join(temp_env, "pykaraoke")

        if env != ENV_WINDOWS:
            # Use tempfile module for secure temp directory
            import tempfile
            temp_dir = tempfile.gettempdir()
            return os.path.join(temp_dir, "pykaraoke")
        else:
            try:
                import win32api

                return os.path.join(win32api.GetTempPath(), "pykaraoke")
            except ImportError:
                # win32api not available, fallback to tempfile
                import tempfile
                temp_dir = tempfile.gettempdir()
                return os.path.join(temp_dir, "pykaraoke")

        # If we can't find a good temp directory, use our save directory.
        return self.get_save_directory()

    def get_home_directory(self):
        """Returns the user's home directory, if we can figure that
        out."""

        if env != ENV_GP2X:
            # First attempt: ask wx, if it's available.
            try:
                import wx

                return wx.GetHomeDir()
            except (ImportError, AttributeError):
                # wx not available or method not found
                pass

            # Second attempt: look in $HOME
            home = os.getenv("HOME")
            if home:
                return home

        # Give up and return the current directory.
        return "."

    def make_song_struct(self, filename):
        """Creates a quick SongStruct representing the indicated
        filename.  The file may be embedded within a zip file; treat
        the zip filename as a directory in this case."""

        # Is this a file within a zip file?
        zip_stored_name = None
        z = filename.find(".zip/")
        if z == -1:
            z = filename.find(".zip" + os.path.sep)
        if z != -1:
            zip_stored_name = filename[z + 5 :]
            filename = filename[: z + 4]

        song = SongStruct(filename, self.Settings, zip_stored_name=zip_stored_name)
        return song

    def choose_titles(self, song):
        """Chooses an appropriate titles file to represent the
        indicated song file.  If there is no appropriate titles file,
        creates one.  Applies the song to the new titles file."""

        if song.titles:
            # This song already has a titles file.
            return

        song_path = song.Filepath
        if song.ZipStoredName:
            song_path = os.path.join(song_path, song.ZipStoredName)

        rel_to = os.path.normcase(os.path.normpath(song_path))

        best_titles = self._findBestTitlesFile(rel_to)

        if not best_titles:
            best_titles = self._createTitlesFile(song, rel_to)

        best_titles.songs.append(song)
        song.titles = best_titles
        best_titles.dirty = True
        self.databaseDirty = True

    def _findBestTitlesFile(self, rel_to):
        """Find the titles file with the longest common prefix with the song path."""
        best_titles = None
        best_prefix = ""
        for titles in self.titles_files:
            titles_path = titles.Filepath
            if titles.ZipStoredName:
                titles_path = os.path.join(titles_path, titles.ZipStoredName)
            norm = os.path.normcase(os.path.normpath(titles_path))

            prefix = os.path.commonprefix((norm, rel_to))
            # The common prefix must end with a slash.
            slash = prefix.rfind(os.sep)
            if slash != -1:
                prefix = prefix[: slash + 1]

            norm = norm[len(prefix) :]
            if os.path.sep in norm:
                continue

            if len(prefix) > len(best_prefix):
                best_titles = titles
                best_prefix = prefix
        return best_titles

    def _createTitlesFile(self, song, rel_to):
        """Create a new titles file in the root directory containing the song."""
        best_dir = None
        for dir in self.Settings.folder_list:
            norm = os.path.normcase(os.path.normpath(dir))
            if rel_to.startswith(norm):
                best_dir = dir
                break

        if not best_dir:
            best_dir = os.path.splitext(song.Filepath)[0]

        best_titles = TitleStruct(os.path.join(best_dir, _TITLES_FILENAME))
        self.titles_files.append(best_titles)
        return best_titles

    def load_settings(self, error_callback):
        """Load the personal settings (but not yet the database)."""
        settings_filepath = os.path.join(self.save_dir, "settings.dat")
        if not os.path.exists(settings_filepath):
            return
        loadsettings = self._parse_settings_file(settings_filepath)
        message = self._validate_settings_version(loadsettings)
        if message:
            if error_callback:
                error_callback(message)
            else:
                print(message)

    def _parse_settings_file(self, settings_filepath):
        loadsettings = SettingsStruct()
        with open(settings_filepath) as file:
            for line in file:
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                if not hasattr(loadsettings, key):
                    continue
                try:
                    import ast
                    value = ast.literal_eval(value)
                except (ValueError, SyntaxError):
                    print("Invalid value for %s" % (key))
                    continue
                setattr(loadsettings, key, value)
        return loadsettings

    def _validate_settings_version(self, loadsettings):
        if loadsettings and loadsettings.Version == SETTINGS_VERSION:
            self.Settings = loadsettings
            return None
        elif loadsettings:
            return "New version of PyKaraoke, clearing settings"
        return None

    def load_database(self, error_callback):
        """Load the saved database."""

        self.FullSongList = []
        self.UniqueSongList = []
        self.titles_files = []
        self.got_titles = False
        self.got_artists = False

        # Load the database file
        db_filepath = os.path.join(self.save_dir, "songdb.dat")
        if os.path.exists(db_filepath):
            file = open(db_filepath, "rb")
            loaddb = None
            try:
                loaddb = pickle.load(file)
            except (EOFError, pickle.UnpicklingError, AttributeError):
                # Corrupt or incompatible database file, will create new one
                pass
            if getattr(loaddb, "Version", None) == DATABASE_VERSION:
                self.FullSongList = loaddb.FullSongList
                self.song_list = loaddb.FullSongList
                self.UniqueSongList = loaddb.UniqueSongList
                self.titles_files = loaddb.titles_files
                self.got_titles = loaddb.got_titles
                self.got_artists = loaddb.got_artists
            else:
                if error_callback:
                    error_callback("New version of PyKaraoke, clearing database")

        self.databaseDirty = False

    ##         # This forces the titles files to be rewritten at the next
    ##         # "save" operation.
    ##         for titles in self.titles_files:
    ##             titles.dirty = True
    ##         self.databaseDirty = True

    def save_settings(self):
        """Save user settings to the home directory."""

        # Create the temp directory if it doesn't exist already
        if not os.path.exists(self.save_dir):
            os.mkdir(self.save_dir)

        # Save the settings file
        settings_filepath = os.path.join(self.save_dir, "settings.dat")
        try:
            file = open(settings_filepath, "w")
        except OSError as message:
            print(message)
        else:
            # We don't use pickle to dump out the settings anymore.
            # Instead, we write them in this human-readable and
            # human-editable format.
            keys = sorted(self.Settings.__dict__.keys())
            for k in keys:
                if not k.startswith("__"):
                    value = getattr(self.Settings, k)
                    print("%s = %s" % (k, repr(value)), file=file)

    def save_database(self):
        """Save the database to the appropriate directory."""

        if not self.databaseDirty:
            return

        try:
            # Create the temp directory if it doesn't exist already
            if not os.path.exists(self.save_dir):
                os.mkdir(self.save_dir)

            # Write out any titles files that have changed.
            for titles in self.titles_files:
                if titles.dirty:
                    titles.rewrite(self)
                    titles.dirty = False

            # Check for newly unique files
            self.make_unique_songs()

            # Save the database file
            db_filepath = os.path.join(self.save_dir, "songdb.dat")
            file = open(db_filepath, "wb")

            loaddb = DBStruct()
            loaddb.FullSongList = self.FullSongList
            loaddb.UniqueSongList = self.UniqueSongList
            loaddb.titles_files = self.titles_files
            loaddb.got_titles = self.got_titles
            loaddb.got_artists = self.got_artists

            pickle.dump(loaddb, file, pickle.HIGHEST_PROTOCOL)
        except OSError as message:
            print(message)
        self.databaseDirty = False

    def get_song(self, index):
        """This returns the song stored in index in the database."""
        return self.FullSongList[index]

    def build_search_database(self, yielder, busy_dlg):
        # Zap the database and build again from scratch. Return True
        # if was cancelled.
        self.FullSongList = []
        self.titles_files = []

        return self.do_search(self.Settings.folder_list, yielder, busy_dlg)

    def add_file(self, filename):
        """Adds just the indicated file to the DB.  If the file is a
        directory or a zip file, recursively scans within it and adds
        all the sub-files."""

        self.do_search([filename], AppYielder(), BusyCancelDialog())

    def get_zip_file(self, filename):
        """Creates a ZipFile object corresponding to the indicated zip
        file on disk and returns it.  If there was already a ZipFile
        for this filename in the cache, just returns that one
        instead, saving on load time from repeatedly loading the same
        zip file."""

        for entry in self.zip_files:
            cache_filename, cache_zip = entry
            if cache_filename == filename:
                # Here is a zip file in the cache; move it to the
                # front of the list.
                self.zip_files.remove(entry)
                self.zip_files.insert(0, entry)
                return cache_zip

        # The zip file was not in the cache, create a new one and cache it.
        zf = zipfile.ZipFile(filename)
        if len(self.zip_files) >= MAX_ZIP_FILES:
            del self.zip_files[-1]
        self.zip_files.insert(0, (filename, zf))
        return zf

    def drop_zip_file(self, filename):
        """Releases an opened zip file by the indicated filename, if any."""

        for entry in self.zip_files:
            cache_filename, _ = entry
            if cache_filename == filename:
                # Here is the zip file in the cache; remove it.
                self.zip_files.remove(entry)
                return

    def do_search(self, file_list, yielder, busy_dlg):
        """This is the actual implementation of BuildSearchDatabase()
        and AddFile()."""

        self.busy_dlg = busy_dlg
        self.busy_dlg.set_progress("Scanning", 0.0)
        yielder.do_yield()
        self.busy_dlg.show()

        self.last_busy_update = time.time()
        self.files_by_fullpath = {}

        for i in range(len(file_list)):
            root_path = file_list[i]

            # Assemble a stack of progress amounts through the various
            # directory levels.  This way we can update a progress bar
            # without knowing exactly how many directories we are
            # going to traverse.  We give each directory equal weight
            # regardless of the number of files within it.
            progress = [(i, len(file_list))]
            self.file_scan(root_path, progress, yielder)
            if self.busy_dlg.clicked:
                break

        if self.titles_files and not self.busy_dlg.clicked:
            self.busy_dlg.set_progress("Reading titles files", 0.0)
            yielder.do_yield()
            self.last_busy_update = time.time()

            # Now go back and read any titles.txt files we came across.
            # These will have meta-information about the files, such as
            # the title and/or artist.
            for i in range(len(self.titles_files)):
                if self.busy_dlg.clicked:
                    break
                now = time.time()
                if now - self.last_busy_update > 0.1:
                    # Every so often, update the current path on the display.
                    self.busy_dlg.set_progress(
                        "Reading titles files", float(i) / float(len(self.titles_files))
                    )
                    yielder.do_yield()
                    self.last_busy_update = now
                self.titles_files[i].read(self)

        if self.Settings.CheckHashes:
            self.check_file_hashes(yielder)

        self.busy_dlg.set_progress("Finalizing", 1.0)
        yielder.do_yield()

        # This structure was just temporary, for use just while
        # scanning the directories.  Remove it now.
        del self.files_by_fullpath

        self.make_unique_songs()
        self.databaseDirty = True

        cancelled = self.busy_dlg.clicked
        self.busy_dlg.destroy()

        return cancelled

    def folder_scan(self, folder_to_scan, progress, yielder):
        # Search for karaoke files inside the folder, looking inside ZIPs if
        # configured to do so. Function is recursive for subfolders.
        try:
            filedir_list = os.listdir(folder_to_scan)
        except OSError:
            print("Couldn't scan %s" % (repr(folder_to_scan)))
            return False

        # Sort the list, using printable strings for the sort key to
        # prevent issues with unicode characters in non-unicode strings
        # in the list
        filedir_list.sort(key=repr)

        # Loop through the list
        for i in range(len(filedir_list)):
            item = filedir_list[i]
            if self.busy_dlg.clicked:
                return True

            # Allow windows to refresh now and again while scanning
            yielder.consider_yield()

            # Build the full file path. Check file types match, as
            # os.listdir() can return non-unicode while the folder
            # is still unicode.
            if not isinstance(folder_to_scan, type(item)):
                full_path = os.path.join(str(folder_to_scan), str(item))
                print("Folder %s and file %s do not match types" % (repr(folder_to_scan), repr(item)))
            else:
                full_path = os.path.join(folder_to_scan, item)

            next_progress = progress + [(i, len(filedir_list))]
            self.file_scan(full_path, next_progress, yielder)
            if self.busy_dlg.clicked:
                return

    def __compute_progress_value(self, progress):
        """Returns a floating-point value in the range 0 to 1 that
        corresponds to the progress list we have built up while
        traversing the directory structure hierarchically.  This is
        used to update the progress bar linearly while we traverse the
        hierarchy."""

        # The progress list is a list of tuples of the form [(i0,
        # len0), (i1, len1), (i2, len2), ..., (in, lenn)].  There is
        # one entry for each directory level we have visited.

        # We need to boil this down into a single nondecreasing
        # number.  A simple mathematical series.

        span = 1.0
        result = 0.0
        for i, count in progress:
            if count > 1:
                result += span * (float(i) / float(count))
                span = span * (1.0 / float(count))
        return result

    def file_scan(self, full_path, progress, yielder):
        self._update_progress_if_needed(full_path, progress, yielder)

        # Recurse into subdirectories
        if os.path.isdir(full_path):
            basename = os.path.split(full_path)[1]
            if basename not in ("CVS", ".svn"):
                self.folder_scan(full_path, progress, yielder)
            if self.busy_dlg.clicked:
                return
            return

        # Store file details if it's a file type we're interested in
        _, ext = os.path.splitext(full_path)
        if self.Settings.read_titles_txt and full_path.endswith(_TITLES_FILENAME):
            self.titles_files.append(TitleStruct(full_path))
        elif self.is_extension_valid(ext):
            self._try_add_song(full_path)
        elif self.Settings.look_inside_zips and ext.lower() == ".zip":
            self._scan_zip_file(full_path, progress, yielder)

    def _update_progress_if_needed(self, full_path, progress, yielder):
        """Update the progress bar if enough time has elapsed."""
        now = time.time()
        if now - self.last_busy_update <= 0.1:
            return
        basename = os.path.split(full_path)[1]
        if isinstance(basename, bytes):
            try:
                basename = basename.decode("utf-8")
            except UnicodeDecodeError:
                basename = basename.decode("ascii", "replace")
        self.busy_dlg.set_progress(
            "Scanning %s" % basename, self.__compute_progress_value(progress)
        )
        yielder.do_yield()
        self.last_busy_update = now

    def _try_add_song(self, full_path, zip_stored_name=None):
        """Try to add a song to the database, ignoring non-matching filenames."""
        try:
            self.add_song(SongStruct(
                full_path, self.Settings,
                zip_stored_name=zip_stored_name, database_add=True,
            ))
        except KeyError:
            display_name = zip_stored_name if zip_stored_name else os.path.basename(full_path)
            print("Excluding filename with unexpected format: %s " % repr(display_name))

    def _scan_zip_file(self, full_path, progress, yielder):
        """Scan inside a ZIP file for karaoke songs and titles files."""
        try:
            if not zipfile.is_zipfile(full_path):
                print("Cannot parse ZIP file: " + repr(full_path))
                return
            zf = self.get_zip_file(full_path)
            namelist = zf.namelist()
            for i, filename in enumerate(namelist):
                self._updateZipProgress(full_path, progress, i, len(namelist), yielder)
                self._processZipMember(full_path, filename, zf)
        except (zipfile.BadZipFile, OSError):
            print("Error looking inside zip " + repr(full_path))

    def _updateZipProgress(self, full_path, progress, i, total, yielder):
        """Update progress bar during ZIP scanning."""
        now = time.time()
        if now - self.last_busy_update <= 0.1:
            return
        next_progress = progress + [(i, total)]
        basename = os.path.split(full_path)[1]
        if isinstance(basename, bytes):
            try:
                basename = basename.decode("utf-8")
            except UnicodeDecodeError:
                basename = basename.decode("ascii", "replace")
        self.busy_dlg.set_progress(
            "Scanning %s" % basename,
            self.__compute_progress_value(next_progress),
        )
        yielder.do_yield()
        self.last_busy_update = now

    def _processZipMember(self, full_path, filename, zf):
        """Process a single member of a ZIP file."""
        root, ext = os.path.splitext(filename)
        if self.Settings.read_titles_txt and filename.endswith(_TITLES_FILENAME):
            self.titles_files.append(TitleStruct(full_path, zip_stored_name=filename))
        elif self.is_extension_valid(ext):
            info = zf.getinfo(filename)
            if info.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                self._try_add_song(full_path, zip_stored_name=filename)
            else:
                print(
                    "ZIP member compressed with unsupported type (%d): %s"
                    % (info.compress_type, repr(full_path))
                )

    # Add a folder to the database search list
    def folder_add(self, folder_path):
        if folder_path not in self.Settings.folder_list:
            self.Settings.folder_list.append(folder_path)

    # Remove a folder from the database search list
    def folder_del(self, folder_path):
        self.Settings.folder_list.remove(folder_path)

    # Get the list of folders currently set up for the database
    def get_folder_list(self):
        return self.Settings.folder_list

    # Search the database for occurrences of the search terms.
    # If there are multiple terms, all must exist for a match.
    # The search is case-insensitive and searches both the title
    # and the pathname.
    # Returns a list of SongStruct instances.
    def search_database(self, search_terms, yielder):
        # Display a busy cursor while searching, yielding now and again
        # to update the GUI.
        results_list = []
        lower_terms = search_terms.lower()
        terms_list = lower_terms.split()
        for song in self.FullSongList:
            yielder.consider_yield()
            lower_title = song.Title.lower()
            lower_artist = song.Artist.lower()
            lower_path = song.DisplayFilename.lower()
            # If it's a zip file, also include the zip filename
            if song.ZipStoredName:
                lower_zip_name = os.path.basename(song.Filepath).lower()
            else:
                lower_zip_name = ""
            misses = 0
            for term in terms_list:
                try:
                    if (
                        (term not in lower_title)
                        and (term not in lower_artist)
                        and (term not in lower_zip_name)
                        and (term not in lower_path)
                    ):
                        misses = misses + 1
                except UnicodeDecodeError:
                    print("Unicode error looking up %s in %s" % (repr(term), repr(lower_zip_name)))
                    misses = misses + 1
            if misses == 0:
                results_list.append(song)
        return results_list

    # Get the song database size (number of songs)
    def get_database_size(self):
        return len(self.FullSongList)

    # Check if the passed file extension is configured for this database
    def is_extension_valid(self, extension):
        ext = extension.lower()
        if ext in self.Settings.IgnoredExtensions:
            return False
        if (
            ext in self.Settings.KarExtensions
            or ext in self.Settings.CdgExtensions
            or ext in self.Settings.MpgExtensions
        ):
            return True
        return False

    # Create a directory for use by PyKaraoke for temporary zip files
    # and for saving the song database and settings.
    # This will be under the Wx idea of the home directory.
    def create_temp_dir(self):
        if not os.path.exists(self.temp_dir):
            os.mkdir(self.temp_dir)

    # Create temporary filename prefix. Returns a path and filename
    # prefix which can be used as a base string for temporary files.
    # You must clean them up when done using cleanup_temp_files().
    # Also automatically creates a temporary directory if one doesn't
    # exist already.
    def create_temp_file_name_prefix(self):
        self.create_temp_dir()
        full_prefix = os.path.join(self.temp_dir, self.temp_file_prefix)
        return full_prefix

    # Clean up any temporary (unzipped) files on startup/exit/end of song
    def cleanup_temp_files(self):
        if os.path.exists(self.temp_dir):
            filedir_list = os.listdir(self.temp_dir)
            for item in filedir_list:
                if item.startswith(self.temp_file_prefix):
                    full_path = os.path.join(self.temp_dir, item)
                    try:
                        os.unlink(full_path)
                    except OSError:
                        # The unlink can fail on Windows due to a bug in
                        # pygame.mixer.music which does not release the
                        # file handle until you load another music file.
                        pass

    def select_sort(self, sort, allow_resort=True):
        """Sorts the list of songs in order according to the indicated
        key, which must be one of 'title', 'artist', or 'filename'.
        Also sets self.GetSongTuple to a functor which, when called, returns a
        3-tuple of strings suitable for displaying for each song,
        where the first string of each tuple is the sort key.

        This may require re-sorting the list on-the-fly.  If
        allow_resort is False, then the list will never be re-sorted;
        rather, the method will return True if the sort was
        successfully applied, or False if a re-sort was necessary but
        not performed, in which case the list retains its original
        sort."""

        get_song_tuple, sort_keys, get_sort_key, sort = self._resolve_sort_config(sort)

        song_list = self.SortedLists.get(get_sort_key, None)
        if song_list is None:
            if not allow_resort:
                return False

            song_list = self.FullSongList[:] if sort == "filename" else self.UniqueSongList[:]
            song_list.sort(key=get_sort_key)
            self.SortedLists[get_sort_key] = song_list

        global file_sort_key
        file_sort_key = get_sort_key

        self.Sort = sort
        self.SortKeys = sort_keys
        self.GetSongTuple = get_song_tuple
        self.GetSortKey = get_sort_key
        self.song_list = song_list

        return True

    def _resolve_sort_config(self, sort):
        """Resolve sort type to (getSongTuple, sortKeys, getSortKey, sort)."""
        if sort == "title" and self.got_titles:
            if self.got_artists:
                return (self.get_song_tuple_title_artist_filename,
                        ("title", "artist", "filename"),
                        self.get_song_tuple_title_artist_filename_sort_key, sort)
            return (self.get_song_tuple_title_filename_artist,
                    ("title", "filename"),
                    self.get_song_tuple_title_filename_artist_sort_key, sort)

        if sort == "artist" and self.got_artists:
            if self.got_titles:
                return (self.get_song_tuple_artist_title_filename,
                        ("artist", "title", "filename"),
                        self.get_song_tuple_artist_title_filename_sort_key, sort)
            return (self.get_song_tuple_artist_filename_title,
                    ("artist", "filename"),
                    self.get_song_tuple_artist_filename_title_sort_key, sort)

        return self._resolve_filename_sort_config()

    def _resolve_filename_sort_config(self):
        """Resolve filename sort config based on available metadata."""
        if self.got_titles and self.got_artists:
            return (self.get_song_tuple_filename_title_artist,
                    ("filename", "title", "artist"),
                    self.get_song_tuple_filename_title_artist_sort_key, "filename")
        if self.got_titles:
            return (self.get_song_tuple_filename_title_artist,
                    ("filename", "title"),
                    self.get_song_tuple_filename_title_artist_sort_key, "filename")
        if self.got_artists:
            return (self.get_song_tuple_filename_artist_title,
                    ("filename", "artist"),
                    self.get_song_tuple_filename_artist_title_sort_key, "filename")
        return (self.get_song_tuple_filename_artist_title,
                ("filename",),
                self.get_song_tuple_filename_artist_title_sort_key, "filename")

    def get_song_tuple_title_artist_filename(self, file):
        return (file.Title, file.Artist, file.get_display_filenames())

    def get_song_tuple_title_filename_artist(self, file):
        return (file.Title, file.get_display_filenames(), file.Artist)

    def get_song_tuple_artist_title_filename(self, file):
        return (file.Artist, file.Title, file.get_display_filenames())

    def get_song_tuple_artist_filename_title(self, file):
        return (file.Artist, file.get_display_filenames(), file.Title)

    def get_song_tuple_filename_title_artist(self, file):
        return (file.DisplayFilename, file.Title, file.Artist)

    def get_song_tuple_filename_artist_title(self, file):
        return (file.DisplayFilename, file.Artist, file.Title)

    def get_song_tuple_title_artist_filename_sort_key(self, file):
        return (
            file.make_sort_key(file.Title),
            file.make_sort_key(file.Artist),
            file.get_display_filenames().lower(),
            id(file),
        )

    def get_song_tuple_title_filename_artist_sort_key(self, file):
        return (
            file.make_sort_key(file.Title),
            file.DisplayFilename.lower(),
            file.make_sort_key(file.Artist),
            id(file),
        )

    def get_song_tuple_artist_title_filename_sort_key(self, file):
        return (
            file.make_sort_key(file.Artist),
            file.make_sort_key(file.Title),
            file.DisplayFilename.lower(),
            id(file),
        )

    def get_song_tuple_artist_filename_title_sort_key(self, file):
        return (
            file.make_sort_key(file.Artist),
            file.DisplayFilename.lower(),
            file.make_sort_key(file.Title),
            id(file),
        )

    def get_song_tuple_filename_title_artist_sort_key(self, file):
        return (
            file.DisplayFilename.lower(),
            file.make_sort_key(file.Title),
            file.make_sort_key(file.Artist),
            id(file),
        )

    def get_song_tuple_filename_artist_title_sort_key(self, file):
        return (
            file.DisplayFilename.lower(),
            file.make_sort_key(file.Artist),
            file.make_sort_key(file.Title),
            id(file),
        )

    def add_song(self, file):
        self.FullSongList.append(file)
        if file.Title:
            self.got_titles = True
        if file.Artist:
            self.got_artists = True

        if hasattr(self, "files_by_fullpath"):
            # Also record the file in the temporary map by fullpath name,
            # so we can cross-reference it with a titles.txt file that
            # might reference it.
            fullpath = file.Filepath
            if file.ZipStoredName:
                name = file.ZipStoredName.replace("/", os.path.sep)
                fullpath = os.path.join(fullpath, name)
            self.files_by_fullpath[fullpath] = file

    def check_file_hashes(self, yielder):
        """Walks through self.FullSongList, checking for file hashes
        to see if any files are duplicated."""

        self.busy_dlg.set_progress("Checking file hashes", 0.0)
        yielder.do_yield()
        self.last_busy_update = time.time()
        num_duplicates = 0

        # Check the hashes of each file, to see if there are any
        # duplicates.
        file_hashes = {}
        num_files = len(self.FullSongList)
        for i in range(num_files):
            now = time.time()
            if now - self.last_busy_update > 0.1:
                label = "Checking file hashes"
                if num_duplicates:
                    label = "%s duplicates found" % (num_duplicates)
                self.busy_dlg.set_progress(label, float(i) / float(num_files))
                yielder.do_yield()
                self.last_busy_update = now

            if self.busy_dlg.clicked:
                return

            digest = self._computeSongHash(self.FullSongList[i])
            if digest is None:
                continue
            hash_list = file_hashes.setdefault(digest, [])
            if hash_list:
                num_duplicates += 1
            hash_list.append(i)

        # Remove the identical files from the database.
        remove_indexes = self._collectDuplicateIndexes(file_hashes)

        # Now rebuild the FullSongList without the removed files.
        self.FullSongList = [
            self.FullSongList[i] for i in range(num_files) if i not in remove_indexes
        ]

    @staticmethod
    def _computeSongHash(song):
        """Compute a SHA-256 hash of the first song data file. Returns the digest or None."""
        datas = song.get_song_datas()
        if not datas:
            return None
        m = sha256()
        song_data = datas[0]
        if song_data.data is not None:
            m.update(song_data.data)
        else:
            try:
                with open(song_data.filename, 'rb') as f:
                    while True:
                        data = f.read(64 * 1024)
                        if not data:
                            break
                        m.update(data)
            except (IOError, OSError):
                return None
        return m.digest()

    def _collectDuplicateIndexes(self, file_hashes):
        """Identify duplicate songs and optionally delete them from disk."""
        remove_indexes = {}
        for hash_list in file_hashes.values():
            if len(hash_list) <= 1:
                continue
            filenames = [self.FullSongList[i].DisplayFilename for i in hash_list]
            print("Identical songs: %s" % repr(', '.join(filenames)))
            for i in hash_list[1:]:
                extra = self.FullSongList[i]
                remove_indexes[i] = True
                if extra.titles:
                    extra.titles.dirty = True
                if self.Settings.DeleteIdentical and not extra.ZipStoredName:
                    os.remove(extra.Filepath)
        return remove_indexes

    def make_unique_songs(self):
        """Walks through self.FullSongList, and builds up
        self.UniqueSongList, which collects only those songs who have
        the same artist/title combination."""

        if not self.got_artists and not self.got_titles:
            # A special case: titles.txt files aren't in use.
            self.UniqueSongList = self.FullSongList
            return

        songs_by_artist_title = {}

        for song in self.FullSongList:
            song_key = (song.Artist.lower(), song.Title.lower())
            song_list = songs_by_artist_title.setdefault(song_key, [])
            song_list.append(song)

        # Now go through and sort each songList into order by type.

        self.UniqueSongList = []
        for song_list in songs_by_artist_title.values():
            song_list.sort(key=SongStruct.get_type_sort)
            for song in song_list:
                song.sameSongs = song_list
            self.UniqueSongList.append(song_list[0])


globalSongDB = SongDB()
