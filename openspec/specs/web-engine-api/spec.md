# Web Engine API Specification

## Purpose

Defines the contract of the single bridge the browser/desktop UI uses to reach
the Python karaoke engine: the `window.pykaraoke_api(name, ...args)` dispatcher
and the `pykaraoke.webapp.KaraokeApp` methods it exposes. Every method returns
JSON-friendly data (plain dicts, lists, bytes, or `None`) or a structured error
payload, so the page can stay a thin, total client that never crashes on engine
failure.

> Source: `src/pykaraoke/webapp.py` (the API) and the inline `<script type="py">`
> bridge in `src/web/index.html` (the dispatcher and value conversion).

## Requirements

### Requirement: Single dispatcher boundary

The engine SHALL be reachable from JavaScript through exactly one global
function, `window.pykaraoke_api(name, *args)`, which invokes the named method on
the single application instance. No other global, module import, or private
method SHALL cross the boundary.

#### Scenario: Named method invocation

- **WHEN** the page calls `window.pykaraoke_api("search", "queen")`
- **THEN** the engine calls `KaraokeApp.search("queen")`
- **AND** the returned Python value is converted for JavaScript

#### Scenario: Engine not yet loaded

- **WHEN** the page reaches the boundary before PyScript has published the
  dispatcher
- **THEN** the dispatcher is not a function and the page treats the engine as
  not ready instead of proceeding as if it were loaded

### Requirement: JSON-friendly boundary values

Arguments SHALL be deep-converted from JavaScript values into plain Python
values before dispatch: JavaScript objects and arrays become Python `dict` and
`list`, and `Uint8Array` arguments arrive as `bytes`. Return values SHALL be
plain Python data structures; `None` SHALL surface to JavaScript as
`undefined`.

#### Scenario: Object argument

- **WHEN** the page passes a JavaScript object as an argument
- **THEN** the engine receives a plain Python `dict`, not an opaque proxy

#### Scenario: Absent result

- **WHEN** an engine method returns `None`
- **THEN** the JavaScript caller observes `undefined`

### Requirement: Persistence round-trip

`to_json` SHALL serialize the library and settings to a JSON string, and
`from_json` SHALL restore a library previously produced by `to_json` so the
restored songs match the original library.

#### Scenario: Save then restore

- **WHEN** a library is scanned, serialized with `to_json`, and restored into a
  fresh instance with `from_json`
- **THEN** the restored library contains the same songs

### Requirement: Malformed persisted state is ignored

`from_json` SHALL tolerate input that is not valid JSON or not a mapping. It
SHALL leave the existing library untouched and SHALL NOT raise.

#### Scenario: Garbage payload

- **WHEN** `from_json` receives a non-JSON string or a missing value
- **THEN** no exception propagates and the current library is unchanged

### Requirement: Library scan from folder entries

`scan_files` SHALL accept a list of file entries shaped as
`{name, path, size}` and add the recognised karaoke songs to the library. A
missing `path` SHALL default to the entry's `name`, and entries that are not
mappings or carry unusable numeric fields SHALL be skipped instead of failing
the scan.

#### Scenario: Recognised songs are added

- **WHEN** `scan_files` receives a `.cdg` entry with a matching audio companion
- **THEN** the song is added and paired with its audio companion

#### Scenario: Junk entries are skipped

- **WHEN** the entry list contains non-mapping values or entries without usable
  metadata
- **THEN** the scan still completes and reports its total

### Requirement: Zip archive scanning

`scan_zip` SHALL accept an archive name and its bytes, remember the archive so
its members can be read later, and add the karaoke members it contains. Data
that cannot be interpreted as an archive SHALL NOT raise; the call SHALL report
zero added members.

#### Scenario: Members are added

- **WHEN** `scan_zip` receives the bytes of an archive containing a karaoke song
- **THEN** the member is added to the library

#### Scenario: Invalid archive bytes

- **WHEN** `scan_zip` receives data that is not a valid archive
- **THEN** no exception propagates and the reported added count is zero

### Requirement: Reading zip members

`read_zip_member` SHALL return the bytes of a named member inside a previously
scanned archive, and SHALL return `None` when the archive was never scanned, the
member is absent, or the archive bytes are unreadable.

#### Scenario: Member found

- **WHEN** a member of a scanned archive is requested
- **THEN** its bytes are returned

#### Scenario: Member unavailable

- **WHEN** the archive is unknown, the member is missing, or the archive is
  malformed
- **THEN** the result is `None`

### Requirement: Listing zip members

`zip_members` SHALL return the member names of a scanned archive, or an empty
list when the archive is not loaded. The cached member list SHALL be refreshed
when the same archive name is scanned again.

#### Scenario: Unknown archive

- **WHEN** `zip_members` is called for an archive that was never scanned
- **THEN** it returns an empty list

#### Scenario: Re-scan refreshes the listing

- **WHEN** an archive with the same name is scanned again with different contents
- **THEN** the member list reflects the newly scanned contents

### Requirement: Search and library queries

`search` SHALL accept a query string and a limit and return a mapping whose
`results` value is a list of song records. Queries SHALL be case-insensitive
substring matches. `library_songs` SHALL return all library songs under a
`songs` key.

#### Scenario: Case-insensitive search

- **WHEN** a query in a different case matches a song's artist or title
- **THEN** the matching song appears in `results`

#### Scenario: Full library listing

- **WHEN** `library_songs` is called
- **THEN** every song in the library is returned under `songs`

### Requirement: Song lookup

`song` SHALL return the song record for a given identifier, or `None` when no
song carries that identifier.

#### Scenario: Known identifier

- **WHEN** `song` is called with a song's identifier
- **THEN** that song's record is returned

#### Scenario: Unknown identifier

- **WHEN** `song` is called with an identifier that is not in the library
- **THEN** the result is `None`

### Requirement: Settings read and update

`get_settings` SHALL return the current settings as a mapping, including the
playback volume. `set_settings` SHALL apply only recognised keys from an update
mapping, ignore unrecognised keys, and return the updated settings.

#### Scenario: Read defaults

- **WHEN** a fresh instance reports its settings
- **THEN** the volume default is present

#### Scenario: Partial update

- **WHEN** an update supplies a recognised key such as the volume or CDG zoom
- **THEN** that setting changes and is reflected in the returned mapping

#### Scenario: Unknown key ignored

- **WHEN** an update contains a key the engine does not recognise
- **THEN** no error is raised and the settings are otherwise unchanged

### Requirement: MIDI parsing

`parse_midi` SHALL accept the bytes of a `.kar`/`.mid` file and return the
parsed lyrics-and-notes payload. Data that cannot be parsed, or that is not
byte-convertible, SHALL return a mapping containing an `error` entry instead of
raising.

#### Scenario: Invalid MIDI data

- **WHEN** `parse_midi` receives bytes that are not a valid MIDI file
- **THEN** the result contains an `error` entry

### Requirement: LRC parsing

`parse_lrc` SHALL accept lyric text and return a payload with the parsed
metadata, lyrics, and timing events. Text that is not a string, or that contains
no timed lyrics, SHALL return a mapping containing an `error` entry instead of
raising.

#### Scenario: Timed lyrics are parsed

- **WHEN** `parse_lrc` receives well-formed LRC text
- **THEN** the payload carries the metadata and the timed lyric events

#### Scenario: Untimed or invalid text

- **WHEN** `parse_lrc` receives empty text, text without timestamps, or a
  non-string value
- **THEN** the result contains an `error` entry

### Requirement: Companion ELRC word timing

`parse_lrc` SHALL accept an optional companion `elrc_text` argument. When that
companion supplies usable word timing, the returned payload SHALL carry the
word-level events and mark the payload as word-timed. When it is missing,
empty, or unusable, the plain line timing SHALL be preserved and the payload
SHALL NOT be marked word-timed. A missing or unusable companion SHALL never be
an error.

#### Scenario: Usable companion

- **WHEN** a companion `elrc_text` provides word timings for the line
- **THEN** the returned events are the word-level events and the payload is
  marked word-timed

#### Scenario: Unusable companion

- **WHEN** the companion is missing, empty, or contains no usable timing
- **THEN** the original line timing is returned unchanged, the payload is not
  marked word-timed, and no error is reported

### Requirement: Duet parts

When the lyrics name the two singers, `parse_lrc` SHALL expose the singer names
under a `parts` key and SHALL carry a per-line `part` value (`a`, `b`, or the
shared `ab`) on tagged lyric events. Word-level merging SHALL preserve the
line's `part`. Songs without duet tags SHALL return the same payload as before
duet support, with neither `parts` nor `part` present.

#### Scenario: Singers and line parts exposed

- **WHEN** the lyrics declare singer names and tag lines with part identifiers
- **THEN** the payload carries the singer-name mapping and each tagged event
  carries its part

#### Scenario: Solo payload unchanged

- **WHEN** the lyrics carry no duet information
- **THEN** neither `parts` nor a per-line `part` appears in the payload

#### Scenario: Parts survive word timing

- **WHEN** a tagged line is upgraded to word-level timing by a companion file
- **THEN** every word event keeps the line's part

### Requirement: CDG decoder lifecycle

`cdg_open` SHALL create a decoder for CD+G data and return its key, raising a
value error when the supplied data cannot be converted to bytes. `cdg_update`
SHALL advance the decoder to a millisecond position and return the changed
render state, or `None` for an unknown key. `cdg_seek` SHALL reposition a known
decoder and SHALL be a no-op for an unknown key. `cdg_close` SHALL discard the
decoder so later updates for its key return `None`.

#### Scenario: Open, update, close

- **WHEN** a decoder is opened, advanced, and then closed
- **THEN** updates before closing return render state and updates after closing
  return `None`

#### Scenario: Undecodable CDG data

- **WHEN** `cdg_open` receives data that cannot be converted to bytes
- **THEN** a value error is raised

#### Scenario: Unknown decoder key

- **WHEN** `cdg_update` or `cdg_seek` is called with a key that was never
  opened
- **THEN** `cdg_update` returns `None` and `cdg_seek` does nothing

### Requirement: CDG packet counting

`cdg_packet_count` SHALL return the number of CD+G packets in a data buffer,
derived from its length in fixed-size packets.

#### Scenario: Packet count for a buffer

- **WHEN** `cdg_packet_count` is called with a buffer of a whole number of
  packets
- **THEN** the returned count equals the number of packets in the buffer
