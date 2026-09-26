# Deployment placement: desktop and home server

Planning snapshot, 2026-09-25. Inspected canonical `C:/Users/Gordo/Documents/Github/proxmox-home` on `main` at `8c54286`, including README, AGENTS, operator-source-of-truth, endpoint index and targeted runbooks. No remote commands, health probes, credential reads, service changes or homelab edits were performed. All infrastructure facts below are **documented inventory, not live verification or a capacity guarantee**. Dates matter where runbooks disagree.

## Available machines and roles

All cited paths below are relative to `C:/Users/Gordo/Documents/Github/proxmox-home`.

| Surface | Documented or user-provided facts | Evidence and qualification |
| --- | --- | --- |
| Windows workstation | User reports RTX 5090 with 32 GB VRAM, 128 GB RAM; Windows-first Tauri, Svelte/WebGPU, local generation and Ableton. | Current interview requirement; hardware not probed in this pass. Existing desktop node is documented as `desktop-q20uuvd` in README's Current model. |
| Proxmox host | `pve-node0`, LAN `192.168.8.178`, Tailnet `100.117.157.14`. CPU documented as Ryzen 9 5900X in July; September maintenance records 64 GiB installed RAM. | `docs/ops-reference.md:24`; `docs/pve-node0-update-recovery-2026-07-04.md:53-58`; `docs/proxmox-storage-runbook.md:121-127`. July's 32 GiB RAM is superseded by September's 64 GiB. CPU has not been live rechecked. |
| Application VM | VM100 `app-vm`, LAN `192.168.8.222`, Tailnet `100.118.78.13`. July baseline has 8 vCPU; RAM increased to 40 GiB with ballooning disabled on September 21. Root virtual disk expanded to 512 GiB on Samsung 990 PRO 4 TB/local-lvm. | `docs/ops-reference.md:26`; `docs/triggerdev-vm100-runbook.md:344-355`; `docs/proxmox-storage-runbook.md:27-41,139-151`. Historical available-memory/disk figures are not current free capacity. |
| Server GPU | VM100 has RTX 4070 Ti, approximately 12 GB VRAM, replacing RTX 4090 on September 22. | `docs/ops-reference.md:26`; `docs/stack-structure-gpu-worker-guardrails.md:58-66` records 12,282 MiB. Older 4090 instructions are stale for capacity planning. |
| Storage VM | VM114 `rustfs-storage`, LAN `192.168.8.241`, Tailnet `100.99.110.105`; dedicated RustFS/media storage. Runbook specifies 4 vCPU, 4 GB RAM, 32G OS disk and 1750G data disk; September notes confirm 4 GiB RAM remains. Data mounted at `/mnt/rustfs-data`. | `docs/ops-reference.md:27`; `hostinger-ops/docs/rustfs-vm-runbook.md:95-109`; `docs/proxmox-storage-runbook.md:14-18,123-127`. RustFS version 1.0.0 is documented in September maintenance; virtual disk size is not free space. |

## Reusable documented services

- **RustFS S3 and media API on VM114:** `s3.v1su4.dev` → port 9000, `media.v1su4.dev` → port 4545, with upload/import/file/image/video-job surfaces (`docs/endpoint-index.md:36-38,124-137`). Use scoped project object namespaces; no bucket creation or storage-policy change is authorized by this research.
- **Essentia on VM100:** port 18000, public `essentia.v1su4.dev`; candidate for song timing/structure analysis (`docs/endpoint-index.md:32`). Availability and exact analysis contract need validation during implementation.
- **FFmpeg/NVENC media worker on VM100:** loopback port 18090; caption gateway on 18091 and Qwen backend on 18093 (`docs/endpoint-index.md:101-103`). Qwen is on-demand and inactive by default; a healthy gateway alone does not establish vision-model readiness. Server GPU jobs should respect existing serialization/locks and the smaller replacement GPU.
- **Trigger.dev on VM100:** existing orchestration surface on 8030 (`docs/endpoint-index.md:39,104`), updated to 4.6.3 according to September maintenance (`docs/proxmox-storage-runbook.md:128`). The user explicitly chose reuse of this self-hosted Trigger instance for durable workflows; do not build a second job scheduler. Keep the Rust application core and integrate through a thin TypeScript/Bun Trigger task layer and HTTP/worker adapters. Do not repurpose Trigger's internal database as this product's database.
- **Caddy ingress on VM100:** secondary LAN address `192.168.8.239`, with routes to app and storage services (`docs/ops-reference.md:26`; `docs/endpoint-index.md:24-27`). Existing routing is a candidate integration point, not authorization to expose a new service publicly.

## Proposed placement

1. **Windows Tauri application:** Svelte workspace, WebGPU preview, media cache/proxies, direct file access, Ableton interchange, and local worker control. Use Rust for the desktop bridge and reusable domain logic. Keep expensive inference in the provider runtimes that already support the selected models; choosing Rust does not require rewriting ComfyUI/model inference.
2. **Rust application backend on app-vm plus existing Trigger:** Rust owns project API, revisions, creative/editing rules, budget authorization, provider/agent contracts and worker capability reports. Trigger owns durable workflow execution, queues, retries and run/cancellation state. Persist product records and Trigger run IDs in the product's database, with immutable snapshots/assets in RustFS; avoid duplicating scheduler state machines. Thin TypeScript/Bun tasks call Rust services or worker adapters and return durable references. Place the product database on the VM's normal application storage and back it up. The Rust product service is proposed, not already deployed.
3. **RustFS on VM114:** originals, reference images, generated asset versions, proxies, completed renders and immutable project snapshots. A project database revision should point to durable object keys/checksums. Show **saved locally / syncing / saved to homelab** separately; an upload attempt is not a completed autosave. RustFS object storage should not be treated as a mounted transactional database directory.
4. **Worker split:** use the RTX5090 desktop for primary heavy generation; optionally dispatch bounded media analysis/transcoding or suitably sized vision work to app-vm after capability and contention checks. Reserve desktop resources while Ableton is in use. The homelab can retain projects and queue work when the desktop is offline; desktop-only jobs wait visibly and do not silently change provider or spend money.

Keep project data authoritative on the homelab with explicit revisions and a local edit journal/cache for disconnection recovery. A shared Rust domain crate can serve both Tauri and the coordinator, while network/API responsibilities remain explicit. Whether offline editing is mandatory, and how concurrent edits from another device are resolved, remain interview decisions.

## Existing Project Stack Trigger integration to adapt

Also inspected `C:/Users/Gordo/Documents/Github/project-stack-structure` source, without reading environment secrets:

- `trigger.config.ts:4-37` uses `defineConfig`, a project reference override, Bun runtime, task discovery under `src/trigger`, duration/retry defaults and FFmpeg build support. This supports a small existing-style TypeScript task package alongside a Rust core.
- `src/trigger/queues.ts:8-47` defines explicit concurrency: media pipeline 3, scene detection 3, finalization 2, assembly 2, VM100-heavy 1, paid generation 1 and external providers 2. These are current source defaults, not measured safe limits for our combined workload. Separate product projects/queues do not automatically serialize a shared physical GPU; coordinate device capacity across applications.
- `src/lib/triggerOrchestration.ts:170-201` submits local generation with input-derived idempotency key, 24-hour key TTL, single attempt, tags and run metadata. Reuse the pattern with our project/shot/asset revision identity and no duplicate paid-spend retries.
- `src/trigger/export.ts:67-80` defines a queued export task, 1800-second duration, one attempt, stored inputs and a bounded workspace. It calls existing media code rather than requiring the business logic to live inside the task definition.
- `docs/operations/trigger-production.md:3-13` documents the self-hosted VM100 project and isolation from Pindeck. Do not reuse another application's project keys or identities. Its 4.5.16 platform claim at line 8 is older than the homelab's September 4.6.3 upgrade; verify platform/SDK compatibility before deploying our tasks. No credentials, queues or deployments were changed in this pass.

## Verification boundary before deployment

Confirm actual CPU/vCPU/RAM, free disk and thin-pool headroom, GPU identity/VRAM, current workloads, storage durability and authenticated upload round-trip before setting concurrency or promising performance. Confirm desktop worker reconnect/resume, revision conflict handling and restoration from an independent backup. The September RustFS VM snapshot is documented as same-host recovery, not an independent backup (`docs/proxmox-storage-runbook.md:124`).

This note records application placement assumptions only. `proxmox-home` remains the canonical infrastructure inventory. Its operator authority document explicitly treats live hosts as final runtime truth (`docs/operator-source-of-truth.md`, Lookup Order); older worker-routing references there are superseded where September maintenance records the Cursor app-vm worker retirement (`docs/proxmox-storage-runbook.md:129`). Do not recreate retired services as part of this application.
