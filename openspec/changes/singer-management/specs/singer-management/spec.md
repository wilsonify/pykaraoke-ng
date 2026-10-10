# Delta for Singer Management

> Proposed change: `singer-management`. This change creates a new capability;
> every requirement below is new behaviour.

## Purpose

How PyKaraoke-NG models the people in the room: named singers with personal,
reusable playlists, a record of what each sang (including the key and tempo
they used), and remembered per-singer key/tempo preferences. It is the
presentation-layer counterpart to the anonymous song queue and is what makes
the app usable for a KJ working a multi-singer night.

> Source: the `ShowState` data model in `src/web/index.html`, persisted under
> the `pykaraoke-ng:show` storage key. Legacy issues addressed:
> kelvinlawson/pykaraoke#1 and #9 (singer history).

## ADDED Requirements

### Requirement: Named singers

The application SHALL let the user create named singers, select the active
singer, and delete a singer, without modal dialogs. Names SHALL be trimmed
and non-empty, SHALL be unique case-insensitively, and deleting a singer
SHALL remove their preferences and playlists while leaving history intact.
The active singer SHALL be remembered across restarts.

#### Scenario: Create and select a singer

- **WHEN** the user creates a singer named "Maria" and selects her
- **THEN** she becomes the active singer
- **AND** she is still the active singer after a restart

#### Scenario: Duplicate name rejected

- **WHEN** the user tries to create a singer whose name matches an existing
  one case-insensitively
- **THEN** no singer is created and a status message explains why

#### Scenario: Deleting a singer

- **WHEN** the user deletes the active singer
- **THEN** her playlists and preferences are removed
- **AND** her entries remain in the history list

### Requirement: Per-singer key and tempo preferences

The application SHALL remember a key offset and tempo for each singer.
Selecting a singer SHALL apply their stored preferences (or the defaults
when none are stored) to the transport controls and the current playback.
Changing the key or tempo while a singer is active SHALL update that
singer's stored preferences.

#### Scenario: Preferences applied on selection

- **WHEN** a singer whose stored key is +2 is selected while a song plays
- **THEN** the transport key offset becomes +2 and the change applies to
  the current playback

#### Scenario: Preferences updated by the controls

- **WHEN** the DJ sets the tempo to ×1.1 while a singer is active
- **THEN** that singer's stored tempo becomes ×1.1

#### Scenario: No preferences yet

- **WHEN** a singer with no stored preferences is selected
- **THEN** the key offset is 0 and the tempo is ×1.0

### Requirement: Saved singer playlists

The application SHALL save the current queue as a named playlist attributed
to the active singer (or to no singer when none is active), SHALL load a
playlist into the queue — resolving stored song ids against the current
library and skipping entries whose songs are gone — and SHALL delete a
playlist. Names SHALL be trimmed and non-empty.

#### Scenario: Save the current queue

- **WHEN** the queue holds three songs and the user saves it as "Maria's
  rotation"
- **THEN** a playlist with those three songs exists, attributed to the
  active singer

#### Scenario: Load resolves against the library

- **WHEN** a playlist is loaded and one of its songs no longer exists in
  the library
- **THEN** the queue receives the remaining songs
- **AND** a status message reports the skipped count

#### Scenario: Load replaces the queue

- **WHEN** a playlist is loaded while the queue already holds songs
- **THEN** the queue contains exactly the playlist's resolvable songs, in
  playlist order

### Requirement: Singer history

The application SHALL record a history entry whenever a song is played,
attributing it to the active singer at the time and capturing the song
label, the key offset and tempo in effect, and a timestamp. Changing the
key or tempo during a song SHALL update that song's entry. The history
SHALL be capped (oldest entries dropped), listed newest-first in the
interface, clearable, and each entry SHALL be re-queueable.

#### Scenario: A play is recorded

- **WHEN** a song finishes with a singer active
- **THEN** one history entry names the singer, the song, the key offset,
  and the tempo

#### Scenario: Mid-song key change is reflected

- **WHEN** the DJ changes the key during a recorded song
- **THEN** the song's history entry shows the final key offset

#### Scenario: Cap drops the oldest

- **WHEN** more songs have been played than the cap allows
- **THEN** the oldest entries are dropped and the newest are retained

#### Scenario: Re-queue from history

- **WHEN** the user activates a history entry's re-queue control
- **THEN** that song is appended to the queue when it still exists in the
  library

### Requirement: Versioned persistence of singer state

Singers, preferences, playlists, and history SHALL persist in a single
versioned browser-storage payload, SHALL be restored on the next launch,
and SHALL degrade to empty defaults — with no crash and no partial apply —
when the payload is missing, malformed, of an unknown version, or
structurally invalid.

#### Scenario: Round-trip

- **WHEN** singers, a playlist, prefs, and history entries exist and the
  state is saved then loaded
- **THEN** every item is restored unchanged

#### Scenario: Malformed payload

- **WHEN** the stored payload is not valid JSON or not an object
- **THEN** the application starts with empty singer state and continues
  normally

#### Scenario: Unknown version

- **WHEN** the stored payload declares a version the application does not
  recognise
- **THEN** the application starts with empty singer state rather than
  partially applying it
