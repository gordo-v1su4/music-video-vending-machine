# Music Vending Machine

Personal narrative music-video studio. **Under construction; not production-ready.**

The approved [PRD](docs/PRD.md), [implementation backlog](docs/implementation-plan.md), and [build status](docs/build-status.md) define acceptance. Existing research is preserved under docs/research. Greptile must award the current implementation PR head 5/5 before merge, with checks green.

## Development

Requirements: Rust stable, Bun, FFmpeg/FFprobe, and PostgreSQL 17. The local coordinator is 127.0.0.1:5199; web development is 127.0.0.1:5198 with strict port binding.

For an isolated loopback-only development database (never use this trust-auth setup in deployment):

```powershell
docker run -d --name mvm-dev-postgres -p 127.0.0.1:55439:5432 -e POSTGRES_DB=mvm_dev -e POSTGRES_USER=mvm -e POSTGRES_HOST_AUTH_METHOD=trust -v mvm-dev-postgres:/var/lib/postgresql/data postgres:17.10-bookworm
$env:DATABASE_URL = 'postgres://mvm@127.0.0.1:55439/mvm_dev'
$env:MVM_DEV_LOCAL = '1'
cargo run -p mvm-coordinator
```

In another terminal:

```powershell
cd apps/web
bun install --frozen-lockfile
bun run dev
```

Local mode uses .runtime/assets and identifies itself as development. It refuses non-loopback binding. Production requires an operator token and configured RustFS credentials; copy variable **names** from .env.example and inject values privately from BWS. The coordinator does not load .env automatically.

## Verification

```powershell
cargo fmt --all -- --check
cargo test --workspace
cargo clippy --workspace --all-targets -- -D warnings
node scripts/generate-contract.mjs --check
# Integration tests require an isolated test database, never a production database:
$env:MVM_TEST_DATABASE_URL = 'postgres://mvm@127.0.0.1:55439/mvm_test'
cargo test -p mvm-coordinator --test persistence -- --ignored
cd apps/web
bun run check
bun run build
```

Health: /api/v1/health. OpenAPI: /api/v1/openapi.json, or `cargo run -p mvm-coordinator -- --openapi` without service credentials.

No generation or final export is presented as available until its real integration gates pass. Current intake caps each request at 128 MiB; stems, MIDI and lyrics have not yet received intake adapters.
