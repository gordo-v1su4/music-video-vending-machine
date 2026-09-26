use crate::{
    AppState,
    analysis_jobs::{Service, json_response},
    convex::Client,
    convex_payloads,
    convex_uploads::StoredAsset,
};
use chrono::{Duration, Utc};
use serde::Deserialize;
use serde_json::{Value, json};
use uuid::Uuid;

pub async fn load(
    state: &AppState,
    client: &Client,
    auth: &crate::convex_sessions::Auth,
    project: Uuid,
    asset: Uuid,
) -> crate::ApiResult<Option<crate::analysis_jobs::AnalysisJob>> {
    let row: Option<Value> = client
        .query(
            "analysis:get",
            json!({"auth":auth,"projectId":project,"assetId":asset}),
        )
        .await?;
    let Some(row) = row else { return Ok(None) };
    let result = convex_payloads::decode(state, project, &row["result"])
        .await
        .map_err(|_| {
            crate::ApiError(
                axum::http::StatusCode::SERVICE_UNAVAILABLE,
                "Saved analysis is temporarily unavailable.".into(),
            )
        })?;
    serde_json::from_value(json!({"id":row["id"],"assetId":row["asset_id"],"sha256":row["sha256"],"status":row["status"],"stage":row["stage"],"message":row["message"],"result":result,"updatedAt":row["updated_at"]})).map(Some).map_err(|_|crate::convex::Error::InvalidResponse.into())
}

#[derive(Deserialize)]
struct Claim {
    job: Value,
    asset: StoredAsset,
}
async fn save(
    client: &Client,
    token: &str,
    job: &mut Value,
    status: &str,
    stage: &str,
    message: Option<&str>,
) -> anyhow::Result<()> {
    job["status"] = json!(status);
    job["stage"] = json!(stage);
    job["message"] = json!(message);
    job["next_poll_at"] = json!((Utc::now() + Duration::seconds(3)).to_rfc3339());
    client
        .mutation::<()>("analysisWorker:save", json!({"token":token,"data":job}))
        .await?;
    Ok(())
}
pub async fn tick(state: &AppState, client: &Client, service: &Service) -> anyhow::Result<()> {
    let token = Uuid::new_v4().to_string();
    let claim: Option<Claim> = client
        .mutation("analysisWorker:claim", json!({"token":token}))
        .await?;
    let Some(claim) = claim else { return Ok(()) };
    let result = process(state, client, service, &token, claim).await;
    // On any failure retain the lease until expiry. A stale worker cannot save,
    // and any saved submission intent becomes reconciliation-required.
    if result.is_ok() {
        client
            .mutation::<()>("analysisWorker:release", json!({"token":token}))
            .await?;
    }
    result
}
async fn process(
    state: &AppState,
    client: &Client,
    service: &Service,
    token: &str,
    claim: Claim,
) -> anyhow::Result<()> {
    let mut job = claim.job;
    let asset = claim.asset.asset()?;
    let id = job["id"]
        .as_str()
        .ok_or_else(|| anyhow::anyhow!("Invalid job identity"))?
        .to_owned();
    if job["provider_origin"] != service.origin {
        return save(
            client,
            token,
            &mut job,
            "reconciliation_required",
            "service_changed",
            Some("Reconcile against the original analysis service."),
        )
        .await;
    }
    let receipt = if job["status"] == "queued" {
        let audio = tokio::time::timeout(std::time::Duration::from_secs(30), async {
            let object = state
                .objects
                .get(&object_store::path::Path::from(
                    claim.asset.object_key.as_str(),
                ))
                .await?;
            anyhow::ensure!(
                object.meta.size == asset.size_bytes && asset.size_bytes <= 128 * 1024 * 1024,
                "Audio size mismatch"
            );
            Ok::<_, anyhow::Error>(object.bytes().await?)
        })
        .await;
        let bytes = match audio {
            Ok(Ok(bytes)) => bytes,
            _ => {
                return save(
                    client,
                    token,
                    &mut job,
                    "queued",
                    "waiting_for_audio",
                    Some("Waiting for stored audio."),
                )
                .await;
            }
        };
        use sha2::{Digest, Sha256};
        if format!("{:x}", Sha256::digest(&bytes)) != asset.sha256 || job["sha256"] != asset.sha256
        {
            return save(
                client,
                token,
                &mut job,
                "failed",
                "source_mismatch",
                Some("Stored audio checksum differs."),
            )
            .await;
        }
        let form = reqwest::multipart::Form::new().part(
            "file",
            reqwest::multipart::Part::bytes(bytes.to_vec())
                .file_name(asset.name.clone())
                .mime_str(&asset.media_type)?,
        );
        save(client, token, &mut job, "submitting", "uploading", None).await?;
        let response = service
            .client
            .post(format!("{}/analyze/studio/jobs", service.origin))
            .header("Idempotency-Key", &id)
            .multipart(form)
            .send()
            .await;
        let receipt = match response {
            Ok(reply) => json_response(reply).await,
            Err(_) => Err(anyhow::anyhow!("Unknown submission outcome")),
        };
        let Ok(receipt) = receipt else {
            return save(
                client,
                token,
                &mut job,
                "reconciliation_required",
                "submission_uncertain",
                Some("Reconcile the retained submission before retrying."),
            )
            .await;
        };
        let Some(provider) = receipt["id"]
            .as_str()
            .filter(|s| !s.is_empty() && s.len() <= 128)
        else {
            return save(
                client,
                token,
                &mut job,
                "reconciliation_required",
                "submission_uncertain",
                Some("Provider returned no usable identity."),
            )
            .await;
        };
        job["provider_id"] = json!(provider);
        job["receipt"] = convex_payloads::encode(state, asset.project_id, &receipt).await?;
        save(client, token, &mut job, "running", "analyzing", None).await?;
        receipt
    } else {
        let provider = job["provider_id"]
            .as_str()
            .ok_or_else(|| anyhow::anyhow!("Missing provider identity"))?
            .to_owned();
        let mut url = reqwest::Url::parse(&format!("{}/analyze/studio/jobs/", service.origin))?;
        url.path_segments_mut()
            .map_err(|_| anyhow::anyhow!("Invalid provider URL"))?
            .pop_if_empty()
            .push(&provider);
        let response = service.client.get(url).send().await;
        if response
            .as_ref()
            .is_ok_and(|r| r.status() == reqwest::StatusCode::NOT_FOUND)
        {
            return save(
                client,
                token,
                &mut job,
                "reconciliation_required",
                "provider_job_missing",
                Some("Provider job missing; no new submission made."),
            )
            .await;
        }
        let receipt = match response {
            Ok(reply) => json_response(reply).await,
            Err(_) => Err(anyhow::anyhow!("Polling unavailable")),
        };
        let Ok(receipt) = receipt else {
            return save(
                client,
                token,
                &mut job,
                "running",
                "reconnecting",
                Some("Reconnecting to the same provider job."),
            )
            .await;
        };
        if receipt["id"] != provider {
            return save(
                client,
                token,
                &mut job,
                "reconciliation_required",
                "identity_mismatch",
                Some("Provider identity differs."),
            )
            .await;
        }
        receipt
    };
    job["receipt"] = convex_payloads::encode(state, asset.project_id, &receipt).await?;
    match receipt["status"].as_str() {
        Some("completed") => {
            let duration = asset
                .duration_ms
                .ok_or_else(|| anyhow::anyhow!("Missing duration"))?;
            match crate::analysis::parse_result(receipt["result"].clone(), duration) {
                Ok(result) => {
                    job["result"] = convex_payloads::encode(
                        state,
                        asset.project_id,
                        &serde_json::to_value(result)?,
                    )
                    .await?;
                    save(client, token, &mut job, "completed", "completed", None).await
                }
                Err(message) => {
                    save(
                        client,
                        token,
                        &mut job,
                        "failed",
                        "invalid_result",
                        Some(&message),
                    )
                    .await
                }
            }
        }
        Some("failed") => {
            save(
                client,
                token,
                &mut job,
                "failed",
                "failed",
                Some("Analysis failed; no estimated sections substituted."),
            )
            .await
        }
        Some("queued" | "running") => {
            save(
                client,
                token,
                &mut job,
                "running",
                receipt["stage"]
                    .as_str()
                    .filter(|s| s.len() <= 128)
                    .unwrap_or("analyzing"),
                None,
            )
            .await
        }
        _ => {
            save(
                client,
                token,
                &mut job,
                "reconciliation_required",
                "unknown_status",
                Some("Unsupported provider state."),
            )
            .await
        }
    }
}
