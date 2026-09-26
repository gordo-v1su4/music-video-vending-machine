//! Private coordinator-to-Convex transport. Admin credentials never reach clients.
use serde::{Serialize, de::DeserializeOwned};
use serde_json::{Value, json};
use std::time::Duration;

#[derive(Clone)]
pub struct Client {
    http: reqwest::Client,
    origin: String,
    authorization: reqwest::header::HeaderValue,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Error {
    Configuration,
    Unavailable,
    InvalidResponse,
    Conflict,
    Unauthorized,
    NotFound,
    Invalid,
}
impl std::fmt::Display for Error {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "Convex operation failed ({self:?})")
    }
}
impl std::error::Error for Error {}

impl Client {
    pub fn new(origin: &str, key: &str) -> Result<Self, Error> {
        let url = reqwest::Url::parse(origin).map_err(|_| Error::Configuration)?;
        if !matches!(url.scheme(), "http" | "https")
            || url.host_str().is_none()
            || !url.username().is_empty()
            || url.password().is_some()
            || url.query().is_some()
            || url.fragment().is_some()
            || url.path() != "/"
            || key.len() < 32
        {
            return Err(Error::Configuration);
        }
        let mut authorization = reqwest::header::HeaderValue::from_str(&format!("Convex {key}"))
            .map_err(|_| Error::Configuration)?;
        authorization.set_sensitive(true);
        let http = reqwest::Client::builder()
            .redirect(reqwest::redirect::Policy::none())
            .connect_timeout(Duration::from_secs(5))
            .timeout(Duration::from_secs(30))
            .build()
            .map_err(|_| Error::Configuration)?;
        Ok(Self {
            http,
            origin: origin.trim_end_matches('/').into(),
            authorization,
        })
    }

    pub async fn query<T: DeserializeOwned>(
        &self,
        path: &str,
        args: impl Serialize,
    ) -> Result<T, Error> {
        self.call("query", path, args).await
    }
    // Do not retry ambiguous mutations. Caller must reconcile durable identities.
    pub async fn mutation<T: DeserializeOwned>(
        &self,
        path: &str,
        args: impl Serialize,
    ) -> Result<T, Error> {
        self.call("mutation", path, args).await
    }
    async fn call<T: DeserializeOwned>(
        &self,
        kind: &str,
        path: &str,
        args: impl Serialize,
    ) -> Result<T, Error> {
        let body = json!({ "path": path, "format": "convex_encoded_json", "args": [args] });
        let mut response = self
            .http
            .post(format!("{}/api/{kind}", self.origin))
            .header(reqwest::header::AUTHORIZATION, self.authorization.clone())
            .json(&body)
            .send()
            .await
            .map_err(|_| Error::Unavailable)?;
        // Function failures use HTTP 560; parse only their structured error data.
        if !response.status().is_success() && response.status().as_u16() != 560 {
            return Err(Error::Unavailable);
        }
        let mut bytes = Vec::new();
        while let Some(chunk) = response.chunk().await.map_err(|_| Error::Unavailable)? {
            if bytes.len() + chunk.len() > 8 * 1024 * 1024 {
                return Err(Error::InvalidResponse);
            }
            bytes.extend_from_slice(&chunk);
        }
        let result: Value = serde_json::from_slice(&bytes).map_err(|_| Error::InvalidResponse)?;
        decode(result)
    }
}

fn decode<T: DeserializeOwned>(result: Value) -> Result<T, Error> {
    match result.get("status").and_then(Value::as_str) {
        Some("success") => {
            serde_json::from_value(result.get("value").cloned().ok_or(Error::InvalidResponse)?)
                .map_err(|_| Error::InvalidResponse)
        }
        Some("error") => Err(match result.get("errorData").and_then(Value::as_str) {
            Some("CONFLICT") => Error::Conflict,
            Some("UNAUTHORIZED") => Error::Unauthorized,
            Some("ASSET_NOT_FOUND" | "NOT_FOUND") => Error::NotFound,
            Some("INVALID_DOCUMENT" | "INVALID_LABEL" | "INVALID_HASH") => Error::Invalid,
            _ => Error::Unavailable,
        }),
        _ => Err(Error::InvalidResponse),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[tokio::test]
    #[ignore = "Requires private MVVM deployment and injected administrator credential"]
    async fn live_private_queries_and_structured_errors() {
        let client = Client::new(
            &std::env::var("CONVEX_SELF_HOSTED_URL").unwrap(),
            &std::env::var("MVVM_CONVEX_SELF_HOSTED_ADMIN_KEY").unwrap(),
        )
        .unwrap();
        let projects: Vec<String> = client
            .query(
                "projects:list",
                json!({"auth":{"sessionId":null,"issuerHash":null,"development":true}}),
            )
            .await
            .unwrap();
        assert!(projects.len() >= 3);
        for document in projects {
            let _: mvm_domain::Project = serde_json::from_str(&document).unwrap();
        }
        assert_eq!(
            client
                .query::<Value>(
                    "projects:list",
                    json!({"auth":{"sessionId":null,"issuerHash":null,"development":false}})
                )
                .await,
            Err(Error::Unauthorized)
        );
    }
    #[test]
    fn ignores_raw_server_errors_and_validates_envelopes() {
        assert_eq!(
            decode::<Value>(json!({"status":"error","errorMessage":"private data UNAUTHORIZED"})),
            Err(Error::Unavailable)
        );
        assert_eq!(
            decode::<Value>(json!({"status":"error","errorData":"CONFLICT"})),
            Err(Error::Conflict)
        );
        assert_eq!(
            decode::<Value>(json!({"status":"success"})),
            Err(Error::InvalidResponse)
        );
        assert_eq!(
            decode::<Value>(json!({"status":"success","value":null})),
            Ok(Value::Null)
        );
    }
    #[test]
    fn rejects_credential_bearing_or_ambiguous_origins() {
        for origin in [
            "file:///tmp",
            "http://user:password@localhost",
            "http://localhost/api",
            "http://localhost/?key=secret",
        ] {
            assert!(matches!(
                Client::new(origin, &"a".repeat(64)),
                Err(Error::Configuration)
            ));
        }
    }
}
