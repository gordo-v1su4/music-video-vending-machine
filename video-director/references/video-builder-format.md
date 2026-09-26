# VRGDG Video Builder Prompt Format

This reference describes the prompt contract observed in a finished video-builder project. Use it when the user is working with the VRGDG/Minimax H3 storyboard video builder. Do not treat rendered video files as source material.

## Primary project artifacts

Read these when present:

- `storyboard/storyboard.json` for the editable storyboard and scene metadata.
- `storyboard/storyboard_export.json` for exported scene records.
- `prompts/video_prompts.json` for generated video prompt records.
- `prompts/i2v_prompts.txt` and `prompts/t2i_prompts.txt` for image-to-video and text-to-image prompt outputs.
- `prompts/lyric_notes.txt`, subject/location notes, and `project_context/` files for creative context.

Ignore rendered videos and other generated media unless the user explicitly asks for visual review.

## Video prompt export JSON

When producing a builder-ready video prompt export, preserve this root structure:

```json
{
  "version": 1,
  "exported_at": "ISO timestamp",
  "type": "storyboard_video_prompts",
  "project_video_engine": "minimax_h3",
  "performance_mode": "singing",
  "scene_count": 20,
  "scenes": []
}
```

Each item in `scenes` uses this structure:

```json
{
  "scene": 1,
  "scene_id": "existing-id-or-new-id",
  "label": "Scene 1",
  "lyric_section": "Verse / Chorus / Intro / Outro / instrumental",
  "lyric_line": "exact lyric or [instrumental]",
  "prompt": "builder-formatted multiline prompt",
  "video_prompt_type": "rtv",
  "minimax_h3_mode": "reference_to_video",
  "video_style": "cinematic_realism",
  "video_style_custom": "",
  "performance_mode": "singing"
}
```

Preserve existing IDs when refining existing scenes. Do not silently renumber scenes or change the scene count. If creating a new project, use the project's actual scene count and existing builder conventions.

## Exact multiline video prompt layout

The `prompt` value is a single multiline string with these blocks in this order:

```text
subject_definitions:
[Define every referenced subject and picture. Use the builder's <Subject N>, <Picture N>, and <Audio 1> tokens.]

summary:
[reference generation + audio reuse] The target video is a cinematic_realism scene featuring [subjects]. <Audio 1> is reused as the complete soundtrack and timing reference.

retention_analysis:
[State what each recurring subject and environment preserves across the scene.]
<Audio 1>: fully_copy - <Audio 1> is reused 1:1 as the target video's complete final audio track.

detailed_description:
[Describe the global visual style, lighting, texture, camera language, and spatial continuity.]

[Shot 1] [Describe the starting frame, action, performance, lyric synchronization, and opening camera movement.]

[Shot 2] At [exact offset], [describe the camera cut or continuation, new framing, action progression, and performance.]

[Shot N] At [exact offset], [describe the next scheduled shot, camera movement, emotional/action progression, and the ending state of this standalone clip.]


overall_soundscape:
No additional environmental or physical sounds are added over <Audio 1>.

non_diegetic_music:
<Audio 1> is reused as the complete audience-facing song/music track.
```

The exact block names, token syntax, shot labels, and audio lines are part of the builder contract. Keep them intact. Do not replace the multiline builder prompt with a generic paragraph.

## Prompt-writing rules for this builder

- Use the exact performed lyric in `lyric_line` and in the sung-performance cue inside the prompt, using the existing `<d>[English] ... </d>` convention when the singer is performing.
- Preserve subject references and identity authority. The project uses `<Subject 1>`, `<Subject 2>`, `<Subject 3>`, `<Picture 1>`, `<Picture 2>`, `<Picture 3>`, and `<Audio 1>` tokens.
- Keep recurring character, wardrobe, location, props, lighting, and spatial anchors consistent across scenes.
- The number of internal shots is controlled by the storyboard `Cut frequency` setting and the exact scene duration. Never assume three shots. Shot 1 establishes the starting state; each later shot begins at a scheduled cut time and advances the same action while preserving continuity.
- Every shot should identify a purposeful camera action, physical character action, facial/emotional response, and relationship to the lyric or instrumental beat.
- For instrumental sections, do not invent sung lyrics. Use `[instrumental]` and describe performance or visual rhythm honestly.
- Keep the singer's visible lip, jaw, and facial movement synchronized when the scene is marked `performance_mode: singing`.
- Keep the audio statements exactly aligned with the established builder wording unless the project intentionally uses a different audio mode.
- When revising a prompt, preserve all valid metadata and references, changing only what is needed to improve the creative flow or prompt quality.

## Storyboard source record

The editable storyboard scene records contain the creative planning fields that should drive prompt generation, including:

`id`, `scene_number`, `label`, `lyrics`, `lyric_section`, `story_beat`, `performance_mode`, `subjects`, `subject_refs`, `speaker_assignments`, `setting`, `location_ref`, `shot_type`, `camera_motion`, `character_motion`, `performance_style`, `performance_direction`, `facial_performance`, `facial_performance_custom`, `facial_performance_direction`, `video_prompt_type`, `project_video_engine`, `minimax_h3_mode`, `minimax_h3_audio_mode`, `video_style`, `temporal_world_effect_override`, `timeline_start`, `timeline_end`, `exact_duration`, `video_prompt_origin`, `status`, and prompt/reference fields.

Use these fields as source data. Do not overwrite them with invented generic fields. If the user asks for a new or revised storyboard, preserve the same schema and populate only fields supported by the project.

## Quality pass

Before delivering builder-ready prompts, verify:

1. The JSON is valid and scene metadata matches the scene records.
2. Required prompt blocks appear in the required order.
3. Every referenced subject, picture, and audio token is defined or already valid in the project.
4. Lyric text matches the intended timeline and is not accidentally copied into instrumental scenes.
5. Shot timing offsets fit the scene duration.
6. The action progresses across all scheduled shots and ends in a state that can be matched by editorial continuity, without cross-scene instructions.
7. Character and location continuity is preserved.
8. The final prompt is usable by the builder without manual conversion.
## Cut frequency and internal shots

The storyboard `Cut frequency` is a scene-default setting from 0 through 10, stored for MiniMax as `minimax_h3_cut_frequency` and sometimes surfaced as `cut_frequency` or `cutFrequency`.

- `0` means one smooth, continuous, uninterrupted shot for the entire segment: no hard cut, angle reset, montage, dissolve, scene change, or transition.
- Higher values create a duration-aware cut plan. The plan determines `cut_count`, `shot_count`, and `cut_times_seconds` for that scene.
- `10` requests the maximum allowed schedule, approximately one continuity-preserving hard cut per second.
- For a duration of `D` seconds, the builder allows at most `ceil(D - 0.000001) - 1` cuts. For frequencies from 1–9, the cut count is scaled from that maximum and limited so there is room for coherent shots. At frequency 10, it uses the maximum.
- Non-maximum cuts are distributed through the segment at `D * (index + 1) / (cut_count + 1)`, rounded to three decimals. Maximum cuts occur at approximately each whole second.

For MiniMax H3, write exactly the scheduled number of shots. Begin with shot 1 at `0s`. Every scheduled cut must be an explicit timestamp block beginning with `CUT TO:` and must introduce a clearly different but continuity-preserving angle, framing, or story detail within the same scene and ongoing action. Do not add, omit, merge, or shift cuts. Do not add extra montage beats, dissolves, scene changes, or transitions outside the schedule.

The prompt should therefore use the scene's actual cut plan, for example:

```text
[Shot 1] Begin at 0s ...

At 2.667s, CUT TO: ...

At 5.333s, CUT TO: ...
```

The exact timestamps, shot count, and cut language must come from the builder's calculated plan, not from a generic three-shot template. If the project provides a saved cut plan, use it as authoritative. If only frequency and duration are available, calculate the plan using the rules above before writing the prompt.
## Conversational cut direction

The user may describe the desired editing directly instead of choosing a slider value. Interpret requests such as `no cuts`, `one continuous take`, `two cuts`, `three internal shots`, `cut on the lyric change`, `make the chorus more dynamic`, or `you decide the cuts` as creative direction.

- If the user specifies a cut count, calculate a duration-aware plan with exactly that many cuts when the scene duration allows it. Use the resulting timestamps in the prompt and identify the corresponding builder frequency or explain that the builder frequency control must be adjusted to match.
- If the requested count is impossible for the duration, explain the constraint and offer the nearest valid plan. Never silently add, remove, or redistribute cuts.
- If the user asks the director to decide, use the lyric, story, emotional intensity, action complexity, and transition needs. Favor fewer cuts for intimate, emotional, suspenseful, or physically continuous moments. Favor more cuts for energetic choruses, rapid action, instrumental builds, location reveals, or escalating visual rhythm.
- Align cuts with meaningful lyric or musical/story beats whenever possible, while still obeying the builder's exact duration and cut schedule.
- Keep a singer's visible performance readable. Do not cut so frequently that lip synchronization, emotional expression, or a single physical action becomes confusing.
- Explain the creative reasoning briefly before applying a non-obvious cut plan, especially when the user asks for help deciding.

The director can work in either direction: convert a requested cut count into the builder's frequency/timing plan, or recommend a cut count and frequency based on the scene's lyrics and story before writing the final prompt.
## Standalone scene rule

Every storyboard scene is an independently generated video. The generation model does not know that another scene exists before or after it. Each scene prompt must independently describe its own complete subjects, references, environment, opening frame, action, camera, lighting, performance, lyric, and ending state.

The full sequence should still flow when the clips are edited together, but the flow must be achieved through matching visual states written separately into adjacent prompts. Use text only to describe the handoff state; never instruct the model to access or continue from another scene.

Never include phrases such as:

- `continue from the previous scene`
- `as seen in Scene 6`
- `the next scene`
- `this becomes Scene 7`
- `match the previous shot`
- `the following shot reveals`

Instead, write the visual state directly. For example:

```text
Ending state of one standalone clip:
Emerald fabric sweeps upward and fills the lens, briefly obscuring the frame as her body rises into the teal light.

Opening state of the next standalone clip:
Emerald fabric drifts away from the lens, revealing the woman already floating motionless in deep blue water beneath a teal halo.
```

The second prompt must make sense when generated by itself. It should not say that the fabric came from another scene; it should simply begin with the fabric already in front of the lens.
## Singing performance requirement

For any scene whose `performance_mode` is `singing` and that includes a singer/vocalist, every builder prompt must explicitly state that the singer is physically and visibly singing the exact scene lyric. Include the exact line in the prompt using the project's established form, for example:

```text
<Subject 1> visibly sings the exact lyric with natural mouth, lip, jaw, and facial movement synchronized to the vocal: <d>[English] Close the door and make me hold your.</d>
```

This direction must remain present in every internal shot where the singer is visible or performing. Do not assume that `performance_mode: singing` alone is enough; the generated prompt must say what the performer is doing and what words are being sung.

Use the scene's exact lyric and speaker assignments. Do not paraphrase or invent lyrics. If the scene is marked `instrumental`, is B-roll, or the user explicitly overrides singing, do not add a sung lyric or lip-sync instruction. A singer may then appear silently, react, dance, or perform another specified action.

