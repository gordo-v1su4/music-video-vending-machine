//! One explicitly requested Deepgram pass per audio asset. No automatic paid retries.
use crate::{ApiError, ApiResult, AppState, Asset, invalid, sessions};
use axum::{
    Json,
    extract::{Path, State},
    http::StatusCode,
};
use chrono::{DateTime, Utc};
use reqwest::{
    Client,
    header::{AUTHORIZATION, HeaderMap, HeaderValue},
};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::{sync::Arc, time::Duration};
use utoipa::ToSchema;
use uuid::Uuid;

pub struct Service {
    client: Client,
    endpoint: String,
}
impl Service {
    pub fn from_env() -> anyhow::Result<Option<Arc<Self>>> {
        let key = std::env::var("DEEPGRAM_API_KEY").or_else(|_| std::env::var("DEEPGRAM_TOKEN"));
        let Ok(key) = key else { return Ok(None) };
        Ok(Some(Arc::new(Self::new("https://api.deepgram.com", &key)?)))
    }
    pub fn new(origin: &str, key: &str) -> anyhow::Result<Self> {
        let url = reqwest::Url::parse(origin)?;
        anyhow::ensure!(
            origin == "https://api.deepgram.com"
                || (url.scheme() == "http"
                    && url.host_str() == Some("127.0.0.1")
                    && url.path() == "/"),
            "Invalid transcription origin"
        );
        anyhow::ensure!(!key.trim().is_empty(), "Empty Deepgram credential");
        let mut headers = HeaderMap::new();
        let mut value = HeaderValue::from_str(&format!("Token {key}"))
            .map_err(|_| anyhow::anyhow!("Invalid Deepgram credential"))?;
        value.set_sensitive(true);
        headers.insert(AUTHORIZATION, value);
        Ok(Self {
            client: Client::builder()
                .default_headers(headers)
                .no_proxy()
                .redirect(reqwest::redirect::Policy::none())
                .connect_timeout(Duration::from_secs(10))
                .timeout(Duration::from_secs(300))
                .build()?,
            endpoint: format!("{}/v1/listen", origin.trim_end_matches('/')),
        })
    }
}

#[derive(Clone, Debug, Serialize, Deserialize, ToSchema)]
#[serde(rename_all = "camelCase")]
pub struct LyricChunk {
    pub start_ms: u64,
    pub end_ms: u64,
    pub text: String,
    pub confidence: Option<f64>,
}
#[derive(Clone, Debug, Serialize, Deserialize, ToSchema)]
#[serde(rename_all = "camelCase")]
pub struct Transcript {
    pub model: String,
    pub duration_ms: u64,
    pub transcript: String,
    pub word_count: usize,
    pub chunks: Vec<LyricChunk>,
    #[serde(default)]
    pub words: Vec<LyricChunk>,
    pub summary: String,
    pub topics: Vec<String>,
    pub intents: Vec<String>,
    pub sentiment: Option<String>,
    pub warnings: Vec<String>,
}
#[derive(Clone, Debug, Serialize, Deserialize, ToSchema)]
#[serde(rename_all = "camelCase")]
pub struct TranscriptionJob {
    pub id: Uuid,
    pub profile: String,
    pub asset_id: Uuid,
    pub sha256: String,
    pub status: String,
    pub message: Option<String>,
    pub result: Option<Transcript>,
    pub updated_at: DateTime<Utc>,
}

#[derive(Deserialize, ToSchema)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct RecoverTranscription {
    pub job_id: Uuid,
    pub expected_updated_at: DateTime<Utc>,
    pub source_sha256: String,
    pub provider_response: Option<Value>,
    #[serde(default)]
    pub confirmed_source: bool,
    /// Operator opt-in: import `provider_response` into a job that already completed (its gaps are filled; saved
    /// words and the original provider receipts are kept). Off by default, so a finished transcript is never
    /// changed by accident.
    #[serde(default)]
    pub replace_completed: bool,
}

#[utoipa::path(post, operation_id="recover_transcription",path="/api/v1/projects/{id}/assets/{asset_id}/transcription/recovery",params(("id"=Uuid,Path),("asset_id"=Uuid,Path)),request_body=RecoverTranscription,responses((status=200,body=Option<TranscriptionJob>)))]
pub(crate) async fn recover(
    State(state): State<AppState>,
    Path((id, asset_id)): Path<(Uuid, Uuid)>,
    axum::Extension(identity): axum::Extension<sessions::Identity>,
    Json(request): Json<RecoverTranscription>,
) -> ApiResult<Json<Option<TranscriptionJob>>> {
    let client = state
        .convex
        .as_ref()
        .ok_or(crate::convex::Error::Configuration)?;
    Ok(Json(
        crate::convex_transcription::recover(
            &state,
            client,
            &sessions::convex_auth(&state, identity),
            id,
            asset_id,
            &request,
        )
        .await?,
    ))
}

pub(crate) fn recover_saved(
    asset: &Asset,
    request: &RecoverTranscription,
    mut receipt: Value,
) -> ApiResult<(Transcript, Value)> {
    let duration = asset.duration_ms.unwrap_or(0);
    let mut selected = recover_passes(&receipt, duration);
    // Older jobs retained a single provider response rather than a pass envelope.
    if selected.is_none() && normalize(&receipt, duration).is_ok() {
        selected = Some(receipt.clone());
    }
    if let (Some(previous), Some(tail), Some(offset)) = (
        selected.as_ref(),
        receipt.get("tail"),
        receipt.get("tailOffsetSeconds").and_then(Value::as_f64),
    ) && offset.is_finite()
        && offset >= 0.
        && offset * 1000. < duration as f64
        && normalize(tail, duration - (offset * 1000.).round() as u64).is_ok()
    {
        selected = Some(merge_tail(previous, tail, offset));
    }
    if let Some(response) = request.provider_response.clone() {
        if !request.confirmed_source {
            return Err(invalid(
                "Confirm that the provider response belongs to this exact source audio.",
            ));
        }
        normalize(&response,duration).map_err(|_|invalid("The provider response has invalid timing or does not match this recording's duration."))?;
        selected = Some(match selected {
            Some(previous) => merge_gaps(&previous, &response),
            None => response.clone(),
        });
        receipt["operatorResponse"] = response;
    }
    let selected = selected.ok_or_else(||invalid("No usable saved response. Obtain the completed response from the provider and import it here. No paid request was repeated."))?;
    let mut result = normalize(&selected, duration)
        .map_err(|_| invalid("Saved responses could not be reconciled safely."))?;
    result.model = "recovered provider responses".into();
    result.sentiment = None;
    result.warnings.push("Recovered without another provider call. Coverage may be incomplete; review the timed words. Original provider receipts are retained.".into());
    receipt["recovery"] = serde_json::json!({"at":Utc::now(),"sourceSha256":asset.sha256,"selected":selected,"paidReplay":false});
    Ok((result, receipt))
}

fn labels(value: &Value, kind: &str, label: &str) -> Vec<String> {
    let mut out = Vec::new();
    if let Some(segments) = value["results"][kind]["segments"].as_array() {
        for segment in segments {
            if let Some(items) = segment[kind].as_array() {
                for item in items {
                    if let Some(s) = item[label].as_str()
                        && !out.iter().any(|v| v == s)
                    {
                        out.push(s.to_string());
                    }
                }
            }
        }
    }
    out
}

pub fn normalize(value: &Value, expected_ms: u64) -> anyhow::Result<Transcript> {
    let duration = value["metadata"]["duration"]
        .as_f64()
        .ok_or_else(|| anyhow::anyhow!("Missing duration"))?;
    anyhow::ensure!(
        duration.is_finite()
            && duration > 0.
            && (duration * 1000. - expected_ms as f64).abs() <= 500.,
        "Transcript duration does not match source"
    );
    let alt = &value["results"]["channels"][0]["alternatives"][0];
    let words = alt["words"]
        .as_array()
        .ok_or_else(|| anyhow::anyhow!("Missing words"))?;
    let mut chunks: Vec<LyricChunk> = Vec::new();
    let mut timed_words = Vec::new();
    let mut last_start = 0.;
    for word in words {
        let start = word["start"]
            .as_f64()
            .ok_or_else(|| anyhow::anyhow!("Missing word timing"))?;
        let end = word["end"]
            .as_f64()
            .ok_or_else(|| anyhow::anyhow!("Missing word timing"))?;
        anyhow::ensure!(
            start.is_finite()
                && end.is_finite()
                && start >= last_start
                && end > start
                && end <= duration + 0.1,
            "Invalid word timing"
        );
        let text = word["punctuated_word"]
            .as_str()
            .or(word["word"].as_str())
            .unwrap_or("")
            .trim();
        last_start = start;
        if text.is_empty() {
            continue;
        }
        let start_ms = (start * 1000.).round() as u64;
        let end_ms = ((end * 1000.).round() as u64).min(expected_ms);
        let confidence = word["confidence"]
            .as_f64()
            .filter(|v| (0.0..=1.0).contains(v));
        timed_words.push(LyricChunk {
            start_ms,
            end_ms,
            text: text.into(),
            confidence,
        });
        if let Some(previous) = chunks.last_mut().filter(|c| {
            end_ms.saturating_sub(c.start_ms) <= 8000 && start_ms.saturating_sub(c.end_ms) <= 800
        }) {
            previous.text.push(' ');
            previous.text.push_str(text);
            previous.end_ms = end_ms;
            previous.confidence = match (previous.confidence, confidence) {
                (Some(a), Some(b)) => Some(a.min(b)),
                _ => None,
            };
        } else {
            chunks.push(LyricChunk {
                start_ms,
                end_ms,
                text: text.into(),
                confidence,
            });
        }
    }
    let mut warnings = vec!["Machine-transcribed lyrics and emotional labels are suggestions. Review them against the recording before story approval.".into()];
    if let Some(alternatives) = value["_mvmMergeAmbiguities"].as_array() {
        for alternative in alternatives {
            if let (Some((start, end)), Some((left, right))) = (
                word_interval(&alternative["alternative"]),
                word_interval(&alternative["preferred"]),
            ) {
                warnings.push(format!(
                    "Unresolved lyric alternative: {:?} at {:.3}–{:.3}s may repeat or duplicate {:?} at {:.3}–{:.3}s. The alternative is retained but not inserted into the draft. Listen to this range and correct the lyric wording before approval.",
                    alternative["alternative"]["punctuated_word"].as_str().or(alternative["alternative"]["word"].as_str()).unwrap_or(""), start, end,
                    alternative["preferred"]["punctuated_word"].as_str().or(alternative["preferred"]["word"].as_str()).unwrap_or(""), left, right,
                ));
            }
        }
    }
    if words.len() < 20 {
        warnings.push(
            "Very few words were detected. An isolated vocal stem may improve coverage.".into(),
        );
    }
    if value["metadata"]["warnings"]
        .as_array()
        .is_some_and(|v| !v.is_empty())
        || value["warnings"].as_array().is_some_and(|v| !v.is_empty())
    {
        warnings.push("Deepgram returned feature warnings. Some metadata may be unavailable; the original response is retained.".into());
    }
    Ok(Transcript {
        model: "nova-3".into(),
        duration_ms: expected_ms,
        transcript: alt["transcript"].as_str().unwrap_or("").into(),
        word_count: words.len(),
        chunks,
        words: timed_words,
        summary: value["results"]["summary"]["short"]
            .as_str()
            .unwrap_or("")
            .into(),
        topics: labels(value, "topics", "topic"),
        intents: labels(value, "intents", "intent"),
        sentiment: value["results"]["sentiments"]["average"]["sentiment"]
            .as_str()
            .map(str::to_string),
        warnings,
    })
}

#[utoipa::path(get, operation_id="get_transcription",path="/api/v1/projects/{id}/assets/{asset_id}/transcription",params(("id"=Uuid,Path),("asset_id"=Uuid,Path)),responses((status=200,body=Option<TranscriptionJob>)))]
pub(crate) async fn get(
    State(state): State<AppState>,
    Path((id, asset_id)): Path<(Uuid, Uuid)>,
    axum::Extension(identity): axum::Extension<sessions::Identity>,
) -> ApiResult<Json<Option<TranscriptionJob>>> {
    let client = state
        .convex
        .as_ref()
        .ok_or(crate::convex::Error::Configuration)?;
    Ok(Json(
        crate::convex_transcription::load(
            &state,
            client,
            &sessions::convex_auth(&state, identity),
            id,
            asset_id,
        )
        .await?,
    ))
}
#[utoipa::path(post, operation_id="start_transcription",path="/api/v1/projects/{id}/assets/{asset_id}/transcription",params(("id"=Uuid,Path),("asset_id"=Uuid,Path)),responses((status=200,body=Option<TranscriptionJob>)))]
pub(crate) async fn start(
    State(state): State<AppState>,
    Path((id, asset_id)): Path<(Uuid, Uuid)>,
    axum::Extension(identity): axum::Extension<sessions::Identity>,
) -> ApiResult<Json<Option<TranscriptionJob>>> {
    let client = state
        .convex
        .as_ref()
        .ok_or(crate::convex::Error::Configuration)?;
    if state.transcription.is_none() {
        return Err(ApiError(
            StatusCode::SERVICE_UNAVAILABLE,
            "Transcription is not configured on this studio server.".into(),
        ));
    }
    let auth = sessions::convex_auth(&state, identity);
    client.mutation::<()>("transcription:enqueue",serde_json::json!({"auth":auth,"projectId":id,"assetId":asset_id,"jobId":Uuid::new_v4()})).await?;
    Ok(Json(
        crate::convex_transcription::load(&state, client, &auth, id, asset_id).await?,
    ))
}

pub async fn tick(state: &AppState) -> anyhow::Result<()> {
    let Some(service) = &state.transcription else {
        return Ok(());
    };
    let client = state
        .convex
        .as_ref()
        .ok_or(crate::convex::Error::Configuration)?;
    crate::convex_transcription::tick(state, client, service).await
}

fn coverage(value: &Value) -> (usize, f64) {
    let Some(words) = value["results"]["channels"][0]["alternatives"][0]["words"].as_array() else {
        return (0, 0.);
    };
    (
        words.len(),
        words
            .iter()
            .filter_map(|w| w["end"].as_f64())
            .filter(|v| v.is_finite())
            .fold(0., f64::max),
    )
}
fn richer(primary: &Value, fallback: &Value) -> bool {
    let (count, end) = coverage(primary);
    let (next_count, next_end) = coverage(fallback);
    next_count > 0
        && (count == 0 || next_end > end * 1.15 || next_count as f64 > count as f64 * 1.3)
}
// Recovery and the live pipeline must make the same wording decision.
fn merge_passes(primary: &Value, fallback: &Value) -> Value {
    if richer(primary, fallback) {
        merge_gaps(fallback, primary)
    } else {
        merge_gaps(primary, fallback)
    }
}
fn recover_passes(receipt: &Value, duration: u64) -> Option<Value> {
    let valid = |name| {
        receipt
            .get(name)
            .filter(|pass| normalize(pass, duration).is_ok())
    };
    let combined = match (valid("primary"), valid("fallback")) {
        (Some(primary), Some(fallback)) => Some(merge_passes(primary, fallback)),
        (Some(pass), None) | (None, Some(pass)) => Some(pass.clone()),
        (None, None) => None,
    };
    match (valid("selected"), combined) {
        (Some(selected), Some(combined)) => Some(merge_gaps(selected, &combined)),
        (Some(selected), None) => Some(selected.clone()),
        (None, combined) => combined,
    }
}
// Retain complementary words in uncovered time ranges. The preferred pass owns
// overlapping timing; combining alternative spellings there would duplicate lyrics.
fn word_interval(word: &Value) -> Option<(f64, f64)> {
    let (start, end) = (word["start"].as_f64()?, word["end"].as_f64()?);
    (start.is_finite() && end.is_finite() && start >= 0. && end >= start).then_some((start, end))
}
fn overlaps((start, end): (f64, f64), (left, right): (f64, f64)) -> bool {
    (start < right && end > left) || (start == left && end == right)
}
fn word_identity(word: &Value) -> String {
    word["word"]
        .as_str()
        .or(word["punctuated_word"].as_str())
        .unwrap_or("")
        .trim_matches(|c: char| !c.is_alphanumeric())
        .to_lowercase()
}
fn merge_gaps(primary: &Value, secondary: &Value) -> Value {
    let mut merged = primary.clone();
    let mut ambiguities = Vec::new();
    for pass in [primary, secondary] {
        for alternative in pass["_mvmMergeAmbiguities"]
            .as_array()
            .into_iter()
            .flatten()
        {
            if !ambiguities.contains(alternative) {
                ambiguities.push(alternative.clone());
            }
        }
    }
    let path = "/results/channels/0/alternatives/0/words";
    let Some(extra) = secondary.pointer(path).and_then(Value::as_array) else {
        return merged;
    };
    let Some(words) = merged.pointer_mut(path).and_then(Value::as_array_mut) else {
        return merged;
    };
    // A matching overlap supplies evidence of an occurrence in both passes.
    // Different overlapping wording cannot establish that correspondence.
    let preferred: Vec<_> = words
        .iter()
        .filter_map(|word| {
            let interval = word_interval(word)?;
            let matched = extra.iter().any(|other| {
                word_identity(other) == word_identity(word)
                    && word_interval(other).is_some_and(|other| overlaps(interval, other))
            });
            Some((interval, word_identity(word), matched, word.clone()))
        })
        .collect();
    for word in extra {
        let Some((start, end)) = word_interval(word) else {
            continue;
        };
        if words
            .iter()
            .filter_map(word_interval)
            .any(|other| overlaps((start, end), other))
        {
            continue;
        }
        let identity = word_identity(word);
        if let Some((_, _, _, preferred_word)) =
            preferred.iter().find(|((left, right), text, matched, _)| {
                !*matched
                    && !identity.is_empty()
                    && *text == identity
                    && start <= *right + 0.05
                    && end >= *left - 0.05
            })
        {
            // Timing/text alone cannot distinguish drift from a real repetition.
            // Preserve the candidate as unresolved evidence, never silently decide.
            let alternative = serde_json::json!({"preferred":preferred_word,"alternative":word});
            if !ambiguities.contains(&alternative) {
                ambiguities.push(alternative);
            }
            continue;
        }
        words.push(word.clone());
    }
    words.sort_by(|a, b| {
        a["start"]
            .as_f64()
            .unwrap_or(0.)
            .total_cmp(&b["start"].as_f64().unwrap_or(0.))
    });
    let text = words
        .iter()
        .filter_map(|word| word["punctuated_word"].as_str().or(word["word"].as_str()))
        .collect::<Vec<_>>()
        .join(" ");
    merged["results"]["channels"][0]["alternatives"][0]["transcript"] = Value::String(text);
    if !ambiguities.is_empty() {
        merged["_mvmMergeAmbiguities"] = Value::Array(ambiguities);
    }
    merged
}
fn merge_tail(primary: &Value, tail: &Value, offset: f64) -> Value {
    let min_start = coverage(primary).1 + 0.25;
    let mut merged = primary.clone();
    let Some(words) = tail["results"]["channels"][0]["alternatives"][0]["words"].as_array() else {
        return merged;
    };
    let mut extra = Vec::new();
    for word in words {
        let start = word["start"].as_f64().unwrap_or(-1.) + offset;
        let end = word["end"].as_f64().unwrap_or(-1.) + offset;
        let text = word["punctuated_word"]
            .as_str()
            .or(word["word"].as_str())
            .unwrap_or("")
            .replace('♪', "")
            .trim()
            .to_string();
        if start < min_start || !text.chars().any(char::is_alphabetic) {
            continue;
        }
        let mut next = word.clone();
        next["start"] = serde_json::json!(start);
        next["end"] = serde_json::json!(end);
        next["punctuated_word"] = serde_json::json!(text);
        extra.push(next);
    }
    let alt = &mut merged["results"]["channels"][0]["alternatives"][0];
    if let Some(words) = alt["words"].as_array_mut() {
        words.extend(extra);
        let transcript = words
            .iter()
            .filter_map(|w| w["punctuated_word"].as_str().or(w["word"].as_str()))
            .collect::<Vec<_>>()
            .join(" ");
        alt["transcript"] = serde_json::json!(transcript);
    }
    merged
}
async fn call(
    service: &Service,
    bytes: bytes::Bytes,
    content_type: &str,
    model: &str,
    intelligence: bool,
) -> anyhow::Result<Value> {
    let mut query = vec![
        ("model", model),
        ("language", "en"),
        ("smart_format", "true"),
        ("punctuate", "true"),
        ("utterances", "true"),
        ("utt_split", "0.8"),
        ("sentiment", "false"),
        ("detect_entities", "false"),
    ];
    if intelligence {
        query.extend([
            ("summarize", "v2"),
            ("topics", "true"),
            ("intents", "true"),
            ("paragraphs", "true"),
        ]);
    }
    let mut response = service
        .client
        .post(&service.endpoint)
        .query(&query)
        .header("Content-Type", content_type)
        .body(bytes)
        .send()
        .await?;
    anyhow::ensure!(response.status().is_success(), "Deepgram rejected request");
    let mut bytes = Vec::new();
    while let Some(chunk) = response.chunk().await? {
        anyhow::ensure!(
            bytes.len() + chunk.len() <= 8 * 1024 * 1024,
            "Response too large"
        );
        bytes.extend_from_slice(&chunk);
    }
    Ok(serde_json::from_slice(&bytes)?)
}

async fn slice_tail(
    bytes: &bytes::Bytes,
    offset: f64,
    duration: f64,
) -> anyhow::Result<bytes::Bytes> {
    let input = tempfile::NamedTempFile::new()?;
    let output = tempfile::NamedTempFile::new()?;
    tokio::fs::write(input.path(), bytes).await?;
    let mut command = tokio::process::Command::new("ffmpeg");
    command
        .kill_on_drop(true)
        .args(["-hide_banner", "-loglevel", "error", "-y", "-i"])
        .arg(input.path())
        .args([
            "-ss",
            &offset.to_string(),
            "-t",
            &(duration - offset).to_string(),
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            "-f",
            "wav",
        ])
        .arg(output.path());
    let result = tokio::time::timeout(Duration::from_secs(45), command.output()).await??;
    anyhow::ensure!(
        result.status.success(),
        "Cannot prepare remaining vocal audio"
    );
    Ok(tokio::fs::read(output.path()).await?.into())
}
pub(crate) async fn run_pipeline(
    state: &AppState,
    service: &Service,
    asset: &Asset,
    bytes: bytes::Bytes,
    pass: &crate::convex_transcription::Pass,
) -> anyhow::Result<(Value, Transcript)> {
    // Same thresholds and pass order as project-stack-structure/src/trigger/deepgram.ts.
    let duration = asset.duration_ms.unwrap_or(0) as f64 / 1000.;
    let primary = call(service, bytes.clone(), &asset.media_type, "nova-3", true).await?;
    let mut receipt =
        serde_json::json!({"profile":"stack-structure-v1","sentiment":false,"primary":primary});
    let mut best = primary.clone();
    let mut model = "nova-3";
    pass.persist(
        state,
        &receipt,
        "Nova-3 response saved. Checking whether words cover the song.",
    )
    .await?;
    normalize(&primary, asset.duration_ms.unwrap_or(0))?;
    let (count, end) = coverage(&best);
    if duration >= 30. && (count == 0 || end < duration * 0.6) {
        pass.persist(
            state,
            &receipt,
            "Pass 2 of up to 3: Whisper fallback for sparse sung lyrics. Sentiment is disabled.",
        )
        .await?;
        let fallback = call(
            service,
            bytes.clone(),
            &asset.media_type,
            "whisper-large",
            false,
        )
        .await?;
        receipt["fallback"] = fallback.clone();
        pass.persist(
            state,
            &receipt,
            "Fallback response saved. Validating recovered timing.",
        )
        .await?;
        normalize(&fallback, asset.duration_ms.unwrap_or(0))?;
        if richer(&best, &fallback) {
            model = "whisper-large";
        }
        best = merge_passes(&best, &fallback);
        if coverage(&best).0 > coverage(&primary).0 && coverage(&best).0 > coverage(&fallback).0 {
            model = "nova-3 / whisper-large";
        }
        pass.persist(
            state,
            &receipt,
            "Fallback response saved. Checking for an uncovered ending.",
        )
        .await?;
    }
    let (_, end) = coverage(&best);
    if duration > 45. && end > 0. && end < duration * 0.85 {
        let offset = (end - 2.).max(0.);
        let tail_bytes = slice_tail(&bytes, offset, duration).await?;
        pass.persist(state,&receipt,&format!("Pass 3 of 3: transcribing the remaining audio from {offset:.1}s, including instrumental gaps.")).await?;
        let tail = call(service, tail_bytes, "audio/wav", "whisper-large", false).await?;
        receipt["tail"] = tail.clone();
        receipt["tailOffsetSeconds"] = serde_json::json!(offset);
        pass.persist(
            state,
            &receipt,
            "Remaining-audio response saved. Validating recovered timing.",
        )
        .await?;
        normalize(&tail, ((duration - offset) * 1000.).round() as u64)?;
        best = merge_tail(&best, &tail, offset);
        model = "nova-3 / whisper-large";
    }
    let mut result = normalize(&best, asset.duration_ms.unwrap_or(0))?;
    result.model = model.into();
    result.sentiment = None;
    result.warnings.push("Sentiment and entity detection are disabled, matching Project Stack Structure. Any returned summary/topics describe the transcript, not an approved story.".into());
    if coverage(&best).1 < duration * 0.85 {
        result.warnings.push("Words still stop before 85% of the recording. This may be an instrumental ending or missed vocals; review coverage.".into());
    }
    receipt["selected"] = best;
    Ok((receipt, result))
}
pub async fn run(state: AppState) {
    let mut interval = tokio::time::interval(Duration::from_secs(2));
    interval.set_missed_tick_behavior(tokio::time::MissedTickBehavior::Skip);
    loop {
        interval.tick().await;
        if tick(&state).await.is_err() {
            tracing::warn!("Transcription worker unavailable; durable request retained");
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    fn response(words: Value) -> Value {
        json!({"metadata":{"duration":158.6},"results":{"channels":[{"alternatives":[{"transcript":"fixture", "words":words}]}]}})
    }
    #[test]
    fn continuation_restores_song_time_and_filters_overlap_and_junk() {
        let primary = response(json!([{"word":"first","start":21.7,"end":82.2}]));
        let tail = response(
            json!([{"word":"overlap","start":0.1,"end":1.0},{"word":"0000","start":10.0,"end":11.0},{"word":"♪ later ♪","start":45.1,"end":46.9}]),
        );
        let merged = merge_tail(&primary, &tail, 80.2);
        let words = merged["results"]["channels"][0]["alternatives"][0]["words"]
            .as_array()
            .unwrap();
        assert_eq!(words.len(), 2);
        assert!((words[1]["start"].as_f64().unwrap() - 125.3).abs() < 0.0001);
        assert_eq!(words[1]["punctuated_word"], "later");
        assert_eq!(coverage(&merged).0, 2);
        assert!(richer(&primary, &merged));
        assert!(!richer(&primary, &response(json!([]))));
    }
    #[test]
    fn fallback_retains_mid_song_words_even_below_richer_threshold() {
        let primary = response(json!([
            {"word":"first","start":1.,"end":2.},
            {"word":"last","start":80.,"end":81.}
        ]));
        let fallback = response(json!([
            {"word":"middle","start":40.,"end":41.},
            {"word":"alternate","start":80.01,"end":81.01}
        ]));
        assert!(!richer(&primary, &fallback));
        let merged = merge_gaps(&primary, &fallback);
        assert_eq!(coverage(&merged), (3, 81.));
        let words = merged["results"]["channels"][0]["alternatives"][0]["words"]
            .as_array()
            .unwrap();
        assert_eq!(words[1]["word"], "middle");
        assert_eq!(words[2]["word"], "last");
        assert_eq!(merge_gaps(&merged, &fallback), merged);
    }
    #[test]
    fn recovery_preserves_pipeline_wording_and_saved_selection() {
        let primary = response(json!([
            {"word":"wrong","start":1.,"end":2.}
        ]));
        let fallback = response(json!([
            {"word":"right","start":1.,"end":2.},
            {"word":"later","start":3.,"end":4.}
        ]));
        let mut receipt = json!({"primary":primary,"fallback":fallback});
        let recovered = recover_passes(&receipt, 158600).unwrap();
        assert_eq!(recovered, merge_passes(&primary, &fallback));
        assert_eq!(
            recovered["results"]["channels"][0]["alternatives"][0]["words"][0]["word"],
            "right"
        );
        receipt["selected"] = primary.clone();
        let selected = recover_passes(&receipt, 158600).unwrap();
        assert_eq!(
            selected["results"]["channels"][0]["alternatives"][0]["words"][0]["word"],
            "wrong"
        );
        assert_eq!(coverage(&selected).0, 2);
    }
    #[test]
    fn gap_merge_keeps_adjacent_and_nearby_distinct_words() {
        let primary = response(json!([
            {"word":"first","start":1.,"end":2.}
        ]));
        let fallback = response(json!([
            {"word":"before","start":0.5,"end":0.98},
            {"word":"alternate","start":1.01,"end":2.01},
            {"word":"adjacent","start":2.,"end":2.2},
            {"word":"nearby","start":2.22,"end":2.4}
        ]));
        let merged = merge_gaps(&primary, &fallback);
        assert_eq!(
            merged["results"]["channels"][0]["alternatives"][0]["transcript"],
            "before first adjacent nearby"
        );
        assert_eq!(merge_gaps(&merged, &fallback), merged);
    }
    #[test]
    fn gap_merge_matches_drifted_duplicates_without_collapsing_repetitions() {
        let primary = response(json!([{"word":"Go","start":2.,"end":2.2}]));
        let drifted = response(json!([{"word":"go!","start":2.22,"end":2.4}]));
        let merged = merge_gaps(&primary, &drifted);
        assert_eq!(coverage(&merged).0, 1);
        assert_eq!(
            merged["_mvmMergeAmbiguities"][0]["alternative"],
            drifted["results"]["channels"][0]["alternatives"][0]["words"][0]
        );
        let normalized = normalize(&merged, 158600).unwrap();
        assert!(
            normalized
                .warnings
                .iter()
                .any(|w| w.contains("Unresolved lyric alternative")
                    && w.contains("2.220")
                    && w.contains("not inserted"))
        );
        assert_eq!(merge_gaps(&merged, &drifted), merged);
        let repeated = response(json!([
            {"word":"go","start":2.,"end":2.2},
            {"word":"go","start":2.22,"end":2.4}
        ]));
        let merged = merge_gaps(&primary, &repeated);
        assert_eq!(coverage(&merged).0, 2);
        assert_eq!(merge_gaps(&merged, &repeated), merged);
        assert_eq!(coverage(&merge_gaps(&repeated, &primary)).0, 2);
        let different_overlap = response(json!([
            {"word":"other","start":2.,"end":2.2},
            {"word":"go!","start":2.22,"end":2.4}
        ]));
        let merged = merge_gaps(&primary, &different_overlap);
        assert_eq!(coverage(&merged).0, 1);
        assert_eq!(merged["_mvmMergeAmbiguities"].as_array().unwrap().len(), 1);
        assert_eq!(merge_gaps(&merged, &different_overlap), merged);
    }
    #[test]
    fn timed_lyrics_preserve_gaps_and_metadata() {
        let value = json!({"metadata":{"duration":10},"results":{"channels":[{"alternatives":[{"transcript":"Hello. World!","words":[{"word":"hello","punctuated_word":"Hello.","start":1,"end":2,"confidence":0.9},{"word":"world","punctuated_word":"World!","start":6,"end":7,"confidence":0.8}]}]}],"summary":{"short":"A greeting"},"topics":{"segments":[{"topics":[{"topic":"greeting"}]}]},"sentiments":{"average":{"sentiment":"positive"}}}});
        let result = normalize(&value, 10000).unwrap();
        assert_eq!(result.chunks.len(), 2);
        assert_eq!(result.chunks[1].start_ms, 6000);
        assert_eq!(result.topics, vec!["greeting"]);
        assert_eq!(result.sentiment.as_deref(), Some("positive"));
        assert!(normalize(&value, 353000).is_err());
        let mut invalid = value;
        invalid["results"]["channels"][0]["alternatives"][0]["words"][1]["end"] = json!(12);
        assert!(normalize(&invalid, 10000).is_err());
    }
}
