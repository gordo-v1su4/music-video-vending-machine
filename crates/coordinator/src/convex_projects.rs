//! Project persistence; pure domain action validation stays in mvm-domain.
use crate::{
    convex::{Client, Error},
    convex_sessions::Auth,
};
use mvm_domain::Project;
use serde::Deserialize;
use serde_json::json;
use uuid::Uuid;

#[derive(Deserialize)]
struct ProjectRow {
    document: String,
}
#[derive(Deserialize)]
pub struct EventRow {
    #[serde(deserialize_with = "revision_number")]
    pub revision: u64,
    pub document: String,
}
fn revision_number<'de, D: serde::Deserializer<'de>>(deserializer: D) -> Result<u64, D::Error> {
    let value = f64::deserialize(deserializer)?;
    if !value.is_finite() || value < 0.0 || value.fract() != 0.0 || value > 9_007_199_254_740_991.0
    {
        return Err(serde::de::Error::custom("Invalid revision"));
    }
    Ok(value as u64)
}

impl Client {
    pub async fn read_asset(
        &self,
        auth: &Auth,
        project: Uuid,
        id: Uuid,
    ) -> Result<crate::Asset, Error> {
        #[derive(Deserialize)]
        struct Row {
            metadata: String,
        }
        let row: Row = self
            .query(
                "assets:get",
                json!({"auth":auth,"projectId":project,"id":id}),
            )
            .await?;
        serde_json::from_str(&row.metadata).map_err(|_| Error::InvalidResponse)
    }
    pub async fn list_projects(&self, auth: &Auth) -> Result<Vec<Project>, Error> {
        let documents: Vec<String> = self.query("projects:list", json!({"auth":auth})).await?;
        documents
            .into_iter()
            .map(|s| serde_json::from_str(&s).map_err(|_| Error::InvalidResponse))
            .collect()
    }
    pub async fn read_project(&self, auth: &Auth, id: Uuid) -> Result<Project, Error> {
        let row: Option<ProjectRow> = self
            .query("projects:get", json!({"auth":auth,"id":id}))
            .await?;
        serde_json::from_str(&row.ok_or(Error::NotFound)?.document)
            .map_err(|_| Error::InvalidResponse)
    }
    pub async fn commit_project(
        &self,
        auth: &Auth,
        project: &Project,
        expected_revision: Option<u64>,
        assets: &[Uuid],
    ) -> Result<(), Error> {
        let document = serde_json::to_string(project).map_err(|_| Error::Invalid)?;
        let _: ProjectRow = self.mutation("projects:commit", json!({"auth":auth,"id":project.id,"expectedRevision":expected_revision,"document":document,"assetIds":assets})).await?;
        Ok(())
    }
    pub async fn project_events(
        &self,
        auth: &Auth,
        id: Uuid,
        after: i64,
    ) -> Result<Vec<EventRow>, Error> {
        self.query(
            "projects:events",
            json!({"auth":auth,"id":id,"after":after}),
        )
        .await
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn convex_float_revisions_require_exact_safe_integers() {
        assert_eq!(
            serde_json::from_str::<EventRow>(r#"{"revision":1.0,"document":"{}"}"#)
                .unwrap()
                .revision,
            1
        );
        for revision in ["-1", "1.5", "9007199254740992"] {
            assert!(
                serde_json::from_str::<EventRow>(&format!(
                    r#"{{"revision":{revision},"document":"{{}}"}}"#
                ))
                .is_err()
            );
        }
    }
}
