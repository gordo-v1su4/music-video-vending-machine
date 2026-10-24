# Existing checks and proposed identity/wardrobe checker

Checked locally 2026-10-09. This is a source/runtime inventory and implementation guidance, not a new media review or a calibrated identity benchmark. Use the [resume handoff](../pilot/agent-production-resume.md) to start another agent system and the [specification](../pilot/agent-production-spec.md) for approvals and acceptance.

## Existing reusable pieces

| Piece | Verified behavior | Limit |
| --- | --- | --- |
| `scripts/mvvm_gen/run.py`, `Run.generate`, lines 77–114 | Records submitted prompt ID, graph hash, seed, model names, elapsed time, backend, output and `generated_unverified`. | Submits through APIs and includes a lost-prompt resubmission path. Do not invoke it as the operator for the current visible-UI experiment; use its receipt concepts, not its submission policy. |
| `Run.check`, lines 307–351 | Checks required frame coverage, resolution, black and frozen spans on the picked take; writes a report and contact sheet. | Deterministic media checks do not certify identity, wardrobe, gravity, acting or cuts. Its thresholds differ from the experimental collector; preserve exact parameters when comparing results. |
| `Run.review`, lines 353–377 | Builds three-frame contact sheets for candidate selection. | Sampled stills are not complete temporal video review. |
| `scripts/mvvm_gen/review.py`, `Store`, lines 82–126 | Stores selection decisions and redo/winner state. | A selection mechanism does not establish visual correctness. |
| `scripts/mvvm_gen/face_check.py`, lines 20–78 | Uses InsightFace `buffalo_l` normalized face embeddings and cosine similarity against a reference; samples every 0.25 seconds, chooses the largest detected face, reports clip/heuristic-shot medians and worst sampled similarity. | Model-assisted identity signal, not a calibrated binary identity gate or wardrobe check. The largest face may be the wrong subject. Missing faces, brief drift and false scene cuts need explicit handling. |
| `scripts/mvvm_gen/grade_match.py` | Transfers image colour statistics. | An image transformation, not an identity/wardrobe verifier. It must not silently alter canonical evidence. |
| Experimental collectors under `D:/output/local/MVVM/` | Preserve actual queued/executed graphs, prompts, source workflows, history, original outputs, embedded metadata and mechanical scan logs. | Folder names and preview dimensions can be stale. Trust actual receipts; collector success is not artistic acceptance. |

The active embedded Python has discoverable `insightface`, `cv2`, `numpy` and `onnxruntime` packages. The local `C:/Users/Gordo/.insightface/models/buffalo_l` directory contains detection and recognition ONNX files. Package/file presence is verified; inference loading, provider choice and calibrated scores have not been tested in this audit. The script's example points to an older Python environment which also exists; select and record the actual intended runtime rather than copying the old path blindly. No inference, GPU face-analysis job, new installation or model download was performed while video generation was active.

## Face matching: reuse with calibration

The script's introductory 0.45/0.30 guidance is an unvalidated heuristic for this material. Do not turn it into a universal pass/fail threshold. A median can conceal a short identity change; the current script does not export all sampled timestamps/boxes/scores. A failed face detection means insufficient evidence, not proof that identity changed.

Prepare a reviewed reference gallery of the approved character across front/three-quarter/profile poses, lighting and expression. Associate faces with the intended character instead of choosing the largest face indiscriminately. Test clear same-character examples, known different identities, occlusion, blur, small faces and multi-person frames. Preserve per-sample evidence, model/runtime version, reference hashes, usable-face coverage and uncertainty; flag brief low-similarity ranges for inspection. Use user-confirmed identity drift as the hard acceptance block, with the metric assisting discovery.

InsightFace's code and pretrained model terms are separate. The upstream pretrained `buffalo_l` package is described as non-commercial research use; evaluate appropriate model licensing before adopting it into a commercial product. [Official InsightFace model documentation](https://github.com/deepinsight/insightface/blob/master/python-package/docs/model_zoo.md). This local audit does not establish license clearance or pin upstream weights.

## Small visual checker service

The proposed cheaper/smaller checker needs actual vision input. Language-only capability is insufficient. Expose a narrow artifact-and-reference contract which can be hosted locally or behind a verified provider adapter; do not assume it already exists.

For each reviewed shot/range, ask fixed questions about the approved Look: same shirt type/colour, same cargo shorts rather than trousers, required hat if any, same boots and visible accessories. Return `yes`, `no` or `unknown`, with artifact hash/revision, target character, frame/time ranges, evidence crops/boxes, observed coverage, visibility limits and reason. A structured schema is deterministic; the visual judgment remains model-assisted and must be calibrated.

Evaluate visible attributes separately. Offscreen boots are unknown, not a pass or wardrobe failure. Blur, occlusion and low resolution remain unknown unless evidence supports a result. Sampling must declare its gaps; claiming consistency in every frame requires inspecting every relevant frame or explicitly reporting coverage limitations. Detector/segmentation/tracking can help localize garments, but cannot by itself establish that the garment is the approved one. Confirm alleged hard identity/Look defects before selection/export; unrelated debris differences retain their lower severity unless they break causality.

This service does not judge gravitational motion, heel-load causality, pauses/sitting, speed-ramp timing, camera continuity, emotion or storytelling. Those belong to temporal and filmmaking review. Keep technical acceptance, brief adherence and artistic preference separate; independent ordinal reviewer scores are not a statistical ranking.

## Test boundary and completion

Use the existing production packet → candidate artifact → timecoded findings → approved repair → candidate edit → Keep/export boundary. Add fixed checker fixtures with known wardrobe drift, identity drift, missing visibility and retained good ranges; require correct unknown handling and source lineage. Compare error/unknown rates, runtime and resource cost before choosing a cheaper provider. A successful completion includes real model/provider evidence, reviewed calibration examples and artifact-bound reports; a mock response or installed package alone is insufficient.

Implementation is tracked with [V1S-230](https://linear.app/v1su4/issue/V1S-230/review-anonymous-shots-whole-clips-and-sequence-context-independently). Full-clip and Sequence review plus salvage remain required even if a fixed visual checker passes.
