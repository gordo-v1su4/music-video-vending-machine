use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use http_body_util::BodyExt;
use mvm_coordinator::{AppState, router};
use object_store::memory::InMemory;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::sync::Arc;
use tower::ServiceExt;

async fn call(
    app: &axum::Router,
    method: &str,
    path: &str,
    token: &str,
    body: Value,
) -> (StatusCode, Value) {
    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .method(method)
                .uri(path)
                .header("authorization", format!("Bearer {token}"))
                .header("content-type", "application/json")
                .body(Body::from(body.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    let status = response.status();
    if status.is_success() {
        assert_eq!(response.headers()["cache-control"], "no-store");
    }
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    (status, serde_json::from_slice(&bytes).unwrap())
}

fn isolated_state(bootstrap: &str) -> AppState {
    let url = std::env::var("MVVM_TEST_CONVEX_URL").expect("dedicated test endpoint required");
    let parsed = reqwest::Url::parse(&url).unwrap();
    assert_eq!(parsed.scheme(), "http");
    assert_eq!(
        parsed.host_str(),
        Some("127.0.0.1"),
        "test backend must be disposable and local"
    );
    let objects: Arc<dyn object_store::ObjectStore> = Arc::new(InMemory::new());
    AppState {
        convex: Some(
            mvm_coordinator::convex::Client::new(
                &url,
                &std::env::var("MVVM_TEST_CONVEX_ADMIN_KEY").unwrap(),
            )
            .unwrap(),
        ),
        analysis: None,
        transcription: None,
        objects,
        token_hash: Some(Sha256::digest(bootstrap.as_bytes()).into()),
        development: false,
        storage_name: "test".into(),
        object_bucket: "music-vending-machine".into(),
    }
}

#[tokio::test]
#[ignore = "requires disposable loopback MVVM_TEST_CONVEX_URL; run scripts/test-convex-http.mjs"]
async fn convex_http_sessions_work_without_postgres() {
    let bootstrap = uuid::Uuid::new_v4().to_string();
    let state = isolated_state(&bootstrap);
    let app = router(state.clone(), vec![]);
    assert_eq!(
        call(
            &app,
            "POST",
            "/api/v1/sessions",
            "wrong",
            json!({"clientLabel":"Test"})
        )
        .await
        .0,
        StatusCode::UNAUTHORIZED
    );
    let (status, grant) = call(
        &app,
        "POST",
        "/api/v1/sessions",
        &bootstrap,
        json!({"clientLabel":"Convex HTTP acceptance"}),
    )
    .await;
    assert_eq!(status, StatusCode::CREATED);
    let token = grant["token"].as_str().unwrap();
    let (status, current) = call(&app, "GET", "/api/v1/sessions/current", token, Value::Null).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(current, grant["session"]);
    let (status, fixture) = call(
        &app,
        "POST",
        "/api/v1/projects",
        token,
        json!({"name":"MVVM Convex persistence acceptance"}),
    )
    .await;
    assert_eq!(status, StatusCode::CREATED);
    let (status, projects) = call(&app, "GET", "/api/v1/projects", token, Value::Null).await;
    assert_eq!(status, StatusCode::OK);
    assert!(
        projects
            .as_array()
            .unwrap()
            .iter()
            .any(|project| project == &fixture)
    );
    let id = fixture["id"].as_str().unwrap();
    let (status, project) = call(
        &app,
        "GET",
        &format!("/api/v1/projects/{id}"),
        token,
        Value::Null,
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(project, fixture);
    let path = format!(
        "/api/v1/projects/{}/actions",
        fixture["id"].as_str().unwrap()
    );
    // An interrupted object PUT must retain the intent until exact bytes exist.
    let project_id = uuid::Uuid::parse_str(fixture["id"].as_str().unwrap()).unwrap();
    let asset_id = uuid::Uuid::new_v4();
    let bytes = bytes::Bytes::from_static(b"MVVM recovery acceptance bytes");
    let key = format!("projects/{project_id}/originals/{asset_id}");
    let asset = mvm_coordinator::Asset {
        id: asset_id,
        project_id,
        name: "recovery-fixture.bin".into(),
        media_type: "application/octet-stream".into(),
        sha256: format!("{:x}", Sha256::digest(&bytes)),
        size_bytes: bytes.len() as u64,
        duration_ms: None,
        url: format!("/api/v1/projects/{project_id}/assets/{asset_id}"),
        created_at: chrono::Utc::now(),
    };
    let auth = mvm_coordinator::convex_sessions::Auth {
        session_id: Some(uuid::Uuid::parse_str(grant["session"]["id"].as_str().unwrap()).unwrap()),
        issuer_hash: Some(mvm_coordinator::convex_sessions::hash(&bootstrap)),
        development: false,
    };
    let client = state.convex.as_ref().unwrap();
    client.begin_upload(&auth, &asset, &key).await.unwrap();
    assert_eq!(mvm_coordinator::reconcile_uploads(&state).await.unwrap(), 0);
    assert!(
        client
            .list_assets(&auth, project_id)
            .await
            .unwrap()
            .is_empty()
    );
    state
        .objects
        .put(
            &object_store::path::Path::from(key.as_str()),
            bytes.clone().into(),
        )
        .await
        .unwrap();
    assert_eq!(mvm_coordinator::reconcile_uploads(&state).await.unwrap(), 1);
    assert_eq!(mvm_coordinator::reconcile_uploads(&state).await.unwrap(), 0);
    assert_eq!(
        client.list_assets(&auth, project_id).await.unwrap().len(),
        1
    );
    let download = app
        .clone()
        .oneshot(
            Request::builder()
                .uri(&asset.url)
                .header("authorization", format!("Bearer {token}"))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(download.status(), StatusCode::OK);
    assert_eq!(
        download.into_body().collect().await.unwrap().to_bytes(),
        bytes
    );
    // Real multipart intake: one second of PCM silence, inspected by ffprobe.
    let mut wav = b"RIFF".to_vec();
    wav.extend_from_slice(&32036u32.to_le_bytes());
    wav.extend_from_slice(b"WAVEfmt ");
    wav.extend_from_slice(&16u32.to_le_bytes());
    wav.extend_from_slice(&1u16.to_le_bytes());
    wav.extend_from_slice(&1u16.to_le_bytes());
    wav.extend_from_slice(&16000u32.to_le_bytes());
    wav.extend_from_slice(&32000u32.to_le_bytes());
    wav.extend_from_slice(&2u16.to_le_bytes());
    wav.extend_from_slice(&16u16.to_le_bytes());
    wav.extend_from_slice(b"data");
    wav.extend_from_slice(&32000u32.to_le_bytes());
    wav.resize(32044, 0);
    let mut multipart = b"--mvvm-test\r\nContent-Disposition: form-data; name=\"file\"; filename=\"silence.wav\"\r\nContent-Type: audio/wav\r\n\r\n".to_vec();
    multipart.extend_from_slice(&wav);
    multipart.extend_from_slice(b"\r\n--mvvm-test--\r\n");
    let upload = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri(format!("/api/v1/projects/{project_id}/assets"))
                .header("authorization", format!("Bearer {token}"))
                .header("content-type", "multipart/form-data; boundary=mvvm-test")
                .body(Body::from(multipart))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(upload.status(), StatusCode::CREATED);
    let uploaded: Value =
        serde_json::from_slice(&upload.into_body().collect().await.unwrap().to_bytes()).unwrap();
    assert_eq!(uploaded["durationMs"], 1000);
    assert_eq!(uploaded["sha256"], format!("{:x}", Sha256::digest(&wav)));
    // Refuse to exercise the worker while any unrelated active job exists.
    let snapshot: Value = client
        .query("migration:exportSnapshot", json!({}))
        .await
        .unwrap();
    assert!(
        snapshot["audio_analysis_jobs"]
            .as_array()
            .unwrap()
            .iter()
            .all(|j| !matches!(
                j["status"].as_str(),
                Some("queued" | "running" | "submitting")
            ))
    );
    let submissions = Arc::new(std::sync::atomic::AtomicUsize::new(0));
    let counter = submissions.clone();
    let provider = axum::Router::new().route(
        "/analyze/studio/jobs",
        axum::routing::post(move || {
            let counter = counter.clone();
            async move {
                let attempt=counter.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
                if attempt==0 { (StatusCode::INTERNAL_SERVER_ERROR,axum::Json(json!({}))) }
                else { (StatusCode::ACCEPTED,axum::Json(json!({"id":"fixture-provider-job","status":"queued"}))) }
            }
        }),
    ).route("/analyze/studio/jobs/{id}",axum::routing::get(||async {
        axum::Json(json!({"id":"fixture-provider-job","status":"completed","padding":"x".repeat(200000),"result":{
            "schema_version":"studio-audio-v1","duration":1.0,"bpm":120.0,"confidence":3.2,"beats":[0.1,0.5],"onsets":[0.2],
            "energy":{"curve":[0.2,0.4],"sample_rate_hz":1.0,"start_time_s":0.0},
            "structure":{"source":"allin1","analyzed_duration_s":1.0,"provenance":{"status":"detected","method":"allin1:test","device":"cuda"},"boundaries":[0.0,1.0],"sections":[{"start":0.0,"end":1.0,"duration":1.0,"label":"verse","original_label":"verse","energy":0.5}]}
        }}))
    }));
    let transcript_fixture = json!({"metadata":{"duration":1.0},"results":{"channels":[{"alternatives":[{"transcript":"test","words":[{"word":"test","start":0.1,"end":0.8,"confidence":0.95}]}]}]}});
    let transcription_posts = Arc::new(std::sync::atomic::AtomicUsize::new(0));
    let transcript_count = transcription_posts.clone();
    let transcript_response = transcript_fixture.clone();
    let provider = provider.route(
        "/v1/listen",
        axum::routing::post(
            move |axum::extract::Query(query): axum::extract::Query<
                std::collections::HashMap<String, String>,
            >| {
                let counter = transcript_count.clone();
                let response = transcript_response.clone();
                async move {
                    assert_eq!(query.get("sentiment").map(String::as_str), Some("false"));
                    assert_eq!(query.get("model").map(String::as_str), Some("nova-3"));
                    if counter.fetch_add(1, std::sync::atomic::Ordering::SeqCst) == 0 {
                        (StatusCode::BAD_GATEWAY, axum::Json(json!({})))
                    } else {
                        (StatusCode::OK, axum::Json(response))
                    }
                }
            },
        ),
    );
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
    let origin = format!("http://{}", listener.local_addr().unwrap());
    let server = tokio::spawn(async move { axum::serve(listener, provider).await.unwrap() });
    let mut worker_state = state.clone();
    worker_state.analysis = Some(Arc::new(
        mvm_coordinator::analysis_jobs::Service::new(&origin, "fixture-key").unwrap(),
    ));
    let worker_app = router(worker_state.clone(), vec![]);
    let analysis_path = format!(
        "/api/v1/projects/{project_id}/assets/{}/analysis",
        uploaded["id"].as_str().unwrap()
    );
    assert_eq!(
        call(&worker_app, "POST", &analysis_path, token, Value::Null)
            .await
            .0,
        StatusCode::OK
    );
    mvm_coordinator::analysis_jobs::tick(&worker_state)
        .await
        .unwrap();
    let (status, job) = call(&worker_app, "GET", &analysis_path, token, Value::Null).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(job["status"], "reconciliation_required");
    mvm_coordinator::analysis_jobs::tick(&worker_state)
        .await
        .unwrap();
    assert_eq!(submissions.load(std::sync::atomic::Ordering::SeqCst), 1);
    let mut success_asset: mvm_coordinator::Asset =
        serde_json::from_value(uploaded.clone()).unwrap();
    success_asset.id = uuid::Uuid::new_v4();
    success_asset.url = format!("/api/v1/projects/{project_id}/assets/{}", success_asset.id);
    let success_key = format!("projects/{project_id}/originals/{}", success_asset.id);
    client
        .begin_upload(&auth, &success_asset, &success_key)
        .await
        .unwrap();
    state
        .objects
        .put(
            &object_store::path::Path::from(success_key.as_str()),
            bytes::Bytes::from(wav).into(),
        )
        .await
        .unwrap();
    client
        .complete_upload(&success_asset, &success_key, None)
        .await
        .unwrap();
    let success_path = format!("{}/analysis", success_asset.url);
    assert_eq!(
        call(&worker_app, "POST", &success_path, token, Value::Null)
            .await
            .0,
        StatusCode::OK
    );
    mvm_coordinator::analysis_jobs::tick(&worker_state)
        .await
        .unwrap();
    assert_eq!(
        call(&worker_app, "GET", &success_path, token, Value::Null)
            .await
            .1["status"],
        "running"
    );
    tokio::time::sleep(std::time::Duration::from_millis(3100)).await;
    mvm_coordinator::analysis_jobs::tick(&worker_state)
        .await
        .unwrap();
    let (status, completed) = call(&worker_app, "GET", &success_path, token, Value::Null).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(completed["status"], "completed", "{}", completed["message"]);
    assert!(completed["result"].is_object());
    assert_eq!(submissions.load(std::sync::atomic::Ordering::SeqCst), 2);
    let snapshot: Value = client
        .query("migration:exportSnapshot", json!({}))
        .await
        .unwrap();
    assert!(
        snapshot["transcription_jobs"]
            .as_array()
            .unwrap()
            .iter()
            .all(|j| !matches!(j["status"].as_str(), Some("queued" | "running")))
    );
    worker_state.transcription = Some(Arc::new(
        mvm_coordinator::transcription::Service::new(&origin, "fixture-key").unwrap(),
    ));
    let transcription_app = router(worker_state.clone(), vec![]);
    let transcript_path = format!(
        "/api/v1/projects/{project_id}/assets/{}/transcription",
        uploaded["id"].as_str().unwrap()
    );
    assert_eq!(
        call(
            &transcription_app,
            "POST",
            &transcript_path,
            token,
            Value::Null
        )
        .await
        .0,
        StatusCode::OK
    );
    mvm_coordinator::transcription::tick(&worker_state)
        .await
        .unwrap();
    let (status, failed) = call(
        &transcription_app,
        "GET",
        &transcript_path,
        token,
        Value::Null,
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(failed["status"], "reconciliation_required");
    mvm_coordinator::transcription::tick(&worker_state)
        .await
        .unwrap();
    assert_eq!(
        transcription_posts.load(std::sync::atomic::Ordering::SeqCst),
        1
    );
    let recovery = json!({"jobId":failed["id"],"expectedUpdatedAt":failed["updatedAt"],"sourceSha256":uploaded["sha256"],"providerResponse":transcript_fixture,"confirmedSource":true});
    let (status, recovered) = call(
        &transcription_app,
        "POST",
        &format!("{transcript_path}/recovery"),
        token,
        recovery.clone(),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(recovered["status"], "completed");
    assert_eq!(
        call(
            &transcription_app,
            "POST",
            &format!("{transcript_path}/recovery"),
            token,
            recovery
        )
        .await
        .0,
        StatusCode::CONFLICT
    );
    assert_eq!(
        transcription_posts.load(std::sync::atomic::Ordering::SeqCst),
        1
    );
    let successful_transcript = format!("{}/transcription", success_asset.url);
    assert_eq!(
        call(
            &transcription_app,
            "POST",
            &successful_transcript,
            token,
            Value::Null
        )
        .await
        .0,
        StatusCode::OK
    );
    mvm_coordinator::transcription::tick(&worker_state)
        .await
        .unwrap();
    let (status, completed) = call(
        &transcription_app,
        "GET",
        &successful_transcript,
        token,
        Value::Null,
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(completed["status"], "completed");
    assert_eq!(completed["result"]["words"].as_array().unwrap().len(), 1);
    assert_eq!(
        transcription_posts.load(std::sync::atomic::Ordering::SeqCst),
        2
    );
    server.abort();
    let edit = json!({"expectedRevision":0,"action":{"type":"setTreatment","text":"Disposable persistence test; not creative approval."}});
    let (a, b) = tokio::join!(
        call(&app, "POST", &path, token, edit.clone()),
        call(&app, "POST", &path, token, edit)
    );
    assert!(matches!(
        (a.0, b.0),
        (StatusCode::OK, StatusCode::CONFLICT) | (StatusCode::CONFLICT, StatusCode::OK)
    ));
    let body = if a.0 == StatusCode::OK { a.1 } else { b.1 };
    assert_eq!(body["revision"], 1);
    let events = app
        .clone()
        .oneshot(
            Request::builder()
                .uri(format!(
                    "/api/v1/projects/{}/events?after=0",
                    fixture["id"].as_str().unwrap()
                ))
                .header("authorization", format!("Bearer {token}"))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(events.status(), StatusCode::OK);
    let mut event_body = events.into_body();
    let first_event = tokio::time::timeout(std::time::Duration::from_secs(5), event_body.frame())
        .await
        .unwrap()
        .unwrap()
        .unwrap()
        .into_data()
        .unwrap();
    let first_event = String::from_utf8(first_event.to_vec()).unwrap();
    assert!(
        first_event.replace(": ", ":").contains("event:project")
            && first_event.replace(": ", ":").contains("id:1")
    );
    let missing = json!({"expectedRevision":1,"action":{"type":"setMaster","assetId":uuid::Uuid::new_v4(),"durationMs":1000}});
    assert_eq!(
        call(&app, "POST", &path, token, missing).await.0,
        StatusCode::NOT_FOUND
    );
    let restarted = router(state, vec![]);
    assert_eq!(
        call(
            &restarted,
            "GET",
            "/api/v1/sessions/current",
            token,
            Value::Null
        )
        .await
        .0,
        StatusCode::OK
    );
    assert_eq!(
        call(
            &restarted,
            "POST",
            "/api/v1/sessions/current/revoke",
            token,
            Value::Null
        )
        .await
        .0,
        StatusCode::OK
    );
    assert_eq!(
        call(&app, "GET", "/api/v1/sessions/current", token, Value::Null)
            .await
            .0,
        StatusCode::UNAUTHORIZED
    );
    let ended = tokio::time::timeout(std::time::Duration::from_secs(5), event_body.frame())
        .await
        .unwrap()
        .unwrap()
        .unwrap()
        .into_data()
        .unwrap();
    assert!(
        String::from_utf8(ended.to_vec())
            .unwrap()
            .replace(": ", ":")
            .contains("event:session-ended")
    );
}

#[tokio::test]
#[ignore = "requires disposable loopback Convex; run scripts/test-convex-http.mjs"]
async fn convex_session_boundaries() {
    let bootstrap = uuid::Uuid::new_v4().to_string();
    let state = isolated_state(&bootstrap);
    let app = router(state.clone(), vec![]);
    for token in [&bootstrap, "wrong"] {
        assert_eq!(
            call(&app, "GET", "/api/v1/projects", token, Value::Null)
                .await
                .0,
            StatusCode::UNAUTHORIZED
        );
    }
    let rejected = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/api/v1/sessions")
                .header("origin", "https://untrusted.invalid")
                .header("authorization", format!("Bearer {bootstrap}"))
                .header("content-type", "application/json")
                .body(Body::from(r#"{"clientLabel":"Test"}"#))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(rejected.status(), StatusCode::FORBIDDEN);
    let mut grants = Vec::new();
    for _ in 0..3 {
        let (status, grant) = call(
            &app,
            "POST",
            "/api/v1/sessions",
            &bootstrap,
            json!({"clientLabel":"Test"}),
        )
        .await;
        assert_eq!(status, StatusCode::CREATED);
        grants.push(grant);
    }
    let a = grants[0]["token"].as_str().unwrap();
    let b = grants[1]["token"].as_str().unwrap();
    let c = grants[2]["token"].as_str().unwrap();
    assert_ne!(a, b);
    assert_eq!(
        call(
            &app,
            "POST",
            "/api/v1/sessions",
            a,
            json!({"clientLabel":"No delegation"})
        )
        .await
        .0,
        StatusCode::UNAUTHORIZED
    );
    // Authentication before body extraction cannot authorize a write after revocation.
    let (arrived_tx, arrived_rx) = tokio::sync::oneshot::channel();
    let (resume_tx, resume_rx) = tokio::sync::oneshot::channel();
    let body = Body::from_stream(async_stream::stream! {
        let _ = arrived_tx.send(());
        let _ = resume_rx.await;
        yield Ok::<_, std::io::Error>(bytes::Bytes::from_static(b"{\"name\":\"Must not be created\"}"));
    });
    let request = Request::builder()
        .method("POST")
        .uri("/api/v1/projects")
        .header("authorization", format!("Bearer {a}"))
        .header("content-type", "application/json")
        .body(body)
        .unwrap();
    let slow_app = app.clone();
    let pending = tokio::spawn(async move { slow_app.oneshot(request).await.unwrap() });
    tokio::time::timeout(std::time::Duration::from_secs(3), arrived_rx)
        .await
        .unwrap()
        .unwrap();
    assert_eq!(
        call(
            &app,
            "POST",
            "/api/v1/sessions/current/revoke",
            a,
            Value::Null
        )
        .await
        .0,
        StatusCode::OK
    );
    resume_tx.send(()).unwrap();
    assert_eq!(pending.await.unwrap().status(), StatusCode::UNAUTHORIZED);
    assert_eq!(
        call(&app, "GET", "/api/v1/projects", b, Value::Null)
            .await
            .0,
        StatusCode::OK
    );
    let rotated = router(
        AppState {
            token_hash: Some(Sha256::digest(b"rotated-test-key").into()),
            ..state
        },
        vec![],
    );
    assert_eq!(
        call(&rotated, "GET", "/api/v1/projects", b, Value::Null)
            .await
            .0,
        StatusCode::UNAUTHORIZED
    );
    assert_eq!(
        call(&app, "POST", "/api/v1/sessions/revoke-all", b, Value::Null)
            .await
            .0,
        StatusCode::OK
    );
    for token in [b, c] {
        assert_eq!(
            call(&app, "GET", "/api/v1/projects", token, Value::Null)
                .await
                .0,
            StatusCode::UNAUTHORIZED
        );
    }
}
