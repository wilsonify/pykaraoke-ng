#!/usr/bin/env python

# pykar - KAR/MID Karaoke Player
#
# Copyright (C) 2010 Kelvin Lawson (kelvinl@users.sf.net)
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


# OVERVIEW
#
# pykar is a MIDI/KAR karaoke player built using python. It was written for
# the PyKaraoke project but is in fact a general purpose KAR player that
# could be used in other python projects requiring a KAR player.
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
# KAR support, this module has been designed to be easily incorporated
# into such projects and is released under the LGPL.


# REQUIREMENTS
#
# pykar requires the following to be installed on your system:
# . Python (www.python.org)
# . Pygame (www.pygame.org)


# LINUX REQUIREMENTS
#
# To play the MIDI songs on Linux, Timidity++ is also required:
# . Timidity++ (timidity.sourceforge.net)

# OSX REQUIREMENTS
#
# On OSX, pygame will run MIDI natively by default, but if the GUS
# patches are installed in /usr/local/lib/timidity, it will run MIDI
# via Timidity instead, which appears to work better than the native
# support, so we recommend this.

# USAGE INSTRUCTIONS
#
# To start the player, pass the KAR filename/path on the command line:
#       python pykar.py /songs/theboxer.kar
#
# You can also incorporate a KAR player in your own projects by
# importing this module. The class MidPlayer is exported by the
# module. You can import and start it as follows:
#   from pykaraoke.players import kar
#   player = kar.MidPlayer("/songs/theboxer.kar")
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
#   MidPlayer ("/songs/theboxer.kar", errorPopup, songFinishedCallback)
# These parameters are optional and default to None.
#
# If the initialiser fails (e.g. the song file is not present), __init__
# raises an exception.


# IMPLEMENTATION DETAILS
#
# pykar is implemented as a handful of python modules. Pygame provides
# support for playing MIDI files, so playing a MIDI song using Pygame
# is very easy. However, in order to find the lyrics from the MIDI
# file it was necessary to write a basic parser that understands the
# MIDI file format. This opens the MIDI file and reads all tracks,
# pulling out the lyric text and times. After this first parse of the
# MIDI file, this module does not do any more MIDI decoding for
# playing purposes - Pygame takes care of all actual music generation.
#
# Because a MIDI file might change tempo throughout the song, and
# because tempo changes are technically allowed to appear within any
# track and apply to all tracks, it is necessary to fully parse the
# MIDI file before making observations of tempo, and thus before being
# able to determine the precise time each lyric is to appear onscreen.
# Thus, we initially save only the "click" count of each lyric's
# appearance, and then once the file has been completely read, we can
# convert clicks to milliseconds.
#
# There is an extra complication on Linux which is that the MIDI
# support (provided by Timidity++, which is built into pygame) reports
# the current song time using the first note being played as the
# start. However on Windows the Pygame MIDI player returns the time
# from the start of the actual song (even if there is no sound for a
# few seconds). This meant that for Linux systems, it was necessary to
# parse the whole MIDI file and calculate the time of the first note
# from all tracks. This is then used as an offset in the calculation
# of when to display the lyrics.
#
# Previous implementations ran the player within a thread; this is no
# longer the case.  Instead, it is the caller's responsibility to call
# pykar.manager.poll() every once in a while to ensure that the player
# gets enough CPU time to do its work.  Ideally, this should be at
# least every 100 milliseconds or so to guarantee good video and audio
# response time.


import struct
import sys

import io

class _CStringIOShim(object):
    # Use BytesIO because MIDI/KAR data is binary
    string_io = io.BytesIO

cStringIO = _CStringIOShim()
import pygame

from pykaraoke.config.constants import (
    ENV_GP2X,
    STATE_CLOSED,
    STATE_CLOSING,
    STATE_INIT,
    STATE_NOT_PLAYING,
    STATE_PAUSED,
    STATE_PLAYING,
    X_BORDER,
    Y_BORDER,
)
from pykaraoke.config.environment import env
from pykaraoke.core.manager import manager
from pykaraoke.core.player import PykPlayer

# At what percentage of the screen height should we try to keep the
# current singing cursor?  33% keeps it on the top third, 50% keeps it
# centered.
VIEW_PERCENT = 33

# Default font size at 480 pixels.
FONT_SIZE = 40

# How much lead time before a new paragraph is scrolled up into view
# (scrolling the old paragraph off), in milliseconds.  This only comes
# into play when there is a large time gap between syllables.
PARAGRAPH_LEAD_TIME = 5000

# text types.
TEXT_LYRIC = 0
TEXT_INFO = 1
TEXT_TITLE = 2

# Debug out MIDI messages as text
debug = False


class midiFile:
    def __init__(self):
        self.trackList = []  # List of TrackDesc track descriptors

        # Chosen lyric list from above.  It is converted by
        # computeTiming() from a list of (clicks, text) into a list of
        # (ms, text).
        self.lyrics = []

        self.text_encoding = ""  # The encoding of text in midi file

        self.ClickUnitsPerSMPTE = None
        self.SMPTEFramesPerSec = None
        self.ClickUnitsPerQuarter = None

        # The tempo of the song may change throughout, so we have to
        # record the click at which each tempo change occurred, and
        # the new tempo at that point.  Then, after we have read in
        # all the tracks (and thus collected all the tempo changes),
        # we can go back and apply this knowledge to the other tracks.
        self.Tempo = [(0, 0)]

        self.Numerator = None  # Numerator
        self.Denominator = None  # Denominator
        self.ClocksPerMetronomeTick = None  # MIDI clocks per metronome tick
        self.NotesPer24MIDIClocks = None  # 1/32 Notes per 24 MIDI clocks
        self.earliest_note_ms = 0  # Start of earliest note in song
        self.last_note_ms = 0  # End of latest note in song


class TrackDesc:
    def __init__(self, trackNum):
        self.TrackNum = trackNum  # Track number
        self.TotalClicksFromStart = 0  # Store number of clicks elapsed from start
        self.BytesRead = 0  # Number of file bytes read for track
        self.FirstNoteClick = None  # Start of first note in track
        self.FirstNoteMs = None  # The same, in milliseconds
        self.last_note_click = None  # End of last note in track
        self.last_note_ms = None  # In millseconds
        self.LyricsTrack = False  # This track contains lyrics
        self.RunningStatus = 0  # MIDI Running Status byte

        self.text_events = Lyrics()  # Lyrics (0x1 events)
        self.lyric_events = Lyrics()  # Lyrics (0x5 events)


class MidiTimestamp:
    """This class is used to apply the tempo changes to the click
    count, thus computing a time in milliseconds for any number of
    clicks from the beginning of the song."""

    def __init__(self, midifile):
        self.ClickUnitsPerQuarter = midifile.ClickUnitsPerQuarter
        self.Tempo = midifile.Tempo
        self.ms = 0
        self.click = 0
        self.i = 0

    def advanceToClick(self, click):
        # Moves time forward to the indicated click number.
        clicks = click - self.click
        if clicks < 0:
            # Ignore jumps backward in time.
            return

        while clicks > 0 and self.i < len(self.Tempo):
            # How many clicks remain at the current tempo?
            clicksRemaining = max(self.Tempo[self.i][0] - self.click, 0)
            clicksUsed = min(clicks, clicksRemaining)
            if clicksUsed != 0:
                self.ms += self.getTimeForClicks(clicksUsed, self.Tempo[self.i - 1][1])
            self.click += clicksUsed
            clicks -= clicksUsed
            clicksRemaining -= clicksUsed
            if clicksRemaining == 0:
                self.i += 1

        if clicks > 0:
            # We have reached the last tempo mark of the song, so this
            # tempo holds forever.
            self.ms += self.getTimeForClicks(clicks, self.Tempo[-1][1])
            self.click += clicks

    def getTimeForClicks(self, clicks, tempo):
        microseconds = (float(clicks) / self.ClickUnitsPerQuarter) * tempo
        time_ms = microseconds / 1000
        return time_ms


class LyricSyllable:
    """Each instance of this class records a single lyric event,
    e.g. a syllable of a word to be displayed and change color at a
    given time.  The Lyrics class stores a list of these."""

    def __init__(self, click, text, line, type=TEXT_LYRIC):
        self.click = click
        self.ms = None
        self.text = text
        self.line = line
        self.type = type

        # This is filled in when the syllable is drawn onscreen.
        self.left = None
        self.right = None

    def makeCopy(self, text):
        # Returns a new LyricSyllable, exactly like this one, with
        # the text replaced by the indicated string
        syllable = LyricSyllable(self.click, text, self.line, self.type)
        syllable.ms = self.ms
        return syllable

    def __repr__(self):
        return "<%s %s>" % (self.ms, self.text)


class Lyrics:
    """This is the complete lyrics of a song, organized as a list of
    syllables sorted by event time."""

    def __init__(self):
        self.list = []
        self.line = 0

    def hasAny(self):
        # Returns true if there are any lyrics.
        return bool(self.list)

    def recordText(self, click, text):
        # Records a MIDI 0x1 text event (a syllable).

        # Make sure there are no stray null characters in the string.
        text = text.replace("\x00", "")
        # Or CR's.
        text = text.replace("\r", "")

        if not text:
            # Ignore blank lines.
            return

        if text[0] == "@":
            if text[1] == "T":
                # A title.
                text_type = TEXT_TITLE
            elif text[1] == "I":
                # An info line.
                text_type = TEXT_INFO
            else:
                # Any other comment we ignore.
                return

            # Put the comment onscreen.
            for line in text[2:].split("\n"):
                line = line.strip()
                self.line += 1
                self.list.append(LyricSyllable(click, line, self.line, text_type))
            return

        if text[0] == "\\":
            # Paragraph break.  We treat it the same as line break,
            # but with an extra blank line.
            self.line += 2
            text = text[1:]
        elif text[0] == "/":
            # Line break.
            self.line += 1
            text = text[1:]

        if text:
            lines = text.split("\n")
            self.list.append(LyricSyllable(click, lines[0], self.line))
            for line in lines[1:]:
                self.line += 1
                self.list.append(LyricSyllable(click, line, self.line))

    def recordLyric(self, click, text):
        # Records a MIDI 0x5 lyric event (a syllable).

        # Make sure there are no stray null characters in the string.
        text = text.replace("\x00", "")

        if text == "\n":
            # Paragraph break.  We treat it the same as line break,
            # but with an extra blank line.
            self.line += 2

        elif text == "\r" or text == "\r\n":
            # Line break.
            self.line += 1

        elif text:
            text = text.replace("\r", "")

            if text[0] == "\\":
                # Paragraph break.  This is a text event convention, not a
                # lyric event convention, but some midi files don't play
                # by the rules.
                self.line += 2
                text = text[1:]
            elif text[0] == "/":
                # Line break.  A text convention, but see above.
                self.line += 1
                text = text[1:]

            # Lyrics aren't supposed to include embedded newlines, but
            # sometimes they do anyway.
            lines = text.split("\n")
            self.list.append(LyricSyllable(click, lines[0], self.line))
            for line in lines[1:]:
                self.line += 1
                self.list.append(LyricSyllable(click, line, self.line))

    def computeTiming(self, midifile):
        # Walk through the lyrics and convert the click information to
        # elapsed time in milliseconds.

        ts = MidiTimestamp(midifile)
        for syllable in self.list:
            ts.advanceToClick(syllable.click)
            syllable.ms = int(ts.ms)

        # Also change the firstNoteClick to firstNoteMs, for each track.
        for track_desc in midifile.trackList:
            ts = MidiTimestamp(midifile)
            if track_desc.FirstNoteClick is not None:
                ts.advanceToClick(track_desc.FirstNoteClick)
                track_desc.FirstNoteMs = ts.ms
                if debug:
                    print(
                        "T%s first note at %s clicks, %s ms"
                        % (track_desc.TrackNum, track_desc.FirstNoteClick, track_desc.FirstNoteMs)
                    )
            if track_desc.last_note_click is not None:
                ts.advanceToClick(track_desc.last_note_click)
                track_desc.last_note_ms = ts.ms

    def analyzeSpaces(self):
        """Checks for a degenerate case: no (or very few) spaces
        between words.  Sometimes Karaoke writers omit the spaces
        between words, which makes the text very hard to read.  If we
        detect this case, repair it by adding spaces back in."""

        lines = self._group_syllables_into_lines()

        # Now, count the spaces between the syllables of the lines.
        total_num_syls, total_num_gaps = self._count_gaps(lines)

        if total_num_syls and float(total_num_gaps) / float(total_num_syls) < 0.1:
            # Too few spaces.  Insert more.
            self._insert_spaces(lines)

    def _group_syllables_into_lines(self):
        """Group the syllables into lines based on their line attribute."""
        line_number = None
        lines = []
        current_line = []

        for syllable in self.list:
            if syllable.line != line_number:
                if current_line:
                    lines.append(current_line)
                current_line = []
                line_number = syllable.line
            current_line.append(syllable)

        if current_line:
            lines.append(current_line)
        return lines

    @staticmethod
    def _count_gaps(lines):
        """Count syllables and inter-syllable gaps across all lines."""
        total_num_syls = 0
        total_num_gaps = 0
        for line in lines:
            num_syls = len(line) - 1
            num_gaps = 0
            for i in range(num_syls):
                if (
                    line[i].text.rstrip() != line[i].text
                    or line[i + 1].text.lstrip() != line[i + 1].text
                ):
                    num_gaps += 1
            total_num_syls += num_syls
            total_num_gaps += num_gaps
        return total_num_syls, total_num_gaps

    @staticmethod
    def _insert_spaces(lines):
        """Add spaces between syllables that lack them."""
        for line in lines:
            for syllable in line[:-1]:
                if syllable.text.endswith("-"):
                    syllable.text = syllable.text[:-1]
                else:
                    syllable.text += " "

    def wordWrapLyrics(self, font):
        # Walks through the lyrics and folds each line to the
        # indicated width.  Returns the new lyrics as a list of lists
        # of syllables; that is, each element in the returned list
        # corresponds to a displayable line, and each line is a list
        # of syllabels.

        if not self.list:
            return []

        max_width = manager.displaySize[0] - X_BORDER * 2

        lines = []

        x = 0
        current_line = []
        current_text = ""
        line_number = self.list[0].line
        for syllable in self.list:
            syllable.left = None
            syllable.right = None

            while line_number < syllable.line:
                lines.append(current_line)
                x = 0
                current_line = []
                current_text = ""
                line_number += 1

            width, height = font.size(syllable.text)
            current_line.append(syllable)
            current_text += syllable.text
            x += width
            while x > max_width:
                result = self._fold_line(current_line, current_text, font, max_width)
                if result is None:
                    break
                output_line, current_line, current_text = result
                lines.append(output_line)
                x, height = font.size(current_text)

        lines.append(current_line)

        # Indicated that the first syllable of each line is flush with
        # the left edge of the screen.
        for l in lines:
            if l:
                l[0].left = X_BORDER

        return lines

    @staticmethod
    def _fold_line(current_line, current_text, font, max_width):
        """Fold a line that exceeds max_width at the best fold point.

        Returns (output_line, remaining_line, remaining_text) or None if
        the line should not be folded (trailing whitespace only).
        """
        fold_point = manager.find_fold_point(current_text, font, max_width)
        if fold_point == len(current_text):
            return None

        # All the characters before fold_point get output as the first line.
        n = 0
        i = 0
        text = current_line[i].text
        output_line = []
        while n + len(text) <= fold_point:
            output_line.append(current_line[i])
            n += len(text)
            i += 1
            text = current_line[i].text

        syllable = current_line[i]
        if i == 0:
            # One long line.  Break it mid-phrase.
            a = syllable.makeCopy(syllable.text[:fold_point])
            output_line.append(a)
            current_line[i] = syllable.makeCopy("  " + syllable.text[fold_point:])
        else:
            current_line[i] = syllable.makeCopy("  " + syllable.text)

        remaining_line = current_line[i:]
        remaining_text = "".join(s.text for s in remaining_line)
        return output_line, remaining_line, remaining_text

    def write(self):
        # Outputs the lyrics, one line at a time.
        for syllable in self.list:
            print(
                "%s(%s) %s %s" % (syllable.ms, syllable.click, syllable.line, repr(syllable.text))
            )


def midi_parse_data(midi_data, error_notify_callback, encoding):
    # Create the midiFile structure
    midifile = midiFile()
    midifile.text_encoding = encoding

    # Open the file
    filehdl = cStringIO.string_io(midi_data)

    # Check it's a MThd chunk
    packet = filehdl.read(8)
    chunk_type, length = struct.unpack(">4sL", packet)
    if chunk_type != "MThd":
        error_notify_callback("No MIDI Header chunk at start")
        return None

    # Read header
    packet = filehdl.read(length)
    _, _, division = struct.unpack(">HHH", packet)
    if division & 0x8000:
        midifile.ClickUnitsPerSMPTE = division & 0x00FF
        midifile.SMPTEFramesPerSec = division & 0x7F00
    else:
        midifile.ClickUnitsPerQuarter = division & 0x7FFF

    # Loop through parsing all tracks
    _parse_midi_tracks(filehdl, midifile)
    filehdl.close()

    # Get the lyrics from the best track.
    midifile.lyrics = _select_best_lyrics(midifile)
    if not midifile.lyrics:
        error_notify_callback("No lyrics in the track")
        return None

    midifile.lyrics.computeTiming(midifile)
    midifile.lyrics.analyzeSpaces()

    # Calculate the song start/end from note events across all tracks.
    midifile.earliest_note_ms, midifile.last_note_ms = _compute_note_bounds(midifile)

    if debug:
        print("first = %s" % (midifile.earliest_note_ms))
        print("last = %s" % (midifile.last_note_ms))

    # Return the populated midiFile structure
    return midifile


def _parse_midi_tracks(filehdl, midifile):
    """Read and parse all MIDI tracks from the file handle."""
    track_num = 0
    while True:
        packet = filehdl.read(8)
        if packet == "" or len(packet) < 8:
            break
        chunk_type, length = struct.unpack(">4sL", packet)
        if chunk_type != "MTrk" and debug:
            print("Didn't find expected MIDI Track")

        track_desc = midi_parse_track(filehdl, midifile, track_num, length)
        if not track_desc:
            break
        midifile.trackList.append(track_desc)
        if debug:
            print("T%d: First note(%s)" % (track_num, track_desc.FirstNoteClick))
        track_num += 1


def _select_best_lyrics(midifile):
    """Select the best lyrics track: prefer 'lyrics' tracks, then most syllables."""
    best_sort_key = None
    best_lyrics = None

    for track_desc in midifile.trackList:
        lyrics = _choose_lyrics_from_track(track_desc)
        if not lyrics:
            continue
        sort_key = (track_desc.LyricsTrack, len(lyrics.list))
        if sort_key > best_sort_key:
            best_sort_key = sort_key
            best_lyrics = lyrics
    return best_lyrics


def _choose_lyrics_from_track(track_desc):
    """Pick the best lyric event list from a single track."""
    has_text = track_desc.text_events.hasAny()
    has_lyric = track_desc.lyric_events.hasAny()

    if has_text and has_lyric:
        if len(track_desc.lyric_events.list) > len(track_desc.text_events.list):
            return track_desc.lyric_events
        return track_desc.text_events
    if has_text:
        return track_desc.text_events
    if has_lyric:
        return track_desc.lyric_events
    return None


def _compute_note_bounds(midifile):
    """Return (earliest_note_ms, last_note_ms) across all tracks."""
    earliest_note_ms = None
    last_note_ms = None
    for track in midifile.trackList:
        if track.FirstNoteMs is not None:
            if earliest_note_ms is None or track.FirstNoteMs < earliest_note_ms:
                earliest_note_ms = track.FirstNoteMs
        if track.last_note_ms is not None:
            if last_note_ms is None or track.last_note_ms > last_note_ms:
                last_note_ms = track.last_note_ms
    return earliest_note_ms, last_note_ms


def midi_parse_track(filehdl, midifile, track_num, length):
    # Create the new TrackDesc structure
    track = TrackDesc(track_num)
    if debug:
        print("Track %d" % track_num)
    # Loop through all events in the track, recording salient meta-events and times
    event_bytes = 0
    while track.BytesRead < length:
        event_bytes = midi_process_event(filehdl, track, midifile)
        if (event_bytes is None) or (event_bytes == -1) or (event_bytes == 0):
            return None
        track.BytesRead = track.BytesRead + event_bytes
    return track


def midi_process_event(filehdl, track_desc, midifile):
    bytes_read = 0
    _running_status = 0
    click, var_bytes = var_length(filehdl)
    if var_bytes == 0:
        return 0
    bytes_read = bytes_read + var_bytes
    track_desc.TotalClicksFromStart += click
    byte_str = filehdl.read(1)
    bytes_read = bytes_read + 1
    status_byte = ord(byte_str)

    # Handle the MIDI running status.
    if status_byte & 0x80:
        event_type = status_byte
        if (event_type & 0xF0) != 0xF0:
            track_desc.RunningStatus = event_type
    else:
        event_type = track_desc.RunningStatus
        filehdl.seek(-1, 1)
        bytes_read = bytes_read - 1

    # Handle all event types
    if event_type == 0xFF:
        bytes_read += _process_meta_event(filehdl, track_desc, midifile)
    else:
        bytes_read += _process_channel_event(filehdl, track_desc, event_type)
    return bytes_read


def _process_meta_event(filehdl, track_desc, midifile):
    """Process a MIDI meta-event (0xFF). Returns bytes read."""
    bytes_read = 0
    byte_str = filehdl.read(1)
    bytes_read += 1
    event = ord(byte_str)
    if debug:
        print("MetaEvent: 0x%X" % event)

    handler = _META_EVENT_HANDLERS.get(event)
    if handler:
        bytes_read += handler(filehdl, track_desc, midifile)
    else:
        bytes_read += _meta_discard_var(filehdl, event)
    return bytes_read


def _meta_sequence_number(filehdl, track_desc, midifile):
    """Meta-event 0x00: Sequence number."""
    bytes_read = 0
    packet = filehdl.read(2)
    bytes_read += 2
    _, type_val = map(ord, packet)
    if type_val == 0x02:
        filehdl.read(2)
    elif type_val != 0x00 and debug:
        print("Invalid sequence number (%d)" % type_val)
    return bytes_read


def _meta_text_event(filehdl, track_desc, midifile):
    """Meta-event 0x01: Text Event."""
    bytes_read = 0
    length, var_bytes = var_length(filehdl)
    bytes_read += var_bytes
    text = filehdl.read(length)
    bytes_read += length
    if length <= 1000:
        if midifile.text_encoding != "":
            text = text.decode(midifile.text_encoding, "replace")
        if _is_lyric_text(text):
            track_desc.text_events.recordText(track_desc.TotalClicksFromStart, text)
        if debug:
            print("Text: %s" % (repr(text)))
    elif debug:
        print("Ignoring text of length %s" % (length))
    return bytes_read


def _meta_copyright(filehdl, track_desc, midifile):
    """Meta-event 0x02: Copyright (discard)."""
    return _read_and_discard_var(filehdl)


def _meta_track_title(filehdl, track_desc, midifile):
    """Meta-event 0x03: Title of track."""
    bytes_read = 0
    length, var_bytes = var_length(filehdl)
    bytes_read += var_bytes
    title = filehdl.read(length)
    bytes_read += length
    if debug:
        print("Track Title: " + repr(title))
    if title == "Words":
        track_desc.LyricsTrack = True
    return bytes_read


def _meta_instrument(filehdl, track_desc, midifile):
    """Meta-event 0x04: Instrument (discard)."""
    return _read_and_discard_var(filehdl)


def _meta_lyric_event(filehdl, track_desc, midifile):
    """Meta-event 0x05: Lyric Event."""
    bytes_read = 0
    length, var_bytes = var_length(filehdl)
    bytes_read += var_bytes
    lyric = filehdl.read(length)
    if midifile.text_encoding != "":
        lyric = lyric.decode(midifile.text_encoding, "replace")
    bytes_read += length
    if _is_lyric_text(lyric):
        track_desc.lyric_events.recordLyric(track_desc.TotalClicksFromStart, lyric)
    if debug:
        print("Lyric: %s" % (repr(lyric)))
    return bytes_read


def _meta_discard_var_length(filehdl, track_desc, midifile):
    """Discard a variable-length meta-event."""
    return _read_and_discard_var(filehdl)


def _meta_fixed_discard_2(filehdl, track_desc, midifile):
    """Discard 2 fixed bytes (MIDI Channel / MIDI Port)."""
    filehdl.read(2)
    return 2


def _meta_end_of_track(filehdl, track_desc, midifile):
    """Meta-event 0x2F: End of track."""
    byte_str = filehdl.read(1)
    valid = ord(byte_str)
    if valid != 0:
        print("Invalid End of track")
    return 1


def _meta_set_tempo(filehdl, track_desc, midifile):
    """Meta-event 0x51: Set Tempo."""
    packet = filehdl.read(4)
    valid, tempo_a, tempo_b, tempo_c = map(ord, packet)
    if valid != 0x03:
        print("Error: Invalid tempo")
    tempo = (tempo_a << 16) | (tempo_b << 8) | tempo_c
    midifile.Tempo.append((track_desc.TotalClicksFromStart, tempo))
    if debug:
        ms_per_quarter = tempo / 1000
        print("Tempo: %d (%d ms per quarter note)" % (tempo, ms_per_quarter))
    return 4


def _meta_smpte(filehdl, track_desc, midifile):
    """Meta-event 0x54: SMPTE (discard)."""
    filehdl.read(6)
    return 6


def _meta_time_signature(filehdl, track_desc, midifile):
    """Meta-event 0x58: Time Signature."""
    packet = filehdl.read(5)
    valid, num, denom, clocks, notes = map(ord, packet)
    if valid != 0x04:
        print(
            "Error: Invalid time signature (valid=%d, num=%d, denom=%d)"
            % (valid, num, denom)
        )
    midifile.Numerator = num
    midifile.Denominator = denom
    midifile.ClocksPerMetronomeTick = clocks
    midifile.NotesPer24MIDIClocks = notes
    return 5


def _meta_key_signature(filehdl, track_desc, midifile):
    """Meta-event 0x59: Key signature (discard)."""
    packet = filehdl.read(3)
    valid, sf, mi = map(ord, packet)
    if valid != 0x02:
        print("Error: Invalid key signature (valid=%d, sf=%d, mi=%d)" % (valid, sf, mi))
    return 3


def _meta_sequencer_specific(filehdl, track_desc, midifile):
    """Meta-event 0x7F: Sequencer Specific."""
    bytes_read = 0
    length, var_bytes = var_length(filehdl)
    bytes_read += var_bytes
    byte_str = filehdl.read(1)
    bytes_read += 1
    ID = ord(byte_str)
    if ID == 0:
        packet = filehdl.read(2)
        bytes_read += 2
        ID = struct.unpack(">H", packet)[0]
        length -= 3
    else:
        length -= 1
    data = filehdl.read(length)
    bytes_read += length
    if debug:
        print("Sequencer Specific Event (Data Length %d)" % length)
        print("Manufacturer's ID: " + str(ID))
        print("Manufacturer Data: " + data)
    return bytes_read


# Lookup table mapping meta-event codes to their handler functions
_META_EVENT_HANDLERS = {
    0x00: _meta_sequence_number,
    0x01: _meta_text_event,
    0x02: _meta_copyright,
    0x03: _meta_track_title,
    0x04: _meta_instrument,
    0x05: _meta_lyric_event,
    0x06: _meta_discard_var_length,  # Marker
    0x07: _meta_discard_var_length,  # Cue point
    0x08: _meta_discard_var_length,  # Program name
    0x09: _meta_discard_var_length,  # Device name
    0x20: _meta_fixed_discard_2,     # MIDI Channel
    0x21: _meta_fixed_discard_2,     # MIDI Port
    0x2F: _meta_end_of_track,
    0x51: _meta_set_tempo,
    0x54: _meta_smpte,
    0x58: _meta_time_signature,
    0x59: _meta_key_signature,
    0x7F: _meta_sequencer_specific,
}


def _is_lyric_text(text):
    """Return True if the text should be treated as lyrics (not sysex markers)."""
    return (
        " SYX" not in text
        and "Track-" not in text
        and "%-" not in text
        and "%+" not in text
    )


def _read_and_discard_var(filehdl):
    """Read a variable-length block and discard it. Returns total bytes read."""
    bytes_read = 0
    length, var_bytes = var_length(filehdl)
    bytes_read += var_bytes
    filehdl.read(length)
    bytes_read += length
    return bytes_read


def _meta_discard_var(filehdl, event):
    """Discard an unknown meta-event with variable-length data."""
    if debug:
        print("Unknown meta-event: 0x%X" % event)
    return _read_and_discard_var(filehdl)


def _process_channel_event(filehdl, track_desc, event_type):
    """Process MIDI channel voice / system messages. Returns bytes read."""
    high_nibble = event_type & 0xF0

    if high_nibble == 0x80:
        # Note off
        filehdl.read(2)
        track_desc.last_note_click = track_desc.TotalClicksFromStart
        return 2

    if high_nibble == 0x90:
        # Note on
        filehdl.read(2)
        if track_desc.FirstNoteClick is None:
            track_desc.FirstNoteClick = track_desc.TotalClicksFromStart
        track_desc.last_note_click = track_desc.TotalClicksFromStart
        return 2

    if high_nibble in (0xA0, 0xB0, 0xE0):
        # Key after-touch / Control change / Pitch wheel (2-byte data)
        packet = filehdl.read(2)
        if debug and high_nibble == 0xB0:
            c, v = map(ord, packet)
            print("Control: C%d V%d" % (c, v))
        return 2

    if high_nibble in (0xC0, 0xD0):
        # Program change / Channel after-touch (1-byte data)
        filehdl.read(1)
        return 1

    if event_type == 0xF0:
        return _process_sysex_f0(filehdl)

    if event_type == 0xF7:
        return _read_and_discard_var(filehdl)

    # Unknown event
    if debug:
        print("Unknown event: 0x%x" % event_type)
    return _read_and_discard_var(filehdl)


def _process_sysex_f0(filehdl):
    """Process F0 Sysex Event."""
    bytes_read = 0
    length, var_bytes = var_length(filehdl)
    bytes_read += var_bytes
    filehdl.read(length - 1)
    end_byte = filehdl.read(1)
    end = ord(end_byte)
    bytes_read += length
    if end != 0xF7:
        print("Invalid F0 Sysex end byte (0x%X)" % end)
    return bytesRead


# Read a variable length quantity from the file's current read position.
# Reads the file one byte at a time until the full value has been read,
# and returns a tuple of the full integer and the number of bytes read
def var_length(filehdl):
    converted_int = 0
    bit_shift = 0
    bytes_read = 0
    while bit_shift <= 42:
        byte_str = filehdl.read(1)
        bytes_read = bytes_read + 1
        if byte_str:
            byte_val = ord(byte_str)
            converted_int = (converted_int << 7) | (byte_val & 0x7F)
            # print ("<0x%X/0x%X>"% (byte_val, converted_int))
            if byte_val & 0x80:
                bit_shift = bit_shift + 7
            else:
                break
        else:
            return (0, 0)
    return (converted_int, bytes_read)


class MidPlayer(PykPlayer):
    def __init__(self, song, song_db, error_notify_callback=None, done_callback=None):
        """The first parameter, song, may be either a pykdb.SongStruct
        instance, or it may be a filename."""

        PykPlayer.__init__(self, song, song_db, error_notify_callback, done_callback)
        settings = self.song_db.Settings

        self.supports_font_zoom = True
        self.isValid = False

        # Parse the MIDI file
        self.midifile = midi_parse_data(
            self.song_datas[0].get_data(), self.error_notify_callback, settings.KarEncoding
        )
        if self.midifile is None:
            error_string = "ERROR: Could not parse the MIDI file"
            self.error_notify_callback(error_string)
            return
        elif self.midifile.lyrics is None:
            error_string = "ERROR: Could not get any lyric data from file"
            self.error_notify_callback(error_string)
            return

        self.isValid = True

        # Debug out the found lyrics
        if debug:
            self.midifile.lyrics.write()

        manager.set_cpu_speed("kar")
        manager.init_player(self)
        manager.open_display()

        if not manager.options.nomusic:
            manager.open_audio(frequency=manager.settings.MIDISampleRate, channels=1)

        # Account for the size of the playback buffer in the lyrics
        # display.  Assume that the buffer will be mostly full.  On a
        # slower computer that's struggling to keep up, this may not
        # be the right amount of delay, but it should usually be
        # pretty close.
        self.internal_offset_time = -manager.get_audio_buffer_ms()

        self.screenDirty = False
        self.initFont()

        # Windows reports the song time correctly (including period up
        # to the first note), so no need for the earliest note hack
        # there.  On timidity-based platforms, we anticipate our
        # lyrics display by the time of the first note.

        # Note: pygame on OSX can run MIDI natively, or if the GUS
        # patches are installed in /usr/local/lib/timidity, it will
        # run MIDI via Timidity instead, which appears to work better
        # than the native support, so we recommend this.
        if env != ENV_WINDOWS:
            self.internal_offset_time += self.midifile.earliest_note_ms

        # Now word-wrap the text to fit our window.
        self.lyrics = self.midifile.lyrics.wordWrapLyrics(self.font)

        # By default, we will use the get_pos() functionality returned
        # by pygame to get the current time through the song, to
        # synchronize lyric display with the music.
        self.useMidiTimer = True

        if env == ENV_WINDOWS:
            # Unless we're running on Windows (i.e., not timidity).
            # For some reason, hardware MIDI playback can report an
            # unreliable time.  To avoid that problem, we'll always
            # use the CPU timer instead of the MIDI timer.
            self.useMidiTimer = False

        # Load the MIDI player
        if manager.options.nomusic:
            # If we're not playing music, use the CPU timer instead of
            # the MIDI timer.
            self.useMidiTimer = False

        else:
            # Load the sound normally for playback.
            audio_path = self.song_datas[0].get_filepath()
            if isinstance(audio_path, str):
                audio_path = audio_path.encode(sys.getfilesystemencoding())
            pygame.mixer.music.load(audio_path)

            # Set an event for when the music finishes playing
            pygame.mixer.music.set_endevent(pygame.USEREVENT)

        # Reset all the state (current lyric index etc) and
        # paint the first numRows lines.
        self.resetPlayingState()

    def get_pos(self):
        if self.useMidiTimer:
            return pygame.mixer.music.get_pos()
        else:
            return PykPlayer.get_pos(self)

    def setup_options(self, usage=None):
        """Initialise and return optparse OptionParser object,
        suitable for parsing the command line options to this
        application."""

        if usage is None:
            usage = "%prog [options] <KAR file>"
        parser = PykPlayer.setup_options(self, usage=usage)

        # Remove irrelevant options.
        parser.remove_option("--fps")
        parser.remove_option("--zoom")

        return parser

    def initFont(self):
        font_size = int(FONT_SIZE * manager.get_font_scale() * manager.displaySize[1] / 480.0)
        self.font = self.find_pygame_font(self.song_db.Settings.KarFont, font_size)
        self.lineSize = max(self.font.get_height(), self.font.get_linesize())
        self.numRows = int((manager.displaySize[1] - Y_BORDER * 2) / self.lineSize)

        # Put the current singing row at the specified fraction of the
        # screen.
        self.viewRow = int(self.numRows * VIEW_PERCENT / 100)

    def resetPlayingState(self):
        # Set the state variables

        # The current point the user was hearing within the song, as
        # of the last screen update.
        self.currentMs = 0

        # The line currently on display at the top of the screen.
        self.topLine = 0

        # The line on which the player is currently singing (that is,
        # the lowest line onscreen containing white syllables).
        self.currentLine = 0

        # The time at which this current syllable was sung.
        self.currentColourMs = 0

        # The next line with syllables that will need to be painted
        # white.
        self.nextLine = 0

        # The next syllable within the line that needs to be painted.
        self.nextSyllable = 0

        # The time at which the next syllable is to be painted.
        self.nextColourMs = 0

        # The time at which something is next scheduled to change
        # onscreen (usually the same as self.nextColourMs).
        self.nextChangeMs = 0

        self.repaintScreen()

    def repaintScreen(self):
        # Redraws the contents of the currently onscreen text.

        # Clear the screen
        settings = self.song_db.Settings
        manager.surface.fill(settings.KarBackgroundColour)

        # Paint the first numRows lines
        for i in range(self.numRows):
            l = self.topLine + i
            x = X_BORDER
            if l < len(self.lyrics):
                for syllable in self.lyrics[l]:
                    syllable.left = x
                    self.drawSyllable(syllable, i, None)
                    x = syllable.right

        manager.flip()
        self.screenDirty = False

    def drawSyllable(self, syllable, row, x):
        """Draws a new syllable on the screen in the appropriate
        color, either red or white, according to self.currentMs.  The
        syllable is draw on the screen at the specified row, numbering
        0 from the top of the screen.  The value x indicates the x
        position of the end of the previous syllable, which is used to
        fill in the syllable's x position if it is not already known.
        x may be none if the syllable's x position is already
        known."""

        if syllable.left is None:
            syllable.left = x
            if syllable.left is None:
                return

        y = Y_BORDER + row * self.lineSize

        settings = self.song_db.Settings

        if syllable.type == TEXT_LYRIC:
            if self.currentMs < syllable.ms:
                color = settings.KarReadyColour
            else:
                color = settings.KarSweepColour
        elif syllable.type == TEXT_INFO:
            color = settings.KarInfoColour
        elif syllable.type == TEXT_TITLE:
            color = settings.KarTitleColour

        # Render text on a black background (instead of transparent)
        # to save a hair of CPU time.
        text = self.font.render(syllable.text, True, color, settings.KarBackgroundColour)

        width, height = text.get_size()
        syllable.right = syllable.left + width

        manager.surface.blit(text, (syllable.left, y, width, height))

    def __hasLyrics(self):
        """Returns true if the midi file contains any lyrics at all,
        false if it doesn't (or contains only comments)."""

        if not self.midifile or not self.midifile.lyrics:
            return False

        for syllable in self.midifile.lyrics.list:
            if syllable.type == TEXT_LYRIC:
                return True
        return False

    def do_validate(self):
        if not self.__hasLyrics():
            return False

        return True

    def do_play(self):
        if not manager.options.nomusic:
            pygame.mixer.music.play()

            # For some reason, timidity sometimes reports a bogus
            # get_pos() until the first few milliseconds have elapsed.  As
            # a cheesy way around this, we'll just wait a bit right up
            # front.
            pygame.time.wait(50)

    def do_pause(self):
        if not manager.options.nomusic:
            pygame.mixer.music.pause()

    def do_unpause(self):
        if not manager.options.nomusic:
            pygame.mixer.music.unpause()

    def do_rewind(self):
        # Reset all the state (current lyric index etc)
        self.resetPlayingState()
        # Stop the audio
        if not manager.options.nomusic:
            pygame.mixer.music.rewind()
            pygame.mixer.music.stop()

    def get_length(self):
        """Give the number of seconds in the song."""
        return self.midifile.last_note_ms / 1000

    def shutdown(self):
        # This will be called by the pykManager to shut down the thing
        # immediately.
        if not manager.options.nomusic and manager.audioProps:
            pygame.mixer.music.stop()
        PykPlayer.shutdown(self)

    def do_stuff(self):
        PykPlayer.do_stuff(self)

        if self.State == STATE_PLAYING or self.State == STATE_CAPTURING:
            self.currentMs = int(
                self.get_pos() + self.internal_offset_time + manager.settings.SyncDelayMs
            )
            self.colourUpdateMs()

            # If we're not using the automatic midi timer, we have to
            # know to when stop the song at the end ourselves.
            if self.currentMs > self.midifile.last_note_ms:
                self.close()

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

    def do_resize(self, new_size):
        # This will be called internally whenever the window is
        # resized for any reason, either due to an application resize
        # request being processed, or due to the user dragging the
        # window handles.
        self.initFont()
        self.lyrics = self.midifile.lyrics.wordWrapLyrics(self.font)

        self.topLine = 0
        self.currentLine = 0
        self.currentColourMs = 0
        self.nextLine = 0
        self.nextSyllable = 0
        self.nextColourMs = 0
        self.nextChangeMs = 0

        self.screenDirty = True
        self.colourUpdateMs()

    def colourUpdateMs(self):
        # If there's nothing yet to happen, just return.
        if self.nextChangeMs is None or self.currentMs < self.nextChangeMs:
            return False

        syllables = self.getNewSyllables()
        self.nextChangeMs = self.nextColourMs

        # Is it time to scroll?
        syllables = self.considerScroll(syllables)

        if self.screenDirty:
            # If the whole screen needs to be redrawn anyway, just do
            # that.
            self.repaintScreen()

        else:
            # Otherwise, draw only the syllables that have changed.
            x = None
            for syllable, line in syllables:
                self.drawSyllable(syllable, line - self.topLine, x)
                x = syllable.right

            manager.flip()

        return True

    def getNewSyllables(self):
        """Scans the list of syllables and returns a list of (syllable,
        line) tuples that represent the syllables that need to be
        updated (changed color) onscreen.

        Also updates self.currentLine, self.currentColourMs, self.nextLine,
        self.nextSyllable, and self.nextColourMs."""

        syllables = []

        while self.nextLine < len(self.lyrics):
            line = self.lyrics[self.nextLine]
            while self.nextSyllable < len(line):
                syllable = line[self.nextSyllable]
                if self.currentMs < syllable.ms:
                    # This is the first syllable we should *not*
                    # display.  Stop here.
                    self.nextColourMs = syllable.ms
                    return syllables

                syllables.append((syllable, self.nextLine))
                self.currentLine = self.nextLine
                self.currentColourMs = syllable.ms
                self.nextSyllable += 1

            self.nextLine += 1
            self.nextSyllable = 0

        # There are no more syllables to be displayed.
        self.nextColourMs = None
        return syllables

    def considerScroll(self, syllables):
        """Determines whether it is time to scroll the screen.  If it
        is, performs the scroll (without flipping the display yet),
        and returns the new list of syllables that need to be painted.
        If it is not yet time to scroll, does nothing and does not
        modify the syllable list."""

        # If the player's still singing the top line, we can't scroll
        # it off yet.
        if self.currentLine <= self.topLine:
            return syllables

        # If the rest of the lines fit onscreen, don't bother scrolling.
        if self.topLine + self.numRows >= len(self.lyrics):
            return syllables

        # But don't scroll unless we have less than
        # PARAGRAPH_LEAD_TIME milliseconds to go.
        timeGap = 0
        if self.nextColourMs is not None:
            timeGap = self.nextColourMs - self.currentColourMs
            scrollTime = self.nextColourMs - PARAGRAPH_LEAD_TIME
            if self.currentMs < scrollTime:
                self.nextChangeMs = scrollTime
                return syllables

        # Put the current line on self.viewRow by choosing
        # self.topLine appropriately.  If there is a long gap between
        # lyrics, go straight to the next line.
        currentLine = self.currentLine
        if timeGap > PARAGRAPH_LEAD_TIME:
            currentLine = self.nextLine
        topLine = max(min(currentLine - self.viewRow, len(self.lyrics) - self.numRows), 0)
        if topLine == self.topLine:
            # No need to scroll.
            return syllables

        # OK, we have to scroll.  How many lines?
        linesScrolled = topLine - self.topLine
        self.topLine = topLine
        if linesScrolled < 0 or linesScrolled >= self.numRows:
            # Never mind; we'll need to repaint the whole screen anyway.
            self.screenDirty = True
            return []

        linesRemaining = self.numRows - linesScrolled

        # Blit the lower part of the screen to the top.
        y = Y_BORDER + linesScrolled * self.lineSize
        h = linesRemaining * self.lineSize
        rect = pygame.Rect(X_BORDER, y, manager.displaySize[0] - X_BORDER * 2, h)
        manager.surface.blit(manager.surface, (X_BORDER, Y_BORDER), rect)

        # And now fill the lower part of the screen with black.
        y = Y_BORDER + linesRemaining * self.lineSize
        h = linesScrolled * self.lineSize
        rect = pygame.Rect(X_BORDER, y, manager.displaySize[0] - X_BORDER * 2, h)
        settings = self.song_db.Settings
        manager.surface.fill(settings.KarBackgroundColour, rect)

        # We can remove any syllables from the list that might have
        # scrolled off the screen now.
        i = 0
        while i < len(syllables) and syllables[i][1] < self.topLine:
            i += 1
        if i:
            syllables = syllables[i:]

        # And furthermore, we need to draw all the syllables that are
        # found in the newly-appearing lines.
        for i in range(self.topLine + self.numRows - linesScrolled, self.topLine + self.numRows):
            line = self.lyrics[i]
            for syllable in line:
                syllables.append((syllable, i))

        return syllables


def usage():
    print("Usage:  %s <kar filename>" % os.path.basename(sys.argv[0]))


# Can be called from the command line with the CDG filepath as parameter
def main():
    player = MidPlayer(None, None)
    if player.isValid:
        player.play()
        manager.wait_for_player()


if __name__ == "__main__":
    sys.exit(main())
