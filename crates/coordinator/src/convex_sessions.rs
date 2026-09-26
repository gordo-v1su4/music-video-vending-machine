//! Typed session operations shared by coordinator routes and acceptance tests.
use crate::convex::{Client, Error};
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use serde_json::json;
use sha2::{Digest, Sha256};
use uuid::Uuid;

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Auth {
    pub session_id: Option<Uuid>,
    pub issuer_hash: Option<String>,
    pub development: bool,
}
#[derive(Debug, Deserialize)]
pub struct Info {
    pub id: Uuid,
    pub client_label: String,
    pub created_at: DateTime<Utc>,
    pub expires_at: DateTime<Utc>,
}
// Match PostgreSQL bytea JSON encoding so migrated session identities stay valid.
pub fn hash(value: &str) -> String {
    format!("\\x{:x}", Sha256::digest(value.as_bytes()))
}

impl Client {
    pub async fn create_session(
        &self,
        issuer_hash: &str,
        label: &str,
    ) -> Result<(String, Info), Error> {
        let token = format!(
            "mvm_s_{}{}",
            Uuid::new_v4().simple(),
            Uuid::new_v4().simple()
        );
        let info = self.mutation("sessions:create", json!({"id":Uuid::new_v4(), "tokenHash":hash(&token), "issuerHash":issuer_hash, "clientLabel":label})).await?;
        Ok((token, info))
    }
    pub async fn identify_session(
        &self,
        issuer_hash: &str,
        token: &str,
    ) -> Result<Option<Uuid>, Error> {
        if !token.starts_with("mvm_s_") || token.len() != 70 {
            return Ok(None);
        }
        self.query(
            "sessions:identify",
            json!({"tokenHash":hash(token), "issuerHash":issuer_hash}),
        )
        .await
    }
    pub async fn valid_session(&self, auth: &Auth) -> Result<bool, Error> {
        self.query("sessions:valid", json!({"auth":auth})).await
    }
    pub async fn current_session(&self, auth: &Auth) -> Result<Option<Info>, Error> {
        self.query("sessions:current", json!({"auth":auth})).await
    }
    pub async fn revoke_session(&self, auth: &Auth, all: bool) -> Result<(), Error> {
        self.mutation("sessions:revoke", json!({"auth":auth,"all":all}))
            .await
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[tokio::test]
    #[ignore = "Creates and revokes disposable sessions on the private MVVM instance"]
    async fn live_session_lifecycle() {
        let client = Client::new(
            &std::env::var("CONVEX_SELF_HOSTED_URL").unwrap(),
            &std::env::var("MVVM_CONVEX_SELF_HOSTED_ADMIN_KEY").unwrap(),
        )
        .unwrap();
        // Independent synthetic issuer: cannot revoke a real operator's sessions.
        let issuer = hash(&Uuid::new_v4().to_string());
        let (token, first) = client
            .create_session(&issuer, "MVVM acceptance")
            .await
            .unwrap();
        let (_, second) = client
            .create_session(&issuer, "MVVM acceptance second")
            .await
            .unwrap();
        let auth = Auth {
            session_id: Some(first.id),
            issuer_hash: Some(issuer.clone()),
            development: false,
        };
        assert_eq!(
            client.identify_session(&issuer, &token).await.unwrap(),
            Some(first.id)
        );
        assert!(
            client
                .identify_session(&hash("other issuer"), &token)
                .await
                .unwrap()
                .is_none()
        );
        assert!(
            client
                .identify_session(&issuer, "bootstrap-key")
                .await
                .unwrap()
                .is_none()
        );
        let current = client.current_session(&auth).await.unwrap().unwrap();
        assert_eq!(current.id, first.id);
        assert_eq!((current.expires_at - current.created_at).num_hours(), 12);
        client.revoke_session(&auth, true).await.unwrap();
        assert!(!client.valid_session(&auth).await.unwrap());
        assert!(
            !client
                .valid_session(&Auth {
                    session_id: Some(second.id),
                    ..auth.clone()
                })
                .await
                .unwrap()
        );
        assert!(
            client
                .identify_session(&issuer, &token)
                .await
                .unwrap()
                .is_none()
        );
    }
}
