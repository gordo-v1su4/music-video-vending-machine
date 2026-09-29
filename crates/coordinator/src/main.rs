use anyhow::Context;
use mvm_coordinator::{ApiDoc, AppState, reconcile_uploads, router};
use object_store::{ObjectStore, aws::AmazonS3Builder};
use sha2::{Digest, Sha256};
use std::{env, net::SocketAddr, sync::Arc, time::Duration};
use utoipa::OpenApi;

/// Coordinator settings are named MVVM_* (2026-09-29). The retired MVM_* spelling is still read, with a warning,
/// until the server's private env file is renamed; then delete this fallback.
/// Retired names actually read this run, reported once at startup so the rename can be confirmed per environment.
static RETIRED_READ: std::sync::Mutex<Vec<String>> = std::sync::Mutex::new(Vec::new());

fn setting(name: &str) -> Result<String, env::VarError> {
    env::var(format!("MVVM_{name}")).or_else(|_| {
        let retired = env::var(format!("MVM_{name}"));
        if retired.is_ok() {
            tracing::warn!("MVM_{name} is a retired name; rename it to MVVM_{name}");
            let mut seen = RETIRED_READ.lock().unwrap();
            if !seen.iter().any(|n| n == name) {
                seen.push(name.to_string());
            }
        }
        retired
    })
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    if env::args().any(|a| a == "--openapi") {
        println!("{}", ApiDoc::openapi().to_pretty_json()?);
        return Ok(());
    }
    tracing_subscriber::fmt()
        .with_env_filter(tracing_subscriber::EnvFilter::from_default_env())
        .init();
    let development = setting("DEV_LOCAL").as_deref() == Ok("1");
    let bind: SocketAddr = setting("BIND")
        .unwrap_or_else(|_| "127.0.0.1:5199".into())
        .parse()?;
    anyhow::ensure!(
        !development || bind.ip().is_loopback(),
        "MVVM_DEV_LOCAL requires a loopback bind"
    );
    let token = setting("OPERATOR_TOKEN").ok();
    anyhow::ensure!(
        development || token.as_ref().is_some_and(|v| v.len() >= 32),
        "Production requires an operator token with at least 32 bytes"
    );
    let token_hash = token.map(|v| Sha256::digest(v.as_bytes()).into());
    let convex_client = mvm_coordinator::convex::Client::new(
        &env::var("CONVEX_SELF_HOSTED_URL")
            .context("CONVEX_SELF_HOSTED_URL is required; PostgreSQL fallback is disabled")?,
        &env::var("MVVM_CONVEX_SELF_HOSTED_ADMIN_KEY")?,
    )?;
    let convex = Some(convex_client.clone());
    anyhow::ensure!(
        setting("S3_BUCKET").is_ok(),
        "MVVM requires configured RustFS storage"
    );
    let endpoint = setting("S3_ENDPOINT").context("MVVM_S3_ENDPOINT is required")?;
    let objects: Arc<dyn ObjectStore> = Arc::new(
        AmazonS3Builder::new()
            .with_bucket_name(setting("S3_BUCKET")?)
            .with_region(setting("S3_REGION").unwrap_or_else(|_| "us-east-1".into()))
            .with_endpoint(&endpoint)
            .with_allow_http(endpoint.starts_with("http://"))
            .with_access_key_id(setting("S3_ACCESS_KEY").context("MVVM_S3_ACCESS_KEY is required")?)
            .with_secret_access_key(setting("S3_SECRET_KEY").context("MVVM_S3_SECRET_KEY is required")?)
            .build()?,
    );
    let origins = setting("ALLOWED_ORIGINS")
        .unwrap_or_else(|_| {
            "http://localhost:5198,http://127.0.0.1:5198,tauri://localhost,http://tauri.localhost"
                .into()
        })
        .split(',')
        .map(|v| v.trim().parse())
        .collect::<Result<Vec<_>, _>>()?;
    let state = AppState {
        convex,
        transcription: mvm_coordinator::transcription::Service::from_env()?,
        analysis: mvm_coordinator::analysis_jobs::Service::from_env()?,
        objects,
        token_hash,
        development,
        storage_name: "rustfs".into(),
        object_bucket: setting("S3_BUCKET")?,
    };
    let retired = RETIRED_READ.lock().unwrap().clone();
    if retired.is_empty() {
        tracing::info!("settings: all read from MVVM_ names (no retired MVM_ names in use)");
    } else {
        tracing::warn!(
            "settings: {} retired MVM_ name(s) still in use: {}; rename them to MVVM_",
            retired.len(),
            retired.join(", ")
        );
    }
    let recovery_state = state.clone();
    let recovery = tokio::spawn(async move {
        let mut interval = tokio::time::interval(Duration::from_secs(30));
        interval.set_missed_tick_behavior(tokio::time::MissedTickBehavior::Skip);
        let mut next_session_prune = tokio::time::Instant::now();
        loop {
            interval.tick().await;
            if tokio::time::Instant::now() >= next_session_prune {
                let prune_failed = convex_client
                    .mutation::<serde_json::Value>(
                        "maintenance:pruneSessions",
                        serde_json::json!({}),
                    )
                    .await
                    .is_err();
                if prune_failed {
                    tracing::warn!("Ended session cleanup unavailable; will retry in one hour");
                }
                next_session_prune = tokio::time::Instant::now() + Duration::from_secs(3600);
            }
            match reconcile_uploads(&recovery_state).await {
                Ok(recovered) if recovered > 0 => {
                    tracing::info!(recovered, "Interrupted uploads recovered")
                }
                Err(_) => {
                    tracing::warn!("Upload reconciliation unavailable; durable intents retained")
                }
                _ => {}
            }
        }
    });
    let analysis_worker = tokio::spawn(mvm_coordinator::analysis_jobs::run(state.clone()));
    let transcription_worker = tokio::spawn(mvm_coordinator::transcription::run(state.clone()));
    let app = router(state, origins);
    let listener = tokio::net::TcpListener::bind(bind).await?;
    tracing::info!(%bind, development, "Music Video Vending Machine coordinator listening");
    axum::serve(listener, app)
        .with_graceful_shutdown(async {
            let _ = tokio::signal::ctrl_c().await;
        })
        .await?;
    recovery.abort();
    analysis_worker.abort();
    transcription_worker.abort();
    Ok(())
}
