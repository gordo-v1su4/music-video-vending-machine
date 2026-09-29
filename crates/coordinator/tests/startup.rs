use std::process::Command;

#[test]
fn missing_convex_configuration_never_falls_back_to_postgres() {
    let output = Command::new(env!("CARGO_BIN_EXE_mvm-coordinator"))
        .env("MVVM_DEV_LOCAL", "1")
        .env("MVVM_BIND", "127.0.0.1:0")
        .env_remove("CONVEX_SELF_HOSTED_URL")
        .env_remove("MVVM_OPERATOR_TOKEN")
        .env("DATABASE_URL", "this is deliberately not a database URL")
        .output()
        .unwrap();
    assert!(!output.status.success());
    let error = String::from_utf8(output.stderr).unwrap();
    assert!(error.contains("CONVEX_SELF_HOSTED_URL is required"));
    assert!(error.contains("fallback is disabled"));
    assert!(!error.contains("this is deliberately"));
}

#[test]
fn missing_rustfs_configuration_never_creates_local_asset_storage() {
    let temporary = tempfile::tempdir().unwrap();
    let assets = temporary.path().join("must-not-be-created");
    let output = Command::new(env!("CARGO_BIN_EXE_mvm-coordinator"))
        .env("MVVM_DEV_LOCAL", "1")
        .env("MVVM_BIND", "127.0.0.1:0")
        .env_remove("MVVM_OPERATOR_TOKEN")
        .env("CONVEX_SELF_HOSTED_URL", "http://127.0.0.1:1")
        .env("MVVM_CONVEX_SELF_HOSTED_ADMIN_KEY", "a".repeat(32))
        .env_remove("MVVM_S3_BUCKET")
        .env("MVVM_LOCAL_ASSETS", &assets)
        .output()
        .unwrap();
    assert!(!output.status.success());
    assert!(
        String::from_utf8(output.stderr)
            .unwrap()
            .contains("MVVM requires configured RustFS storage")
    );
    assert!(!assets.exists());
}
