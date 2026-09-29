# Private home deployment

Target: home `app-vm`, with primary Convex 13210 and private RustFS bucket `mvvm`.
The public edge is not used. Dedicated Tailscale HTTPS origin:
`https://app-vm.tail7fdbe2.ts.net:8443`.

`deploy/Dockerfile` builds separate coordinator and static web images from pinned
base-image digests and frozen Cargo/Bun dependencies. Pass the exact HTTPS
origin as `VITE_API_ORIGIN` when building the web target. No credentials are
build arguments. `.dockerignore` excludes private runtime/env files and local
dependencies. The coordinator includes FFmpeg, runs as UID 10001, and requires
its existing production session configuration. The web image removes Caddy's
unneeded privileged-port file capability and also runs as UID 10001.

`deploy/compose.yaml` serves HTTP only on app-vm loopback port 13220; the
coordinator has no host-published port. Both containers drop all capabilities,
use read-only roots and bounded memory/CPU. Writable scratch is tmpfs. Tailscale
Serve will terminate HTTPS and proxy to loopback. Never enable Funnel for this
deployment. Inspect existing Serve configuration before configuring port 8443.
The static web service starts independently of coordinator health: a backend or
storage outage must not prevent the UI from loading and showing connection errors.

## Deployment procedure

After exact-head review/CI gates and merge:

1. Take a verified independent backup. Inspect current containers and listeners.
2. Build the merged source's two targets and record image IDs, source commit and
   artifact checksums. Set `MVVM_COORDINATOR_IMAGE` and `MVVM_WEB_IMAGE` to the
   reviewed local `sha256:` image IDs in the deployment's protected configuration.
3. Place Compose in `/opt/mvvm-studio`. A root-only private env file supplies only
   `MVVM_OPERATOR_TOKEN`, `MVVM_CONVEX_SELF_HOSTED_ADMIN_KEY`, `MVVM_S3_ACCESS_KEY`
   and `MVVM_S3_SECRET_KEY`, fetched freshly from BWS. Map scoped MVVM storage
   secrets to the coordinator's existing MVM env names. Set `MVVM_PRIVATE_ENV`
   to that file's absolute path. Do not log `docker compose config` with expanded
   env values. Provider credentials remain omitted until their capability and
   approval gates are satisfied.
4. Start the dedicated stack and verify health reports production mode,
   sessionRequired true and Convex/RustFS healthy. Configure private HTTPS on
   8443 only after loopback acceptance. Test anonymous denial, bootstrap-only
   session creation, authenticated reads, logout/revocation, media and restart
   persistence. Verify the visible browser against HTTPS.
5. Record the active source/image identities and rollback configuration in the
   canonical `proxmox-home` runbook and synced operator index.

Rollback uses the previous image IDs/configuration with the same compatible
database. Do not restore an old database over newer edits to undo an image
change. Database/schema rollback needs a matching verified archive and separate
recovery decision. Do not remove Convex or RustFS volumes.

## Current verification boundary

The static web image builds and serves HTTP 200 under the same non-root,
read-only, no-capability restrictions. Header checks and Caddy config validation
pass. The coordinator image built on app-vm after Docker Desktop repeatedly
failed downloading a pinned Rust image layer; the same image pulled successfully
on app-vm. Its restricted-runtime OpenAPI check passed, image user is 10001,
and Compose configuration validates. This is packaging work, not an accepted live private deployment.
CI builds both images and smoke-tests their restricted runtimes.
