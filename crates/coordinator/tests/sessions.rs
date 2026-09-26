use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use http_body_util::BodyExt;
use mvm_coordinator::{AppState, migrate, prune_operator_sessions, router};
use object_store::memory::InMemory;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use sqlx::{Row, postgres::PgPoolOptions};
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

#[tokio::test]
#[ignore = "requires isolated MVM_TEST_DATABASE_URL; CI runs explicitly"]
async fn sessions_are_bounded_revocable_and_durable() {
    let url = std::env::var("MVM_TEST_DATABASE_URL").unwrap();
    let pool = PgPoolOptions::new()
        .max_connections(5)
        .connect(&url)
        .await
        .unwrap();
    let db: String = sqlx::query_scalar("SELECT current_database()")
        .fetch_one(&pool)
        .await
        .unwrap();
    assert_eq!(db, "mvm_test", "Refusing non-test database");
    migrate(&pool).await.unwrap();
    let bootstrap = uuid::Uuid::new_v4().to_string();
    let state = AppState {
        pool: pool.clone(),
        objects: Arc::new(InMemory::new()),
        token_hash: Some(Sha256::digest(bootstrap.as_bytes()).into()),
        development: false,
        storage_name: "test".into(),
    };
    let app = router(state.clone(), vec![]);
    for token in [&bootstrap, "wrong", &format!("mvm_s_{}", "0".repeat(64))] {
        assert_eq!(
            call(&app, "GET", "/api/v1/projects", token, Value::Null)
                .await
                .0,
            StatusCode::UNAUTHORIZED
        );
    }
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
    for _ in 0..6 {
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
    let d = grants[3]["token"].as_str().unwrap();
    let old_expired = uuid::Uuid::parse_str(grants[4]["session"]["id"].as_str().unwrap()).unwrap();
    let old_revoked = uuid::Uuid::parse_str(grants[5]["session"]["id"].as_str().unwrap()).unwrap();
    sqlx::query("UPDATE operator_sessions SET created_at=clock_timestamp()-interval '9 days', expires_at=clock_timestamp()-interval '8 days' WHERE id=$1")
        .bind(old_expired).execute(&pool).await.unwrap();
    sqlx::query(
        "UPDATE operator_sessions SET revoked_at=clock_timestamp()-interval '8 days' WHERE id=$1",
    )
    .bind(old_revoked)
    .execute(&pool)
    .await
    .unwrap();
    assert!(prune_operator_sessions(&pool).await.unwrap() >= 2);
    let retained: i64 =
        sqlx::query_scalar("SELECT count(*) FROM operator_sessions WHERE id=ANY($1)")
            .bind(vec![old_expired, old_revoked])
            .fetch_one(&pool)
            .await
            .unwrap();
    assert_eq!(retained, 0);
    assert_eq!(
        call(&app, "GET", "/api/v1/sessions/current", b, Value::Null)
            .await
            .0,
        StatusCode::OK
    );
    // Authenticate headers first, then expire the session while the JSON body
    // is still arriving. The write must check again after body extraction.
    let (arrived_tx, arrived_rx) = tokio::sync::oneshot::channel();
    let (resume_tx, resume_rx) = tokio::sync::oneshot::channel();
    let slow_body = Body::from_stream(async_stream::stream! {
        let _ = arrived_tx.send(());
        let _ = resume_rx.await;
        yield Ok::<_, std::io::Error>(bytes::Bytes::from_static(b"{\"name\":\"Must not be created after expiry\"}"));
    });
    let slow_app = app.clone();
    let slow_request = Request::builder()
        .method("POST")
        .uri("/api/v1/projects")
        .header("authorization", format!("Bearer {c}"))
        .header("content-type", "application/json")
        .body(slow_body)
        .unwrap();
    let pending = tokio::spawn(async move { slow_app.oneshot(slow_request).await.unwrap() });
    tokio::time::timeout(std::time::Duration::from_secs(3), arrived_rx)
        .await
        .unwrap()
        .unwrap();
    sqlx::query("UPDATE operator_sessions SET created_at=clock_timestamp()-interval '13 hours', expires_at=clock_timestamp()-interval '1 hour' WHERE id=$1")
        .bind(uuid::Uuid::parse_str(grants[2]["session"]["id"].as_str().unwrap()).unwrap()).execute(&pool).await.unwrap();
    resume_tx.send(()).unwrap();
    assert_eq!(pending.await.unwrap().status(), StatusCode::UNAUTHORIZED);
    assert_ne!(a, b);
    let id = uuid::Uuid::parse_str(grants[0]["session"]["id"].as_str().unwrap()).unwrap();
    let row = sqlx::query("SELECT token_hash,extract(epoch from expires_at-created_at)::float8 AS lifetime FROM operator_sessions WHERE id=$1").bind(id).fetch_one(&pool).await.unwrap();
    assert_eq!(
        row.get::<Vec<u8>, _>("token_hash"),
        Sha256::digest(a.as_bytes()).to_vec()
    );
    assert!((row.get::<f64, _>("lifetime") - 43200.0).abs() < 1.0);
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
    let restarted = router(
        AppState {
            pool: PgPoolOptions::new().connect(&url).await.unwrap(),
            ..state.clone()
        },
        vec![],
    );
    assert_eq!(
        call(
            &restarted,
            "GET",
            "/api/v1/sessions/current",
            a,
            Value::Null
        )
        .await
        .1,
        grants[0]["session"]
    );
    let (status, project) = call(
        &app,
        "POST",
        "/api/v1/projects",
        a,
        json!({"name":"Session stream fixture"}),
    )
    .await;
    assert_eq!(status, StatusCode::CREATED);
    let stream = app
        .clone()
        .oneshot(
            Request::builder()
                .uri(format!(
                    "/api/v1/projects/{}/events?after=0",
                    project["id"].as_str().unwrap()
                ))
                .header("authorization", format!("Bearer {a}"))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(stream.status(), StatusCode::OK);
    let mut stream_body = stream.into_body();
    // Poll the live stream before revoking: an open SSE connection must stop too.
    assert!(
        tokio::time::timeout(std::time::Duration::from_millis(100), stream_body.frame())
            .await
            .is_err()
    );
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
    let ended = tokio::time::timeout(std::time::Duration::from_secs(3), stream_body.collect())
        .await
        .unwrap()
        .unwrap()
        .to_bytes();
    assert!(String::from_utf8_lossy(&ended).contains("event: session-ended"));
    assert_eq!(
        call(&restarted, "GET", "/api/v1/projects", a, Value::Null)
            .await
            .0,
        StatusCode::UNAUTHORIZED
    );
    assert_eq!(
        call(&app, "GET", "/api/v1/projects", b, Value::Null)
            .await
            .0,
        StatusCode::OK
    );
    sqlx::query("UPDATE operator_sessions SET created_at=clock_timestamp()-interval '13 hours', expires_at=clock_timestamp()-interval '1 hour' WHERE id=$1")
        .bind(uuid::Uuid::parse_str(grants[2]["session"]["id"].as_str().unwrap()).unwrap()).execute(&pool).await.unwrap();
    assert_eq!(
        call(&app, "GET", "/api/v1/projects", c, Value::Null)
            .await
            .0,
        StatusCode::UNAUTHORIZED
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
    assert_eq!(
        call(&app, "GET", "/api/v1/projects", b, Value::Null)
            .await
            .0,
        StatusCode::UNAUTHORIZED
    );
    assert_eq!(
        call(&app, "GET", "/api/v1/projects", d, Value::Null)
            .await
            .0,
        StatusCode::UNAUTHORIZED
    );
}
