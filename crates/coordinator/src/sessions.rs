//! Operator bootstrap keys mint bounded sessions; only hashes enter storage.
use super::*;
use axum::Extension;

#[derive(Clone, Copy)]
pub(crate) struct Identity(pub Option<Uuid>);

pub(crate) fn convex_auth(state: &AppState, identity: Identity) -> convex_sessions::Auth {
    convex_sessions::Auth {
        session_id: identity.0,
        issuer_hash: state.token_hash.map(|bytes| {
            format!(
                "\\x{}",
                bytes.iter().map(|b| format!("{b:02x}")).collect::<String>()
            )
        }),
        development: state.development,
    }
}
impl From<convex_sessions::Info> for SessionInfo {
    fn from(value: convex_sessions::Info) -> Self {
        Self {
            id: value.id,
            client_label: value.client_label,
            created_at: value.created_at,
            expires_at: value.expires_at,
        }
    }
}

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
    let client = state
        .convex
        .as_ref()
        .ok_or(crate::convex::Error::Configuration)?;
    let issuer = convex_auth(state, Identity(None))
        .issuer_hash
        .ok_or_else(unauthorized)?;
    Ok(Identity(Some(
        client
            .identify_session(&issuer, token)
            .await?
            .ok_or_else(unauthorized)?,
    )))
}

pub(crate) async fn valid(state: &AppState, identity: Identity) -> ApiResult<bool> {
    let client = state
        .convex
        .as_ref()
        .ok_or(crate::convex::Error::Configuration)?;
    Ok(client.valid_session(&convex_auth(state, identity)).await?)
}

#[utoipa::path(post, path="/api/v1/sessions", request_body=CreateSession, responses((status=201, body=SessionGrant), (status=401)))]
pub(crate) async fn create(
    State(state): State<AppState>,
    Json(input): Json<CreateSession>,
) -> ApiResult<impl IntoResponse> {
    let label = input.client_label.trim();
    if label.is_empty() || label.chars().count() > 80 || label.chars().any(char::is_control) {
        return Err(invalid(
            "Name this session using 1–80 characters without control characters.",
        ));
    }
    let client = state
        .convex
        .as_ref()
        .ok_or(crate::convex::Error::Configuration)?;
    let issuer = convex_auth(&state, Identity(None))
        .issuer_hash
        .ok_or_else(unauthorized)?;
    let (token, session) = client.create_session(&issuer, label).await?;
    Ok((
        StatusCode::CREATED,
        Json(SessionGrant {
            token,
            session: session.into(),
        }),
    ))
}

#[utoipa::path(get, path="/api/v1/sessions/current", responses((status=200, body=Option<SessionInfo>), (status=401)))]
pub(crate) async fn current(
    State(state): State<AppState>,
    Extension(identity): Extension<Identity>,
) -> ApiResult<Json<Option<SessionInfo>>> {
    let client = state
        .convex
        .as_ref()
        .ok_or(crate::convex::Error::Configuration)?;
    Ok(Json(
        client
            .current_session(&convex_auth(&state, identity))
            .await?
            .map(Into::into),
    ))
}

#[utoipa::path(post, path="/api/v1/sessions/current/revoke", responses((status=200), (status=401)))]
pub(crate) async fn revoke(
    State(state): State<AppState>,
    Extension(identity): Extension<Identity>,
) -> ApiResult<Json<serde_json::Value>> {
    let client = state
        .convex
        .as_ref()
        .ok_or(crate::convex::Error::Configuration)?;
    client
        .revoke_session(&convex_auth(&state, identity), false)
        .await?;
    Ok(Json(serde_json::json!({"revoked":true})))
}

#[utoipa::path(post, path="/api/v1/sessions/revoke-all", responses((status=200), (status=401)))]
pub(crate) async fn revoke_all(
    State(state): State<AppState>,
    Extension(identity): Extension<Identity>,
) -> ApiResult<Json<serde_json::Value>> {
    let client = state
        .convex
        .as_ref()
        .ok_or(crate::convex::Error::Configuration)?;
    client
        .revoke_session(&convex_auth(&state, identity), true)
        .await?;
    Ok(Json(serde_json::json!({"revoked":true})))
}
