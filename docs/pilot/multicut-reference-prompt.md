# Multi-cut reference prompt (H3, 5 shots / 4 hard cuts, 15 s)

Source: `D:\output\MiniMax_H3_00006-audio.mp4` (user test, official ComfyUI H3 graph: fl2va_pruned_int8,
qwen3vl nvfp4 TE, res_multistep/simple 20 steps, 1344x768, 24 fps, first frame = Picture 1, last frame = Picture 2).
Measured cuts (ffmpeg scene detect): 5.04 / 8.33 / 9.42 / 11.67 s vs prompted 5.3 / 8.8 / 10.0 / 12.4 s,
so cuts land 0.3-0.7 s early. Identity held across all shots incl. the 1.2 s flashback.
Use as the structural template for I Ran multi-cut sequences.

```text
How the reference pictures align with the target video — Picture 1 (from Shot 1) aligns with the 0.00-second opening frame of the target video; Picture 2 (from Shot 5) defines the exterior Video Haven shot and aligns with the 15.00-second final frame.

<Subject 1> is the pale dark-haired young male vampire-student shown in Picture 1. Fully preserve his exact facial identity, short dark hair, nose rings, faint fangs, black coat, burgundy hoodie, body proportions, age, and overall appearance throughout every shot in which he appears.

<Subject 2> is the dark-haired young male vampire shown in Picture 2 outside Video Haven. Fully preserve his exact facial identity, dark wet hair, pale complexion, blue eyes, white hoodie, backpack, body proportions, age, and overall appearance.

Visual Style: Photorealistic live-action cinematic photography. Premium contemporary supernatural college drama. The vampire world exists inside an otherwise completely normal modern city. Realistic skin, fabric, wet pavement, fluorescent interiors, practical neon, shallow depth of field, subtle film grain, physically accurate reflections and lighting. Tense, youthful, dangerous, intimate, and increasingly intense without becoming fantasy spectacle.

[Shot 1]
Begin exactly from Picture 1 inside Video Haven. <Subject 1> stands beside the DVD shelf holding a case. For a brief moment he freezes as a sudden wave of blood hunger hits him. His jaw tightens, his breathing changes, and he loses focus on the DVD.

He lowers the case and starts walking, passing extremely close to the camera on the right side. As his shoulder crosses the lens, the camera smoothly pivots around with him in one continuous physical movement, revealing his back and right profile, then falls in behind him and tracks him deeper through the store.

His pace begins controlled but gradually becomes more urgent. He briefly drags one hand along the shelving to steady himself. His breathing gets heavier. He looks over his shoulder once to make sure nobody is following him, reaches the employee-only door at the rear of the same Video Haven, slips through it, and shuts the door firmly behind him.

[Shot 2] At 00:05.300, HARD CUT. The previous store shot ends completely. A new full-frame tight handheld medium shot begins inside a cramped fluorescent employee bathroom directly behind the Video Haven back room.

The same <Subject 1> is already gripping the sink hard with both hands. Another severe wave of blood hunger hits. His knees nearly buckle and he bends forward over the sink, breathing roughly, trying desperately to control himself.

He forces his head upward and looks into the mirror. Sweat gathers on his skin. His expression shifts from pain to panic. His lips separate just enough to expose his vampire fangs. He turns on the water and splashes his face, but it does nothing. His hands tighten against the porcelain and his breathing becomes increasingly desperate.

[Shot 3] At 00:08.800, ABRUPT HARD CUT INTO FLASHBACK.

A rapid fragmented sensory memory: the exact same <Subject 1> at night under hostile red and amber light, an extreme close-up of another person's terrified eyes, a hand violently pulling away from him, his own hand grabbing for them, a fraction-of-a-second glimpse of blood against his lips, his pupils locked with predatory hunger.

The flashback is visceral and extremely brief, composed of sharp realistic memory fragments rather than a dream sequence. No magical imagery and no dissolves.

Audio abruptly changes with the image: one heavy bass impact, frightened movement, a breathless gasp, then silence.

[Shot 4] At 00:10.000, HARD CUT BACK TO PRESENT DAY in the employee bathroom.

<Subject 1> jerks upright at the sink as though the memory physically struck him. He gasps for air. His grip nearly cracks his composure. He stares at himself in the mirror, terrified of what he is becoming.

Another wave hits. He doubles over, catches himself against the sink, then slowly raises his face again. His fear begins turning into a frightening realization: this is no longer something he can simply wait out. He needs blood soon.

His fangs remain visible. His eyes sharpen. There is no full monster transformation — the danger comes from the fact that he still looks almost completely human while visibly losing control.

[Shot 5] At 00:12.400, HARD CUT TO EXTERIOR NIGHT — directly outside the exact same Video Haven where <Subject 1> is currently hiding in the back room.

The atmosphere immediately opens up: wet pavement, misty night air, warm streetlights, cool fluorescent light pouring through the Video Haven windows, practical neon reflections sliding over the sidewalk.

<Subject 2> walks into frame from the right side of the sidewalk. He has clearly come here looking specifically for <Subject 1>.

He slows as he approaches Video Haven, scanning the storefront and looking through the windows with focused concern. His gaze moves across the entrance and interior as though trying to determine whether <Subject 1> is still inside. His body language is alert and purposeful, not casual.

He stops outside the store. A faint trace of blood remains at his mouth, suggesting that unlike <Subject 1>, he has already fed. He looks sharply toward the Video Haven entrance as if he can sense that something is wrong inside.

Throughout Shot 5, <Subject 2>'s movement, position, expression, wardrobe, storefront geometry, camera position, lighting, wet pavement, neon reflections, and composition progressively converge toward Picture 2.

At 00:15.000, the video lands precisely on Picture 2 as the final frame and holds completely stable.

Camera and Transitions: Five clearly separated cinematic shots. Shot 1 is a smooth continuous character-following move: begin from Picture 1, allow <Subject 1> to pass close on camera-right, smoothly pivot with him, then transition naturally into a rear tracking shot. Shot 2 uses subtle claustrophobic handheld movement. Shot 3 is an abrupt fragmented flashback using extremely fast full-frame inserts. Shot 4 immediately restores the bathroom camera language. Shot 5 is a clean exterior setup outside the same Video Haven and progressively arrives at Picture 2. All editorial changes between shots are unmistakable HARD CUTS. No dissolves, morph transitions, split screens, or blended locations.

overall_soundscape: Inside Video Haven, soft fluorescent electrical hum, distant store ambience, subtle DVD-case movement, footsteps, clothing rustle, and increasingly audible breathing. After entering the employee area, the environment becomes quieter and more enclosed. In the bathroom, harsh fluorescent hum, hands against porcelain, running water, splashes, strained breathing, and subtle internal heartbeat dominate. The flashback violently interrupts the bathroom ambience with a brief bass impact, frightened movement, and a gasp. On the hard cut back, the bathroom fluorescent hum returns immediately. At the exterior cut, sound opens into fine nighttime rain, distant traffic, wet-road tire noise, faint neon electrical buzz, and muffled Video Haven ambience through the glass.

non_diegetic_music: N/A

Constraints: Preserve the exact identity of <Subject 1> throughout the video-store scene, bathroom scene, and flashback. Preserve the exact identity of <Subject 2> throughout Shot 5 and finish exactly on Picture 2. The exterior in Shot 5 is directly outside the same Video Haven shown and entered from Shot 1; it is not a different store or unrelated location. Maintain coherent physical geography between the store interior, employee back room, bathroom, and exterior storefront. No facial drift, accidental recasting, duplicated characters, changing piercings, changing hair, unintended wardrobe mutation, extra fingers, extra limbs, body morphing, giant monster fangs, glowing aura, magical particles, teleportation, fantasy smoke, excessive gore, subtitles, added text, or watermarks. Preserve the existing Video Haven storefront signage from Picture 2. Vampire behavior remains physical, painful, dangerous, contemporary, and grounded in an otherwise realistic world.
```
