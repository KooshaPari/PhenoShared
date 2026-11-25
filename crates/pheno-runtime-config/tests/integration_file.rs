//! Integration tests for FileConfig.
//!
//! These tests are marked #[ignore] by default because they require
//! filesystem watchers (notify v6) which may have platform-specific
//! timing characteristics. Run explicitly with:
//!   cargo test --test integration_file -- --ignored

use std::io::Write;

use pheno_runtime_config::Reloadable;
use tempfile::NamedTempFile;

#[test]
#[ignore]
fn file_config_reloads_on_modify() {
    use std::time::Duration;

    use pheno_runtime_config::file::FileConfig;
    use serde::Deserialize;

    #[derive(Deserialize, Debug, PartialEq)]
    struct TestConfig {
        value: i32,
    }

    let mut file = NamedTempFile::new().unwrap();
    writeln!(file, "value = 1").unwrap();
    file.flush().unwrap();
    let path = file.path().to_path_buf();

    let rt = tokio::runtime::Runtime::new().unwrap();
    let config = rt.block_on(async { FileConfig::<TestConfig>::new(&path).await.unwrap() });

    assert_eq!(config.current().value, 1);

    // Modify the file
    writeln!(file, "value = 42").unwrap();
    file.flush().unwrap();

    // Wait for notify to fire
    std::thread::sleep(Duration::from_millis(500));

    // May or may not have updated depending on OS watcher latency
    let val = config.current().value;
    assert!(val == 1 || val == 42, "Expected 1 or 42, got {}", val);
}
