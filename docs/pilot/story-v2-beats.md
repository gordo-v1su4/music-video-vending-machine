# I Ran pilot v2: story beats on the music

User feedback on the first cut (2026-09-28): the crowd pull is slow; the stranger twist does not read (he
looks like Rafa, we never see his face, her reaction never lands); no surreal/dream moments; the edit needs
speed ramps and accents that hit the music. Visual and cutting target: `seedance-reference-cuts.md`.

Chunks come from the studio's edit plan at 45% density (`.runtime/gen/i-ran-pilot/edit-plan.json`);
shot slots, impacts, stutters and builds are from the song analysis, not hand timing.

| Chunk | Song | Music | Beat |
|---|---|---|---|
| 23 | 3:32-3:40 | break, quiet | Lune alone in the crowd, still, searching; held close-up where the longing reads. One flash insert of Rafa (memory). |
| 24 | 3:40-3:49 | break -> chorus, impact 3:47.1 | She glimpses Rafa across the crowd, reaches toward camera ("wait... let me through"). Speed ramp up; on the 3:47 hit the crowd swallows her with a **dolly zoom** (Vertigo / Jaws effect: camera pulls back while the lens zooms in, so she holds her size while the crowd behind her stretches and warps), then a fast whip as she's pulled under. |
| 25 | 3:49-3:58 | chorus, hits | Jungle run montage: POV through palms -> her running looking back -> flash eyes -> flash boots in mud -> bursting onto the festival ridge under the moon. (Plain-vs-song A/B test chunk.) |
| 26 | 3:58-4:06 | chorus, build from 4:05.5 | Dream: the rope bridge. They kiss on the edge under the moon; the bridge sways into slow motion; flash inserts of her foot slipping as the build starts. |
| 27 | 4:06-4:14 | inst, impact on every beat | The fall: freefall through mist and lasers, strobe-cut on every beat (flash/pulse), her face between terror and bliss. |
| 28 | 4:14-4:24 | inst, stutter rolls 4:16-4:19, impact 4:20 | She lands stumbling in the crowd (landing stuttered on the roll) and falls into a man's arms: relief, a smile. He is seen only from behind. |
| 29 | 4:24-4:34 | inst, build to 4:31.6 | The reveal: slow push as he turns; on the peak hit, hard cut to his face, clearly not Rafa. Cut to her: smile collapses into confusion then hurt, held in slow motion. |
| 30 | 4:34-4:42 | verse, calm | She pulls away; he is bewildered. Alone again, searching the crowd. |

## Making the twist read

1. Establish Rafa's face: a clean close-up in chunks 23-24 (curly black hair, goatee, open olive shirt).
2. The stranger is a separate character with contrasting traits (e.g. shaved or bleached-blond head,
   clean-shaven, a different coloured shirt), with his own identity text so the model cannot blend him
   into Rafa. His face gets one full-frame, held beat.
3. Her expression is directed explicitly in the prompt ("her smile falls, lips part, confusion turns to
   hurt") and held >= 1.5 s, slowed in the edit so it breathes.

## Movement: accents that are not cuts

Style (user reference): pedestrian / lyrical contemporary movement, i.e. everyday actions (walking,
turning, reaching, falling, looking back) that flow in and out of short danced phrases. Musicality: the body
lands the song's accents.

- Impacts that are not cut points become movement hits inside a shot, timestamped in the prompt like cuts:
  `At 00:01.30, she snaps her head toward the camera`. Hit vocabulary: sharp stop / freeze, head snap,
  hand flick, torso contraction, drop, suspension then release.
- The almost-touch (chunk 24, on the 3:47.1 impact and the accents after it): her hand reaches toward
  camera -> hard cut to a close-up of two hands -> on the next accent his fingers stop a finger-width from
  hers (a movement hit, no cut) -> on the next accent the crowd rips her away (speed ramp into the whip).
- Danced phrases on the densest hit runs (chunk 27 fall, chunk 28 landing); pedestrian movement on the calm
  stretches (23, 30) so the dance reads as an eruption, not a constant.

## Speed ramps: generate slow, speed up in the edit

User decision (2026-09-28): ramp shots are generated in slow motion and sped up in the edit, never slowed
down after the fact. Speeding up only drops frames (no interpolation artifacts), and slow-motion prompts
give the model more frames per moment, which renders better.

- Prompt: shots under a build say "filmed in slow motion, half speed".
- Edit: the ramp starts near source speed (the dreamy slow look) and accelerates to 2-3x into the hit, so
  it lands on the impact at real speed or faster.
- Budget: generated length = the integral of playback speed over the shot's edit time (a 2 s ramp averaging
  2x needs ~4 s of footage). The chunk planner counts ramp shots at generated length, so chunks around
  builds carry fewer shots.

## Edit effects per beat

- Speed ramps: into the 3:47.1 impact (24), across the 4:05.5-4:13 build into the fall (26-27), and the
  4:19.7-4:31.6 build into the reveal (28-29); slow motion on her reaction (29).
- Stutters on the 4:16-4:19 drum rolls (the landing, 28).
- Flash/brightness pulses on the per-beat impacts of the fall (27).
- Wardrobe continuity (plan `look`s) holds in every shot, dream included.
