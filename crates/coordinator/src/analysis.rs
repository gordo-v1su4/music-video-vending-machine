//! Validated musical evidence. These measurements never approve a story or edit.
use serde::{Deserialize, Serialize};
use utoipa::ToSchema;

#[derive(Clone, Debug, Serialize, Deserialize, ToSchema)]
#[serde(rename_all = "camelCase")]
pub struct SongAnalysis {
    pub duration_ms: u64,
    pub bpm: f64,
    /// Essentia's native confidence, not a normalized probability.
    pub native_confidence: f64,
    pub beats_ms: Vec<u64>,
    pub onsets_ms: Vec<u64>,
    pub energy: EnergyCurve,
    pub sections: Vec<MusicalSection>,
    pub method: String,
    pub warnings: Vec<String>,
}

#[derive(Clone, Debug, Serialize, Deserialize, ToSchema)]
#[serde(rename_all = "camelCase")]
pub struct EnergyCurve {
    pub values: Vec<f64>,
    pub sample_rate_hz: f64,
    pub start_ms: u64,
}

#[derive(Clone, Debug, Serialize, Deserialize, ToSchema)]
#[serde(rename_all = "camelCase")]
pub struct MusicalSection {
    pub start_ms: u64,
    pub end_ms: u64,
    pub label: String,
    pub original_label: String,
    pub energy: f64,
}

/// Parse the live studio-audio-v1 contract without inventing missing evidence.
pub fn parse_result(
    value: serde_json::Value,
    master_duration_ms: u64,
) -> Result<SongAnalysis, String> {
    let raw: ProviderAnalysis =
        serde_json::from_value(value).map_err(|_| "Analysis result has an invalid schema")?;
    if raw.schema_version != "studio-audio-v1"
        || raw.structure.source != "allin1"
        || raw.structure.provenance.status != "detected"
        || !raw.structure.provenance.method.starts_with("allin1:")
        || raw.structure.provenance.device != "cuda"
        || raw.structure.sections.is_empty()
        || raw.structure.sections.len() > 200
        || raw.beats.is_empty()
    {
        return Err("Analysis provenance is missing or unsupported".into());
    }
    let duration = master_duration_ms as f64 / 1000.0;
    if master_duration_ms == 0
        || !raw.duration.is_finite()
        || (raw.duration - duration).abs() > 0.25
        || !raw.structure.analyzed_duration_s.is_finite()
        || (raw.structure.analyzed_duration_s - duration).abs() > 0.25
    {
        return Err("Analysis does not cover the selected master duration".into());
    }
    if !raw.bpm.is_finite() || raw.bpm <= 0.0 || !raw.confidence.is_finite() || raw.confidence < 0.0
    {
        return Err("Analysis contains invalid rhythm measurements".into());
    }
    let times = |values: Vec<f64>, upper: f64| -> Result<Vec<u64>, String> {
        if values
            .iter()
            .any(|v| !v.is_finite() || *v < 0.0 || *v > upper)
            || values.windows(2).any(|v| v[0] >= v[1])
        {
            return Err("Analysis timing is outside the master or out of order".into());
        }
        Ok(values
            .into_iter()
            .map(|v| (v * 1000.0).round() as u64)
            .collect())
    };
    let beats_ms = times(raw.beats, duration)?;
    let onsets_ms = times(raw.onsets, duration)?;
    // The service preserves model edge rounding up to 250ms while decoded
    // audio remains authoritative. Apply the same tolerance to section edges.
    let _ = times(raw.structure.boundaries, duration + 0.25)?;
    let energy = raw.energy;
    if !energy.sample_rate_hz.is_finite()
        || energy.sample_rate_hz <= 0.0
        || !energy.start_time_s.is_finite()
        || energy.start_time_s < 0.0
        || energy.start_time_s > duration
        || energy.curve.is_empty()
        || energy
            .curve
            .iter()
            .any(|v| !v.is_finite() || !(0.0..=1.0).contains(v))
        || energy.start_time_s + (energy.curve.len() - 1) as f64 / energy.sample_rate_hz
            > duration + 0.25
        || energy.start_time_s + (energy.curve.len() - 1) as f64 / energy.sample_rate_hz
            < duration - 0.25
    {
        return Err("Analysis energy timebase is invalid".into());
    }
    let mut sections = Vec::new();
    let mut previous_end = 0;
    let mut warnings = vec!["Detected musical sections are suggestions. Review their boundaries; lyrics are not time-aligned.".into()];
    for part in raw.structure.sections {
        if !part.start.is_finite()
            || !part.end.is_finite()
            || !part.duration.is_finite()
            || part.start < 0.0
            || part.end <= part.start
            || part.end > duration + 0.25
            || (part.duration - (part.end - part.start)).abs() > 0.05
            || !part.energy.is_finite()
            || !(0.0..=1.0).contains(&part.energy)
            || part.label.trim().is_empty()
            || part.label.len() > 128
            || part.original_label.len() > 128
            || part.original_label.trim().is_empty()
        {
            return Err("Analysis contains an invalid musical section".into());
        }
        let start_ms = (part.start * 1000.0).round() as u64;
        let end_ms = ((part.end * 1000.0).round() as u64).min(master_duration_ms);
        if part.end > duration {
            warnings.push("The model's final section extended beyond the audio; its editable end is limited to the master duration. The original service result is retained.".into());
        }
        if start_ms < previous_end || end_ms <= start_ms {
            return Err("Analysis sections overlap or have no duration".into());
        }
        if start_ms > previous_end {
            warnings.push(format!(
                "Unclassified audio from {previous_end} to {start_ms} ms."
            ));
        }
        if end_ms - start_ms < 1000 {
            warnings.push(format!(
                "Very short detected section at {start_ms} ms needs review."
            ));
        }
        previous_end = end_ms;
        sections.push(MusicalSection {
            start_ms,
            end_ms,
            label: part.label,
            original_label: part.original_label,
            energy: part.energy,
        });
    }
    if previous_end < master_duration_ms {
        warnings.push(format!(
            "Unclassified audio from {previous_end} to {master_duration_ms} ms."
        ));
    }
    Ok(SongAnalysis {
        duration_ms: master_duration_ms,
        bpm: raw.bpm,
        native_confidence: raw.confidence,
        beats_ms,
        onsets_ms,
        energy: EnergyCurve {
            values: energy.curve,
            sample_rate_hz: energy.sample_rate_hz,
            start_ms: (energy.start_time_s * 1000.0).round() as u64,
        },
        sections,
        method: raw.structure.provenance.method,
        warnings,
    })
}

#[derive(Deserialize)]
struct ProviderAnalysis {
    schema_version: String,
    duration: f64,
    bpm: f64,
    confidence: f64,
    beats: Vec<f64>,
    onsets: Vec<f64>,
    energy: ProviderEnergy,
    structure: ProviderStructure,
}
#[derive(Deserialize)]
struct ProviderEnergy {
    curve: Vec<f64>,
    sample_rate_hz: f64,
    start_time_s: f64,
}
#[derive(Deserialize)]
struct ProviderStructure {
    sections: Vec<ProviderSection>,
    boundaries: Vec<f64>,
    source: String,
    analyzed_duration_s: f64,
    provenance: ProviderProvenance,
}
#[derive(Deserialize)]
struct ProviderSection {
    start: f64,
    end: f64,
    duration: f64,
    label: String,
    original_label: String,
    energy: f64,
}
#[derive(Deserialize)]
struct ProviderProvenance {
    status: String,
    method: String,
    device: String,
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::{Value, json};
    fn fixture() -> Value {
        json!({"schema_version":"studio-audio-v1","duration":10.0,"bpm":120.0,"confidence":3.593,"beats":[0.5,1.0],"onsets":[0.1,0.9],"energy":{"curve":[0.1,0.4],"sample_rate_hz":0.1,"start_time_s":0.0},"structure":{"source":"allin1","analyzed_duration_s":10.0,"provenance":{"status":"detected","method":"allin1:test","device":"cuda"},"boundaries":[0.0,10.0],"sections":[{"start":0.0,"end":10.0,"duration":10.0,"label":"verse","original_label":"verse","energy":0.4}]}})
    }
    #[test]
    fn preserves_native_confidence_and_song_time() {
        let result = parse_result(fixture(), 10_000).unwrap();
        assert_eq!(result.native_confidence, 3.593);
        assert_eq!(result.beats_ms, vec![500, 1000]);
        assert_eq!(result.sections[0].end_ms, 10_000);
    }
    #[test]
    fn rejects_wrong_master_truncated_results_and_out_of_order_beats() {
        assert!(parse_result(fixture(), 20_000).is_err());
        let mut value = fixture();
        value["structure"]["analyzed_duration_s"] = json!(5.0);
        assert!(parse_result(value, 10_000).is_err());
        let mut value = fixture();
        value["beats"] = json!([1.0, 0.5]);
        assert!(parse_result(value, 10_000).is_err());
    }
    #[test]
    fn keeps_gaps_and_short_sections_explicit() {
        let mut value = fixture();
        value["structure"]["sections"][0]["start"] = json!(1.0);
        value["structure"]["sections"][0]["end"] = json!(1.5);
        value["structure"]["sections"][0]["duration"] = json!(0.5);
        let result = parse_result(value, 10_000).unwrap();
        assert_eq!(result.sections.len(), 1);
        assert_eq!(result.warnings.len(), 4);
    }
    #[test]
    fn accepts_documented_model_edge_rounding_without_extending_the_master() {
        let mut value = fixture();
        value["structure"]["boundaries"][1] = json!(10.04);
        value["structure"]["sections"][0]["end"] = json!(10.04);
        value["structure"]["sections"][0]["duration"] = json!(10.04);
        let result = parse_result(value.clone(), 10_000).unwrap();
        assert_eq!(result.sections[0].end_ms, 10_000);
        assert_eq!(result.warnings.len(), 2);
        value["onsets"] = json!([10.04]);
        assert!(parse_result(value, 10_000).is_err());
    }
}
