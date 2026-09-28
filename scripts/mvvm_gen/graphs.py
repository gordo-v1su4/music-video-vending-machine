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


def qwen21_image(prompt, refs, width, height, seed, prefix, steps=40, ref_resolution=1024, unet=None):
    """Text-to-image (no refs) or reference edit/composite (refs = uploaded names)."""
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
    g["sample"] = {"class_type": "KSampler", "inputs": {
        "model": ["cache", 0], "positive": ["encode", 0], "negative": ["encode", 1], "latent_image": ["latent", 0],
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
    """H3 reference prompt: subjects is [(description, picture_numbers)], pictures numbered from 1."""
    # Follows the mustyrocks/PlagueKind six-section Ref2Vid contract: one line per subject, labels
    # defined before use, style/lighting stated before the first [Shot N].
    defs, keep = [], []
    for n, (desc, pics) in enumerate(subjects, start=1):
        tags = " and ".join(f"<Picture {p}>" for p in pics)
        defs.append(f"<Subject {n}> is the person in {tags} (identity and wardrobe only, not their grey studio "
                    f"background, lighting or pose): {desc}")
        keep.append(f"<Subject {n}> (appears in [Shot 1]): fully_preserved - exact face, hair, skin tone and every "
                    "garment and accessory; no other person shares this face or outfit.")
    parts = []
    if defs:
        parts += ["subject_definitions:", *defs, ""]
    parts += ["summary:", f"[reference generation] {summary}", ""]
    if keep:
        parts += ["retention_analysis:", *keep, ""]
    parts += ["detailed_description:", look, f"[Shot 1] {shot}", "",
              "overall_soundscape:", sound, "", "non_diegetic_music:", "N/A"]
    return "\n".join(parts)


def h3_prompt(scene, motion, camera, sound="Muffled festival bass and crowd ambience. No dialogue or vocals."):
    """H3's documented multimodal prompt structure for a single continuous shot."""
    return (
        "For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.\n\n"
        f"integrated_multimodal_description: [Shot 1] {scene} {motion} {camera} "
        "Keep every person's face, hair and clothing identical to Picture 1; no cuts, no text.\n\n"
        f"overall_soundscape: {sound}\n\nnon_diegetic_music: N/A"
    )
