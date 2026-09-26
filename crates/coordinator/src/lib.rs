pub mod analysis;
pub mod analysis_jobs;
pub mod convex;
pub mod convex_analysis;
pub mod convex_payloads;
pub mod convex_projects;
pub mod convex_sessions;
pub mod convex_transcription;
pub mod convex_uploads;
mod sessions;
pub mod transcription;

use axum::{
    Json, Router,
    body::Body,
    extract::{DefaultBodyLimit, Multipart, Path, Query, Request, State},
    http::{StatusCode, header},
    middleware::{self, Next},
    response::{
        IntoResponse, Response, Sse,
        sse::{Event, KeepAlive},
    },
    routing::{get, post},
};
use bytes::Bytes;
use chrono::{DateTime, Utc};
use mvm_domain::{Action, DomainError, Project};
use object_store::{ObjectStore, path::Path as ObjectPath};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::{convert::Infallible, sync::Arc, time::Duration};
use subtle::ConstantTimeEq;
use tower_http::cors::CorsLayer;
use utoipa::{OpenApi, ToSchema};
use uuid::Uuid;

#[derive(Clone)]
pub struct AppState {
    pub convex: Option<convex::Client>,
    pub transcription: Option<Arc<transcription::Service>>,
    pub analysis: Option<Arc<analysis_jobs::Service>>,
    pub objects: Arc<dyn ObjectStore>,
    pub token_hash: Option<[u8; 32]>,
    pub development: bool,
    pub storage_name: String,
    pub object_bucket: String,
}
#[derive(Debug)]
pub struct ApiError(StatusCode, String);
impl From<convex::Error> for ApiError {
    fn from(error: convex::Error) -> Self {
        use convex::Error;
        match error {
            Error::Unauthorized => sessions::unauthorized(),
            Error::NotFound => missing(),
            Error::Conflict => Self(
                StatusCode::CONFLICT,
                "This project changed. Reload before saving.".into(),
            ),
            Error::Invalid => invalid("Invalid saved data or request."),
            _ => Self(
                StatusCode::SERVICE_UNAVAILABLE,
                "Project storage is unavailable. Reconnect to check whether your change was saved."
                    .into(),
            ),
        }
    }
}
impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        (self.0, Json(serde_json::json!({"error": self.1}))).into_response()
    }
}
impl From<DomainError> for ApiError {
    fn from(e: DomainError) -> Self {
        Self(
            if e == DomainError::Conflict {
                StatusCode::CONFLICT
            } else {
                StatusCode::UNPROCESSABLE_ENTITY
            },
            e.to_string(),
        )
    }
}
type ApiResult<T> = Result<T, ApiError>;
fn invalid(message: &str) -> ApiError {
    ApiError(StatusCode::UNPROCESSABLE_ENTITY, message.into())
}
fn missing() -> ApiError {
    ApiError(
        StatusCode::NOT_FOUND,
        "Project or asset was not found.".into(),
    )
}

#[derive(Serialize, Deserialize, ToSchema)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct CreateProject {
    pub name: String,
}
#[derive(Serialize, Deserialize, ToSchema)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct ProjectAction {
    pub expected_revision: u64,
    pub action: Action,
}
#[derive(Clone, Serialize, Deserialize, ToSchema)]
#[serde(rename_all = "camelCase")]
pub struct Asset {
    pub id: Uuid,
    pub project_id: Uuid,
    pub name: String,
    pub media_type: String,
    pub sha256: String,
    pub size_bytes: u64,
    pub duration_ms: Option<u64>,
    pub url: String,
    pub created_at: DateTime<Utc>,
}

pub fn router(state: AppState, origins: Vec<axum::http::HeaderValue>) -> Router {
    let protected = Router::new()
        .route(
            "/api/v1/sessions",
            post(sessions::create).layer(DefaultBodyLimit::max(4096)),
        )
        .route("/api/v1/sessions/current", get(sessions::current))
        .route("/api/v1/sessions/current/revoke", post(sessions::revoke))
        .route("/api/v1/sessions/revoke-all", post(sessions::revoke_all))
        .route("/api/v1/projects", get(list_projects).post(create_project))
        .route("/api/v1/projects/{id}", get(get_project))
        .route("/api/v1/projects/{id}/actions", post(project_action))
        .route("/api/v1/projects/{id}/events", get(project_events))
        .route(
            "/api/v1/projects/{id}/assets",
            get(list_assets).post(upload_asset),
        )
        .route("/api/v1/projects/{id}/assets/{asset_id}", get(get_asset))
        .route(
            "/api/v1/projects/{id}/assets/{asset_id}/transcription",
            get(transcription::get).post(transcription::start),
        )
        .route(
            "/api/v1/projects/{id}/assets/{asset_id}/transcription/recovery",
            post(transcription::recover),
        )
        .route(
            "/api/v1/projects/{id}/assets/{asset_id}/analysis",
            get(analysis_jobs::get).post(analysis_jobs::start),
        )
        .route_layer(middleware::from_fn_with_state(
            (state.clone(), origins.clone()),
            authenticate,
        ));
    Router::new()
        .merge(protected)
        .route("/api/v1/health", get(health))
        .route(
            "/api/v1/openapi.json",
            get(|| async { Json(ApiDoc::openapi()) }),
        )
        .layer(DefaultBodyLimit::max(128 * 1024 * 1024))
        .layer(
            CorsLayer::new()
                .allow_origin(origins)
                .allow_methods([axum::http::Method::GET, axum::http::Method::POST])
                .allow_headers([header::AUTHORIZATION, header::CONTENT_TYPE]),
        )
        .with_state(state)
}
async fn authenticate(
    State((state, origins)): State<(AppState, Vec<axum::http::HeaderValue>)>,
    mut req: Request,
    next: Next,
) -> Response {
    // A DNS-rebound page can send same-origin GETs without Origin. Anonymous
    // development requests must also address the API through a loopback host.
    if state.development && !local_request_host(&req) {
        return ApiError(StatusCode::FORBIDDEN, "Use a loopback API hostname.".into())
            .into_response();
    }
    // CORS alone does not prevent simple multipart POSTs from reaching handlers.
    if req
        .headers()
        .get(header::ORIGIN)
        .is_some_and(|origin| !origins.contains(origin))
    {
        return ApiError(
            StatusCode::FORBIDDEN,
            "This browser origin is not allowed.".into(),
        )
        .into_response();
    }
    let bearer = req
        .headers()
        .get(header::AUTHORIZATION)
        .and_then(|v| v.to_str().ok())
        .and_then(|v| v.strip_prefix("Bearer "));
    let login = req.uri().path() == "/api/v1/sessions" && req.method() == axum::http::Method::POST;
    let identity = if login {
        match (state.token_hash, bearer) {
            (Some(expected), Some(value))
                if bool::from(
                    <[u8; 32]>::from(Sha256::digest(value.as_bytes())).ct_eq(&expected),
                ) =>
            {
                sessions::Identity(None)
            }
            _ => return sessions::unauthorized().into_response(),
        }
    } else if state.development && state.token_hash.is_none() {
        sessions::Identity(None)
    } else {
        let Some(value) = bearer else {
            return sessions::unauthorized().into_response();
        };
        match sessions::identify(&state, value).await {
            Ok(identity) => identity,
            Err(error) => return error.into_response(),
        }
    };
    req.extensions_mut().insert(identity);
    let mut response = next.run(req).await;
    response
        .headers_mut()
        .insert(header::CACHE_CONTROL, "no-store".parse().unwrap());
    response
}
fn local_request_host(req: &Request) -> bool {
    let header_host = req
        .headers()
        .get(header::HOST)
        .and_then(|v| v.to_str().ok());
    let uri_host = req.uri().authority().map(|v| v.as_str());
    if header_host.is_none() && uri_host.is_none() {
        return false;
    }
    [header_host, uri_host].into_iter().flatten().all(|host| {
        host.parse::<axum::http::uri::Authority>()
            .is_ok_and(|authority| {
                matches!(authority.host(), "localhost" | "127.0.0.1" | "[::1]")
                    && !authority.as_str().contains('@')
            })
    })
}
async fn health(State(state): State<AppState>) -> impl IntoResponse {
    let healthy = if let Some(client) = &state.convex {
        client
            .query::<bool>("maintenance:health", serde_json::json!({}))
            .await
            .unwrap_or(false)
    } else {
        false
    };
    (
        if healthy {
            StatusCode::OK
        } else {
            StatusCode::SERVICE_UNAVAILABLE
        },
        Json(serde_json::json!({
            "status":if healthy {"ok"} else {"unavailable"},"database":"convex","storage":state.storage_name,"version":env!("CARGO_PKG_VERSION"),
            "capabilities":{"generation":false,"export":false,"essentia":state.analysis.is_some()},"development":state.development,"sessionRequired":state.token_hash.is_some() || !state.development
        })),
    )
}


#[utoipa::path(get, path="/api/v1/projects", responses((status=200, body=Vec<Project>)))]
async fn list_projects(
    State(state): State<AppState>,
    axum::Extension(identity): axum::Extension<sessions::Identity>,
) -> ApiResult<Json<Vec<Project>>> {
    let client = state
        .convex
        .as_ref()
        .ok_or(crate::convex::Error::Configuration)?;
    Ok(Json(
        client
            .list_projects(&sessions::convex_auth(&state, identity))
            .await?,
    ))
}
#[utoipa::path(post, path="/api/v1/projects", request_body=CreateProject, responses((status=201, body=Project)))]
async fn create_project(
    State(state): State<AppState>,
    axum::Extension(identity): axum::Extension<sessions::Identity>,
    Json(input): Json<CreateProject>,
) -> ApiResult<impl IntoResponse> {
    let p = Project::new(input.name)?;
    let client = state
        .convex
        .as_ref()
        .ok_or(crate::convex::Error::Configuration)?;
    client
        .commit_project(&sessions::convex_auth(&state, identity), &p, None, &[])
        .await?;
    Ok((StatusCode::CREATED, Json(p)))
}
#[utoipa::path(get, path="/api/v1/projects/{id}", params(("id"=Uuid, Path)), responses((status=200, body=Project)))]
async fn get_project(
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    axum::Extension(identity): axum::Extension<sessions::Identity>,
) -> ApiResult<Json<Project>> {
    let client = state
        .convex
        .as_ref()
        .ok_or(crate::convex::Error::Configuration)?;
    Ok(Json(
        client
            .read_project(&sessions::convex_auth(&state, identity), id)
            .await?,
    ))
}

#[utoipa::path(post, path="/api/v1/projects/{id}/actions", params(("id"=Uuid, Path)), request_body=ProjectAction, responses((status=200, body=Project),(status=409, description="Stale revision"),(status=422, description="Invalid action")))]
async fn project_action(
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    axum::Extension(identity): axum::Extension<sessions::Identity>,
    Json(input): Json<ProjectAction>,
) -> ApiResult<Json<Project>> {
    let client = state
        .convex
        .as_ref()
        .ok_or(crate::convex::Error::Configuration)?;
    let auth = sessions::convex_auth(&state, identity);
    let p = client.read_project(&auth, id).await?;
    let ids = action_asset_ids(&input.action);
    let mut assets = std::collections::HashMap::new();
    for asset_id in &ids {
        assets.insert(*asset_id, client.read_asset(&auth, id, *asset_id).await?);
    }
    validate_action_assets(&p, &input.action, &assets)?;
    let next = p.apply(input.expected_revision, input.action)?;
    client
        .commit_project(&auth, &next, Some(input.expected_revision), &ids)
        .await?;
    Ok(Json(next))
}

fn action_asset_ids(action: &Action) -> Vec<Uuid> {
    match action {
        Action::SetLyrics {
            lyrics: Some(lyrics),
        } => lyrics.aligned_asset_id.into_iter().collect(),
        Action::SetMaster { asset_id, .. } => vec![*asset_id],
        Action::AddReference { reference } => vec![reference.asset_id],
        Action::SetBreaks { breaks } => breaks.iter().filter_map(|b| b.asset_id).collect(),
        Action::SetShots { shots } | Action::CreateRevision { shots, .. } => {
            shots.iter().filter_map(|s| s.candidate_asset_id).collect()
        }
        _ => vec![],
    }
}

fn validate_action_assets(
    p: &Project,
    action: &Action,
    assets: &std::collections::HashMap<Uuid, Asset>,
) -> ApiResult<()> {
    // Trusted metadata and ownership checks are adapter responsibilities, before pure domain rules.
    match action {
        Action::SetLyrics {
            lyrics: Some(lyrics),
        } => {
            if let Some(asset_id) = lyrics.aligned_asset_id {
                let a = assets.get(&asset_id).ok_or_else(missing)?;
                if !a.media_type.starts_with("audio/") || a.duration_ms != Some(p.duration_ms()) {
                    return Err(invalid(
                        "Aligned lyric audio must share the master's measured duration.",
                    ));
                }
            }
        }
        Action::SetMaster {
            asset_id,
            duration_ms,
        } => {
            let a = assets.get(asset_id).ok_or_else(missing)?;
            if !a.media_type.starts_with("audio/") || a.duration_ms != Some(*duration_ms) {
                return Err(invalid(
                    "Choose an uploaded audio asset with its measured duration.",
                ));
            }
        }
        Action::AddReference { reference } => {
            let a = assets.get(&reference.asset_id).ok_or_else(missing)?;
            if !a.media_type.starts_with("image/") {
                return Err(invalid("References must be uploaded images."));
            }
        }
        Action::SetBreaks { breaks } => {
            for b in breaks {
                if let Some(asset_id) = b.asset_id {
                    let a = assets.get(&asset_id).ok_or_else(missing)?;
                    if !a.media_type.starts_with("audio/") {
                        return Err(invalid("Audio breaks require audio assets."));
                    }
                }
            }
        }
        Action::SetShots { shots } | Action::CreateRevision { shots, .. } => {
            for shot in shots {
                if let Some(asset_id) = shot.candidate_asset_id {
                    let a = assets.get(&asset_id).ok_or_else(missing)?;
                    if !a.media_type.starts_with("video/")
                        || a.duration_ms
                            .is_none_or(|d| d < shot.end_ms.saturating_sub(shot.start_ms))
                    {
                        return Err(invalid(
                            "Shot needs a video asset long enough for its range.",
                        ));
                    }
                }
            }
        }
        _ => {}
    }
    Ok(())
}

#[derive(Deserialize)]
struct EventCursor {
    #[serde(default)]
    after: i64,
}
async fn project_events(
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Query(query): Query<EventCursor>,
    axum::Extension(identity): axum::Extension<sessions::Identity>,
) -> ApiResult<impl IntoResponse> {
    let client = state.convex.clone().ok_or(convex::Error::Configuration)?;
    client
        .read_project(&sessions::convex_auth(&state, identity), id)
        .await?;
    let stream = async_stream::stream! {
        let mut after = query.after;
        loop {
            if !sessions::valid(&state, identity).await.unwrap_or(false) {
                yield Ok::<Event, Infallible>(Event::default().event("session-ended").data("Sign in to resume saved events."));
                break;
            }
                match client.project_events(&sessions::convex_auth(&state, identity), id, after).await {
                    Ok(rows) => for row in rows {
                        yield Ok(Event::default().event("project").id(row.revision.to_string()).data(row.document));
                        after = row.revision as i64;
                    },
                    Err(convex::Error::Unauthorized) => { yield Ok(Event::default().event("session-ended").data("Sign in to resume saved events.")); break; },
                    Err(_) => { yield Ok(Event::default().event("storage-error").data("Reconnect to resume saved events.")); break; }
                }
                tokio::time::sleep(Duration::from_secs(1)).await;

        }
    };
    Ok(Sse::new(stream).keep_alive(KeepAlive::default()))
}

#[utoipa::path(get, path="/api/v1/projects/{id}/assets", params(("id"=Uuid, Path)), responses((status=200, body=Vec<Asset>)))]
async fn list_assets(
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    axum::Extension(identity): axum::Extension<sessions::Identity>,
) -> ApiResult<Json<Vec<Asset>>> {
    let client = state
        .convex
        .as_ref()
        .ok_or(crate::convex::Error::Configuration)?;
    Ok(Json(
        client
            .list_assets(&sessions::convex_auth(&state, identity), id)
            .await?,
    ))
}
async fn upload_asset(
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    axum::Extension(identity): axum::Extension<sessions::Identity>,
    mut multipart: Multipart,
) -> ApiResult<impl IntoResponse> {
    let client = state.convex.as_ref().ok_or(convex::Error::Configuration)?;
    client
        .read_project(&sessions::convex_auth(&state, identity), id)
        .await?;
    let field = multipart
        .next_field()
        .await
        .map_err(|_| invalid("Invalid upload."))?
        .ok_or_else(|| invalid("Select a media file."))?;
    if field.name() != Some("file") {
        return Err(invalid("Upload field must be named file."));
    }
    let name = field
        .file_name()
        .unwrap_or("media")
        .replace(['/', '\\', '\0'], "_");
    if name.len() > 255 {
        return Err(invalid("Filename is too long."));
    }
    let data = field.bytes().await.map_err(|_| {
        invalid("File exceeds the 128 MiB intake limit or the upload was interrupted.")
    })?;
    let detected = infer::get(&data).ok_or_else(|| invalid("Unrecognized media format."))?;
    let media_type = detected.mime_type().to_owned();
    if !matches!(
        media_type.as_str(),
        "image/png"
            | "image/jpeg"
            | "image/webp"
            | "audio/wav"
            | "audio/x-wav"
            | "audio/mpeg"
            | "audio/flac"
            | "audio/x-flac"
            | "audio/ogg"
            | "video/mp4"
            | "video/webm"
            | "video/quicktime"
    ) {
        return Err(invalid(
            "Use PNG, JPEG, WebP, WAV, MP3, FLAC, OGG, MP4, WebM or MOV.",
        ));
    }
    let duration_ms = probe_duration(&data, &media_type).await?;
    if !sessions::valid(&state, identity).await? {
        return Err(sessions::unauthorized());
    }
    let asset_id = Uuid::new_v4();
    let sha256 = format!("{:x}", Sha256::digest(&data));
    let asset = Asset {
        id: asset_id,
        project_id: id,
        name,
        media_type,
        sha256,
        size_bytes: data.len() as u64,
        duration_ms,
        url: format!("/api/v1/projects/{id}/assets/{asset_id}"),
        created_at: Utc::now(),
    };
    let key = ObjectPath::from(format!("projects/{id}/originals/{asset_id}"));
    client
        .begin_upload(
            &sessions::convex_auth(&state, identity),
            &asset,
            key.as_ref(),
        )
        .await?;
    state.objects.put(&key, data.into()).await.map_err(|_| {
        ApiError(
            StatusCode::SERVICE_UNAVAILABLE,
            "Upload outcome uncertain; recovery will verify it.".into(),
        )
    })?;
    convex_uploads::verify(&state, &asset, key.as_ref())
        .await
        .map_err(|_| {
            ApiError(
                StatusCode::SERVICE_UNAVAILABLE,
                "Upload verification pending; recovery will check it.".into(),
            )
        })?;
    client
        .complete_upload(
            &asset,
            key.as_ref(),
            state.analysis.as_ref().map(|s| s.origin.as_str()),
        )
        .await?;
    Ok((StatusCode::CREATED, Json(asset)))
}

/// Reconcile complete media left behind by an interrupted request or process.
/// Missing/uncertain objects retain their intent; never delete a key while a
/// timed-out remote PUT might still complete. Promotion is idempotent after verification.
pub async fn reconcile_uploads(state: &AppState) -> anyhow::Result<usize> {
    let client = state
        .convex
        .as_ref()
        .ok_or(crate::convex::Error::Configuration)?;
    convex_uploads::reconcile(state, client).await
}
async fn probe_duration(data: &Bytes, media_type: &str) -> ApiResult<Option<u64>> {
    if media_type.starts_with("image/") {
        return Ok(None);
    }
    let temp = tempfile::NamedTempFile::new()
        .map_err(|_| invalid("Unable to prepare media inspection."))?;
    tokio::fs::write(temp.path(), data)
        .await
        .map_err(|_| invalid("Unable to inspect this file."))?;
    let mut cmd = tokio::process::Command::new("ffprobe");
    cmd.kill_on_drop(true)
        .args([
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
        ])
        .arg(temp.path());
    let output = tokio::time::timeout(Duration::from_secs(30), cmd.output())
        .await
        .map_err(|_| invalid("Media inspection timed out."))?
        .map_err(|_| {
            ApiError(
                StatusCode::SERVICE_UNAVAILABLE,
                "FFprobe is required for media intake.".into(),
            )
        })?;
    if !output.status.success() {
        return Err(invalid("Media cannot be decoded."));
    }
    let metadata: serde_json::Value =
        serde_json::from_slice(&output.stdout).map_err(|_| invalid("Invalid media metadata."))?;
    let duration = metadata["format"]["duration"]
        .as_str()
        .and_then(|s| s.parse::<f64>().ok())
        .filter(|d| d.is_finite() && *d > 0.0 && *d <= 3600.0)
        .ok_or_else(|| invalid("Media must have a measurable duration up to one hour."))?;
    Ok(Some((duration * 1000.0).round() as u64))
}
async fn get_asset(
    State(state): State<AppState>,
    Path((id, asset_id)): Path<(Uuid, Uuid)>,
    axum::Extension(identity): axum::Extension<sessions::Identity>,
) -> ApiResult<Response> {
    let client = state.convex.as_ref().ok_or(convex::Error::Configuration)?;
    let row = client
        .asset_record(&sessions::convex_auth(&state, identity), id, asset_id)
        .await?;
    let (asset, key) = (row.asset()?, row.object_key);
    let key = ObjectPath::from(key);
    let object = state.objects.get(&key).await.map_err(|_| {
        ApiError(
            StatusCode::SERVICE_UNAVAILABLE,
            "Media is temporarily unavailable.".into(),
        )
    })?;
    let mut response = Response::new(Body::from_stream(object.into_stream()));
    response.headers_mut().insert(
        header::CONTENT_TYPE,
        asset
            .media_type
            .parse()
            .map_err(|_| invalid("Invalid stored media type."))?,
    );
    response
        .headers_mut()
        .insert(header::X_CONTENT_TYPE_OPTIONS, "nosniff".parse().unwrap());
    response
        .headers_mut()
        .insert(header::CACHE_CONTROL, "private, no-store".parse().unwrap());
    Ok(response)
}

#[derive(OpenApi)]
#[openapi(
    paths(
        list_projects,
        create_project,
        get_project,
        project_action,
        list_assets,
        analysis_jobs::get,
        analysis_jobs::start,
        transcription::get,
        transcription::start,
        transcription::recover,
        sessions::create,
        sessions::current,
        sessions::revoke,
        sessions::revoke_all
    ),
    components(schemas(Project, Action, ProjectAction, CreateProject, Asset))
)]
pub struct ApiDoc;
