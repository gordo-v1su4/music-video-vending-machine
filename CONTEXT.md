# Music Video Production

A personal workflow for turning a finished song into a complete editable music video, starting with recurring-character narrative videos.

## Language

**Source song**:
The finished song supplied by the user as the musical basis for a music video.
_Avoid_: Generated soundtrack

**Production master**:
The audio version approved by the user after any cleanup or arrangement work. It is the musical reference for video production, with separately approved dramatic audio breaks.
_Avoid_: Source song

**Narrative mode**:
A music video's visual approach built around a story with recurring characters.

**Singing mode**:
A music video's visual approach in which a visible performer sings the song's lyrics.

**Abstract mode**:
A music video's visual approach built around stylized or abstract imagery driven by the music.

**Timed preview**:
A sequence of still images played against the production master, including approved dramatic audio breaks, to review the planned video's pacing and visual direction before video production.
_Avoid_: Finished video, rendered scene

**Production approval**:
The user's acceptance of the timed preview, production master, treatment, references, Character Looks and their sequence assignments, dramatic audio breaks, route, and estimated cost or attempt allowance. It authorizes production but does not start it; changing any approved input invalidates it.

**Generate action**:
The separate, explicit user action that starts one unattended production run under the current production approval. It is unavailable while approval is missing or stale.
_Avoid_: Production approval (the approval is a precondition, not the start)

**Review**:
The distinct stage after the automatic musical edit that combines independent visual reviewers and deterministic evidence to judge story coherence, musical fit, continuity, and technical cut quality.
_Avoid_: Hybrid review, production self-check, final QC

**Production self-check**:
Automated per-shot checks during generation for prompt/reference fit, required Look, timing, and media health, with at most two replacement attempts per shot before the musical edit is submitted for Review.
_Avoid_: Generation self-check, Review

**Finding**:
A recorded observation from the production self-check or Review, tied to an edit revision or artifact, a time range, evidence, uncertainty, the reviewer or check that produced it, and a proposed action.

**Blocking finding**:
A finding of an objective failure: a coverage gap, corrupt, frozen or wrongly timed media, preview/export timing beyond one output frame, or a violation of an approved input such as an unapproved or unassigned Look. It blocks export of every range it covers until a repair resolves it. A reviewer-reported objective defect becomes blocking once deterministic evidence or the user confirms it. Subjective story and style judgments are advisory and never blocking.
_Avoid_: Blocking QC

**Character**:
A persistent visual identity whose recognizable features should remain stable across the video.
_Avoid_: Look

**Look**:
An approved appearance variant of a Character, including a particular hair and costume combination, assigned to one or more scenes or sequences.
_Avoid_: Character, outfit (when referring to the full approved variant)

**Character sheet**:
The approved visual reference set anchoring one Character Look for generation.
_Avoid_: Character profile, character identity profile

**Sequence**:
A contiguous group of shots planned and reviewed together as part of the musical edit.
_Avoid_: Shot

**Repair chunk**:
A candidate edit section proposed for revision, with neighboring footage and context handles included so the user can judge continuity. Approving a repair chunk grants its regenerated shots a fresh attempt allowance and places it in a new candidate edit revision; it becomes active only after local recheck, full-cut Review and Keep.
_Avoid_: Single-shot fix (unless only one shot is affected)

**Performance footage**:
Supplied footage of an artist performing or singing, treated as an intentional visual strand. Review checks its continuity and technical health; word-level lip-sync scoring belongs to a later milestone, not v1.
_Avoid_: Generated singing

**Director agent**:
The collaborator that develops and operates the music-video project through concrete creative and production actions, with visual results the user can inspect and revise.
_Avoid_: Chatbot

**Musical edit**:
An arrangement of the video's scenes shaped through musical timing, energy, and variation, rather than primarily through manual clip placement. Production assembles it automatically after the production self-check.
_Avoid_: Beat-derived compositing

**Timeline**:
The time-based view of the musical edit, showing how scenes relate to the song. It supports inspection without requiring manual clip arrangement as the main editing workflow.

**Candidate clip**:
A generated or supplied clip being considered for a place in the musical edit, evaluated for both its own attributes and its fit with neighboring clips.

**Coverage gap**:
A part of the planned video for which no suitable clip has been selected. The gap remains an explicit unresolved production need.

**Edit revision**:
A saved version of the musical edit that can be previewed against its preceding version. A candidate edit revision never replaces the active cut until the user chooses Keep.

**Dialogue interlude**:
A deliberate narrative scene that pauses the song for dialogue before the music resumes. Outside these breaks, the original song remains intact.

**Dramatic audio break**:
An optional, approved interruption or departure from continuous song playback that serves a story moment, such as a prelude, dialogue interlude, suspenseful cutout, or deliberate silence.

**Song time**:
A position in the original source song, used to locate musical events and lyric cues.

**Video time**:
A position in the finished video, including dialogue interludes as well as the song.
_Avoid_: Song time
