use crate::{
    ApiResult, AppState,
    convex::{Client, Error},
    convex_payloads,
    convex_sessions::Auth,
    transcription::{RecoverTranscription, Transcript, TranscriptionJob},
};
use serde_json::{Value, json};
use uuid::Uuid;

pub struct Pass {
    client: Client,
    token: String,
    id: Uuid,
    project: Uuid,
}
impl Pass {
    pub async fn persist(
        &self,
        state: &AppState,
        receipt: &Value,
        message: &str,
    ) -> anyhow::Result<()> {
        let receipt = convex_payloads::encode(state, self.project, receipt).await?;
        self.client
            .mutation::<()>(
                "transcriptionWorker:save",
                json!({"token":self.token,"id":self.id,"receipt":receipt,"message":message}),
            )
            .await?;
        Ok(())
    }
    async fn status(&self, status: &str, message: Option<&str>) -> anyhow::Result<()> {
        self.client
            .mutation::<()>(
                "transcriptionWorker:save",
                json!({"token":self.token,"id":self.id,"status":status,"message":message}),
            )
            .await?;
        Ok(())
    }
}
pub async fn tick(
    state: &AppState,
    client: &Client,
    service: &crate::transcription::Service,
) -> anyhow::Result<()> {
    #[derive(serde::Deserialize)]
    struct Claim {
        job: Value,
        asset: crate::convex_uploads::StoredAsset,
    }
    let token = Uuid::new_v4().to_string();
    let claim: Option<Claim> = client
        .mutation("transcriptionWorker:claim", json!({"token":token}))
        .await?;
    let Some(claim) = claim else { return Ok(()) };
    let asset = claim.asset.asset()?;
    let pass = Pass {
        client: client.clone(),
        token,
        id: serde_json::from_value(claim.job["id"].clone())?,
        project: asset.project_id,
    };
    let result=async {
        let audio=tokio::time::timeout(std::time::Duration::from_secs(30),async {
            let object=state.objects.get(&object_store::path::Path::from(claim.asset.object_key.as_str())).await?;
            anyhow::ensure!(object.meta.size==asset.size_bytes && asset.size_bytes<=128*1024*1024,"Invalid source length");
            Ok::<_,anyhow::Error>(object.bytes().await?)
        }).await;
        let bytes=match audio {Ok(Ok(bytes))=>bytes,_=>return pass.status("queued",Some("Waiting for stored audio. Other queued files can continue.")).await};
        use sha2::{Digest,Sha256};
        if format!("{:x}",Sha256::digest(&bytes))!=asset.sha256 || claim.job["sha256"]!=asset.sha256 {
            return pass.status("failed",Some("Stored audio failed its integrity check.")).await;
        }
        // Durable intent before the first billable request. Every subsequent pass
        // renews and checks the same lease before it can send another request.
        pass.status("running",Some("Pass 1 of up to 3: Nova-3, sentiment disabled.")).await?;
        match crate::transcription::run_pipeline(state,service,&asset,bytes,&pass).await {
            Ok((receipt,result))=> {
                let receipt=convex_payloads::encode(state,asset.project_id,&receipt).await?;
                let result=convex_payloads::encode(state,asset.project_id,&serde_json::to_value(result)?).await?;
                client.mutation::<()>("transcriptionWorker:save",json!({"token":pass.token,"id":pass.id,"status":"completed","message":null,"result":result,"receipt":receipt})).await?;
                Ok(())
            },
            Err(_)=>pass.status("reconciliation_required",Some("Transcription outcome needs reconciliation. No automatic paid retry was made.")).await,
        }
    }.await;
    if result.is_ok() {
        client
            .mutation::<()>("transcriptionWorker:release", json!({"token":pass.token}))
            .await?;
    }
    result
}
pub async fn load(
    state: &AppState,
    client: &Client,
    auth: &Auth,
    project: Uuid,
    asset: Uuid,
) -> ApiResult<Option<TranscriptionJob>> {
    let row: Option<Value> = client
        .query(
            "transcription:get",
            json!({"auth":auth,"projectId":project,"assetId":asset}),
        )
        .await?;
    let Some(row) = row else { return Ok(None) };
    let result = convex_payloads::decode(state, project, &row["result"])
        .await
        .map_err(|_| Error::Unavailable)?;
    let mut result: Option<Transcript> =
        serde_json::from_value(result).map_err(|_| Error::InvalidResponse)?;
    if let Some(result) = result.as_mut().filter(|r| r.words.is_empty()) {
        let receipt = convex_payloads::decode(state, project, &row["receipt"])
            .await
            .map_err(|_| Error::Unavailable)?;
        if let Ok(recovered) = crate::transcription::normalize(
            receipt.get("selected").unwrap_or(&receipt),
            result.duration_ms,
        ) {
            result.words = recovered.words;
        }
    }
    serde_json::from_value(json!({"id":row["id"],"profile":row["model"],"assetId":row["asset_id"],"sha256":row["sha256"],"status":row["status"],"message":row["message"],"result":result,"updatedAt":row["updated_at"]})).map(Some).map_err(|_|Error::InvalidResponse.into())
}
pub async fn recover(
    state: &AppState,
    client: &Client,
    auth: &Auth,
    project: Uuid,
    asset_id: Uuid,
    request: &RecoverTranscription,
) -> ApiResult<Option<TranscriptionJob>> {
    let asset = client.read_asset(auth, project, asset_id).await?;
    let row: Option<Value> = client
        .query(
            "transcription:get",
            json!({"auth":auth,"projectId":project,"assetId":asset_id}),
        )
        .await?;
    let mut row = row.ok_or(Error::NotFound)?;
    let updated = row["updated_at"]
        .as_str()
        .and_then(|s| chrono::DateTime::parse_from_rfc3339(s).ok())
        .ok_or(Error::InvalidResponse)?;
    if row["id"] != request.job_id.to_string()
        || updated != request.expected_updated_at
        || !(matches!(
            row["status"].as_str(),
            Some("failed" | "reconciliation_required")
        ) || (request.replace_completed
            && request.provider_response.is_some()
            && row["status"].as_str() == Some("completed")))
    {
        return Err(Error::Conflict.into());
    }
    if request.source_sha256 != asset.sha256 || row["sha256"] != asset.sha256 {
        return Err(crate::invalid(
            "Recovery source does not match this audio file.",
        ));
    }
    let receipt = convex_payloads::decode(state, project, &row["receipt"])
        .await
        .map_err(|_| Error::Unavailable)?;
    let (result, receipt) = crate::transcription::recover_saved(
        &asset,
        request,
        if receipt.is_null() {
            json!({})
        } else {
            receipt
        },
    )?;
    row["result"] = convex_payloads::encode(
        state,
        project,
        &serde_json::to_value(result).map_err(|_| Error::InvalidResponse)?,
    )
    .await
    .map_err(|_| Error::Unavailable)?;
    row["receipt"] = convex_payloads::encode(state, project, &receipt)
        .await
        .map_err(|_| Error::Unavailable)?;
    row["status"] = json!("completed");
    client
        .mutation::<()>(
            "transcription:recover",
            json!({"auth":auth,"expectedUpdatedAt":request.expected_updated_at,"allowCompleted":request.replace_completed,"data":row}),
        )
        .await?;
    load(state, client, auth, project, asset_id).await
}
