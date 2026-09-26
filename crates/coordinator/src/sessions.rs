//! Operator bootstrap keys mint bounded sessions; only hashes enter storage.
use super::*;
use axum::Extension;

#[derive(Clone, Copy)]
pub(crate) struct Identity(pub Option<Uuid>);

#[derive(Deserialize, ToSchema)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct CreateSession {
    client_label: String,
}

#[derive(Serialize, ToSchema)]
#[serde(rename_all = "camelCase")]
pub struct SessionInfo {
    id: Uuid,
    client_label: String,
    created_at: DateTime<Utc>,
    expires_at: DateTime<Utc>,
}

#[derive(Serialize, ToSchema)]
#[serde(rename_all = "camelCase")]
pub struct SessionGrant {
    token: String,
    session: SessionInfo,
}

pub(crate) fn unauthorized() -> ApiError {
    ApiError(
        StatusCode::UNAUTHORIZED,
        "Your session has ended. Sign in to continue; your unsaved story stays in this window."
            .into(),
    )
}

pub(crate) async fn identify(state: &AppState, token: &str) -> ApiResult<Identity> {
    // Bootstrap keys can never authorize ordinary API operations.
    if !token.starts_with("mvm_s_") || token.len() != 70 {
        return Err(unauthorized());
    }
    let issuer = state.token_hash.ok_or_else(unauthorized)?;
    let hash: [u8; 32] = Sha256::digest(token.as_bytes()).into();
    let id: Option<Uuid> = sqlx::query_scalar("SELECT id FROM operator_sessions WHERE token_hash=$1 AND issuer_hash=$2 AND revoked_at IS NULL AND expires_at>clock_timestamp()")
        .bind(hash.as_slice()).bind(issuer.as_slice()).fetch_optional(&state.pool).await?;
    Ok(Identity(Some(id.ok_or_else(unauthorized)?)))
}

pub(crate) async fn valid(state: &AppState, identity: Identity) -> ApiResult<bool> {
    valid_on(&state.pool, state, identity).await
}

pub(crate) async fn valid_on<'e, E: sqlx::Executor<'e, Database = sqlx::Postgres>>(
    executor: E,
    state: &AppState,
    identity: Identity,
) -> ApiResult<bool> {
    let Some(id) = identity.0 else {
        return Ok(state.development && state.token_hash.is_none());
    };
    let Some(issuer) = state.token_hash else {
        return Ok(false);
    };
    Ok(sqlx::query_scalar("SELECT EXISTS(SELECT 1 FROM operator_sessions WHERE id=$1 AND issuer_hash=$2 AND revoked_at IS NULL AND expires_at>clock_timestamp())")
        .bind(id).bind(issuer.as_slice()).fetch_one(executor).await?)
}

#[utoipa::path(post, path="/api/v1/sessions", request_body=CreateSession, responses((status=201, body=SessionGrant), (status=401)))]
pub(crate) async fn create(
    State(state): State<AppState>,
    Json(input): Json<CreateSession>,
) -> ApiResult<impl IntoResponse> {
    let issuer = state.token_hash.ok_or_else(unauthorized)?;
    let label = input.client_label.trim();
    if label.is_empty() || label.chars().count() > 80 || label.chars().any(char::is_control) {
        return Err(invalid(
            "Name this session using 1–80 characters without control characters.",
        ));
    }
    // Two independent UUIDv4 values provide 244 random bits. Never log the grant.
    let token = format!(
        "mvm_s_{}{}",
        Uuid::new_v4().simple(),
        Uuid::new_v4().simple()
    );
    let hash: [u8; 32] = Sha256::digest(token.as_bytes()).into();
    let id = Uuid::new_v4();
    let row = sqlx::query("INSERT INTO operator_sessions(id,token_hash,issuer_hash,client_label,created_at,expires_at) VALUES($1,$2,$3,$4,clock_timestamp(),clock_timestamp()+interval '12 hours') RETURNING created_at,expires_at")
        .bind(id).bind(hash.as_slice()).bind(issuer.as_slice()).bind(label).fetch_one(&state.pool).await?;
    Ok((
        StatusCode::CREATED,
        Json(SessionGrant {
            token,
            session: SessionInfo {
                id,
                client_label: label.into(),
                created_at: row.get("created_at"),
                expires_at: row.get("expires_at"),
            },
        }),
    ))
}

#[utoipa::path(get, path="/api/v1/sessions/current", responses((status=200, body=Option<SessionInfo>), (status=401)))]
pub(crate) async fn current(
    State(state): State<AppState>,
    Extension(identity): Extension<Identity>,
) -> ApiResult<Json<Option<SessionInfo>>> {
    let Some(id) = identity.0 else {
        return Ok(Json(None));
    };
    let row = sqlx::query("SELECT client_label,created_at,expires_at FROM operator_sessions WHERE id=$1 AND revoked_at IS NULL AND expires_at>clock_timestamp()")
        .bind(id).fetch_optional(&state.pool).await?.ok_or_else(unauthorized)?;
    Ok(Json(Some(SessionInfo {
        id,
        client_label: row.get("client_label"),
        created_at: row.get("created_at"),
        expires_at: row.get("expires_at"),
    })))
}

#[utoipa::path(post, path="/api/v1/sessions/current/revoke", responses((status=200), (status=401)))]
pub(crate) async fn revoke(
    State(state): State<AppState>,
    Extension(identity): Extension<Identity>,
) -> ApiResult<Json<serde_json::Value>> {
    let id = identity.0.ok_or_else(unauthorized)?;
    sqlx::query("UPDATE operator_sessions SET revoked_at=clock_timestamp() WHERE id=$1 AND revoked_at IS NULL").bind(id).execute(&state.pool).await?;
    Ok(Json(serde_json::json!({"revoked":true})))
}

#[utoipa::path(post, path="/api/v1/sessions/revoke-all", responses((status=200), (status=401)))]
pub(crate) async fn revoke_all(
    State(state): State<AppState>,
    Extension(identity): Extension<Identity>,
) -> ApiResult<Json<serde_json::Value>> {
    identity.0.ok_or_else(unauthorized)?;
    let issuer = state.token_hash.ok_or_else(unauthorized)?;
    sqlx::query("UPDATE operator_sessions SET revoked_at=clock_timestamp() WHERE issuer_hash=$1 AND revoked_at IS NULL").bind(issuer.as_slice()).execute(&state.pool).await?;
    Ok(Json(serde_json::json!({"revoked":true})))
}
