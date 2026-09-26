//! Durable adapter for the same studio job endpoints used by Beatsmaxxer Pro.
use crate::{
    ApiError, ApiResult, AppState, Asset, analysis::SongAnalysis, invalid, read_asset, sessions,
};
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
use sha2::{Digest, Sha256};
use sqlx::{PgPool, Row};
use std::{sync::Arc, time::Duration};
use utoipa::ToSchema;
use uuid::Uuid;

#[derive(Clone)]
pub struct Service {
    client: Client,
    origin: String,
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

pub async fn enqueue(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    asset: &Asset,
    service: Option<&Service>,
) -> Result<(), sqlx::Error> {
    let Some(service) = service else {
        return Ok(());
    };
    let Some(duration) = asset.duration_ms.filter(|v| *v > 0) else {
        return Ok(());
    };
    if !asset.media_type.starts_with("audio/") {
        return Ok(());
    }
    sqlx::query("INSERT INTO audio_analysis_jobs(id,asset_id,project_id,sha256,duration_ms,provider_origin,status,stage) VALUES($1,$2,$3,$4,$5,$6,'queued','queued') ON CONFLICT(asset_id) DO NOTHING")
        .bind(Uuid::new_v4()).bind(asset.id).bind(asset.project_id).bind(&asset.sha256).bind(duration as i64).bind(&service.origin).execute(&mut **tx).await?;
    Ok(())
}

async fn load(pool: &PgPool, project: Uuid, asset: Uuid) -> ApiResult<Option<AnalysisJob>> {
    let row = sqlx::query("SELECT id,asset_id,sha256,status,stage,message,result,updated_at FROM audio_analysis_jobs WHERE project_id=$1 AND asset_id=$2").bind(project).bind(asset).fetch_optional(pool).await?;
    row.map(|r| {
        Ok(AnalysisJob {
            id: r.try_get("id")?,
            asset_id: r.try_get("asset_id")?,
            sha256: r.try_get("sha256")?,
            status: r.try_get("status")?,
            stage: r.try_get("stage")?,
            message: r.try_get("message")?,
            result: r
                .try_get::<Option<sqlx::types::Json<SongAnalysis>>, _>("result")?
                .map(|v| v.0),
            updated_at: r.try_get("updated_at")?,
        })
    })
    .transpose()
}

#[utoipa::path(get, path="/api/v1/projects/{id}/assets/{asset_id}/analysis", params(("id"=Uuid,Path),("asset_id"=Uuid,Path)), responses((status=200,body=Option<AnalysisJob>)))]
pub async fn get(
    State(state): State<AppState>,
    Path((id, asset_id)): Path<(Uuid, Uuid)>,
) -> ApiResult<Json<Option<AnalysisJob>>> {
    read_asset(&state.pool, id, asset_id).await?;
    Ok(Json(load(&state.pool, id, asset_id).await?))
}

#[utoipa::path(post, path="/api/v1/projects/{id}/assets/{asset_id}/analysis", params(("id"=Uuid,Path),("asset_id"=Uuid,Path)), responses((status=200,body=AnalysisJob)))]
pub(crate) async fn start(
    State(state): State<AppState>,
    Path((id, asset_id)): Path<(Uuid, Uuid)>,
    axum::Extension(identity): axum::Extension<sessions::Identity>,
) -> ApiResult<Json<Option<AnalysisJob>>> {
    let asset = read_asset(&state.pool, id, asset_id).await?;
    if !asset.media_type.starts_with("audio/") || asset.duration_ms.unwrap_or(0) == 0 {
        return Err(invalid("Select audio with a known duration."));
    }
    if state.analysis.is_none() {
        return Err(ApiError(
            StatusCode::SERVICE_UNAVAILABLE,
            "Song analysis is not configured on this studio server.".into(),
        ));
    }
    let mut tx = state.pool.begin().await?;
    if !sessions::valid_on(&mut *tx, &state, identity).await? {
        return Err(sessions::unauthorized());
    }
    enqueue(&mut tx, &asset, state.analysis.as_deref()).await?;
    tx.commit().await?;
    Ok(Json(load(&state.pool, id, asset_id).await?))
}

async fn update(
    pool: &PgPool,
    id: Uuid,
    status: &str,
    stage: &str,
    message: Option<&str>,
) -> anyhow::Result<()> {
    sqlx::query("UPDATE audio_analysis_jobs SET status=$2,stage=$3,message=$4,updated_at=clock_timestamp(),next_poll_at=clock_timestamp()+interval '3 seconds' WHERE id=$1")
        .bind(id).bind(status).bind(stage).bind(message).execute(pool).await?;
    Ok(())
}

async fn json_response(mut response: reqwest::Response) -> anyhow::Result<serde_json::Value> {
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

/// A transaction-scoped advisory lock serializes dispatch across coordinators.
/// Submission intent is committed separately BEFORE HTTP; a lost response is
/// never blindly resubmitted, even when the worker dies at any await point.
pub async fn tick(state: &AppState) -> anyhow::Result<()> {
    let Some(service) = state.analysis.as_ref() else {
        return Ok(());
    };
    let mut guard = state.pool.begin().await?;
    let (locked,): (bool,) = sqlx::query_as("SELECT pg_try_advisory_xact_lock(1297501505)")
        .fetch_one(&mut *guard)
        .await?;
    if !locked {
        return Ok(());
    }
    // Any prior dispatch still marked submitting belongs to an interrupted worker.
    sqlx::query("UPDATE audio_analysis_jobs SET status='reconciliation_required',stage='submission_uncertain',message='The submission outcome is uncertain. The studio must reconcile the retained request before another submission.',updated_at=clock_timestamp() WHERE status='submitting'").execute(&state.pool).await?;
    let row = sqlx::query("SELECT j.*,a.object_key,a.metadata FROM audio_analysis_jobs j JOIN assets a ON a.id=j.asset_id WHERE j.status IN ('queued','running') AND j.next_poll_at<=clock_timestamp() ORDER BY j.next_poll_at,j.created_at LIMIT 1").fetch_optional(&state.pool).await?;
    let Some(row) = row else { return Ok(()) };
    let id: Uuid = row.try_get("id")?;
    let origin: String = row.try_get("provider_origin")?;
    if origin != service.origin {
        update(&state.pool, id, "reconciliation_required", "service_changed", Some("The analysis service address changed. Reconcile this job against its original service.")).await?;
        return Ok(());
    }
    let status: String = row.try_get("status")?;
    let receipt = if status == "queued" {
        let asset = row.try_get::<sqlx::types::Json<Asset>, _>("metadata")?.0;
        let key: String = row.try_get("object_key")?;
        let bytes = tokio::time::timeout(Duration::from_secs(30), async {
            state
                .objects
                .get(&object_store::path::Path::from(key))
                .await?
                .bytes()
                .await
        })
        .await;
        let bytes = match bytes {
            Ok(Ok(bytes)) => bytes,
            _ => {
                update(
                    &state.pool,
                    id,
                    "queued",
                    "waiting_for_audio",
                    Some("Waiting for the stored audio to become available."),
                )
                .await?;
                return Ok(());
            }
        };
        let expected: String = row.try_get("sha256")?;
        if bytes.len() as u64 != asset.size_bytes
            || format!("{:x}", Sha256::digest(&bytes)) != expected
        {
            update(
                &state.pool,
                id,
                "failed",
                "source_mismatch",
                Some("Stored audio does not match the imported source checksum."),
            )
            .await?;
            return Ok(());
        }
        let part = reqwest::multipart::Part::bytes(bytes.to_vec())
            .file_name(asset.name)
            .mime_str(&asset.media_type)?;
        let form = reqwest::multipart::Form::new().part("file", part);
        update(&state.pool, id, "submitting", "uploading", None).await?;
        let reply = service
            .client
            .post(format!("{}/analyze/studio/jobs", service.origin))
            .header("Idempotency-Key", id.to_string())
            .multipart(form)
            .send()
            .await;
        let reply = match reply {
            Ok(reply) => json_response(reply).await,
            Err(_) => Err(anyhow::anyhow!("Unknown submission outcome")),
        };
        let Ok(receipt) = reply else {
            update(&state.pool,id,"reconciliation_required","submission_uncertain",Some("The service response was lost or rejected. The retained request must be reconciled before retrying.")).await?;
            return Ok(());
        };
        let Some(provider_id) = receipt
            .get("id")
            .and_then(|v| v.as_str())
            .filter(|v| !v.is_empty() && v.len() <= 128)
        else {
            update(
                &state.pool,
                id,
                "reconciliation_required",
                "submission_uncertain",
                Some("The service did not return a usable job identity."),
            )
            .await?;
            return Ok(());
        };
        sqlx::query(
            "UPDATE audio_analysis_jobs SET provider_id=$2,status='running',receipt=$3 WHERE id=$1",
        )
        .bind(id)
        .bind(provider_id)
        .bind(&receipt)
        .execute(&state.pool)
        .await?;
        receipt
    } else {
        let provider_id: String = row.try_get("provider_id")?;
        let mut url = Url::parse(&format!("{}/analyze/studio/jobs/", service.origin))?;
        url.path_segments_mut()
            .map_err(|_| anyhow::anyhow!("Invalid job URL"))?
            .pop_if_empty()
            .push(&provider_id);
        let reply = service.client.get(url).send().await;
        if reply
            .as_ref()
            .is_ok_and(|r| r.status() == StatusCode::NOT_FOUND)
        {
            update(
                &state.pool,
                id,
                "reconciliation_required",
                "provider_job_missing",
                Some(
                    "The retained service job is no longer available. No new submission was made.",
                ),
            )
            .await?;
            return Ok(());
        }
        let receipt = match reply {
            Ok(reply) => json_response(reply).await,
            Err(_) => Err(anyhow::anyhow!("Polling unavailable")),
        };
        let Ok(receipt) = receipt else {
            update(
                &state.pool,
                id,
                "running",
                "reconnecting",
                Some("Progress is temporarily unavailable. Reconnecting to the same job."),
            )
            .await?;
            return Ok(());
        };
        if receipt.get("id").and_then(|v| v.as_str()) != Some(provider_id.as_str()) {
            update(
                &state.pool,
                id,
                "reconciliation_required",
                "identity_mismatch",
                Some("The service returned a different job identity."),
            )
            .await?;
            return Ok(());
        }
        receipt
    };
    sqlx::query("UPDATE audio_analysis_jobs SET receipt=$2 WHERE id=$1")
        .bind(id)
        .bind(&receipt)
        .execute(&state.pool)
        .await?;
    match receipt.get("status").and_then(|v| v.as_str()) {
        Some("completed") => {
            let duration: i64 = row.try_get("duration_ms")?;
            match crate::analysis::parse_result(
                receipt.get("result").cloned().unwrap_or_default(),
                duration as u64,
            ) {
                Ok(result) => {
                    sqlx::query("UPDATE audio_analysis_jobs SET result=$2 WHERE id=$1")
                        .bind(id)
                        .bind(sqlx::types::Json(result))
                        .execute(&state.pool)
                        .await?;
                    update(&state.pool, id, "completed", "completed", None).await?;
                }
                Err(message) => {
                    update(&state.pool, id, "failed", "invalid_result", Some(&message)).await?;
                }
            }
        }
        Some("failed") => {
            update(&state.pool,id,"failed","failed",Some("Essentia could not analyze this audio. No estimated sections were substituted.")).await?;
        }
        Some("queued" | "running") => {
            let stage = receipt
                .get("stage")
                .and_then(|v| v.as_str())
                .filter(|v| v.len() <= 128)
                .unwrap_or("analyzing");
            update(&state.pool, id, "running", stage, None).await?;
        }
        _ => {
            update(
                &state.pool,
                id,
                "reconciliation_required",
                "unknown_status",
                Some("The service returned an unsupported job state."),
            )
            .await?;
        }
    }
    guard.commit().await?;
    Ok(())
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
