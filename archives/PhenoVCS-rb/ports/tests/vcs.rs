use ports::adapters::git::GitBackend;
use ports::adapters::jj::JjBackend;
use ports::vcs::Vcs;

#[tokio::test]
async fn git_backend() {
    assert_eq!(GitBackend.backend(), "git");
}

#[tokio::test]
async fn jj_backend() {
    assert_eq!(JjBackend.backend(), "jj");
}

#[tokio::test]
async fn git_log_empty() {
    assert!(GitBackend.log(10).await.unwrap().is_empty());
}

#[tokio::test]
async fn jj_commit_returns_at() {
    assert_eq!(JjBackend.commit("x").await.unwrap(), "@");
}

#[tokio::test]
async fn trait_object_safe() {
    let _t: Box<dyn Vcs> = Box::new(GitBackend);
}
