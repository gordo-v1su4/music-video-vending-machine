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
A sequence of still images played against the source song to review the planned video's pacing and visual direction before video production.
_Avoid_: Finished video, rendered scene

**Production approval**:
The user's acceptance of the timed preview, reference images, and estimated cost before automated video production begins.

**Hybrid review**:
Review after the automatic musical edit that combines independent visual reviewers and deterministic evidence to judge story coherence, musical fit, continuity, and technical cut quality.
_Avoid_: Generation self-check, final QC

**Production self-check**:
Automated per-shot checks during generation for prompt/reference fit, timing, and media health, with bounded repair before the edit is submitted for Review.
_Avoid_: Review

**Character**:
A persistent visual identity whose recognizable features should remain stable across the video.
_Avoid_: Look

**Look**:
An approved appearance variant of a Character, including a particular hair and costume combination, assigned to one or more scenes or sequences.
_Avoid_: Character, outfit (when referring to the full approved variant)

**Character sheet**:
The approved visual reference set anchoring one Character Look for generation.
_Avoid_: Character profile

**Sequence**:
A contiguous group of clips and their shots planned and reviewed together as part of the musical edit.
_Avoid_: Shot

**Clip**:
A generated or supplied video asset containing one or more shots. A Sequence can use a whole clip or selected shot ranges within it.

**Repair chunk**:
A candidate edit section proposed for revision, with neighboring footage and context handles included so the user can judge continuity.
_Avoid_: Single-shot fix (unless only one shot is affected)

**Performance footage**:
Supplied footage of an artist performing or singing, treated as an intentional visual strand; word-level lip-sync is evaluated separately from story Review.
_Avoid_: Generated singing

**Director agent**:
The collaborator that develops and operates the music-video project through concrete creative and production actions, with visual results the user can inspect and revise.
_Avoid_: Chatbot

**Musical edit**:
An arrangement of the video's scenes shaped through musical timing, energy, and variation, rather than primarily through manual clip placement.

**Timeline**:
The time-based view of the musical edit, showing how scenes relate to the song. It supports inspection without requiring manual clip arrangement as the main editing workflow.

**Candidate clip**:
A generated or supplied clip being considered for a place in the musical edit, evaluated for both its own attributes and its fit with neighboring clips.

**Prompt interpretation**:
An independently authored creative treatment of the same shot brief, expressed as a generation prompt. Different interpretations can be compared while keeping the intended shot and references consistent.

**Blind candidate comparison**:
A comparison of candidate clips under anonymous labels, without revealing their prompt writer or model to reviewers before judgments are recorded. Competing prompt writers do not see one another's prompts or results during the independent comparison.

**Usable range**:
A timecoded portion of a candidate clip suitable for the intended edit even when other portions are defective. It must cover the needed action and remain suitable in context with neighboring footage.

**Workflow run**:
One execution of a generation workflow with a recorded set of inputs and settings. Its output clip may contain one or more generated shots.

**Generated shot**:
One continuous camera view within a generated clip, bounded by reviewed cuts or the clip's edges. It can be reviewed and selected independently of other shots from the same Workflow run.

**Coverage gap**:
A part of the planned video for which no suitable clip has been selected. The gap remains an explicit unresolved production need.

**Edit revision**:
A saved version of the musical edit that can be previewed against its preceding version.

**Dialogue interlude**:
A deliberate narrative scene that pauses the song for dialogue before the music resumes. Outside these breaks, the original song remains intact.

**Dramatic audio break**:
An optional, approved interruption or departure from continuous song playback that serves a story moment, such as a prelude, dialogue interlude, suspenseful cutout, or deliberate silence.

**Song time**:
A position in the original source song, used to locate musical events and lyric cues.

**Video time**:
A position in the finished video, including dialogue interludes as well as the song.
_Avoid_: Song time
