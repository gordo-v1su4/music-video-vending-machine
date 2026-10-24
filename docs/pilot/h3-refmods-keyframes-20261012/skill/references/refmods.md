# RefMod extraction and verification

## Meaning of merge, stack and bundle

H3 RefMods store reference VAE latents; they are not automatically LoRA weight changes. A hybrid safetensors can contain both, so inspect actual keys rather than deciding from its extension.

Keep these distinct: packing independent references into one file, stacking runtime references, concatenating still latents along the temporal axis, and averaging/refining/compressing latents. Do not average images merely because the user wants “multiple images in one RefMod.” In this task the desired result was one reusable file per character that retains selected independent still references.

The local version-5 bundle implementation in `custom_nodes/ComfyUI-MiniMaxH3Mod/bundle.py` stores `refmod_meta` JSON with `kind=bundle`, `_format_version=5`, and `members`; tensors are `ref_0`, `ref_1`, etc. Each image member has `[1,24,1,H,W]`, even H/W. A video member with T greater than 1 is not the desired independent-still representation. Stored bundle strengths are not baked into the latents; verify runtime loading and strengths separately.

## Creation route tested here

Use the user's selected images only, in an explicit source manifest. Do not silently re-add excluded views. Balance portrait/body coverage according to the task and reviewed results; there is no validated universal image-count or angle ratio for these characters.

Local `MiniMaxH3RefModMasterExtract` inherits extraction controls. Verify `/object_info` rather than assuming widget order. The `identity_encode` preset in local `nodes.py` forces Full Reference/encode, reference resolution 1024, Refinement Steps 0, merge false, motion_only false. This avoids the compressed/refined training path that previously produced stylized plastic results here. Those observations do not prove all compressed presets are unusable.

Tested additional controls: concept_type identity, background_retention 0, multiplier 1, max_tokens 0, max_total_tokens 0, budget_policy error, save true, save_layout bundle. Read current tooltip/code for zero-budget semantics. Do not silently truncate sources or reduce resolution to satisfy a token limit. Full references may require much more memory/compute than compact pooled adapters.

The old serializer omitted newer COMBO fields and shifted widgets. When repairing workflow JSON, enumerate the current required/optional schema in order and include COMBO, list combos, BOOLEAN, INT, FLOAT and STRING widget slots. Reimport, inspect visible preset, run via top Run, and verify the saved content.

The master maker in this installation initially produced one temporal visual stack from multiple stills. `D:/ComfyUI-Easy-Install_v3122/maintenance/preserve_identity_still_members.py` converted it into independent T=1 image members while preserving the exact tensors. It imports local core/bundle modules, backs up the original stack and depends on the source manifest. Inspect/adapt it before running; it is a project-specific migration, not a generic extractor. It uses the backup as its input, so rerunning after new extraction could restore stale content. Do not blindly reuse it. Rerunning the maker with the same filename can overwrite the independent bundle; audit afterward.

## Reviewed library and evidence

Under `D:/ComfyUI-Easy-Install_v3122/ComfyUI-Easy-Install/ComfyUI/models/refmods`:

- `Rafa_IdentityEncode_v1.safetensors`: 7 image members, views 01,02,03,04,05,07,08.
- `Lune_IdentityEncode_v1.safetensors`: 6 image members, views 01,02,03,04,06,08. User says Luna/her; preserve Lune on-disk filenames.
- No video members in these converted bundles; each observed tensor was `[1,24,1,64,114]`, 1824 patch tokens, 23712 visual tokens across 13 members. Verify against current contents; no universal 8192-token ceiling is established for this full-reference route.

Evidence: `maintenance/trimmed-identity-encode-sources.json`, `identity-still-members-verified.json`, original-stack backups and `repair_identity_encode_maker.py`. Older `Rafa_character_images`/other master files are separate experiments; do not substitute them by similar name.

Read-only header inspector prints metadata and tensor shapes without loading tensor payloads or rewriting files. It cannot certify identity or conditioning. For every new bundle also load through the installed bundle loader, verify member count/kind/T, compare source manifest and check reference-map/guider wiring. Render a small reviewed test before adopting it.

## Subject routing and environment

Do not assume member index automatically equals Subject index. Check the installed reference map and prompt, especially when multiple members belong to one person. Label Rafa/Lune distinctly in text and state what each reference supplies. Environment may be a subject/world reference; it need not be encoded using an identity preset. ReferenceToVideo naming is an API label, not proof that still sources are videos.

For the currently preferred still route, raw environment and character sheets are active and RefModApply is disabled. Do not claim the improved still is proof of RefMod conditioning.

## Documentation authority

Saved upstream docs live at `D:/ComfyUI-Easy-Install_v3122/docs/minimax-h3/upstream`: creation, stacking/multisubject, installation/usage, hybrid containers, prompting and official reference prompt guide. `sources.json` records source URLs and hashes. Read relevant sections; verify claims against installed implementation. Do not repeat guide claims such as guaranteed identity lock, noise cancellation, exact percentages or universal budgets as proven results.
