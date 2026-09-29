FROM rust:1.95-bookworm@sha256:6258907abe69656e41cd992e0b705cdcfabcbbe3db374f92ed2d47121282d4a1 AS rust-build
WORKDIR /src
COPY Cargo.toml Cargo.lock ./
COPY crates ./crates
RUN cargo build --locked --release -p mvm-coordinator

FROM debian:bookworm-slim@sha256:3783cc01769c7b2b1b83a5c5ad96c815348e28ed7da68e2e3687004faa906251 AS coordinator
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates ffmpeg curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 mvvm && useradd --uid 10001 --gid mvvm --no-create-home mvvm
COPY --from=rust-build /src/target/release/mvm-coordinator /usr/local/bin/mvvm-coordinator
USER 10001:10001
ENV MVVM_BIND=0.0.0.0:5199
EXPOSE 5199
STOPSIGNAL SIGINT
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 CMD curl --fail --silent http://127.0.0.1:5199/api/v1/health > /dev/null || exit 1
ENTRYPOINT ["/usr/local/bin/mvvm-coordinator"]

FROM oven/bun:1.3.14@sha256:e10577f0db68676a7024391c6e5cb4b879ebd17188ab750cf10024a6d700e5c4 AS web-build
WORKDIR /src/apps/web
COPY apps/web/package.json apps/web/bun.lock ./
RUN bun install --frozen-lockfile
COPY apps/web ./
ARG VITE_API_ORIGIN
RUN test -n "$VITE_API_ORIGIN" && VITE_API_ORIGIN="$VITE_API_ORIGIN" bun run build

FROM caddy:2-alpine@sha256:6aeddd44c3078b0f9a35206472a11420648a79c184603ef95957d0a20044cb2b AS web
RUN setcap -r /usr/bin/caddy
COPY --from=web-build /src/apps/web/build /srv
COPY deploy/Caddyfile /etc/caddy/Caddyfile
USER 10001:10001
EXPOSE 8080
