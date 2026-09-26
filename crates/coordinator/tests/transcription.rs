mod support;
use axum::{
    Json, Router,
    body::Body,
    http::{Request, StatusCode},
    routing::post,
};
use http_body_util::BodyExt;
use mvm_coordinator::{
    AppState, Asset, router,
    transcription::{Service, tick},
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
#[ignore = "requires disposable Convex and ffmpeg; run scripts/test-convex-http.mjs"]
async fn convex_transcription_survives_restart_and_never_repeats_paid_submissions() {
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
            if fail.load(Ordering::SeqCst)==1 { (StatusCode::BAD_GATEWAY,Json(json!({"error":"lost response"}))) }
            else { (StatusCode::OK,Json(json!({"metadata":{"duration":if fail.load(Ordering::SeqCst)==2 {11} else {10}},"results":{"channels":[{"alternatives":[{"transcript":"Test phrase", "words":[{"word":"test","start":1,"end":2,"confidence":0.9},{"word":"phrase","start":2,"end":3,"confidence":0.9}]}]}]}}))) }
        }
    }));
    let provider = provider.layer(axum::extract::DefaultBodyLimit::max(8 * 1024 * 1024));
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
    let origin = format!("http://{}", listener.local_addr().unwrap());
    let server = tokio::spawn(async move { axum::serve(listener, provider).await.unwrap() });
    let state = AppState {
        transcription: Some(Arc::new(Service::new(&origin, "test-key").unwrap())),
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
    for n in 0..5 {
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
    state
        .objects
        .delete(&Path::from(format!(
            "projects/{project_id}/originals/{}",
            ids[3]
        )))
        .await
        .unwrap();
    let unavailable_path = format!(
        "/api/v1/projects/{project_id}/assets/{}/transcription",
        ids[3]
    );
    request(app.clone(), "POST", &unavailable_path, Value::Null).await;
    tick(&state).await.unwrap();
    assert_eq!(posts.load(Ordering::SeqCst), 0);
    let (_, waiting) = request(app.clone(), "GET", &unavailable_path, Value::Null).await;
    assert_eq!(waiting["status"], "queued");
    assert!(
        waiting["message"]
            .as_str()
            .unwrap()
            .contains("Other queued files can continue")
    );
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
    let _: Value = client
        .mutation(
            "testing:transcriptionState",
            json!({"assetId":ids[0],"mode":"legacy"}),
        )
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
    let _: Value = client
        .mutation(
            "testing:transcriptionState",
            json!({"assetId":ids[2],"mode":"running"}),
        )
        .await
        .unwrap();
    tick(&state).await.unwrap();
    let (_, interrupted) = request(app.clone(), "GET", &path, Value::Null).await;
    assert_eq!(interrupted["status"], "reconciliation_required");
    assert_eq!(posts.load(Ordering::SeqCst), 2);
    fail.store(2, Ordering::SeqCst);
    let path = format!(
        "/api/v1/projects/{project_id}/assets/{}/transcription",
        ids[4]
    );
    request(app.clone(), "POST", &path, Value::Null).await;
    tick(&state).await.unwrap();
    let (_, invalid) = request(app.clone(), "GET", &path, Value::Null).await;
    assert_eq!(invalid["status"], "reconciliation_required");
    let receipt: Value = client
        .mutation(
            "testing:transcriptionState",
            json!({"assetId":ids[4],"mode":"read"}),
        )
        .await
        .unwrap();
    assert_eq!(
        receipt["primary"]["metadata"]["duration"].as_f64(),
        Some(11.0)
    );
    tick(&state).await.unwrap();
    assert_eq!(posts.load(Ordering::SeqCst), 3);
    // Recovery never resubmits: use saved valid passes or an explicitly verified
    // completed provider response, and reject stale or cross-source decisions.
    let recovery_path = format!("{path}/recovery");
    let decision = json!({"jobId":invalid["id"],"expectedUpdatedAt":invalid["updatedAt"],"sourceSha256":invalid["sha256"]});
    assert_eq!(
        request(app.clone(), "POST", &recovery_path, decision.clone())
            .await
            .0,
        StatusCode::UNPROCESSABLE_ENTITY
    );
    let saved: Value = client
        .mutation(
            "testing:transcriptionState",
            json!({"assetId":ids[0],"mode":"read"}),
        )
        .await
        .unwrap();
    let mut imported = decision.clone();
    imported["providerResponse"] = saved["primary"].clone();
    assert_eq!(
        request(app.clone(), "POST", &recovery_path, imported.clone())
            .await
            .0,
        StatusCode::UNPROCESSABLE_ENTITY
    );
    imported["confirmedSource"] = json!(true);
    imported["sourceSha256"] = json!("wrong-source");
    assert_eq!(
        request(app.clone(), "POST", &recovery_path, imported.clone())
            .await
            .0,
        StatusCode::UNPROCESSABLE_ENTITY
    );
    imported["sourceSha256"] = invalid["sha256"].clone();
    let (status, restored) = request(app.clone(), "POST", &recovery_path, imported.clone()).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(restored["status"], "completed");
    assert_eq!(restored["result"]["wordCount"], 2);
    assert_eq!(
        request(app.clone(), "POST", &recovery_path, imported)
            .await
            .0,
        StatusCode::CONFLICT
    );
    let retained: Value = client
        .mutation(
            "testing:transcriptionState",
            json!({"assetId":ids[4],"mode":"read"}),
        )
        .await
        .unwrap();
    assert_eq!(retained["primary"], receipt["primary"]);
    assert_eq!(retained["recovery"]["paidReplay"], false);
    // A interrupted later pass can recover the response already on disk.
    let _: Value = client
        .mutation(
            "testing:transcriptionState",
            json!({"assetId":ids[2],"mode":"receipt","receipt":saved}),
        )
        .await
        .unwrap();
    let saved_path = format!(
        "/api/v1/projects/{project_id}/assets/{}/transcription/recovery",
        ids[2]
    );
    let saved_decision = json!({"jobId":interrupted["id"],"expectedUpdatedAt":interrupted["updatedAt"],"sourceSha256":interrupted["sha256"]});
    let mut unauthorized = state.clone();
    unauthorized.development = false;
    unauthorized.token_hash = Some([1; 32]);
    assert_eq!(
        request(
            router(unauthorized, vec![]),
            "POST",
            &saved_path,
            saved_decision.clone()
        )
        .await
        .0,
        StatusCode::UNAUTHORIZED
    );
    let (status, restored) = request(app.clone(), "POST", &saved_path, saved_decision).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(restored["result"]["wordCount"], 2);
    tick(&state).await.unwrap();
    assert_eq!(posts.load(Ordering::SeqCst), 3);
    server.abort();
    let _: Value = client
        .mutation(
            "testing:clearTranscription",
            json!({"projectId":project_id}),
        )
        .await
        .unwrap();
}

#[tokio::test]
#[ignore = "requires disposable Convex and ffmpeg; run scripts/test-convex-http.mjs"]
async fn convex_sparse_vocals_trigger_bounded_fallback_and_timed_tail() {
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
        transcription: Some(Arc::new(Service::new(&origin, "test-key").unwrap())),
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
    client.begin_upload(&auth, &asset, &key).await.unwrap();
    client.complete_upload(&asset, &key, None).await.unwrap();
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
    let _: Value = client
        .mutation(
            "testing:clearTranscription",
            json!({"projectId":project_id}),
        )
        .await
        .unwrap();
}
