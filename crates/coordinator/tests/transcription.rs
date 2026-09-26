use axum::{
    Json, Router,
    body::Body,
    http::{Request, StatusCode},
    routing::post,
};
use http_body_util::BodyExt;
use mvm_coordinator::{
    AppState, Asset, migrate, router,
    transcription::{Service, tick},
};
use object_store::{ObjectStore, memory::InMemory, path::Path};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use sqlx::postgres::PgPoolOptions;
use std::sync::{
    Arc,
    atomic::{AtomicUsize, Ordering},
};
use tower::ServiceExt;
use uuid::Uuid;

async fn request(app: Router, method: &str, path: &str, body: Value) -> (StatusCode, Value) {
    let response = app
        .oneshot(
            Request::builder()
                .method(method)
                .uri(path)
                .header("Host", "127.0.0.1:5199")
                .header("Content-Type", "application/json")
                .body(Body::from(body.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    let status = response.status();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    (status, serde_json::from_slice(&bytes).unwrap())
}

#[tokio::test]
#[ignore = "requires isolated MVM_TEST_DATABASE_URL; CI runs explicitly"]
async fn transcription_survives_restart_and_never_repeats_paid_submissions() {
    let pool = PgPoolOptions::new()
        .max_connections(8)
        .connect(&std::env::var("MVM_TEST_DATABASE_URL").unwrap())
        .await
        .unwrap();
    let (database,): (String,) = sqlx::query_as("SELECT current_database()")
        .fetch_one(&pool)
        .await
        .unwrap();
    assert_eq!(database, "mvm_test");
    migrate(&pool).await.unwrap();
    let posts = Arc::new(AtomicUsize::new(0));
    let fail = Arc::new(AtomicUsize::new(0));
    let post_count = posts.clone();
    let post_fail = fail.clone();
    let provider = Router::new().route("/v1/listen",post(move |axum::extract::Query(query):axum::extract::Query<std::collections::HashMap<String,String>>, headers:axum::http::HeaderMap| {
        let count=post_count.clone(); let fail=post_fail.clone();
        async move {
            assert_eq!(query.get("sentiment").map(String::as_str),Some("false"));
            assert_eq!(query.get("model").map(String::as_str),Some("nova-3"));
            assert_eq!(headers["authorization"],"Token test-key");
            count.fetch_add(1,Ordering::SeqCst);
            if fail.load(Ordering::SeqCst)>0 { (StatusCode::BAD_GATEWAY,Json(json!({"error":"lost response"}))) }
            else { (StatusCode::OK,Json(json!({"metadata":{"duration":10},"results":{"channels":[{"alternatives":[{"transcript":"Test phrase", "words":[{"word":"test","start":1,"end":2,"confidence":0.9},{"word":"phrase","start":2,"end":3,"confidence":0.9}]}]}]}}))) }
        }
    }));
    let provider = provider.layer(axum::extract::DefaultBodyLimit::max(8 * 1024 * 1024));
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
    let origin = format!("http://{}", listener.local_addr().unwrap());
    let server = tokio::spawn(async move { axum::serve(listener, provider).await.unwrap() });
    let state = AppState {
        pool: pool.clone(),
        objects: Arc::new(InMemory::new()),
        token_hash: None,
        development: true,
        storage_name: "analysis-test".into(),
        analysis: None,
        transcription: Some(Arc::new(Service::new(&origin, "test-key").unwrap())),
    };
    let app = router(state.clone(), vec![]);
    let (_, project) = request(
        app.clone(),
        "POST",
        "/api/v1/projects",
        json!({"name":"Analysis lifecycle fixture"}),
    )
    .await;
    let project_id: Uuid = project["id"].as_str().unwrap().parse().unwrap();
    let mut ids = Vec::new();
    for n in 0..3 {
        let id = Uuid::new_v4();
        ids.push(id);
        let bytes = bytes::Bytes::from_static(b"private analysis fixture");
        let key = format!("projects/{project_id}/originals/{id}");
        state
            .objects
            .put(&Path::from(key.clone()), bytes.clone().into())
            .await
            .unwrap();
        let asset = Asset {
            id,
            project_id,
            name: format!("fixture-{n}.wav"),
            media_type: "audio/wav".into(),
            sha256: format!("{:x}", Sha256::digest(&bytes)),
            size_bytes: bytes.len() as u64,
            duration_ms: Some(10_000),
            url: format!("/api/v1/projects/{project_id}/assets/{id}"),
            created_at: chrono::Utc::now(),
        };
        sqlx::query("INSERT INTO assets(id,project_id,object_key,metadata) VALUES($1,$2,$3,$4)")
            .bind(id)
            .bind(project_id)
            .bind(key)
            .bind(sqlx::types::Json(asset))
            .execute(&pool)
            .await
            .unwrap();
    }
    let path = format!(
        "/api/v1/projects/{project_id}/assets/{}/transcription",
        ids[0]
    );
    let (status, first) = request(app.clone(), "POST", &path, Value::Null).await;
    assert_eq!(status, StatusCode::OK);
    let (_, second) = request(app.clone(), "POST", &path, Value::Null).await;
    assert_eq!(first["id"], second["id"]);
    let (a, b) = tokio::join!(tick(&state), tick(&state));
    a.unwrap();
    b.unwrap();
    assert_eq!(posts.load(Ordering::SeqCst), 1);
    let (_, recovered) = request(router(state.clone(), vec![]), "GET", &path, Value::Null).await;
    assert_eq!(recovered["status"], "completed");
    assert_eq!(recovered["result"]["chunks"][0]["startMs"], 1_000);
    assert_eq!(recovered["result"]["wordCount"], 2);
    sqlx::query("UPDATE transcription_jobs SET result=result-'words' WHERE asset_id=$1")
        .bind(ids[0])
        .execute(&pool)
        .await
        .unwrap();
    let (_, legacy) = request(app.clone(), "GET", &path, Value::Null).await;
    assert_eq!(legacy["result"]["words"][1]["startMs"], 2000);
    assert_eq!(posts.load(Ordering::SeqCst), 1);
    let action_path = format!("/api/v1/projects/{project_id}/actions");
    let (status, _) = request(app.clone(), "POST", &action_path, json!({"expectedRevision":0,"action":{"type":"setMaster","assetId":ids[0],"durationMs":10000}})).await;
    assert_eq!(status, StatusCode::OK);
    let (status, saved) = request(app.clone(), "POST", &action_path, json!({"expectedRevision":1,"action":{"type":"setLyrics","lyrics":{"text":"Reference","sourceName":"lyrics.txt","alignedAssetId":ids[1]}}})).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(saved["lyrics"]["alignedAssetId"], ids[1].to_string());
    let (status, _) = request(app.clone(), "POST", &action_path, json!({"expectedRevision":2,"action":{"type":"setLyrics","lyrics":{"text":"Reference","sourceName":"lyrics.txt","alignedAssetId":Uuid::new_v4()}}})).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
    tick(&state).await.unwrap();
    assert_eq!(posts.load(Ordering::SeqCst), 1);
    let (status, _) = request(
        app.clone(),
        "GET",
        &format!(
            "/api/v1/projects/{}/assets/{}/transcription",
            Uuid::new_v4(),
            ids[0]
        ),
        Value::Null,
    )
    .await;
    assert_eq!(status, StatusCode::NOT_FOUND);

    fail.store(1, Ordering::SeqCst);
    let path = format!(
        "/api/v1/projects/{project_id}/assets/{}/transcription",
        ids[1]
    );
    request(app.clone(), "POST", &path, Value::Null).await;
    tick(&state).await.unwrap();
    let (_, uncertain) = request(app.clone(), "GET", &path, Value::Null).await;
    assert_eq!(uncertain["status"], "reconciliation_required");
    tick(&state).await.unwrap();
    assert_eq!(posts.load(Ordering::SeqCst), 2);
    let path = format!(
        "/api/v1/projects/{project_id}/assets/{}/transcription",
        ids[2]
    );
    request(app.clone(), "POST", &path, Value::Null).await;
    sqlx::query("UPDATE transcription_jobs SET status='running' WHERE asset_id=$1")
        .bind(ids[2])
        .execute(&pool)
        .await
        .unwrap();
    tick(&state).await.unwrap();
    let (_, interrupted) = request(app, "GET", &path, Value::Null).await;
    assert_eq!(interrupted["status"], "reconciliation_required");
    assert_eq!(posts.load(Ordering::SeqCst), 2);
    server.abort();
    sqlx::query("DELETE FROM transcription_jobs WHERE project_id=$1")
        .bind(project_id)
        .execute(&pool)
        .await
        .unwrap();
}

#[tokio::test]
#[ignore = "requires isolated MVM_TEST_DATABASE_URL and ffmpeg"]
async fn sparse_vocals_trigger_bounded_fallback_and_timed_tail() {
    let pool = PgPoolOptions::new()
        .max_connections(8)
        .connect(&std::env::var("MVM_TEST_DATABASE_URL").unwrap())
        .await
        .unwrap();
    let (database,): (String,) = sqlx::query_as("SELECT current_database()")
        .fetch_one(&pool)
        .await
        .unwrap();
    assert_eq!(database, "mvm_test");
    migrate(&pool).await.unwrap();
    let posts = Arc::new(AtomicUsize::new(0));
    let counter = posts.clone();
    let provider=Router::new().route("/v1/listen",post(move |axum::extract::Query(query):axum::extract::Query<std::collections::HashMap<String,String>>, _audio: axum::body::Bytes| {
        let counter=counter.clone();async move {
            let pass=counter.fetch_add(1,Ordering::SeqCst);
            assert_eq!(query["sentiment"],"false");
            assert_eq!(query["model"],if pass==0 {"nova-3"}else{"whisper-large"});
            if pass>0 {assert!(!query.contains_key("topics"));assert!(!query.contains_key("summarize"));}
            let (duration,words)=match pass {
                0=>(100.,json!([{"word":"first","start":1.,"end":10.}])),
                1=>(100.,json!([{"word":"first","start":1.,"end":10.},{"word":"middle","start":30.,"end":40.}])),
                2=>(62.,json!([{"word":"duplicate","start":0.,"end":1.},{"word":"ending","start":50.,"end":60.}])),
                _=>panic!("unexpected extra paid pass"),
            };
            Json(json!({"metadata":{"duration":duration},"results":{"channels":[{"alternatives":[{"transcript":"fixture","words":words}]}]}}))
        }
    }));
    let provider = provider.layer(axum::extract::DefaultBodyLimit::max(8 * 1024 * 1024));
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
    let origin = format!("http://{}", listener.local_addr().unwrap());
    let server = tokio::spawn(async move { axum::serve(listener, provider).await.unwrap() });
    let state = AppState {
        pool: pool.clone(),
        objects: Arc::new(InMemory::new()),
        token_hash: None,
        development: true,
        storage_name: "transcript-tail-test".into(),
        analysis: None,
        transcription: Some(Arc::new(Service::new(&origin, "test-key").unwrap())),
    };
    let app = router(state.clone(), vec![]);
    let (_, project) = request(
        app.clone(),
        "POST",
        "/api/v1/projects",
        json!({"name":"Transcription continuation fixture"}),
    )
    .await;
    let project_id: Uuid = project["id"].as_str().unwrap().parse().unwrap();
    let id = Uuid::new_v4();
    // Valid silent WAV, 100s at 16k mono. Only provider words are fixtures.
    let data_size = 100u32 * 16000 * 2;
    let mut bytes = Vec::new();
    bytes.extend(b"RIFF");
    bytes.extend((data_size + 36).to_le_bytes());
    bytes.extend(b"WAVEfmt ");
    bytes.extend(16u32.to_le_bytes());
    bytes.extend(1u16.to_le_bytes());
    bytes.extend(1u16.to_le_bytes());
    bytes.extend(16000u32.to_le_bytes());
    bytes.extend(32000u32.to_le_bytes());
    bytes.extend(2u16.to_le_bytes());
    bytes.extend(16u16.to_le_bytes());
    bytes.extend(b"data");
    bytes.extend(data_size.to_le_bytes());
    bytes.resize(44 + data_size as usize, 0);
    let key = format!("projects/{project_id}/originals/{id}");
    let asset = Asset {
        id,
        project_id,
        name: "continuation.wav".into(),
        media_type: "audio/wav".into(),
        sha256: format!("{:x}", Sha256::digest(&bytes)),
        size_bytes: bytes.len() as u64,
        duration_ms: Some(100000),
        url: format!("/api/v1/projects/{project_id}/assets/{id}"),
        created_at: chrono::Utc::now(),
    };
    state
        .objects
        .put(&Path::from(key.clone()), bytes.into())
        .await
        .unwrap();
    sqlx::query("INSERT INTO assets(id,project_id,object_key,metadata) VALUES($1,$2,$3,$4)")
        .bind(id)
        .bind(project_id)
        .bind(key)
        .bind(sqlx::types::Json(asset))
        .execute(&pool)
        .await
        .unwrap();
    let path = format!("/api/v1/projects/{project_id}/assets/{id}/transcription");
    request(app.clone(), "POST", &path, Value::Null).await;
    tick(&state).await.unwrap();
    let (_, job) = request(app.clone(), "GET", &path, Value::Null).await;
    assert_eq!(job["status"], "completed", "{job}");
    assert_eq!(job["result"]["wordCount"], 3);
    assert_eq!(job["result"]["chunks"][2]["startMs"], 88000);
    assert_eq!(job["result"]["chunks"][2]["endMs"], 98000);
    request(app, "POST", &path, Value::Null).await;
    tick(&state).await.unwrap();
    assert_eq!(posts.load(Ordering::SeqCst), 3);
    server.abort();
    sqlx::query("DELETE FROM transcription_jobs WHERE project_id=$1")
        .bind(project_id)
        .execute(&pool)
        .await
        .unwrap();
}
