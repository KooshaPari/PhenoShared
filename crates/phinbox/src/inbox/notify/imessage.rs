//! iMessage and email notification backends.
//!
//! - iMessage: sends via `AppleScript` `Messages`-app integration.
//! - Email: opens the user's default mail handler with a prefilled `mailto:` URL.

use super::{open_url, render_imessage_body, truncate, url_encode, NotifyAttempt};
use crate::inbox::{NotificationKind, PendingRequest};

/// Send the request via iMessage. Uses `AppleScript` `Messages`-app
/// integration. No-op if the target is unparseable.
#[must_use]
pub fn notify_imessage(req: &PendingRequest, target: &str) -> NotifyAttempt {
    let body = render_imessage_body(req);
    let script = format!(
        "tell application \"Messages\"\n\
         \x20 set targetService to 1st service whose service type = iMessage\n\
         \x20 set targetBuddy to buddy \"{target}\" of targetService\n\
         \x20 send \"{body}\" to targetBuddy\n\
         end tell",
        target = super::escape_applescript(target),
        body = super::escape_applescript(&body),
    );
    match super::run_osascript(&script) {
        Ok(()) => NotifyAttempt::ok(NotificationKind::IMessage, format!("sent to {target}")),
        Err(e) => NotifyAttempt::err(NotificationKind::IMessage, e),
    }
}

/// Open the user's default mail handler prefilled with the rendered
/// form. One click on "Send" delivers to the user's own mailbox; they
/// reply by running `phinbox answer --request-id <id> --reply`.
#[must_use]
pub fn notify_email(req: &PendingRequest, target: &str) -> NotifyAttempt {
    let subject = format!("[phinbox] {}", truncate(&req.spec.title, 60));
    let body = render_imessage_body(req);
    let url = format!(
        "mailto:{target}?subject={}&body={}",
        url_encode(&subject),
        url_encode(&body)
    );
    match open_url(&url) {
        Ok(()) => NotifyAttempt::ok(NotificationKind::Email, format!("opened mailto for {target}")),
        Err(e) => NotifyAttempt::err(NotificationKind::Email, e),
    }
}
