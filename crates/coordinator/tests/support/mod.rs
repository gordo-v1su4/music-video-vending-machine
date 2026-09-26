use mvm_coordinator::{AppState, convex::Client};
use object_store::memory::InMemory;
use std::sync::Arc;

pub fn state() -> AppState {
    let url = std::env::var("MVVM_TEST_CONVEX_URL").expect("dedicated test endpoint required");
    let parsed = reqwest::Url::parse(&url).unwrap();
    assert_eq!(parsed.scheme(), "http");
    assert_eq!(parsed.host_str(), Some("127.0.0.1"));
    AppState {
        convex: Some(
            Client::new(&url, &std::env::var("MVVM_TEST_CONVEX_ADMIN_KEY").unwrap()).unwrap(),
        ),
        analysis: None,
        transcription: None,
        objects: Arc::new(InMemory::new()),
        token_hash: None,
        development: true,
        storage_name: "test".into(),
        object_bucket: "mvvm".into(),
    }
}
