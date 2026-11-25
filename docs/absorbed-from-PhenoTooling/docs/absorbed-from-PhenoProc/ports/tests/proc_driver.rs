use ports::adapters::cargo_expand::CargoExpandAdapter;
use ports::adapters::trybuild::TrybuildAdapter;
use ports::proc_driver::ProcDriver;

#[tokio::test]
async fn cargo_expand_backend() {
    assert_eq!(CargoExpandAdapter.backend(), "cargo-expand");
}

#[tokio::test]
async fn trybuild_backend() {
    assert_eq!(TrybuildAdapter.backend(), "trybuild");
}

#[tokio::test]
async fn cargo_expand_no_panic() {
    let _ = CargoExpandAdapter.expand(std::path::Path::new(".")).await;
}

#[tokio::test]
async fn trybuild_ok() {
    assert!(TrybuildAdapter
        .trybuild(std::path::Path::new("."))
        .await
        .is_ok());
}

#[tokio::test]
async fn trait_object_safe() {
    let _t: Box<dyn ProcDriver> = Box::new(CargoExpandAdapter);
}
