# Live capability probes — 2026-09-25

M1 remains **partial**. These are operator-run service probes, not the production worker or full-song acceptance. Machine-readable versions, hashes and run receipts are in [capabilities.json](capabilities.json). Large artifacts and original receipts are retained under the ignored `.runtime/` directory on the Windows workstation.

## Observed results

| Capability | Result | Evidence and limits |
| --- | --- | --- |
| RustFS | Service probe passed | Private `music-vending-machine` bucket; 1 MiB write/read SHA-256 match, byte range 64–127 match, anonymous GET denied with 403. [Receipt](2026-09-25-rustfs.json). Coordinator integration and a separately scoped application writer remain pending. |
| Essentia | Service probe passed | Authenticated job on the existing private Tailscale endpoint analyzed a synthetic 48-second, 120 BPM fixture: 120.011 BPM, 95 beats, 98 onsets. Returned musical boundaries need review; a tiny terminal section is not a reliable structural boundary. Native confidence 3.593 is not a normalized probability. Real-song acceptance remains pending. |
| Qwen Image 2.1 generation | Single-fixture pass | A 1280×736 still shows the requested empty recording studio, red mug, amber lamp and blue window. Provider execution 25.540 seconds. Visually inspected. |
| Qwen Image 2.1 editing | Runtime passed; preservation failed | The mug becomes green, but both 25-step and 50-step edits introduce unwanted global brightness/texture changes. Exact lighting preservation is not accepted. Initial malformed image input failed explicitly; the corrected API key is `images.image_1`. |
| MiniMax H3 image-to-video | Single-clip feasibility passed with finding | Actual H.264/AAC output: 1280×736, 24 fps, 124 frames, 5.167 seconds; provider execution 261.069 seconds. Complete FFmpeg decode passed. Temporal stills and actual browser playback were inspected; steam develops and scene geometry remains stable. A low-motion interval at 0–1.083 seconds was flagged. This is neither final 720p export nor production reliability evidence. |
| Directed review adapter | Pending | Operator observations above do not establish an autonomous vision adapter. No Gemini paid review requested. |
| Browser/WebView2 | Partial / pending | [Dark UI browser audit](2026-09-25-impeccable-ui.md) passed its scoped checks. WebGPU device-loss/proxy behavior and installed Windows WebView2 acceptance are still pending. |
| Jcode / Ableton | Pending separate evaluations | Neither is represented as operational. |

Audio inspection is limited to measurements: H3 output has stereo 32 kHz AAC, mean volume −52.5 dB and maximum −39.6 dB. No listening acceptance is claimed. The complete clip played in the browser; sampled temporal frames were visually examined. This does not claim continuous observation of every decoded frame.

## Runtime and resource boundary

The test used the explicitly allowed **standalone** installation at `D:\ComfyUI-Easy-Install_v3122\ComfyUI-Easy-Install`, bound to `127.0.0.1:8198`, with separate project input/output/temp/user directories. Custom nodes and paid API nodes were disabled. ComfyUI 0.37.0 at `73c9bad4d21e7addbe1d13bc92eee0f1431b017d`, embedded Python 3.12.10, PyTorch 2.11.0+cu130, RTX 5090 and 128 GiB host RAM were observed. One heavy GPU request ran at a time.

Five-second NVIDIA samples during the edit/H3 sequence reached **31,659 MiB whole-device usage** out of 32,607 MiB. That includes display/browser and resident allocations; it is not isolated model memory, and sampling began after the text-to-image run. `--reserve-vram 6` did not establish a six-GiB hard headroom guarantee. Coexistence with preview playback has not passed; do not raise concurrency from one.

The supplied `ComfyUI-EZi KitchenAttention.bat` delegates to the installation helper, whose launch command includes `--use-ck-attention`. This probe instead used PyTorch attention; KitchenAttention compatibility/performance is **unverified**. Preserve that distinction when reproducing or changing the runtime.

If switching to SwarmUI, use only the user-approved SwarmUI launcher and let it own its ComfyUI backend; never start the backend independently. The vault runbook identifies `D:\SwarmUI\Windows_Start_SwarmUI.bat`; the literal supplied `D:\SwarmUI\Windows\_Start\_SwarmUI.bat` was absent. No SwarmUI launch occurred. The current standalone route avoids guessing a replacement launcher. The canonical local instructions were read from `hermes-notebook-vault/10-Infrastructure/SwarmUI-ComfyUI Runtime Runbook.md`.

## Reproduction and submission safety

These scripts are bounded operator probes against fixed endpoints. They are not a multi-worker scheduler. Do not run simultaneous starts: queue preflight is not an atomic GPU lease.

```powershell
uv run --python 3.12 python -m unittest discover -s scripts -p 'test_probe*.py' -v
uv run scripts/probe-comfy.py start --workflow workflows/qwen-image-2.1-probe.json --receipt .runtime/comfy/new-qwen-receipt.json
uv run scripts/probe-comfy.py inspect --receipt .runtime/comfy/new-qwen-receipt.json
```

Use a new receipt only for a deliberately authorized new attempt. The script persists an exclusive submission intent before contacting ComfyUI, then stores the returned provider ID. An uncertain response is reconciled against history/queue using the persisted probe ID. Inspection never submits. Existing intent cannot be overwritten. Generated output remains `generated_unverified` until separately inspected.

For the edit and H3 workflows, first copy the accepted source still to the isolated input directory as `mvm-qwen-source.png`; verify its checksum against the manifest. The workflows are API-format JSON, not canvas-format exports. Uploading through `/upload/image` is another supported preparation path; no upload automation is implemented by this probe.

Storage and Essentia probes use existing BWS-injected credentials; never include their values in command arguments, receipts or Git. Run `probe-storage.py --output <new-evidence-path>` under that injected environment. `--create-bucket` is an explicit operator option, not the normal round-trip requirement. Run `probe-essentia.py start --audio <new-fixture.wav> --receipt <new-receipt.json>` and then `inspect --receipt <same-receipt.json>` under the injected `ESSENTIA_API_KEY` environment.

The first public-ingress Essentia submission returned an HTTP error without a provider ID. A live inspection of the configured service job directory and access logs found no submitted job; that receipt was retained as `reconciled_not_submitted` before a separate private-endpoint attempt. The public ingress cause remains undiagnosed. This operator reconciliation is not a completed automated recovery gate.

## Next gates

- Diagnose Qwen edit preservation using a concrete new hypothesis, retaining failed candidates and their settings.
- Validate runtime adapters, scoped storage credentials, GPU leases, cancellation and restart recovery in the application.
- Implement and test directed temporal review, including treatment of low-motion shots rather than blindly rejecting intentional stillness.
- Validate WebGPU fallback and Windows WebView2 separately; evaluate Jcode and Ableton independently.
- Render approved final output at 1280×720/24 fps after the model's native canvas, with timing and coverage checks.

Primary API/workflow references: [ComfyUI routes](https://docs.comfy.org/development/comfyui-server/comms_routes), [official API example](https://github.com/Comfy-Org/ComfyUI/blob/master/script_examples/websockets_api_example.py), [Qwen 2.1 release](https://blog.comfy.org/p/qwen-image-21-in-comfyui-open-weight), [official edit template](https://github.com/Comfy-Org/workflow_templates/blob/main/templates/image_qwen_image_2_1_image_edit.json), [official weights](https://huggingface.co/Comfy-Org/Qwen-Image-2.1). The locally hashed diffusion model and Qwen 8B text encoder match the official repository LFS hashes. The 9B PE weights are optional prompt enhancers, not the workflow's text encoder.
