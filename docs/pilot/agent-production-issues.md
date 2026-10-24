# Agent production issue map

Published and read back in Linear on 2026-10-09: one specification and twelve focused work items, including the optional read-only reuse assessment. Project: [Music Video Vending Machine](https://linear.app/v1su4/project/music-video-vending-machine-ad0ab08ba80d), team V1S. Every new issue has `ready-for-agent` and the App label; readiness does not override its native blockers.

Specification: [V1S-223](https://linear.app/v1su4/issue/V1S-223/specify-independent-local-agent-production-review-and-demo-flow). Local [specification](agent-production-spec.md), [master prompts](agent-production-master-prompts.md) and [skill setup audit](../agents/skill-audit.md).

| Issue | Complete vertical slice | Existing parent | Native blockers |
| --- | --- | --- | --- |
| [V1S-224](https://linear.app/v1su4/issue/V1S-224/audit-and-prepare-approved-rafa-lune-environment-and-motion-references) | Audit and prepare approved Rafa, Lune, environment and motion references | V1S-105 | None |
| [V1S-225](https://linear.app/v1su4/issue/V1S-225/plan-and-persist-sequence-clip-and-generated-shot-candidates) | Plan and persist Sequence, Clip and Generated-shot candidates | V1S-106 | V1S-224 |
| [V1S-226](https://linear.app/v1su4/issue/V1S-226/compile-and-lint-h3-prompts-against-approved-workflow-input-maps) | Compile and lint H3 prompts against approved workflow input maps | V1S-107 | V1S-225 |
| [V1S-227](https://linear.app/v1su4/issue/V1S-227/run-isolated-prompt-teams-with-configurable-provider-handoffs) | Run isolated prompt teams with configurable provider handoffs | V1S-103 | V1S-226 |
| [V1S-228](https://linear.app/v1su4/issue/V1S-228/launch-visible-local-renders-and-reconcile-durable-output-receipts) | Launch visible local renders and reconcile durable output receipts | V1S-102 | V1S-226 |
| [V1S-229](https://linear.app/v1su4/issue/V1S-229/execute-and-inspect-revision-bound-native-interior-guide-trials) | Execute and inspect revision-bound native interior-guide trials | V1S-102 | V1S-228 |
| [V1S-230](https://linear.app/v1su4/issue/V1S-230/review-anonymous-shots-whole-clips-and-sequence-context-independently) | Review anonymous shots, whole clips and sequence context independently | V1S-108 | V1S-228 |
| [V1S-231](https://linear.app/v1su4/issue/V1S-231/keep-usable-shot-ranges-and-recheck-contextual-musical-edit-joins) | Keep usable shot ranges and recheck contextual musical-edit joins | V1S-107 | V1S-230 |
| [V1S-232](https://linear.app/v1su4/issue/V1S-232/approve-bounded-evidence-driven-repairs-and-re-review-candidates) | Approve bounded evidence-driven repairs and re-review candidates | V1S-108 | V1S-227, V1S-231 |
| [V1S-233](https://linear.app/v1su4/issue/V1S-233/present-a-short-local-end-to-end-production-and-improvement-demo) | Present a short local end-to-end production and improvement demo | V1S-155 | V1S-232, V1S-229, V1S-234 |
| [V1S-234](https://linear.app/v1su4/issue/V1S-234/polish-the-demo-production-and-review-journey-in-the-existing-dark-ui) | Polish the integrated dark production/review demo journey | V1S-155 | V1S-231 |
| [V1S-235](https://linear.app/v1su4/issue/V1S-235/assess-project-stack-reusable-contracts-and-independent-app) | Read-only Project Stack reuse assessment and independent-app alternative | V1S-155 | None; does not block quick demo |

The first implementation frontier is **V1S-224**; optional assessment **V1S-235** can start independently. Independent teams and visible render operation branch after prompt compilation; guided trials and Review branch after the operator slice. Repair joins independent critique and salvage; UI refinement completes the integrated presentation after salvage, and the demo follows repair, guided trials and that UI. Fixture visual exploration may proceed earlier but does not complete the real integrated journey. Blocks are the minimal direct edges; transitive prerequisites remain enforced.

Coverage reconciliation added explicit UI refinement and optional donor assessment rather than treating these branches as already decided or implemented. V1S-229 now supports approved one-or-more guides and controlled zero/one/two-guide comparisons; anchor conflict remains a hypothesis.

Existing parent descriptions and states were read back unchanged for V1S-102,103,105,106,107,108,155. V1S-111/112 and the release/deployment gates remain open. These children do not claim the broader roadmap complete. No implementation, merge, deployment or render is authorized by the readiness label alone.

## Slice completion

Each issue contains an observable end-to-end behavior, acceptance checks, source specification and native parent/blocking links. Use one fresh implementation context per slice and work the dependency-ready frontier. Read actual current source/runtime artifacts before implementation; receipts and current render findings remain in the [experiment evidence](rafa-render-experiment-results.md).

Validation: project UUID `8be90960-579a-4e33-b7d9-fbecb32a046b`; labels, parent IDs and exact blocking sets confirmed through issue reads. Publication receipts and verification data are retained under the local planning scratch folder. No duplicate GitHub issues were created.

## Remote production rendering

- [V1S-236 — Connect a hosted app to local SwarmUI rendering with authenticated remote jobs](https://linear.app/v1su4/issue/V1S-236/connect-a-hosted-app-to-local-swarmui-rendering-with-authenticated): Music Video Vending Machine; parent V1S-102; related V1S-228; Backlog, ready-for-agent. Covers an authenticated private route or outbound worker, externally initiated production jobs, hosted/local progress visibility, metadata and parameter reuse, authorization and reconnect/offline recovery. Publication does not mean remote access is configured. Production 7861 → managed 7821; standalone 8188 remains experimentation. No network exposure or authentication change was made by this planning pass.
