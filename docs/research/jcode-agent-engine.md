# Jcode as the music-video agent engine

Research snapshot: 2026-09-25. Documentation review only; no runtime installed or tested.

## Identity and recommendation

The user confirmed [Jcode at jcode.sh](https://jcode.sh/) as the candidate and chose to evaluate it before deciding. The site links to [1jehuang/jcode](https://github.com/1jehuang/jcode); the unrelated [cnjack/jcode](https://github.com/cnjack/jcode) is outside this evaluation.

Recommendation (architectural inference): Jcode is a credible candidate for the creative director/planner and tool-using agent. Keep it behind an application-owned adapter; keep paid generation state, assets, budgets, and render execution in application services. Evaluate with one short video before committing to the engine.

## Verified capabilities

The [official TypeScript SDK](https://jcode.sh/sdk) provides:

- Private embedded instances through `JcodeClient.launch()` and attachment to an existing daemon through `connect()`.
- Prompt execution, streaming tool/text events, permission responses, cancellation, and model selection.
- Schema-validated JSON through `runStructured()`, with bounded repair attempts. This suits shot plans and edit decisions.
- Persisted transcripts with a fixed `jcodeHome`, session discovery, and history inspection.
- Node 20+ support. Linux/macOS receive end-to-end CI coverage; Windows uses named pipes but lacks live end-to-end coverage.
- API-key provisioning and optional inherited provider logins. Inheritance is enabled by default and spends the user's quota.
- Instance-state separation, but no operating-system sandbox: tools run with the process user's privileges.
- A stable versioned protocol; disconnects/timeouts can leave mutating outcomes uncertain. Global event subscriptions do not replay events predating discovery.

The [configuration documentation](https://jcode.sh/docs) documents headless `jcode run`, a persistent daemon, direct API and subscription login routes, OpenAI-compatible endpoints, local Ollama/LM Studio routes, and project instructions/skills. MCP support is currently **stdio only**; HTTP/SSE configurations are skipped. Media APIs therefore need a local stdio wrapper or another application adapter. Remote daemon use supports SSH/socket forwarding.

The [server architecture](https://raw.githubusercontent.com/1jehuang/jcode/master/docs/SERVER_ARCHITECTURE.md) describes disk-persisted sessions and client reconnection. It also documents a shared-server idle shutdown after five minutes without clients or live headless swarm workers. Those are conversation/server lifecycle features, not evidence of transactional media-job recovery.

The repository carries the [MIT license](https://raw.githubusercontent.com/1jehuang/jcode/master/LICENSE). Preserve the required notice when distributing it; model and media-provider agreements are separate dependencies.

## Proposed boundary (inference)

1. App creates a project with immutable song, references, output requirements, and a spending limit.
2. Audio analysis produces timing data; Jcode proposes a structured treatment and shot plan using those facts.
3. App validates timing, asset references, and estimated cost, then records any required approval.
4. Narrow tools submit generation jobs and return durable job IDs. Workers poll or accept callbacks and save artifacts.
5. Jcode reviews contact sheets/available analysis, requests bounded revisions, and proposes an edit decision list.
6. Deterministic rendering assembles the approved timeline. App records provenance, costs, failures, and export checks.

The database should own project/shot/job state and idempotency keys. A resumed conversation must query those records before retrying a submission. An agent transcript alone should not authorize repeat spending after an uncertain response.

## Questions and proof needed

- Is this the intended Jcode repository?
- Is the product personal/homelab software or a service for multiple users? This changes account handling and isolation.
- Should the worker run on Linux, with local Windows GPU services exposed through adapters?
- Which model account/API route is intended, and which media-generation APIs are available?
- Can a pilot return a valid shot plan, invoke a stdio tool, survive a worker restart, and recover without duplicate paid jobs?
- Does a failed generation consume the budget, and how many replacements can the agent request automatically?
- Does the chosen version accept the image/video inputs needed for visual review through the selected model route? Not verified in this documentation pass.
- Exact custom-tool registration ergonomics, provider-specific limits, and crash recovery during a tool mutation need implementation-level validation.

Suggested pilot acceptance: one 20–30 second music excerpt, a coherent reference-driven plan, several generated shots, a rendered synchronized export, persisted cost/provenance, and a deliberately interrupted job recovered without duplicate submission. No claim of full-song reliability until that test passes.
