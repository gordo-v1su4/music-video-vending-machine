//! Pure project rules. Adapters supply verified media; no model can bypass these rules.
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::HashSet;
use utoipa::ToSchema;
use uuid::Uuid;

#[derive(Debug, thiserror::Error, PartialEq)]
pub enum DomainError {
    #[error("{0}")]
    Invalid(String),
    #[error("The project changed. Reload it before saving.")]
    Conflict,
}
type Result<T> = std::result::Result<T, DomainError>;
fn require(ok: bool, message: &str) -> Result<()> {
    if ok {
        Ok(())
    } else {
        Err(DomainError::Invalid(message.into()))
    }
}

#[derive(Clone, Debug, Serialize, Deserialize, ToSchema, PartialEq)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Master {
    pub asset_id: Uuid,
    pub duration_ms: u64,
    pub approved: bool,
}
#[derive(Clone, Debug, Serialize, Deserialize, ToSchema, PartialEq)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Section {
    pub id: Uuid,
    pub name: String,
    pub start_ms: u64,
    pub end_ms: u64,
    pub intent: String,
}
#[derive(Clone, Debug, Serialize, Deserialize, ToSchema, PartialEq)]
#[serde(rename_all = "camelCase")]
pub enum ReferenceRole {
    Exact,
    Inspiration,
}
#[derive(Clone, Debug, Serialize, Deserialize, ToSchema, PartialEq)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Reference {
    pub id: Uuid,
    pub asset_id: Uuid,
    pub name: String,
    pub role: ReferenceRole,
    pub description: String,
}
#[derive(Clone, Debug, Serialize, Deserialize, ToSchema, PartialEq)]
#[serde(rename_all = "camelCase")]
pub enum BreakKind {
    Insertion,
    Cutout,
}
#[derive(Clone, Debug, Serialize, Deserialize, ToSchema, PartialEq)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct AudioBreak {
    pub id: Uuid,
    pub kind: BreakKind,
    pub song_start_ms: u64,
    pub duration_ms: u64,
    pub asset_id: Option<Uuid>,
}
#[derive(Clone, Debug, Serialize, Deserialize, ToSchema, PartialEq)]
#[serde(rename_all = "camelCase")]
pub enum ShotStatus {
    Gap,
    Candidate,
    Accepted,
}
#[derive(Clone, Debug, Serialize, Deserialize, ToSchema, PartialEq)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Shot {
    pub id: Uuid,
    pub section_id: Uuid,
    pub start_ms: u64,
    pub end_ms: u64,
    pub intent: String,
    pub pinned: bool,
    pub candidate_asset_id: Option<Uuid>,
    pub status: ShotStatus,
    pub attempts: u8,
}
#[derive(Clone, Debug, Serialize, Deserialize, ToSchema, PartialEq)]
#[serde(rename_all = "camelCase")]
pub enum RevisionStatus {
    Candidate,
    Active,
    Rejected,
    Archived,
}
#[derive(Clone, Debug, Serialize, Deserialize, ToSchema, PartialEq)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct EditRevision {
    pub id: Uuid,
    pub label: String,
    pub parent_id: Option<Uuid>,
    pub approval_fingerprint: String,
    pub status: RevisionStatus,
    pub shots: Vec<Shot>,
}
#[derive(Clone, Debug, Serialize, Deserialize, ToSchema)]
#[serde(rename_all = "camelCase")]
pub struct Approval {
    pub fingerprint: String,
    pub local_attempts_per_shot: u8,
}
#[derive(Clone, Debug, Serialize, Deserialize, ToSchema)]
#[serde(rename_all = "camelCase")]
pub struct Project {
    pub id: Uuid,
    pub name: String,
    pub revision: u64,
    pub master: Option<Master>,
    pub treatment: String,
    pub sections: Vec<Section>,
    pub references: Vec<Reference>,
    pub breaks: Vec<AudioBreak>,
    pub shots: Vec<Shot>,
    pub revisions: Vec<EditRevision>,
    pub active_revision_id: Option<Uuid>,
    pub production_approval: Option<Approval>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

#[derive(Clone, Debug, Serialize, Deserialize, ToSchema)]
#[serde(
    tag = "type",
    rename_all = "camelCase",
    rename_all_fields = "camelCase",
    deny_unknown_fields
)]
pub enum Action {
    SetTreatment {
        text: String,
    },
    SetMaster {
        #[serde(rename = "assetId")]
        asset_id: Uuid,
        #[serde(rename = "durationMs")]
        duration_ms: u64,
    },
    ApproveMaster,
    SetSections {
        sections: Vec<Section>,
    },
    AddReference {
        reference: Reference,
    },
    SetBreaks {
        breaks: Vec<AudioBreak>,
    },
    ApproveProduction {
        #[serde(rename = "localAttemptsPerShot")]
        local_attempts_per_shot: u8,
    },
    SetShots {
        shots: Vec<Shot>,
    },
    PinShot {
        #[serde(rename = "shotId")]
        shot_id: Uuid,
        pinned: bool,
    },
    CreateRevision {
        label: String,
        shots: Vec<Shot>,
    },
    KeepRevision {
        #[serde(rename = "revisionId")]
        revision_id: Uuid,
    },
    RejectRevision {
        #[serde(rename = "revisionId")]
        revision_id: Uuid,
    },
    RestoreRevision {
        #[serde(rename = "revisionId")]
        revision_id: Uuid,
    },
}

impl Project {
    pub fn new(name: String) -> Result<Self> {
        require(
            !name.trim().is_empty() && name.len() <= 160,
            "Name must contain 1–160 bytes.",
        )?;
        let now = Utc::now();
        Ok(Self {
            id: Uuid::new_v4(),
            name: name.trim().into(),
            revision: 0,
            master: None,
            treatment: String::new(),
            sections: vec![],
            references: vec![],
            breaks: vec![],
            shots: vec![],
            revisions: vec![],
            active_revision_id: None,
            production_approval: None,
            created_at: now,
            updated_at: now,
        })
    }
    pub fn duration_ms(&self) -> u64 {
        self.master.as_ref().map_or(0, |m| m.duration_ms)
    }
    pub fn approval_fingerprint(&self) -> String {
        let content = serde_json::json!({"master":self.master,"treatment":self.treatment,
            "sections":self.sections,"references":self.references,"breaks":self.breaks,"route":"local"});
        format!("{:x}", Sha256::digest(content.to_string().as_bytes()))
    }
    pub fn production_approved(&self) -> bool {
        self.production_approval
            .as_ref()
            .is_some_and(|a| a.fingerprint == self.approval_fingerprint())
    }
    /// Apply to a clone so a validation error never partially changes the caller's state.
    pub fn apply(&self, expected_revision: u64, action: Action) -> Result<Self> {
        if self.revision != expected_revision {
            return Err(DomainError::Conflict);
        }
        let mut next = self.clone();
        next.apply_inner(action)?;
        if next.approval_fingerprint() != self.approval_fingerprint() {
            next.production_approval = None;
        }
        next.revision = next
            .revision
            .checked_add(1)
            .ok_or_else(|| DomainError::Invalid("Revision overflow".into()))?;
        next.updated_at = Utc::now();
        Ok(next)
    }
    fn apply_inner(&mut self, action: Action) -> Result<()> {
        match action {
            Action::SetTreatment { text } => {
                require(text.len() <= 100_000, "Treatment is too long.")?;
                self.treatment = text;
            }
            Action::SetMaster {
                asset_id,
                duration_ms,
            } => {
                require(
                    duration_ms > 0 && duration_ms <= 3_600_000,
                    "Master must be between zero and one hour.",
                )?;
                require(
                    self.active_revision_id.is_none() && self.revisions.is_empty(),
                    "Create a new project for a different master after editing has begun.",
                )?;
                self.master = Some(Master {
                    asset_id,
                    duration_ms,
                    approved: false,
                });
                self.sections.clear();
                self.breaks.clear();
                self.shots.clear();
            }
            Action::ApproveMaster => {
                let master = self
                    .master
                    .as_mut()
                    .ok_or_else(|| DomainError::Invalid("Choose a master first.".into()))?;
                master.approved = true;
            }
            Action::SetSections { sections } => {
                require(
                    self.shots.is_empty() && self.revisions.is_empty(),
                    "Section restructuring after shot planning requires a new project in this foundation release.",
                )?;
                validate_sections(&sections, self.duration_ms())?;
                self.sections = sections;
            }
            Action::AddReference { reference } => {
                require(
                    !reference.name.trim().is_empty()
                        && reference.name.len() <= 160
                        && reference.description.len() <= 10_000,
                    "Invalid reference text.",
                )?;
                require(
                    !self.references.iter().any(|r| r.id == reference.id),
                    "Reference ID already exists.",
                )?;
                require(
                    self.references.len() < 100,
                    "At most 100 references are supported.",
                )?;
                self.references.push(reference);
            }
            Action::SetBreaks { breaks } => {
                validate_breaks(&breaks, self.duration_ms())?;
                self.breaks = breaks;
            }
            Action::ApproveProduction {
                local_attempts_per_shot,
            } => {
                require(
                    self.master.as_ref().is_some_and(|m| m.approved),
                    "Approve the master first.",
                )?;
                require(
                    !self.treatment.trim().is_empty(),
                    "Describe the story before approval.",
                )?;
                validate_sections(&self.sections, self.duration_ms())?;
                require(
                    !self.sections.is_empty()
                        && self.sections.first().unwrap().start_ms == 0
                        && self.sections.last().unwrap().end_ms == self.duration_ms(),
                    "Sections must cover the complete song.",
                )?;
                require(
                    self.sections
                        .windows(2)
                        .all(|w| w[0].end_ms == w[1].start_ms),
                    "Sections contain a gap.",
                )?;
                require(
                    local_attempts_per_shot == 3,
                    "The local allowance is one attempt plus two repairs.",
                )?;
                self.production_approval = Some(Approval {
                    fingerprint: self.approval_fingerprint(),
                    local_attempts_per_shot,
                });
            }
            Action::SetShots { shots } => {
                require(
                    self.production_approved(),
                    "Approve current production inputs first.",
                )?;
                require(
                    self.active_revision_id.is_none(),
                    "Create a candidate revision to change an active cut.",
                )?;
                self.validate_shots(&shots)?;
                self.protect_pins(&shots)?;
                self.shots = shots;
            }
            Action::PinShot { shot_id, pinned } => {
                let shot = self
                    .shots
                    .iter_mut()
                    .find(|s| s.id == shot_id)
                    .ok_or_else(|| DomainError::Invalid("Unknown shot.".into()))?;
                shot.pinned = pinned;
            }
            Action::CreateRevision { label, shots } => {
                self.add_candidate(label, shots)?;
            }
            Action::KeepRevision { revision_id } => {
                require(
                    self.production_approved(),
                    "Approve current production inputs first.",
                )?;
                let candidate = self
                    .revisions
                    .iter()
                    .find(|r| r.id == revision_id && r.status == RevisionStatus::Candidate)
                    .ok_or_else(|| DomainError::Invalid("Only a candidate can be kept.".into()))?
                    .clone();
                require(
                    candidate.approval_fingerprint == self.approval_fingerprint(),
                    "This candidate belongs to an earlier direction. Create a new candidate.",
                )?;
                self.validate_shots(&candidate.shots)?;
                self.protect_pins(&candidate.shots)?;
                for r in &mut self.revisions {
                    if r.status == RevisionStatus::Active {
                        r.status = RevisionStatus::Archived;
                    }
                    if r.id == revision_id {
                        r.status = RevisionStatus::Active;
                    }
                }
                self.shots = candidate.shots;
                self.active_revision_id = Some(revision_id);
            }
            Action::RejectRevision { revision_id } => {
                let r = self
                    .revisions
                    .iter_mut()
                    .find(|r| r.id == revision_id && r.status == RevisionStatus::Candidate)
                    .ok_or_else(|| {
                        DomainError::Invalid("Only a candidate can be rejected.".into())
                    })?;
                r.status = RevisionStatus::Rejected;
            }
            Action::RestoreRevision { revision_id } => {
                let old = self
                    .revisions
                    .iter()
                    .find(|r| r.id == revision_id)
                    .ok_or_else(|| DomainError::Invalid("Unknown revision.".into()))?
                    .clone();
                require(
                    old.approval_fingerprint == self.approval_fingerprint(),
                    "This revision belongs to an earlier direction and cannot be restored under the current approval.",
                )?;
                self.add_candidate(format!("Restore {}", old.label), old.shots)?;
            }
        }
        Ok(())
    }
    fn add_candidate(&mut self, label: String, shots: Vec<Shot>) -> Result<()> {
        require(
            self.production_approved(),
            "Approve current production inputs first.",
        )?;
        require(
            !label.trim().is_empty() && label.len() <= 200,
            "Revision label must contain 1–200 bytes.",
        )?;
        require(self.revisions.len() < 500, "Revision limit reached.")?;
        self.validate_shots(&shots)?;
        self.protect_pins(&shots)?;
        self.revisions.push(EditRevision {
            id: Uuid::new_v4(),
            label,
            parent_id: self.active_revision_id,
            approval_fingerprint: self.approval_fingerprint(),
            status: RevisionStatus::Candidate,
            shots,
        });
        Ok(())
    }
    fn protect_pins(&self, shots: &[Shot]) -> Result<()> {
        for pinned in self.shots.iter().filter(|s| s.pinned) {
            require(
                shots.iter().any(|s| s == pinned),
                "Unpin a protected shot before changing it.",
            )?;
        }
        Ok(())
    }
    fn validate_shots(&self, shots: &[Shot]) -> Result<()> {
        require(shots.len() <= 1000, "Shot limit reached.")?;
        let mut ids = HashSet::new();
        let mut previous_end = 0;
        for shot in shots {
            require(ids.insert(shot.id), "Duplicate shot ID.")?;
            let section = self
                .sections
                .iter()
                .find(|s| s.id == shot.section_id)
                .ok_or_else(|| DomainError::Invalid("Unknown shot section.".into()))?;
            require(
                shot.start_ms >= previous_end
                    && shot.start_ms >= section.start_ms
                    && shot.end_ms <= section.end_ms
                    && shot.end_ms > shot.start_ms,
                "Shot ranges must be ordered, non-overlapping and within their section.",
            )?;
            require(
                shot.intent.len() <= 10_000 && shot.attempts <= 3,
                "Invalid shot intent or attempt count.",
            )?;
            require(
                shot.status == ShotStatus::Gap || shot.candidate_asset_id.is_some(),
                "Candidate and accepted shots need a media asset.",
            )?;
            previous_end = shot.end_ms;
        }
        Ok(())
    }
    /// Coverage prerequisite only; media/QC and insertion coverage are separate export gates.
    pub fn validate_export_coverage(&self, start_ms: u64, end_ms: u64) -> Result<()> {
        require(
            self.production_approved(),
            "Production approval is stale or missing.",
        )?;
        if let Some(active_id) = self.active_revision_id {
            require(
                self.revisions.iter().any(|r| {
                    r.id == active_id && r.approval_fingerprint == self.approval_fingerprint()
                }),
                "The active cut belongs to an earlier production approval.",
            )?;
        }
        require(
            start_ms < end_ms && end_ms <= self.duration_ms(),
            "Invalid export range.",
        )?;
        let mut cursor = start_ms;
        for s in &self.shots {
            if s.end_ms <= start_ms || s.start_ms >= end_ms {
                continue;
            }
            require(
                s.start_ms <= cursor
                    && s.status == ShotStatus::Accepted
                    && s.candidate_asset_id.is_some(),
                "Export contains a coverage gap or unaccepted shot.",
            )?;
            cursor = s.end_ms.min(end_ms);
        }
        require(cursor == end_ms, "Export contains a coverage gap.")
    }
}

fn validate_sections(sections: &[Section], duration: u64) -> Result<()> {
    require(sections.len() <= 200, "Section limit reached.")?;
    let mut ids = HashSet::new();
    let mut previous_end = 0;
    for s in sections {
        require(ids.insert(s.id), "Duplicate section ID.")?;
        require(
            !s.name.trim().is_empty() && s.name.len() <= 160 && s.intent.len() <= 10_000,
            "Invalid section text.",
        )?;
        require(
            s.start_ms >= previous_end && s.end_ms > s.start_ms && s.end_ms <= duration,
            "Section ranges must be ordered, non-overlapping and within the song.",
        )?;
        previous_end = s.end_ms;
    }
    Ok(())
}
fn validate_breaks(breaks: &[AudioBreak], duration: u64) -> Result<()> {
    require(breaks.len() <= 100, "Break limit reached.")?;
    let mut ids = HashSet::new();
    let mut last_start = None;
    let mut cutout_end = 0;
    for b in breaks {
        require(ids.insert(b.id), "Duplicate break ID.")?;
        require(
            b.duration_ms > 0 && b.duration_ms <= 300_000 && b.song_start_ms <= duration,
            "Invalid audio break.",
        )?;
        require(
            last_start.is_none_or(|last| b.song_start_ms > last),
            "Breaks must be ordered with distinct start times.",
        )?;
        require(
            b.song_start_ms >= cutout_end,
            "Audio breaks cannot overlap cutouts.",
        )?;
        if b.kind == BreakKind::Cutout {
            let end = b
                .song_start_ms
                .checked_add(b.duration_ms)
                .ok_or_else(|| DomainError::Invalid("Time overflow".into()))?;
            require(end <= duration, "Cutout extends beyond the song.")?;
            cutout_end = end;
        }
        last_start = Some(b.song_start_ms);
    }
    Ok(())
}

#[derive(Debug, Clone, PartialEq)]
pub enum PlaybackPosition {
    Song { song_ms: u64, muted: bool },
    Insertion { break_id: Uuid, offset_ms: u64 },
    End,
}
pub fn video_to_song(video_ms: u64, duration_ms: u64, breaks: &[AudioBreak]) -> PlaybackPosition {
    let mut inserted = 0;
    for b in breaks.iter().filter(|b| b.kind == BreakKind::Insertion) {
        let start = b.song_start_ms + inserted;
        if video_ms < start {
            break;
        }
        if video_ms < start + b.duration_ms {
            return PlaybackPosition::Insertion {
                break_id: b.id,
                offset_ms: video_ms - start,
            };
        }
        inserted += b.duration_ms;
    }
    let song_ms = video_ms - inserted;
    if song_ms >= duration_ms {
        return PlaybackPosition::End;
    }
    PlaybackPosition::Song {
        song_ms,
        muted: breaks.iter().any(|b| {
            b.kind == BreakKind::Cutout
                && song_ms >= b.song_start_ms
                && song_ms < b.song_start_ms + b.duration_ms
        }),
    }
}
