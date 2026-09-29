"""API-format ComfyUI graphs for the MVVM production path.

Stills and edits use Qwen Image 2.1 (not Qwen Image Edit 2511). Clips use
MiniMax H3 image-to-video from an approved keyframe so identity carries from
the first frame. Model filenames match the Swarm-managed V89 backend.
"""

QWEN = {
    "unet": "qwen_image_2.1_int8_convrot.safetensors",
    "clip": "qwen3vl_8b_bf16.safetensors",
    "vae": "qwen_image_2.1_vae_bf16.safetensors",
}
H3 = {
    "unet": "minimax_h3_fl2va_pruned_w4a8_mixed.safetensors",
    "clip": "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors",
    "vae": "minimax_h3_video_vae_fp16.safetensors",
    "audio_vae": "minimax_h3_audio_vae_fp32.safetensors",
}


def snap32(value):
    return max(32, int(round(value / 32)) * 32)


def h3_length(seconds):
    """Smallest H3 frame count (17k+5 grid at 24 fps) covering `seconds`, min 124."""
    frames = max(124, int(-(-seconds * 24 // 1)))
    return frames + (17 - (frames - 5) % 17) % 17


def qwen21_image(prompt, refs, width, height, seed, prefix, steps=40, ref_resolution=1024, unet=None,
                 init_image=None, denoise=1.0, mask_image=None):
    """Text-to-image (no refs) or reference edit/composite (refs = uploaded names).

    init_image + denoise < 1: start from that image (scaled to the canvas) instead of an empty latent, so its
    composition, framing and light survive and only `denoise` of it is re-rendered (image-to-image).
    mask_image (with init_image): only the white area of that mask is re-rendered (inpaint); the rest stays exact."""
    g = {
        "unet": {"class_type": "UNETLoader", "inputs": {"unet_name": unet or QWEN["unet"], "weight_dtype": "default"}},
        "cache": {"class_type": "QwenImage21Cache", "inputs": {"model": ["unet", 0], "device": "auto", "dtype": "default"}},
        "clip": {"class_type": "CLIPLoader", "inputs": {"clip_name": QWEN["clip"], "type": "qwen_image", "device": "default"}},
        "vae": {"class_type": "VAELoader", "inputs": {"vae_name": QWEN["vae"]}},
        "latent": {"class_type": "EmptyLatentImage", "inputs": {"width": snap32(width), "height": snap32(height), "batch_size": 1}},
    }
    encode = {"clip": ["clip", 0], "prompt": prompt, "negative_prompt": "", "resolution": ref_resolution, "vae": ["vae", 0]}
    for i, name in enumerate(refs, start=1):
        g[f"ref{i}"] = {"class_type": "LoadImage", "inputs": {"image": name}}
        encode[f"images.image_{i}"] = [f"ref{i}", 0]
    g["encode"] = {"class_type": "TextEncodeQwenImage21", "inputs": encode}
    if init_image:
        g["init"] = {"class_type": "LoadImage", "inputs": {"image": init_image}}
        g["init_scaled"] = {"class_type": "ImageScale", "inputs": {"image": ["init", 0], "upscale_method": "lanczos",
                                                                   "width": snap32(width), "height": snap32(height),
                                                                   "crop": "center"}}
        g["latent"] = {"class_type": "VAEEncode", "inputs": {"pixels": ["init_scaled", 0], "vae": ["vae", 0]}}
        if mask_image:
            g["mask"] = {"class_type": "LoadImageMask", "inputs": {"image": mask_image, "channel": "red"}}
            g["encoded"] = g.pop("latent")
            g["latent"] = {"class_type": "SetLatentNoiseMask", "inputs": {"samples": ["encoded", 0], "mask": ["mask", 0]}}
    g["sample"] = {"class_type": "KSampler", "inputs": {
        "model": ["cache", 0], "positive": ["encode", 0], "negative": ["encode", 1], "latent_image": ["latent", 0],
        "seed": seed, "steps": steps, "cfg": 1.0, "sampler_name": "euler", "scheduler": "simple",
        "denoise": float(denoise) if init_image else 1.0}}
    g["decode"] = {"class_type": "VAEDecode", "inputs": {"samples": ["sample", 0], "vae": ["vae", 0]}}
    g["save"] = {"class_type": "SaveImage", "inputs": {"images": ["decode", 0], "filename_prefix": prefix}}
    return g


QWEN_PE_CLIP = "qwen3.5_9b_qwen_image_2.1_pe_i2i.int8_convrot.safetensors"
QWEN_EDIT_UNET = "qwen_image_2.1_bf16.safetensors"  # the user's workflow; never the int8 or a LoRA for edits


def qwen21_edit(instruction, refs, seed, prefix, steps=40, resolution=1024, unet=None, pe=True, pe_seed=42):
    """The user's proven Qwen 2.1 edit (SwarmUI kim-ho-qwen/swarm-safe-qwen-2.1-pe-i2i.json), node for node.

    Straight qwen_image_2.1 bf16 (no LoRA), 40 steps euler/simple, cfg 1, denoise 1.0; refs are `<image1>..` in order,
    and the canvas is the encoder's own latent (sized from the refs), not an empty latent. With pe, the
    EditPromptRewrite node (Qwen 3.5 PE model, sampling 1.0 / 0.95 / 0 / 24000) looks at the refs and rewrites the
    instruction before encoding, exactly as in that workflow."""
    g = {
        "unet": {"class_type": "UNETLoader", "inputs": {"unet_name": unet or QWEN_EDIT_UNET, "weight_dtype": "default"}},
        "cache": {"class_type": "QwenImage21Cache", "inputs": {"model": ["unet", 0], "device": "auto", "dtype": "default"}},
        "clip": {"class_type": "CLIPLoader", "inputs": {"clip_name": QWEN["clip"], "type": "qwen_image", "device": "default"}},
        "vae": {"class_type": "VAELoader", "inputs": {"vae_name": QWEN["vae"]}},
    }
    encode = {"clip": ["clip", 0], "prompt": instruction, "negative_prompt": "", "resolution": resolution, "vae": ["vae", 0]}
    rewrite = {"prompt": instruction, "temperature": 1.0, "top_p": 0.95, "presence_penalty": 0.0,
               "max_length": 24000, "seed": pe_seed}
    for i, name in enumerate(refs, start=1):
        g[f"ref{i}"] = {"class_type": "LoadImage", "inputs": {"image": name}}
        encode[f"images.image_{i}"] = [f"ref{i}", 0]
        rewrite[f"image_{i}"] = [f"ref{i}", 0]
    if pe:
        g["pe_clip"] = {"class_type": "CLIPLoader", "inputs": {"clip_name": QWEN_PE_CLIP, "type": "qwen_image", "device": "default"}}
        g["rewrite"] = {"class_type": "QwenImage21_EditPromptRewrite", "inputs": {"clip": ["pe_clip", 0], **rewrite}}
        encode["prompt"] = ["rewrite", 0]
        g["pe_text"] = {"class_type": "PreviewAny", "inputs": {"source": ["rewrite", 0]}}
    g["encode"] = {"class_type": "TextEncodeQwenImage21", "inputs": encode}
    g["sample"] = {"class_type": "KSampler", "inputs": {
        "model": ["cache", 0], "positive": ["encode", 0], "negative": ["encode", 1], "latent_image": ["encode", 2],
        "seed": seed, "steps": steps, "cfg": 1.0, "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}}
    g["decode"] = {"class_type": "VAEDecode", "inputs": {"samples": ["sample", 0], "vae": ["vae", 0]}}
    g["save"] = {"class_type": "SaveImage", "inputs": {"images": ["decode", 0], "filename_prefix": prefix}}
    return g


def qwen21_upsample(source, width, height, seed, prefix, steps=30):
    """Detail-preserving Qwen 2.1 re-render of `source` at a larger canvas."""
    prompt = ("<image1> Preserve every element of the image exactly: identity, faces, hair, clothing, pose, layout "
              "and lighting. Upsample the image to high resolution with fine natural detail and skin texture.")
    return qwen21_image(prompt, [source], width, height, seed, prefix, steps=steps, ref_resolution=0)


def h3_i2v(first_frame, prompt, seed, prefix, width=1344, height=768, seconds=5.0, steps=20):
    return {
        "unet": {"class_type": "UNETLoader", "inputs": {"unet_name": H3["unet"], "weight_dtype": "default"}},
        "clip": {"class_type": "CLIPLoader", "inputs": {"clip_name": H3["clip"], "type": "minimax", "device": "default"}},
        "vae": {"class_type": "VAELoader", "inputs": {"vae_name": H3["vae"]}},
        "frame": {"class_type": "LoadImage", "inputs": {"image": first_frame}},
        "cond": {"class_type": "MiniMaxH3ImageToVideo", "inputs": {
            "clip": ["clip", 0], "vae": ["vae", 0], "first_frame": ["frame", 0], "prompt": prompt,
            "width": snap32(width), "height": snap32(height), "length": h3_length(seconds)}},
        "guider": {"class_type": "BasicGuider", "inputs": {"model": ["unet", 0], "conditioning": ["cond", 0]}},
        "noise": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "sampler": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "res_multistep"}},
        "sigmas": {"class_type": "BasicScheduler", "inputs": {"model": ["unet", 0], "scheduler": "simple", "steps": steps, "denoise": 1.0}},
        "sample": {"class_type": "SamplerCustomAdvanced", "inputs": {
            "noise": ["noise", 0], "guider": ["guider", 0], "sampler": ["sampler", 0], "sigmas": ["sigmas", 0], "latent_image": ["cond", 1]}},
        "decode": {"class_type": "VAEDecode", "inputs": {"samples": ["sample", 0], "vae": ["vae", 0]}},
        "audio_vae": {"class_type": "VAELoader", "inputs": {"vae_name": H3["audio_vae"]}},
        "audio": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["sample", 0], "vae": ["audio_vae", 0]}},
        "video": {"class_type": "CreateVideo", "inputs": {"images": ["decode", 0], "audio": ["audio", 0], "fps": 24}},
        "save": {"class_type": "SaveVideo", "inputs": {"video": ["video", 0], "filename_prefix": prefix, "format": "auto", "codec": "auto"}},
    }


def h3_ref2v(refs, prompt, seed, prefix, width=1344, height=768, seconds=5.0, steps=20, loras=(), sampler="res_multistep"):
    """MiniMax H3 reference-to-video: identity comes from sheet panels, no composited keyframe.

    `loras` is [(filename, strength)], e.g. a turbo LoRA with steps=4 or 8.
    """
    cond = {"clip": ["clip", 0], "vae": ["vae", 0], "audio_vae": ["audio_vae", 0], "prompt": prompt,
            "width": snap32(width), "height": snap32(height), "length": h3_length(seconds), "ref_image_size": "match"}
    g = {"unet": {"class_type": "UNETLoader", "inputs": {"unet_name": "minimax_h3_ref2va_pruned_int8_convrot.safetensors", "weight_dtype": "default"}}}
    model = ["unet", 0]
    for i, (name, strength) in enumerate(loras):
        g[f"lora{i}"] = {"class_type": "LoraLoaderModelOnly", "inputs": {"model": model, "lora_name": name, "strength_model": strength}}
        model = [f"lora{i}", 0]
    g.update({
        "shift": {"class_type": "MiniMaxH3SigmaShift", "inputs": {"model": model, "shift_video": 12.0, "shift_audio": 3.0}},
        "clip": {"class_type": "CLIPLoader", "inputs": {"clip_name": H3["clip"], "type": "minimax", "device": "default"}},
        "vae": {"class_type": "VAELoader", "inputs": {"vae_name": H3["vae"]}},
        "audio_vae": {"class_type": "VAELoader", "inputs": {"vae_name": H3["audio_vae"]}},
    })
    for i, name in enumerate(refs):
        g[f"ref{i}"] = {"class_type": "LoadImage", "inputs": {"image": name}}
        cond[f"ref_images.ref_image_{i}"] = [f"ref{i}", 0]
    g.update({
        "cond": {"class_type": "MiniMaxH3ReferenceToVideo", "inputs": cond},
        "guider": {"class_type": "BasicGuider", "inputs": {"model": ["shift", 0], "conditioning": ["cond", 0]}},
        "noise": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "sampler": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": sampler}},
        "sigmas": {"class_type": "BasicScheduler", "inputs": {"model": ["shift", 0], "scheduler": "simple", "steps": steps, "denoise": 1.0}},
        "sample": {"class_type": "SamplerCustomAdvanced", "inputs": {
            "noise": ["noise", 0], "guider": ["guider", 0], "sampler": ["sampler", 0], "sigmas": ["sigmas", 0], "latent_image": ["cond", 1]}},
        "decode": {"class_type": "VAEDecode", "inputs": {"samples": ["sample", 0], "vae": ["vae", 0]}},
        "audio": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["sample", 0], "vae": ["audio_vae", 0]}},
        "video": {"class_type": "CreateVideo", "inputs": {"images": ["decode", 0], "audio": ["audio", 0], "fps": 24}},
        "save": {"class_type": "SaveVideo", "inputs": {"video": ["video", 0], "filename_prefix": prefix, "format": "auto", "codec": "auto"}},
    })
    return g


def h3_ref2v_prompt(subjects, summary, look, shot, sound):
    """H3 reference prompt. subjects: [(description, picture_numbers[, name[, shots]])], pictures numbered from 1.

    name: the character's full name (first and last when they have both), which is also printed on their reference
        pictures, so name and face travel together (user rule 2026-09-28).
    shots: the [Shot N] numbers the subject appears in; the retention line must name those shots, not Shot 1 by
        default (a multi-shot montage whose Shot 1 lacks the subject loses their face otherwise).
    """
    # Follows the mustyrocks/PlagueKind six-section Ref2Vid contract: one line per subject, labels
    # defined before use, style/lighting stated before the first [Shot N].
    defs, keep = [], []
    for n, subject in enumerate(subjects, start=1):
        desc, pics = subject[0], subject[1]
        name = subject[2] if len(subject) > 2 else None
        shots = subject[3] if len(subject) > 3 and subject[3] else [1]
        tags = " and ".join(f"<Picture {p}>" for p in pics)
        who = (f"{name}, the person labeled \"{name.upper()}\" in {tags} (the label is for identification only; never "
               f"render any text in the video)" if name else f"the person in {tags}")
        defs.append(f"<Subject {n}> is {who} (identity and wardrobe only, not their grey studio background, lighting "
                    f"or pose): {desc}")
        where = ", ".join(f"[Shot {s}]" for s in shots)
        keep.append(f"<Subject {n}> (appears in {where}): fully_preserved - exact face, hair, skin tone and every "
                    "garment and accessory in every one of these shots; no other person shares this face or outfit.")
    parts = []
    if defs:
        parts += ["subject_definitions:", *defs, ""]
    parts += ["summary:", f"[reference generation] {summary}", ""]
    if keep:
        parts += ["retention_analysis:", *keep, ""]
    parts += ["detailed_description:", look, f"[Shot 1] {shot}", "",
              "overall_soundscape:", sound, "", "non_diegetic_music:", "N/A"]
    return "\n".join(parts)


MUSIC_HEADER = (
    "Use <Audio 1> as the master musical timing reference. Preserve the original audio continuously and synchronize "
    "visual performance, camera movement, cuts, transitions, and motion intensity to its rhythm, transients, musical "
    "phrases, builds, drops, and changes in energy. The visual editing should feel intentionally choreographed to the "
    "music, not randomly reactive.")

MUSIC_MOTION = """MOTION BEHAVIOR
Low-frequency energy and kick drums: increase physical weight, camera impact, push-ins, body movement, and large-scale motion.
Snare and sharp mid-frequency transients: trigger fast directional accents, whip-pans, abrupt framing changes, or cuts.
High-frequency percussion: influence small rapid visual details, micro-jitters, lighting accents, or very brief glitch-like events.
Rising musical energy: progressively increase camera speed, movement amplitude, and visual intensity.
Breakdowns or sparse musical passages: reduce motion, lengthen shots, and stabilize the camera.
Major drops: allow the strongest changes in shot scale, camera position, movement, or environment.

EDITING RULE
Use the supplied timestamps as explicit editing anchors. Between those anchors, interpret <Audio 1> naturally and
maintain audiovisual synchronization. Prioritize: 1. major downbeats 2. musical drops 3. phrase changes 4. strong
transients 5. rhythmic movement. Do not force a cut onto every beat. Do not create constant random cutting. The result
should feel like a music-video director choreographed the camera and edit around the track."""


def h3_music_prompt(subjects, summary, look, timeline):
    """H3 reference prompt in the user's audio-reactive music-video template (2026-09-28): <Audio 1> is the master
    timing reference, the timeline carries timestamped anchors from the edit plan, motion behaviour maps frequency
    bands to kinds of movement, and the song stays the continuous soundtrack. subjects as in h3_ref2v_prompt."""
    base = h3_ref2v_prompt(subjects, f"{MUSIC_HEADER} {summary}", look, "", "")
    head = base.split("detailed_description:")[0]
    return "\n".join([
        head.rstrip(), "", "detailed_description:", look, "", "TIMELINE", timeline, "", MUSIC_MOTION, "",
        "overall_soundscape:",
        "Preserve any intended diegetic sound while maintaining synchronization with <Audio 1>.", "",
        "non_diegetic_music:",
        "<Audio 1> remains continuous and serves as the complete musical timing reference for the target video."])


def h3_prompt(scene, motion, camera, sound="Muffled festival bass and crowd ambience. No dialogue or vocals."):
    """H3's documented multimodal prompt structure for a single continuous shot."""
    return (
        "For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.\n\n"
        f"integrated_multimodal_description: [Shot 1] {scene} {motion} {camera} "
        "Keep every person's face, hair and clothing identical to Picture 1; no cuts, no text.\n\n"
        f"overall_soundscape: {sound}\n\nnon_diegetic_music: N/A"
    )
