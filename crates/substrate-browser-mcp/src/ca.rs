//! Trust for the daemon's TLS certificate.
//!
//! A `brokerd` that serves HTTPS presents a certificate it generated for
//! itself, so the client has to be told which certificate to trust.
//! [`CA_ENV`](crate::client::CA_ENV) names a PEM file holding that
//! certificate. Pinning it keeps the daemon's identity bound to the
//! certificate the daemon was started with, and keeps the machine's trust
//! store out of the picture.
//!
//! Two failure modes live here, and neither of them is an unreachable
//! daemon: a mis-pointed `BROKERD_CA` never sends a request at all, and a
//! rejected certificate is a certificate the client refuses to trust.

use std::{error::Error as StdError, path::Path};

use substrate_browser_broker::BrokerError;

use crate::client::{refused, CA_ENV};

/// Read the PEM file at `path` and return the certificates to pin.
///
/// A bundle may hold more than one certificate, and every one of them is
/// pinned: a chain file names the authority and the intermediates that lead
/// to it.
///
/// The error text names the environment variable and the path, because a
/// mis-pointed `BROKERD_CA` is a configuration mistake rather than a daemon
/// that failed to answer.
pub(crate) fn pinned_certificates(path: &Path) -> Result<Vec<reqwest::Certificate>, BrokerError> {
    let repair = format!("point {CA_ENV} at the PEM certificate the daemon was started with");
    let bytes = std::fs::read(path).map_err(|err| {
        if err.kind() == std::io::ErrorKind::NotFound {
            refused(format!(
                "{CA_ENV} points at {}, which does not exist; {repair}",
                path.display()
            ))
        } else {
            refused(format!(
                "{CA_ENV} points at {}, which cannot be read ({err}); {repair}",
                path.display()
            ))
        }
    })?;

    let certificates = reqwest::Certificate::from_pem_bundle(&bytes).map_err(|err| {
        refused(format!(
            "{CA_ENV} points at {}, which is not a valid PEM certificate ({err}); {repair}",
            path.display()
        ))
    })?;

    if certificates.is_empty() {
        return Err(refused(format!(
            "{CA_ENV} points at {}, which holds no PEM certificate; {repair}",
            path.display()
        )));
    }
    Ok(certificates)
}

/// Report a certificate the client cannot use as a trust anchor.
///
/// The file parsed as PEM, but the TLS stack refused the certificate inside
/// it, so the path is named again: a truncated or mangled file is a
/// configuration mistake, not a daemon that failed to answer.
pub(crate) fn unusable_certificate(path: &Path, err: &reqwest::Error) -> BrokerError {
    refused(format!(
        "{CA_ENV} points at {}, which the client cannot use as a trust anchor ({}); point {CA_ENV} \
         at the PEM certificate the daemon was started with",
        path.display(),
        cause_chain(err)
    ))
}

/// Render an error and everything that caused it, deepest cause last.
fn cause_chain(err: &reqwest::Error) -> String {
    let mut parts = vec![err.to_string()];
    let mut cause = err.source();
    while let Some(error) = cause {
        parts.push(error.to_string());
        cause = error.source();
    }
    parts.join(": ")
}

/// Find the text of a rejected peer certificate in an error chain.
///
/// rustls reports a certificate the client refuses to trust as "invalid peer
/// certificate: ...". The text is what identifies that case here: naming the
/// rustls error type would mean depending on rustls from this crate.
pub(crate) fn certificate_rejection(err: &reqwest::Error) -> Option<String> {
    let mut cause: Option<&(dyn StdError + 'static)> = Some(err);
    while let Some(error) = cause {
        let text = error.to_string();
        if is_certificate_rejection(&text) {
            return Some(text);
        }
        cause = error.source();
    }
    None
}

/// Whether an error text describes a certificate this client refuses.
fn is_certificate_rejection(text: &str) -> bool {
    let lowered = text.to_ascii_lowercase();
    lowered.contains("certificate") || lowered.contains("unknown issuer")
}
