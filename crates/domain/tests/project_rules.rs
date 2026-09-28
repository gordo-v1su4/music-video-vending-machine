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

fn reference(p: Project, role: ReferenceRole) -> (Project, Uuid) {
    let id = Uuid::new_v4();
    let p = step(
        p,
        Action::AddReference {
            reference: Reference {
                id,
                asset_id: Uuid::new_v4(),
                name: "Sheet".into(),
                role,
                description: String::new(),
            },
        },
    );
    (p, id)
}
fn look(sheet: Uuid, costume: &str) -> Look {
    Look {
        id: Uuid::new_v4(),
        name: costume.into(),
        hair: "Short black".into(),
        costume: costume.into(),
        sheet_reference_ids: vec![sheet],
        approved: false,
    }
}
fn traveller(looks: Vec<Look>) -> Character {
    Character {
        id: Uuid::new_v4(),
        name: "Traveller".into(),
        description: "Returns home".into(),
        looks,
    }
}
fn err(p: &Project, action: Action) -> String {
    p.apply(p.revision, action).unwrap_err().to_string()
}
fn approve_production(p: &Project) -> std::result::Result<Project, DomainError> {
    p.apply(
        p.revision,
        Action::ApproveProduction {
            local_attempts_per_shot: 3,
        },
    )
}

#[test]
fn legacy_projects_without_characters_keep_their_approval() {
    let mut legacy = serde_json::to_value(approved()).unwrap();
    let object = legacy.as_object_mut().unwrap();
    object.remove("characters");
    object.remove("lookAssignments");
    let restored: Project = serde_json::from_value(legacy).unwrap();
    assert!(restored.production_approved());
    assert!(restored.characters.is_empty());
}

#[test]
fn looks_need_exact_sheet_and_separate_approval() {
    let (p, inspiration) = reference(approved(), ReferenceRole::Inspiration);
    let (p, exact) = reference(p, ReferenceRole::Exact);
    let mut coat = look(inspiration, "Grey coat");
    coat.approved = true;
    assert!(
        err(
            &p,
            Action::SetCharacters {
                characters: vec![traveller(vec![coat.clone()])]
            }
        )
        .contains("own approval")
    );
    coat.approved = false;
    let c = traveller(vec![coat.clone()]);
    let p = step(
        p,
        Action::SetCharacters {
            characters: vec![c.clone()],
        },
    );
    assert!(err(&p, Action::ApproveLook { look_id: coat.id }).contains("exact-match"));

    coat.sheet_reference_ids = vec![exact];
    let c = Character {
        looks: vec![coat.clone()],
        ..c
    };
    let p = step(
        p,
        Action::SetCharacters {
            characters: vec![c.clone()],
        },
    );
    let p = step(p, Action::ApproveLook { look_id: coat.id });
    assert!(p.characters[0].looks[0].approved);

    // Resubmitting the unchanged approved Look keeps approval; changing its costume needs a new one.
    let characters = p.characters.clone();
    let p = step(p, Action::SetCharacters { characters });
    assert!(p.characters[0].looks[0].approved);
    let mut changed = p.characters.clone();
    changed[0].looks[0].costume = "Red coat".into();
    assert!(
        err(
            &p,
            Action::SetCharacters {
                characters: changed.clone()
            }
        )
        .contains("own approval")
    );
    changed[0].looks[0].approved = false;
    let p = step(
        p,
        Action::SetCharacters {
            characters: changed,
        },
    );
    assert!(!p.characters[0].looks[0].approved);
}

#[test]
fn production_approval_requires_approved_looks_assigned_to_every_section() {
    let (p, exact) = reference(approved(), ReferenceRole::Exact);
    let coat = look(exact, "Grey coat");
    let dress = look(exact, "Blue dress");
    let c = traveller(vec![coat.clone(), dress.clone()]);
    let p = step(
        p,
        Action::SetCharacters {
            characters: vec![c],
        },
    );
    let section = p.sections[0].id;
    assert!(
        approve_production(&p)
            .unwrap_err()
            .to_string()
            .contains("every section")
    );

    assert!(
        err(
            &p,
            Action::SetLookAssignments {
                assignments: vec![LookAssignment {
                    section_id: section,
                    look_ids: vec![coat.id, dress.id]
                }],
            }
        )
        .contains("one Look per Character")
    );
    assert!(
        err(
            &p,
            Action::SetLookAssignments {
                assignments: vec![LookAssignment {
                    section_id: Uuid::new_v4(),
                    look_ids: vec![]
                }],
            }
        )
        .contains("known section")
    );

    let p = step(
        p,
        Action::SetLookAssignments {
            assignments: vec![LookAssignment {
                section_id: section,
                look_ids: vec![coat.id],
            }],
        },
    );
    assert!(
        approve_production(&p)
            .unwrap_err()
            .to_string()
            .contains("must be approved")
    );
    let p = step(p, Action::ApproveLook { look_id: coat.id });
    let p = approve_production(&p).unwrap();
    assert!(p.production_approved());

    // An assigned Look cannot be removed out from under the plan.
    let mut removed = p.characters.clone();
    removed[0].looks.retain(|l| l.id != coat.id);
    assert!(
        err(
            &p,
            Action::SetCharacters {
                characters: removed
            }
        )
        .contains("Unassign")
    );
}

#[test]
fn changed_look_or_assignment_invalidates_production_approval() {
    let (p, exact) = reference(approved(), ReferenceRole::Exact);
    let coat = look(exact, "Grey coat");
    let dress = look(exact, "Blue dress");
    let p = step(
        p,
        Action::SetCharacters {
            characters: vec![traveller(vec![coat.clone(), dress.clone()])],
        },
    );
    let p = step(p, Action::ApproveLook { look_id: coat.id });
    let p = step(p, Action::ApproveLook { look_id: dress.id });
    let section = p.sections[0].id;
    let p = step(
        p,
        Action::SetLookAssignments {
            assignments: vec![LookAssignment {
                section_id: section,
                look_ids: vec![coat.id],
            }],
        },
    );
    let p = approve_production(&p).unwrap();

    let swapped = step(
        p.clone(),
        Action::SetLookAssignments {
            assignments: vec![LookAssignment {
                section_id: section,
                look_ids: vec![dress.id],
            }],
        },
    );
    assert!(swapped.production_approval.is_none());

    let mut renamed = p.characters.clone();
    renamed[0].looks[1].name = "Evening dress".into();
    renamed[0].looks[1].approved = false;
    let renamed = step(
        p,
        Action::SetCharacters {
            characters: renamed,
        },
    );
    assert!(renamed.production_approval.is_none());
}

#[test]
fn looks_stay_with_their_character_and_sections_drop_stale_assignments() {
    let (p, exact) = reference(approved(), ReferenceRole::Exact);
    let coat = look(exact, "Grey coat");
    let first = traveller(vec![coat.clone()]);
    let second = Character {
        id: Uuid::new_v4(),
        name: "Guard".into(),
        looks: vec![],
        ..first.clone()
    };
    let p = step(
        p,
        Action::SetCharacters {
            characters: vec![first.clone(), second.clone()],
        },
    );
    let moved = vec![
        Character {
            looks: vec![],
            ..first
        },
        Character {
            looks: vec![coat.clone()],
            ..second
        },
    ];
    assert!(err(&p, Action::SetCharacters { characters: moved }).contains("different Character"));

    let section = p.sections[0].id;
    let p = step(
        p,
        Action::SetLookAssignments {
            assignments: vec![LookAssignment {
                section_id: section,
                look_ids: vec![coat.id],
            }],
        },
    );
    let p = step(
        p,
        Action::SetSections {
            sections: vec![Section {
                id: Uuid::new_v4(),
                name: "Rewritten".into(),
                start_ms: 0,
                end_ms: 60_000,
                intent: "New structure".into(),
            }],
        },
    );
    assert!(p.look_assignments.is_empty());
}
