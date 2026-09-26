use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use http_body_util::BodyExt;
use mvm_coordinator::{AppState, migrate, router};
use object_store::{ObjectStore, memory::InMemory};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use sqlx::postgres::PgPoolOptions;
use std::sync::Arc;
use tower::ServiceExt;

async fn request(app: axum::Router, method: &str, path: &str, body: Value) -> (StatusCode, Value) {
    let response = app
        .oneshot(
            Request::builder()
                .method(method)
                .uri(path)
                .header("content-type", "application/json")
                .body(Body::from(body.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    let status = response.status();
    let data = response.into_body().collect().await.unwrap().to_bytes();
    (status, serde_json::from_slice(&data).unwrap())
}

#[tokio::test]
async fn missing_auth_is_rejected_before_database_access() {
    let pool = PgPoolOptions::new()
        .connect_lazy("postgres://localhost/never_connected")
        .unwrap();
    let state = AppState {
        pool,
        objects: Arc::new(InMemory::new()),
        token_hash: Some(Sha256::digest(b"test-only-operator-token-not-for-runtime").into()),
        development: false,
        storage_name: "test".into(),
    };
    let app = router(state, vec![]);
    let (status, _) = request(app, "GET", "/api/v1/projects", Value::Null).await;
    assert_eq!(status, StatusCode::UNAUTHORIZED);
}

#[tokio::test]
async fn cross_origin_multipart_cannot_mutate_local_development() {
    let pool = PgPoolOptions::new()
        .connect_lazy("postgres://localhost/never_connected")
        .unwrap();
    let state = AppState {
        pool,
        objects: Arc::new(InMemory::new()),
        token_hash: None,
        development: true,
        storage_name: "test".into(),
    };
    let response = router(state, vec!["http://127.0.0.1:5198".parse().unwrap()])
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/api/v1/projects")
                .header("Origin", "https://untrusted.invalid")
                .header("Content-Type", "application/json")
                .body(Body::from(r#"{"name":"Unsolicited"}"#))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::FORBIDDEN);
}

#[test]
fn openapi_matches_camel_case_action_wire_contract() {
    use utoipa::OpenApi;
    let schema = serde_json::to_value(mvm_coordinator::ApiDoc::openapi()).unwrap();
    let alternatives = schema["components"]["schemas"]["Action"]["oneOf"]
        .as_array()
        .unwrap();
    let serialized = alternatives
        .iter()
        .map(Value::to_string)
        .collect::<String>();
    for field in [
        "assetId",
        "durationMs",
        "localAttemptsPerShot",
        "shotId",
        "revisionId",
    ] {
        assert!(serialized.contains(field), "missing {field}");
    }
    for field in [
        "asset_id",
        "duration_ms",
        "local_attempts_per_shot",
        "shot_id",
        "revision_id",
    ] {
        assert!(!serialized.contains(field), "wrong field {field}");
    }
}

#[tokio::test]
#[ignore = "requires isolated MVM_TEST_DATABASE_URL; CI runs explicitly"]
async fn concurrent_writes_restart_and_asset_ownership() {
    let url = std::env::var("MVM_TEST_DATABASE_URL")
        .expect("Set MVM_TEST_DATABASE_URL to isolated mvm_test database");
    let pool = PgPoolOptions::new()
        .max_connections(5)
        .connect(&url)
        .await
        .unwrap();
    let (database,): (String,) = sqlx::query_as("SELECT current_database()")
        .fetch_one(&pool)
        .await
        .unwrap();
    assert_eq!(
        database, "mvm_test",
        "Refusing to run integration tests against another database"
    );
    migrate(&pool).await.unwrap();
    let objects: Arc<dyn ObjectStore> = Arc::new(InMemory::new());
    let state = AppState {
        pool: pool.clone(),
        objects,
        token_hash: None,
        development: true,
        storage_name: "test-memory-assets".into(),
    };
    let app = router(state.clone(), vec![]);
    let (status, project) = request(
        app.clone(),
        "POST",
        "/api/v1/projects",
        json!({"name":"Persistence acceptance"}),
    )
    .await;
    assert_eq!(status, StatusCode::CREATED);
    let id = project["id"].as_str().unwrap();
    let path = format!("/api/v1/projects/{id}/actions");
    let first =
        json!({"expectedRevision":0,"action":{"type":"setTreatment","text":"A traveller arrives"}});
    let second =
        json!({"expectedRevision":0,"action":{"type":"setTreatment","text":"Conflicting edit"}});
    let (a, b) = tokio::join!(
        request(app.clone(), "POST", &path, first),
        request(app.clone(), "POST", &path, second)
    );
    assert!(
        (a.0 == StatusCode::OK && b.0 == StatusCode::CONFLICT)
            || (b.0 == StatusCode::OK && a.0 == StatusCode::CONFLICT)
    );
    let expected = if a.0 == StatusCode::OK { a.1 } else { b.1 };
    // A new router and fresh DB connections recover committed state, with no process-local project map.
    let restarted_pool = PgPoolOptions::new().connect(&url).await.unwrap();
    let restarted = router(
        AppState {
            pool: restarted_pool,
            ..state
        },
        vec![],
    );
    let (status, recovered) = request(
        restarted,
        "GET",
        &format!("/api/v1/projects/{id}"),
        Value::Null,
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(recovered, expected);

    let wav = test_wav();
    let mut multipart = b"--mvm-boundary\r\nContent-Disposition: form-data; name=\"file\"; filename=\"fixture.wav\"\r\nContent-Type: audio/wav\r\n\r\n".to_vec();
    multipart.extend(wav);
    multipart.extend(b"\r\n--mvm-boundary--\r\n");
    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri(format!("/api/v1/projects/{id}/assets"))
                .header("content-type", "multipart/form-data; boundary=mvm-boundary")
                .body(Body::from(multipart))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::CREATED);
    let asset: Value =
        serde_json::from_slice(&response.into_body().collect().await.unwrap().to_bytes()).unwrap();
    assert_eq!(asset["durationMs"], 1_000);
    let (_, other) = request(
        app.clone(),
        "POST",
        "/api/v1/projects",
        json!({"name":"Other project"}),
    )
    .await;
    let wrong_path = format!("/api/v1/projects/{}/actions", other["id"].as_str().unwrap());
    let (status, _) = request(app.clone(), "POST", &wrong_path, json!({"expectedRevision":0,"action":{"type":"setMaster","assetId":asset["id"],"durationMs":1000}})).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
    let (status, _) = request(app.clone(), "POST", &path, json!({"expectedRevision":1,"action":{"type":"setMaster","assetId":asset["id"],"durationMs":999}})).await;
    assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY);
    let (status, _) = request(app.clone(), "POST", &path, json!({"expectedRevision":1,"action":{"type":"setMaster","assetId":asset["id"],"durationMs":1000}})).await;
    assert_eq!(status, StatusCode::OK);
    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .uri(format!("/api/v1/projects/{id}/events?after=1"))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    let mut stream = response.into_body();
    let frame = tokio::time::timeout(std::time::Duration::from_secs(3), stream.frame())
        .await
        .unwrap()
        .unwrap()
        .unwrap();
    let event = String::from_utf8(frame.into_data().unwrap().to_vec()).unwrap();
    assert!(event.contains("id: 2"));
    assert!(event.contains("event: project"));
    let asset_response = app
        .oneshot(
            Request::builder()
                .uri(asset["url"].as_str().unwrap())
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(asset_response.status(), StatusCode::OK);
    let downloaded = asset_response
        .into_body()
        .collect()
        .await
        .unwrap()
        .to_bytes();
    assert_eq!(
        format!("{:x}", Sha256::digest(downloaded)),
        asset["sha256"].as_str().unwrap()
    );
    pool.close().await;
}

fn test_wav() -> Vec<u8> {
    let samples: Vec<i16> = (0..8_000)
        .map(|i| ((i as f32 * 440.0 * std::f32::consts::TAU / 8_000.0).sin() * 4000.0) as i16)
        .collect();
    let len = (samples.len() * 2) as u32;
    let mut b = Vec::new();
    b.extend(b"RIFF");
    b.extend((len + 36).to_le_bytes());
    b.extend(b"WAVEfmt ");
    b.extend(16u32.to_le_bytes());
    b.extend(1u16.to_le_bytes());
    b.extend(1u16.to_le_bytes());
    b.extend(8_000u32.to_le_bytes());
    b.extend(16_000u32.to_le_bytes());
    b.extend(2u16.to_le_bytes());
    b.extend(16u16.to_le_bytes());
    b.extend(b"data");
    b.extend(len.to_le_bytes());
    for s in samples {
        b.extend(s.to_le_bytes());
    }
    b
}
