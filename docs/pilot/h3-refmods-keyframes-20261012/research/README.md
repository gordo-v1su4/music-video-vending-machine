# MiniMax H3 reference documents

Local snapshots downloaded on 2026-10-12. Upstream Markdown is preserved; original URLs are in [sources.json](sources.json).

## Documents

- [Official MiniMax full-reference prompting guide](upstream/VIDEO_PROMPT_WRITING_GUIDE_ref_en.md)
- [RefMod creation and extraction](upstream/MINIMAX_H3_REFMOD_CREATION_GUIDE.md)
- [RefMod stacking and multiple subjects](upstream/MINIMAX_H3_REFMOD_STACKING_AND_MULTISUBJECT_GUIDE.md)
- [RefMod installation and quickstart](upstream/MINIMAX_H3_REFMODS_INSTALLATION_AND_USAGE_GUIDE.md)
- [Hybrid LoRA and RefMod containers](upstream/MINIMAX_H3_HYBRID_LORA_REFMOD_CONTAINERS_GUIDE.md)
- [Community prompting guide](upstream/MINIMAX_H3_PROMPTING_GUIDE.md)
- [Benjiyaya prompt skill](prompt-skill/SKILL.md), including its README and all three reference documents.

## Verified local distinctions

- A RefMod stores reference latents; it does not train model weights. A hybrid RefLoRA also includes actual LoRA weights. These character files are RefMod-only.
- `identity_encode` in the installed pack selects Full Reference, 1024-pixel short-edge cap, zero refinement and merge off. Multiple source images in Create H3 RefMod Master are concatenated temporally and labeled video. That is container behavior, not proof the inputs were video.
- The selected character files now preserve separate image members in one native format-5 file: Rafa has seven, Lune has six. Their encoded tensors were retained exactly; originals are backed up in workspace maintenance.
- Two supported conditioning routes have different prompt behavior. H3 RefMod Text Encode presents decoded refs to Qwen and assigns Picture/Video labels. The native Reference to Video plus Apply H3 RefMod route presents the raw environment picture to Qwen and appends character reference latents afterwards. Character subjects on that second route need distinctive descriptions; loader slots are not hard subject bindings.
- The official full-reference guide allows environments as Subjects. For frames 4–6, Subject 1 is Rafa, Subject 2 is Lune, and Subject 3 is the environment sourced from Picture 1.
- Broad claims in community documents about perfect identity, exact order invariance, file sizes, token limits or voice cloning are not guaranteed by these local checks. Use actual node schemas and rendered results to assess this installation.

The latest maker still uses the upstream temporal stacking behavior. Its output would replace the corrected character containers if rerun with the same names; rerun the `maintenance/preserve_identity_still_members.py` conversion after such a rebuild. The conversion retains all selected encoded views without blending them.
