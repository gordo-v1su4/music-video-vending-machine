//! Lossless JSON payloads shared by Convex jobs and the RustFS migration format.
use crate::AppState;
use object_store::{PutMode, PutOptions, path::Path};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use uuid::Uuid;
const MAX: u64 = 8 * 1024 * 1024;

pub async fn encode(state: &AppState, project: Uuid, value: &Value) -> anyhow::Result<Value> {
    let data = serde_json::to_vec(value)?;
    anyhow::ensure!(data.len() as u64 <= MAX, "JSON payload exceeds limit");
    if data.len() <= 128 * 1024 {
        return Ok(Value::String(String::from_utf8(data)?));
    }
    let sha256 = format!("{:x}", Sha256::digest(&data));
    let key = format!("projects/{project}/mvvm/payloads/{sha256}.json");
    let reference = json!({"kind":"rustfs-json-v1","bucket":state.object_bucket,"key":key,"sha256":sha256,"bytes":data.len()});
    match state
        .objects
        .put_opts(
            &Path::from(key),
            data.into(),
            PutOptions {
                mode: PutMode::Create,
                ..Default::default()
            },
        )
        .await
    {
        Ok(_) | Err(object_store::Error::AlreadyExists { .. }) => {}
        Err(error) => return Err(error.into()),
    }
    anyhow::ensure!(
        decode(state, project, &reference).await? == *value,
        "Payload readback mismatch"
    );
    Ok(reference)
}
pub async fn decode(state: &AppState, project: Uuid, value: &Value) -> anyhow::Result<Value> {
    if value.is_null() {
        return Ok(Value::Null);
    }
    if let Some(text) = value.as_str() {
        return Ok(serde_json::from_str(text)?);
    }
    let sha = value["sha256"].as_str().unwrap_or("");
    let expected = value["bytes"].as_f64().unwrap_or(-1.0);
    let key = format!("projects/{project}/mvvm/payloads/{sha}.json");
    anyhow::ensure!(
        value["kind"] == "rustfs-json-v1"
            && value["bucket"] == state.object_bucket
            && value["key"] == key
            && sha.len() == 64
            && sha.bytes().all(|b| b.is_ascii_hexdigit())
            && expected >= 0.0
            && expected <= MAX as f64
            && expected.fract() == 0.0,
        "Invalid payload reference"
    );
    let object = state.objects.get(&Path::from(key)).await?;
    anyhow::ensure!(
        object.meta.size == expected as u64,
        "Payload length mismatch"
    );
    let bytes = object.bytes().await?;
    anyhow::ensure!(
        bytes.len() as u64 == expected as u64 && format!("{:x}", Sha256::digest(&bytes)) == sha,
        "Payload checksum mismatch"
    );
    Ok(serde_json::from_slice(&bytes)?)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[tokio::test]
    async fn payload_roundtrip_rejects_corruption_and_cross_project_reads() {
        let state = AppState {
            convex: None,
            analysis: None,
            transcription: None,
            objects: std::sync::Arc::new(object_store::memory::InMemory::new()),
            token_hash: None,
            development: true,
            storage_name: "test".into(),
            object_bucket: "mvvm".into(),
        };
        let project = Uuid::new_v4();
        let value = json!({"curve":(0..40000).map(|i|i as f64/10000.0).collect::<Vec<_>>()});
        let reference = encode(&state, project, &value).await.unwrap();
        assert!(reference.is_object());
        assert_eq!(reference["bucket"], "mvvm");
        let mut foreign = reference.clone();
        foreign["bucket"] = json!("music-vending-machine");
        assert!(decode(&state, project, &foreign).await.is_err());
        assert_eq!(decode(&state, project, &reference).await.unwrap(), value);
        assert_eq!(encode(&state, project, &value).await.unwrap(), reference);
        assert!(decode(&state, Uuid::new_v4(), &reference).await.is_err());
        let key = Path::from(reference["key"].as_str().unwrap());
        state
            .objects
            .put(&key, bytes::Bytes::from_static(b"corrupt").into())
            .await
            .unwrap();
        assert!(decode(&state, project, &reference).await.is_err());
        assert!(encode(&state, project, &value).await.is_err());
    }
}
