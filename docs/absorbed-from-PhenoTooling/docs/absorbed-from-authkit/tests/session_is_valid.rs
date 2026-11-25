use authkit_core::domain::session::{Session, SessionState};
use chrono::Utc;

#[test]
fn test_session_is_valid_pure() {
    let mut session = Session::new("user-123");
    // Fresh session should be valid
    assert!(session.is_valid());

    // Expired but still active -> invalid
    session.expires_at = Utc::now() - chrono::Duration::hours(1);
    assert!(!session.is_valid());

    // Revoked but not expired -> invalid
    session.expires_at = Utc::now() + chrono::Duration::hours(1);
    session.state = SessionState::Revoked;
    assert!(!session.is_valid());
}
