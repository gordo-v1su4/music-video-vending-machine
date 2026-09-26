use mvm_domain::*;
use uuid::Uuid;

fn step(p: Project, action: Action) -> Project {
    p.apply(p.revision, action).unwrap()
}
fn approved() -> Project {
    let mut p = Project::new("Narrative pilot".into()).unwrap();
    p = step(
        p,
        Action::SetMaster {
            asset_id: Uuid::new_v4(),
            duration_ms: 60_000,
        },
    );
    p = step(p, Action::ApproveMaster);
    p = step(
        p,
        Action::SetTreatment {
            text: "A traveller returns to an empty station.".into(),
        },
    );
    p = step(
        p,
        Action::SetSections {
            sections: vec![Section {
                id: Uuid::new_v4(),
                name: "Arrival".into(),
                start_ms: 0,
                end_ms: 60_000,
                intent: "Establish the place".into(),
            }],
        },
    );
    step(
        p,
        Action::ApproveProduction {
            local_attempts_per_shot: 3,
        },
    )
}

#[test]
fn lyric_context_is_durable_invalidates_approval_and_loses_alignment_on_master_change() {
    let original = approved();
    let mut legacy = serde_json::to_value(&original).unwrap();
    legacy.as_object_mut().unwrap().remove("lyrics");
    let restored: Project = serde_json::from_value(legacy).unwrap();
    assert!(restored.production_approved());
    let next = step(
        restored,
        Action::SetLyrics {
            lyrics: Some(LyricsContext {
                text: "User supplied wording".into(),
                source_name: "words.txt".into(),
                aligned_asset_id: Some(Uuid::new_v4()),
            }),
        },
    );
    assert!(!next.production_approved());
    let next = step(
        next,
        Action::SetMaster {
            asset_id: Uuid::new_v4(),
            duration_ms: 60_000,
        },
    );
    assert!(next.lyrics.as_ref().unwrap().aligned_asset_id.is_none());
    assert_eq!(next.lyrics.unwrap().text, "User supplied wording");
}
fn shot(p: &Project, start: u64, end: u64) -> Shot {
    Shot {
        id: Uuid::new_v4(),
        section_id: p.sections[0].id,
        start_ms: start,
        end_ms: end,
        intent: "Arrival".into(),
        pinned: false,
        candidate_asset_id: Some(Uuid::new_v4()),
        status: ShotStatus::Accepted,
        attempts: 1,
    }
}
#[test]
fn stale_writes_do_not_mutate_project() {
    let p = approved();
    let original = serde_json::to_value(&p).unwrap();
    assert_eq!(
        p.apply(
            p.revision - 1,
            Action::SetTreatment {
                text: "Lost update".into()
            }
        )
        .unwrap_err(),
        DomainError::Conflict
    );
    assert_eq!(serde_json::to_value(&p).unwrap(), original);
}
#[test]
fn changed_reference_invalidates_bound_approval() {
    let p = approved();
    assert!(p.production_approved());
    let p = step(
        p,
        Action::AddReference {
            reference: Reference {
                id: Uuid::new_v4(),
                asset_id: Uuid::new_v4(),
                name: "New face".into(),
                role: ReferenceRole::Exact,
                description: String::new(),
            },
        },
    );
    assert!(!p.production_approved());
    assert!(
        p.apply(
            p.revision,
            Action::CreateRevision {
                label: "Unauthorized".into(),
                shots: vec![]
            }
        )
        .is_err()
    );
}
#[test]
fn keep_is_explicit_and_pins_protect_against_existing_candidates() {
    let p = approved();
    let mut a = shot(&p, 0, 60_000);
    let p = step(
        p,
        Action::CreateRevision {
            label: "First".into(),
            shots: vec![a.clone()],
        },
    );
    assert!(p.active_revision_id.is_none());
    assert!(p.shots.is_empty());
    let id = p.revisions[0].id;
    let p = step(p, Action::KeepRevision { revision_id: id });
    a.intent = "Different action".into();
    let p = step(
        p,
        Action::CreateRevision {
            label: "Second".into(),
            shots: vec![a.clone()],
        },
    );
    let candidate_id = p.revisions[1].id;
    let p = step(
        p,
        Action::PinShot {
            shot_id: a.id,
            pinned: true,
        },
    );
    assert!(
        p.apply(
            p.revision,
            Action::KeepRevision {
                revision_id: candidate_id
            }
        )
        .is_err()
    );
    assert_eq!(p.active_revision_id, Some(id));
}
#[test]
fn export_range_can_pass_while_full_song_has_gap() {
    let p = approved();
    let a = shot(&p, 0, 30_000);
    let p = step(p, Action::SetShots { shots: vec![a] });
    assert!(p.validate_export_coverage(0, 30_000).is_ok());
    assert!(p.validate_export_coverage(0, 60_000).is_err());
}
#[test]
fn candidate_asset_is_not_accepted_coverage() {
    let p = approved();
    let mut a = shot(&p, 0, 60_000);
    a.status = ShotStatus::Candidate;
    let p = step(p, Action::SetShots { shots: vec![a] });
    assert!(p.validate_export_coverage(0, 60_000).is_err());
}
#[test]
fn allowance_and_overlapping_sections_are_rejected() {
    let p = approved();
    assert!(
        p.apply(
            p.revision,
            Action::ApproveProduction {
                local_attempts_per_shot: 255
            }
        )
        .is_err()
    );
    let mut a = p.sections[0].clone();
    a.id = Uuid::new_v4();
    assert!(
        p.apply(
            p.revision,
            Action::SetSections {
                sections: vec![p.sections[0].clone(), a]
            }
        )
        .is_err()
    );
}
#[test]
fn insertion_extends_video_but_cutout_advances_song() {
    let insertion = AudioBreak {
        id: Uuid::new_v4(),
        kind: BreakKind::Insertion,
        song_start_ms: 10_000,
        duration_ms: 5_000,
        asset_id: None,
    };
    let cutout = AudioBreak {
        id: Uuid::new_v4(),
        kind: BreakKind::Cutout,
        song_start_ms: 20_000,
        duration_ms: 3_000,
        asset_id: None,
    };
    let breaks = vec![insertion.clone(), cutout];
    assert_eq!(
        video_to_song(9_999, 60_000, &breaks),
        PlaybackPosition::Song {
            song_ms: 9_999,
            muted: false
        }
    );
    assert_eq!(
        video_to_song(12_000, 60_000, &breaks),
        PlaybackPosition::Insertion {
            break_id: insertion.id,
            offset_ms: 2_000
        }
    );
    assert_eq!(
        video_to_song(15_000, 60_000, &breaks),
        PlaybackPosition::Song {
            song_ms: 10_000,
            muted: false
        }
    );
    assert_eq!(
        video_to_song(25_000, 60_000, &breaks),
        PlaybackPosition::Song {
            song_ms: 20_000,
            muted: true
        }
    );
    assert_eq!(
        video_to_song(28_000, 60_000, &breaks),
        PlaybackPosition::Song {
            song_ms: 23_000,
            muted: false
        }
    );
    assert_eq!(
        video_to_song(65_000, 60_000, &breaks),
        PlaybackPosition::End
    );
}
#[test]
fn failed_action_is_atomic() {
    let p = approved();
    let before = serde_json::to_value(&p).unwrap();
    let bad = AudioBreak {
        id: Uuid::new_v4(),
        kind: BreakKind::Cutout,
        song_start_ms: 59_000,
        duration_ms: 5_000,
        asset_id: None,
    };
    assert!(
        p.apply(p.revision, Action::SetBreaks { breaks: vec![bad] })
            .is_err()
    );
    assert_eq!(before, serde_json::to_value(&p).unwrap());
}

#[test]
fn reapproval_does_not_authorize_old_direction_candidates() {
    let p = approved();
    let a = shot(&p, 0, 60_000);
    let p = step(
        p,
        Action::CreateRevision {
            label: "Old story".into(),
            shots: vec![a],
        },
    );
    let candidate_id = p.revisions[0].id;
    let p = step(
        p,
        Action::SetTreatment {
            text: "A completely different story".into(),
        },
    );
    let p = step(
        p,
        Action::ApproveProduction {
            local_attempts_per_shot: 3,
        },
    );
    assert!(
        p.apply(
            p.revision,
            Action::KeepRevision {
                revision_id: candidate_id
            }
        )
        .is_err()
    );
    assert!(
        p.apply(
            p.revision,
            Action::RestoreRevision {
                revision_id: candidate_id
            }
        )
        .is_err()
    );
}
