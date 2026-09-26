mod support;
use axum::{
    Json, Router,
    body::Body,
    http::{Request, StatusCode},
    routing::{get, post},
};
use http_body_util::BodyExt;
use mvm_coordinator::{
    AppState, Asset,
    analysis_jobs::{Service, tick},
    router,
};
use object_store::path::Path;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
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
#[ignore = "requires disposable Convex; run scripts/test-convex-http.mjs"]
async fn convex_analysis_survives_restart_and_never_repeats_uncertain_submissions() {
    let posts = Arc::new(AtomicUsize::new(0));
    let fail = Arc::new(AtomicUsize::new(0));
    let provider_id = Uuid::new_v4().to_string();
    let post_id = provider_id.clone();
    let post_count = posts.clone();
    let post_fail = fail.clone();
    let provider = Router::new().route("/analyze/studio/jobs",post(move || {
        let id=post_id.clone(); let count=post_count.clone(); let fail=post_fail.clone();
        async move { count.fetch_add(1,Ordering::SeqCst); if fail.load(Ordering::SeqCst)>0 { (StatusCode::BAD_GATEWAY,Json(json!({"error":"lost response"}))) } else { (StatusCode::ACCEPTED,Json(json!({"id":id,"status":"queued","stage":"queued"}))) } }
    })).route("/analyze/studio/jobs/{id}",get(move || { let id=provider_id.clone(); async move { Json(json!({"id":id,"status":"completed","stage":"completed","result":{"schema_version":"studio-audio-v1","duration":10.0,"bpm":137.0,"confidence":3.2,"beats":[0.1,0.5],"onsets":[0.2],"energy":{"curve":[0.2,0.4],"sample_rate_hz":0.1,"start_time_s":0.0},"structure":{"source":"allin1","analyzed_duration_s":10.0,"provenance":{"status":"detected","method":"allin1:test","device":"cuda"},"boundaries":[0.0,10.04],"sections":[{"start":0.0,"end":10.04,"duration":10.04,"label":"verse","original_label":"verse","energy":0.5}]}}})) } }));
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
    let origin = format!("http://{}", listener.local_addr().unwrap());
    let server = tokio::spawn(async move { axum::serve(listener, provider).await.unwrap() });
    let state = AppState {
        analysis: Some(Arc::new(Service::new(&origin, "test-key").unwrap())),
        ..support::state()
    };
    let client = state.convex.as_ref().unwrap();
    let auth = mvm_coordinator::convex_sessions::Auth {
        session_id: None,
        issuer_hash: None,
        development: true,
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
        client.begin_upload(&auth, &asset, &key).await.unwrap();
        client.complete_upload(&asset, &key, None).await.unwrap();
    }
    let path = format!("/api/v1/projects/{project_id}/assets/{}/analysis", ids[0]);
    let (status, first) = request(app.clone(), "POST", &path, Value::Null).await;
    assert_eq!(status, StatusCode::OK);
    let (_, second) = request(app.clone(), "POST", &path, Value::Null).await;
    assert_eq!(first["id"], second["id"]);
    let (a, b) = tokio::join!(tick(&state), tick(&state));
    a.unwrap();
    b.unwrap();
    assert_eq!(posts.load(Ordering::SeqCst), 1);
    let _: Value = client
        .mutation(
            "testing:analysisState",
            json!({"assetId":ids[0],"submitting":false}),
        )
        .await
        .unwrap();
    tick(&state).await.unwrap();
    let (_, recovered) = request(router(state.clone(), vec![]), "GET", &path, Value::Null).await;
    assert_eq!(recovered["status"], "completed");
    assert_eq!(recovered["result"]["sections"][0]["endMs"], 10_000);
    assert_eq!(recovered["result"]["nativeConfidence"], 3.2);
    tick(&state).await.unwrap();
    assert_eq!(posts.load(Ordering::SeqCst), 1);
    let (status, _) = request(
        app.clone(),
        "GET",
        &format!(
            "/api/v1/projects/{}/assets/{}/analysis",
            Uuid::new_v4(),
            ids[0]
        ),
        Value::Null,
    )
    .await;
    assert_eq!(status, StatusCode::NOT_FOUND);

    fail.store(1, Ordering::SeqCst);
    let path = format!("/api/v1/projects/{project_id}/assets/{}/analysis", ids[1]);
    request(app.clone(), "POST", &path, Value::Null).await;
    tick(&state).await.unwrap();
    let (_, uncertain) = request(app.clone(), "GET", &path, Value::Null).await;
    assert_eq!(uncertain["status"], "reconciliation_required");
    tick(&state).await.unwrap();
    assert_eq!(posts.load(Ordering::SeqCst), 2);
    let path = format!("/api/v1/projects/{project_id}/assets/{}/analysis", ids[2]);
    request(app.clone(), "POST", &path, Value::Null).await;
    let _: Value = client
        .mutation(
            "testing:analysisState",
            json!({"assetId":ids[2],"submitting":true}),
        )
        .await
        .unwrap();
    tick(&state).await.unwrap();
    let (_, interrupted) = request(app, "GET", &path, Value::Null).await;
    assert_eq!(interrupted["status"], "reconciliation_required");
    assert_eq!(posts.load(Ordering::SeqCst), 2);
    server.abort();
}
