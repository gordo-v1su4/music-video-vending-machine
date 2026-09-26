//! Durable adapter for the same studio job endpoints used by Beatsmaxxer Pro.
use crate::{ApiError, ApiResult, AppState, analysis::SongAnalysis, sessions};
use axum::{
    Json,
    extract::{Path, State},
    http::StatusCode,
};
use chrono::{DateTime, Utc};
use reqwest::{
    Client, Url,
    header::{HeaderMap, HeaderValue},
};
use serde::{Deserialize, Serialize};
use std::{sync::Arc, time::Duration};
use utoipa::ToSchema;
use uuid::Uuid;

#[derive(Clone)]
pub struct Service {
    pub(crate) client: Client,
    pub(crate) origin: String,
}
impl Service {
    pub fn from_env() -> anyhow::Result<Option<Arc<Self>>> {
        let Ok(key) = std::env::var("ESSENTIA_API_KEY") else {
            return Ok(None);
        };
        let origin = std::env::var("ESSENTIA_API_BASE_URL")
            .unwrap_or_else(|_| "https://essentia.v1su4.dev".into());
        Ok(Some(Arc::new(Self::new(&origin, &key)?)))
    }
    pub fn new(origin: &str, key: &str) -> anyhow::Result<Self> {
        let url = Url::parse(origin)?;
        anyhow::ensure!(
            url.scheme() == "https"
                || (url.scheme() == "http"
                    && matches!(url.host_str(), Some("127.0.0.1" | "localhost" | "[::1]"))),
            "Essentia requires HTTPS or a loopback test service"
        );
        anyhow::ensure!(
            url.username().is_empty()
                && url.password().is_none()
                && url.query().is_none()
                && url.fragment().is_none()
                && url.path() == "/",
            "Essentia must be a bare service origin"
        );
        anyhow::ensure!(!key.is_empty(), "Essentia credential is empty");
        let mut headers = HeaderMap::new();
        let mut value = HeaderValue::from_str(key)
            .map_err(|_| anyhow::anyhow!("Invalid Essentia credential format"))?;
        value.set_sensitive(true);
        headers.insert("X-API-Key", value);
        let client = Client::builder()
            .default_headers(headers)
            .redirect(reqwest::redirect::Policy::none())
            .no_proxy()
            .connect_timeout(Duration::from_secs(10))
            .timeout(Duration::from_secs(90))
            .build()?;
        Ok(Self {
            client,
            origin: origin.trim_end_matches('/').into(),
        })
    }
}

#[derive(Clone, Debug, Serialize, Deserialize, ToSchema)]
#[serde(rename_all = "camelCase")]
pub struct AnalysisJob {
    pub id: Uuid,
    pub asset_id: Uuid,
    pub sha256: String,
    pub status: String,
    pub stage: String,
    pub message: Option<String>,
    pub result: Option<SongAnalysis>,
    pub updated_at: DateTime<Utc>,
}

#[utoipa::path(get, operation_id="get_analysis", path="/api/v1/projects/{id}/assets/{asset_id}/analysis", params(("id"=Uuid,Path),("asset_id"=Uuid,Path)), responses((status=200,body=Option<AnalysisJob>)))]
pub(crate) async fn get(
    State(state): State<AppState>,
    Path((id, asset_id)): Path<(Uuid, Uuid)>,
    axum::Extension(identity): axum::Extension<sessions::Identity>,
) -> ApiResult<Json<Option<AnalysisJob>>> {
    let client = state
        .convex
        .as_ref()
        .ok_or(crate::convex::Error::Configuration)?;
    Ok(Json(
        crate::convex_analysis::load(
            &state,
            client,
            &sessions::convex_auth(&state, identity),
            id,
            asset_id,
        )
        .await?,
    ))
}

#[utoipa::path(post, operation_id="start_analysis", path="/api/v1/projects/{id}/assets/{asset_id}/analysis", params(("id"=Uuid,Path),("asset_id"=Uuid,Path)), responses((status=200,body=AnalysisJob)))]
pub(crate) async fn start(
    State(state): State<AppState>,
    Path((id, asset_id)): Path<(Uuid, Uuid)>,
    axum::Extension(identity): axum::Extension<sessions::Identity>,
) -> ApiResult<Json<Option<AnalysisJob>>> {
    let client = state
        .convex
        .as_ref()
        .ok_or(crate::convex::Error::Configuration)?;
    let service = state.analysis.as_ref().ok_or_else(|| {
        ApiError(
            StatusCode::SERVICE_UNAVAILABLE,
            "Song analysis is not configured on this studio server.".into(),
        )
    })?;
    let auth = sessions::convex_auth(&state, identity);
    client.mutation::<()>("analysis:enqueue",serde_json::json!({"auth":auth,"projectId":id,"assetId":asset_id,"jobId":Uuid::new_v4(),"origin":service.origin})).await?;
    Ok(Json(
        crate::convex_analysis::load(&state, client, &auth, id, asset_id).await?,
    ))
}

pub(crate) async fn json_response(
    mut response: reqwest::Response,
) -> anyhow::Result<serde_json::Value> {
    anyhow::ensure!(
        response.status().is_success(),
        "Provider request unsuccessful"
    );
    let mut bytes = Vec::new();
    while let Some(chunk) = response.chunk().await? {
        anyhow::ensure!(
            bytes.len() + chunk.len() <= 8 * 1024 * 1024,
            "Provider response exceeds limit"
        );
        bytes.extend_from_slice(&chunk);
    }
    Ok(serde_json::from_slice(&bytes)?)
}

/// A durable Convex lease serializes dispatch across coordinators.
/// Submission intent is committed separately BEFORE HTTP; a lost response is
/// never blindly resubmitted, even when the worker dies at any await point.
pub async fn tick(state: &AppState) -> anyhow::Result<()> {
    let Some(service) = state.analysis.as_ref() else {
        return Ok(());
    };
    let client = state
        .convex
        .as_ref()
        .ok_or(crate::convex::Error::Configuration)?;
    crate::convex_analysis::tick(state, client, service).await
}

pub async fn run(state: AppState) {
    let mut interval = tokio::time::interval(Duration::from_secs(2));
    interval.set_missed_tick_behavior(tokio::time::MissedTickBehavior::Skip);
    loop {
        interval.tick().await;
        if tick(&state).await.is_err() {
            tracing::warn!("Analysis worker unavailable; durable job identities retained");
        }
    }
}
