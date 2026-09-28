# Seedance reference clips: cut rhythm (I Ran)

Six user-generated Seedance clips (Higgsfield downloads, `C:\Users\Gordo\Downloads\hf_2026090*`), measured
2026-09-28 with ffmpeg scene detection (threshold 0.28). They are the visual and editing target for the
pilot: same story (moon, cliff jump, kiss in the water, festival crowd, lasers).

| Clip | Length | Cuts | Shot lengths (s) |
|---|---|---|---|
| 20260908_011842 | 15.0 | 7 | 0.29, 0.04, 0.08, 4.62, 1.96, 3.21, 4.79, 0.04 |
| 20260904_084842 | 12.0 | 5 | 3.17, 2.67, 3.50, 1.96, 0.54, 0.21 |
| 20260904_084659 | 12.1 | 2 | 9.93, 1.37, 0.80 |
| 20260907_221158 | 15.0 | 5 | 0.46, 0.71, 3.96, 2.33, 7.33, 0.25 |
| 20260907_221204 | 15.0 | 9 | 0.29, 0.38, 0.37, 1.08, 0.58, 0.92, 1.75, 2.08, 7.33, 0.25 |
| 20260908_011727 | 15.0 | 8 | 0.33, 0.38, 0.63, 3.92, 1.54, 0.50, 2.88, 4.62, 0.25 |

Mostly 480x854 (9:16), 24 fps. Very short entries (0.04-0.08 s) are flashes, not shots.

## Grammar of one generation

Each 15 s generation is a mini-sequence, not one shot or a set of similar coverage angles:

1. **Opening montage:** 3-4 flash inserts of 0.3-0.4 s on the first accents, jumping place and scale
   (crowd silhouette -> green laser -> full moon over the canopy -> a face in close-up).
2. **Story beats:** 2-4 s shots in different locations and angles (silhouetted leap off a cliff against
   the moon -> underwater -> the kiss in the water).
3. **Hold:** one 4-7 s shot that plays out.
4. **Out:** hard cut to black for ~0.25 s at the end.

## What the pipeline takes from this

- A prompt chunk (<= 12-15 s) is written as a montage whose cut timestamps come from the cut map: fast
  inserts where hits cluster, story beats on mid-energy stretches, a hold on sustained sections.
- Shots inside a chunk change place/scale freely; identity and wardrobe stay fixed (see the plan's
  wardrobe continuity rule).
- Flash inserts are cheap in a multi-cut prompt and supply the "a lot of cutting" feel without
  more generations.
