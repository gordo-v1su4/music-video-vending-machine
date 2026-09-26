use crate::{
    AppState, Asset,
    convex::{Client, Error},
    convex_sessions::Auth,
};
use chrono::Utc;
use object_store::path::Path;
use serde::Deserialize;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::time::Duration;
use uuid::Uuid;

#[derive(Deserialize)]
pub struct StoredAsset {
    pub metadata: String,
    pub object_key: String,
}
impl StoredAsset {
    pub fn asset(&self) -> Result<Asset, Error> {
        serde_json::from_str(&self.metadata).map_err(|_| Error::InvalidResponse)
    }
}
impl Client {
    pub async fn asset_record(
        &self,
        auth: &Auth,
        project: Uuid,
        id: Uuid,
    ) -> Result<StoredAsset, Error> {
        self.query(
            "assets:get",
            json!({"auth":auth,"projectId":project,"id":id}),
        )
        .await
    }
    pub async fn list_assets(&self, auth: &Auth, project: Uuid) -> Result<Vec<Asset>, Error> {
        let rows: Vec<StoredAsset> = self
            .query("assets:list", json!({"auth":auth,"projectId":project}))
            .await?;
        rows.iter().map(StoredAsset::asset).collect()
    }
    pub async fn begin_upload(&self, auth: &Auth, asset: &Asset, key: &str) -> Result<(), Error> {
        self.mutation(
            "assets:beginUpload",
            json!({"auth":auth,"data":{
                "id":asset.id,"project_id":asset.project_id,"object_key":key,
                "metadata":serde_json::to_string(asset).map_err(|_| Error::Invalid)?,
                "created_at":asset.created_at.to_rfc3339(),"checked_at":Utc::now().to_rfc3339()
            }}),
        )
        .await
    }
    pub async fn complete_upload(
        &self,
        asset: &Asset,
        key: &str,
        analysis_origin: Option<&str>,
    ) -> Result<(), Error> {
        let now = Utc::now().to_rfc3339();
        let analysis = analysis_origin.filter(|_| asset.media_type.starts_with("audio/") && asset.duration_ms.is_some_and(|d| d>0)).map(|origin| json!({
            "id":Uuid::new_v4(),"asset_id":asset.id,"project_id":asset.project_id,
            "sha256":asset.sha256,"duration_ms":asset.duration_ms,"provider_origin":origin,
            "provider_id":null,"status":"queued","stage":"queued","message":null,"result":null,"receipt":null,
            "created_at":now,"updated_at":now,"next_poll_at":now
        })).unwrap_or(Value::Null);
        self.mutation("assets:completeUpload", json!({"id":asset.id,"metadata":serde_json::to_string(asset).map_err(|_| Error::Invalid)?,"objectKey":key,"analysis":analysis})).await
    }
}
pub async fn verify(state: &AppState, asset: &Asset, key: &str) -> anyhow::Result<()> {
    tokio::time::timeout(Duration::from_secs(30), async {
        let object = state.objects.get(&Path::from(key)).await?;
        anyhow::ensure!(
            object.meta.size == asset.size_bytes && asset.size_bytes <= 128 * 1024 * 1024,
            "Upload length mismatch"
        );
        let bytes = object.bytes().await?;
        anyhow::ensure!(
            format!("{:x}", Sha256::digest(&bytes)) == asset.sha256,
            "Upload checksum mismatch"
        );
        Ok::<(), anyhow::Error>(())
    })
    .await??;
    Ok(())
}
pub async fn reconcile(state: &AppState, client: &Client) -> anyhow::Result<usize> {
    let rows: Vec<StoredAsset> = client.mutation("assets:pendingUploads", json!({})).await?;
    let mut recovered = 0;
    for row in rows {
        let asset = row.asset()?;
        if verify(state, &asset, &row.object_key).await.is_ok() {
            client
                .complete_upload(
                    &asset,
                    &row.object_key,
                    state.analysis.as_ref().map(|s| s.origin.as_str()),
                )
                .await?;
            recovered += 1;
        } else {
            tracing::warn!(id=%asset.id,"Upload intent retained: object missing, unverified or unavailable");
        }
    }
    Ok(recovered)
}
