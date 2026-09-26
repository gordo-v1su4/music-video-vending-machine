use mvm_coordinator::{ApiDoc, AppState, migrate, router};
use object_store::{ObjectStore, aws::AmazonS3Builder, local::LocalFileSystem};
use sha2::{Digest, Sha256};
use sqlx::postgres::PgPoolOptions;
use std::{env, net::SocketAddr, sync::Arc, time::Duration};
use utoipa::OpenApi;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    if env::args().any(|a| a == "--openapi") {
        println!("{}", ApiDoc::openapi().to_pretty_json()?);
        return Ok(());
    }
    tracing_subscriber::fmt()
        .with_env_filter(tracing_subscriber::EnvFilter::from_default_env())
        .init();
    let development = env::var("MVM_DEV_LOCAL").as_deref() == Ok("1");
    let bind: SocketAddr = env::var("MVM_BIND")
        .unwrap_or_else(|_| "127.0.0.1:5199".into())
        .parse()?;
    anyhow::ensure!(
        !development || bind.ip().is_loopback(),
        "MVM_DEV_LOCAL requires a loopback bind"
    );
    let token = env::var("MVM_OPERATOR_TOKEN").ok();
    anyhow::ensure!(
        development || token.as_ref().is_some_and(|v| v.len() >= 32),
        "Production requires an operator token with at least 32 bytes"
    );
    let token_hash = token.map(|v| Sha256::digest(v.as_bytes()).into());
    let pool = PgPoolOptions::new()
        .max_connections(10)
        .acquire_timeout(Duration::from_secs(5))
        .connect(&env::var("DATABASE_URL")?)
        .await?;
    migrate(&pool).await?;
    let (objects, storage_name): (Arc<dyn ObjectStore>, String) =
        if development && env::var("MVM_S3_BUCKET").is_err() {
            let path = env::var("MVM_LOCAL_ASSETS").unwrap_or_else(|_| ".runtime/assets".into());
            std::fs::create_dir_all(&path)?;
            (
                Arc::new(LocalFileSystem::new_with_prefix(path)?),
                "local-development".into(),
            )
        } else {
            let endpoint = env::var("MVM_S3_ENDPOINT")?;
            let store = AmazonS3Builder::new()
                .with_bucket_name(env::var("MVM_S3_BUCKET")?)
                .with_region(env::var("MVM_S3_REGION").unwrap_or_else(|_| "us-east-1".into()))
                .with_endpoint(&endpoint)
                .with_allow_http(endpoint.starts_with("http://"))
                .with_access_key_id(env::var("MVM_S3_ACCESS_KEY")?)
                .with_secret_access_key(env::var("MVM_S3_SECRET_KEY")?)
                .build()?;
            (Arc::new(store), "rustfs".into())
        };
    let origins = env::var("MVM_ALLOWED_ORIGINS")
        .unwrap_or_else(|_| {
            "http://localhost:5198,http://127.0.0.1:5198,tauri://localhost,http://tauri.localhost"
                .into()
        })
        .split(',')
        .map(|v| v.trim().parse())
        .collect::<Result<Vec<_>, _>>()?;
    let app = router(
        AppState {
            pool,
            objects,
            token_hash,
            development,
            storage_name,
        },
        origins,
    );
    let listener = tokio::net::TcpListener::bind(bind).await?;
    tracing::info!(%bind, development, "Music Vending Machine coordinator listening");
    axum::serve(listener, app)
        .with_graceful_shutdown(async {
            let _ = tokio::signal::ctrl_c().await;
        })
        .await?;
    Ok(())
}
