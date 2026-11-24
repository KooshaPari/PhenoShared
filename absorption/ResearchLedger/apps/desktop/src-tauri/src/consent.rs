use chrono::{DateTime, Utc};
use rusqlite::{params, Connection, Result as SqlResult};
use sha2::{Digest, Sha256};

pub const REFERENCE_FETCH_PURPOSE: &str = "reference_fetch";
pub const PUBLIC_WEB_CATEGORY: &str = "public_web";

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ConsentGrant {
    pub id: String,
    pub local_profile: String,
    pub provider: String,
    pub purpose: String,
    pub data_categories: Vec<String>,
    pub url_scope: String,
    pub expires_at: Option<String>,
    pub version: i64,
    pub granted_at: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ConsentDecision {
    pub allowed: bool,
    pub reason: String,
}

pub struct ConsentRegistry<'a> {
    connection: &'a Connection,
}

impl<'a> ConsentRegistry<'a> {
    pub fn new(connection: &'a Connection) -> Self {
        Self { connection }
    }

    pub fn grant(&self, grant: ConsentGrant) -> SqlResult<()> {
        if grant
            .data_categories
            .iter()
            .any(|category| category.contains(','))
        {
            return Err(rusqlite::Error::InvalidParameterName(
                "consent data categories must not contain commas".into(),
            ));
        }
        parse_rfc3339(&grant.granted_at).map_err(|_| {
            rusqlite::Error::InvalidParameterName(
                "consent granted_at must be an RFC3339 timestamp".into(),
            )
        })?;
        if let Some(expires_at) = &grant.expires_at {
            parse_rfc3339(expires_at).map_err(|_| {
                rusqlite::Error::InvalidParameterName(
                    "consent expires_at must be an RFC3339 timestamp".into(),
                )
            })?;
        }
        let scope = canonical_scope(&grant.url_scope);
        self.connection.execute(
            "INSERT INTO consent_grants
             (id, local_profile, provider, purpose, data_categories, url_scope,
              granted_at, expires_at, revoked_at, version)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, NULL, ?9)
             ON CONFLICT(id) DO UPDATE SET local_profile=excluded.local_profile,
              provider=excluded.provider, purpose=excluded.purpose,
              data_categories=excluded.data_categories, url_scope=excluded.url_scope,
              granted_at=excluded.granted_at, expires_at=excluded.expires_at,
              revoked_at=NULL, version=excluded.version",
            params![
                grant.id,
                grant.local_profile,
                grant.provider,
                grant.purpose,
                grant.data_categories.join(","),
                scope,
                grant.granted_at,
                grant.expires_at,
                grant.version,
            ],
        )?;
        Ok(())
    }

    pub fn revoke(&self, id: &str, revoked_at: &str) -> SqlResult<bool> {
        let changed = self.connection.execute(
            "UPDATE consent_grants SET revoked_at = ?2 WHERE id = ?1 AND revoked_at IS NULL",
            params![id, revoked_at],
        )?;
        Ok(changed == 1)
    }

    pub fn decide(&self, target_url: &str, now: &str) -> SqlResult<ConsentDecision> {
        let target = canonical_scope(target_url);
        let now_at = match parse_rfc3339(now) {
            Ok(now_at) => now_at,
            Err(()) => {
                self.audit("none", &target, false, "invalid_decision_time", now)?;
                return Ok(ConsentDecision {
                    allowed: false,
                    reason: "invalid_decision_time".into(),
                });
            }
        };
        let mut statement = self.connection.prepare(
            "SELECT id, purpose, data_categories, url_scope, granted_at, expires_at, revoked_at
             FROM consent_grants ORDER BY version DESC, granted_at DESC, id",
        )?;
        let mut rows = statement.query([])?;
        let mut reason = "no_matching_consent";
        let mut matching_scope_seen = false;
        while let Some(row) = rows.next()? {
            let id: String = row.get(0)?;
            let purpose: String = row.get(1)?;
            let categories: String = row.get(2)?;
            let scope: String = row.get(3)?;
            let granted_at: String = row.get(4)?;
            let expires_at: Option<String> = row.get(5)?;
            let revoked_at: Option<String> = row.get(6)?;
            let row_reason = if purpose != REFERENCE_FETCH_PURPOSE {
                "purpose_mismatch"
            } else if !categories
                .split(',')
                .any(|value| value == PUBLIC_WEB_CATEGORY)
            {
                "category_mismatch"
            } else if revoked_at.is_some() {
                "revoked"
            } else if scope != target {
                "out_of_scope"
            } else {
                let granted_at = match parse_rfc3339(&granted_at) {
                    Ok(granted_at) => granted_at,
                    Err(()) => {
                        self.audit(&id, &target, false, "invalid_granted_at", now)?;
                        return Ok(ConsentDecision {
                            allowed: false,
                            reason: "invalid_granted_at".into(),
                        });
                    }
                };
                let expires_at = match expires_at.as_deref() {
                    Some(expires_at) => match parse_rfc3339(expires_at) {
                        Ok(expires_at) => Some(expires_at),
                        Err(()) => {
                            self.audit(&id, &target, false, "invalid_expires_at", now)?;
                            return Ok(ConsentDecision {
                                allowed: false,
                                reason: "invalid_expires_at".into(),
                            });
                        }
                    },
                    None => None,
                };
                if granted_at > now_at {
                    "not_yet_granted"
                } else if expires_at.is_some_and(|expires_at| expires_at <= now_at) {
                    "expired"
                } else {
                    self.audit(&id, &target, true, "allowed", now)?;
                    return Ok(ConsentDecision {
                        allowed: true,
                        reason: "allowed".into(),
                    });
                }
            };
            if scope == target {
                matching_scope_seen = true;
                reason = row_reason;
            } else if !matching_scope_seen {
                reason = row_reason;
            }
        }
        self.audit("none", &target, false, reason, now)?;
        Ok(ConsentDecision {
            allowed: false,
            reason: reason.into(),
        })
    }

    fn audit(
        &self,
        grant_id: &str,
        target: &str,
        allowed: bool,
        reason: &str,
        at: &str,
    ) -> SqlResult<()> {
        let target_hash = format!("{:x}", Sha256::digest(target.as_bytes()));
        self.connection.execute(
            "INSERT INTO consent_audit (grant_id, target_hash, decision, reason, decided_at)
             VALUES (?1, ?2, ?3, ?4, ?5)",
            params![
                grant_id,
                target_hash,
                if allowed { "allow" } else { "deny" },
                reason,
                at
            ],
        )?;
        Ok(())
    }
}

pub fn canonical_scope(raw: &str) -> String {
    crate::enrichment::canonical_url(raw)
}

fn parse_rfc3339(value: &str) -> Result<DateTime<Utc>, ()> {
    DateTime::parse_from_rfc3339(value)
        .map(|value| value.with_timezone(&Utc))
        .map_err(|_| ())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn connection() -> Connection {
        let connection = Connection::open_in_memory().unwrap();
        connection
            .execute_batch(include_str!("../migrations/001_initial.sql"))
            .unwrap();
        connection
    }

    fn grant(connection: &Connection, expires_at: Option<&str>) {
        ConsentRegistry::new(connection)
            .grant(ConsentGrant {
                id: "grant-1".into(),
                local_profile: "default".into(),
                provider: "manual".into(),
                purpose: REFERENCE_FETCH_PURPOSE.into(),
                data_categories: vec![PUBLIC_WEB_CATEGORY.into()],
                url_scope: "https://example.com/reference".into(),
                expires_at: expires_at.map(str::to_owned),
                version: 1,
                granted_at: "2026-08-10T00:00:00Z".into(),
            })
            .unwrap();
    }

    fn assert_denied_and_redacted(connection: &Connection, url: &str, reason: &str) {
        let decision = ConsentRegistry::new(connection)
            .decide(url, "2026-08-10T01:00:00Z")
            .unwrap();
        assert!(!decision.allowed);
        assert_eq!(decision.reason, reason);
        let (hash, decision, audit_reason): (String, String, String) = connection
            .query_row(
                "SELECT target_hash, decision, reason FROM consent_audit ORDER BY id DESC LIMIT 1",
                [],
                |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?)),
            )
            .unwrap();
        assert_eq!(decision, "deny");
        assert_eq!(audit_reason, reason);
        assert_eq!(
            hash,
            format!("{:x}", Sha256::digest(canonical_scope(url).as_bytes()))
        );
        assert_ne!(hash, url);
    }

    #[test]
    fn canonical_scope_removes_fragment_and_trailing_slash() {
        assert_eq!(
            canonical_scope("https://example.com/a/#section"),
            "https://example.com/a"
        );
    }

    #[test]
    fn no_consent_is_denied_and_audited_without_raw_url() {
        let connection = connection();
        assert_denied_and_redacted(
            &connection,
            "https://example.com/reference",
            "no_matching_consent",
        );
    }

    #[test]
    fn revoked_consent_is_denied_and_audited_without_raw_url() {
        let connection = connection();
        grant(&connection, None);
        assert!(ConsentRegistry::new(&connection)
            .revoke("grant-1", "2026-08-10T00:30:00Z")
            .unwrap());
        assert_denied_and_redacted(&connection, "https://example.com/reference", "revoked");
    }

    #[test]
    fn expired_consent_is_denied_and_audited_without_raw_url() {
        let connection = connection();
        grant(&connection, Some("2026-08-10T00:30:00Z"));
        assert_denied_and_redacted(&connection, "https://example.com/reference", "expired");
    }

    #[test]
    fn malformed_stored_expiry_is_denied_and_audited_without_raw_url() {
        let connection = connection();
        grant(&connection, None);
        connection
            .execute(
                "UPDATE consent_grants SET expires_at = 'zzzz' WHERE id = 'grant-1'",
                [],
            )
            .unwrap();

        assert_denied_and_redacted(
            &connection,
            "https://example.com/reference",
            "invalid_expires_at",
        );
    }

    #[test]
    fn malformed_stored_grant_time_is_denied_and_audited_without_raw_url() {
        let connection = connection();
        grant(&connection, None);
        connection
            .execute(
                "UPDATE consent_grants SET granted_at = 'zzzz' WHERE id = 'grant-1'",
                [],
            )
            .unwrap();

        assert_denied_and_redacted(
            &connection,
            "https://example.com/reference",
            "invalid_granted_at",
        );
    }

    #[test]
    fn malformed_newer_grant_cannot_fall_through_to_an_older_grant() {
        let connection = connection();
        let registry = ConsentRegistry::new(&connection);
        for (id, version) in [("older", 1), ("newer", 2)] {
            registry
                .grant(ConsentGrant {
                    id: id.into(),
                    local_profile: "default".into(),
                    provider: "manual".into(),
                    purpose: REFERENCE_FETCH_PURPOSE.into(),
                    data_categories: vec![PUBLIC_WEB_CATEGORY.into()],
                    url_scope: "https://example.com/reference".into(),
                    expires_at: None,
                    version,
                    granted_at: "2026-08-10T00:00:00Z".into(),
                })
                .unwrap();
        }
        connection
            .execute(
                "UPDATE consent_grants SET expires_at = 'zzzz' WHERE id = 'newer'",
                [],
            )
            .unwrap();

        assert_denied_and_redacted(
            &connection,
            "https://example.com/reference",
            "invalid_expires_at",
        );
    }

    #[test]
    fn malformed_out_of_scope_grant_cannot_block_valid_scoped_consent() {
        let connection = connection();
        let registry = ConsentRegistry::new(&connection);
        for (id, scope, version) in [
            ("in-scope", "https://example.com/reference", 1),
            ("out-of-scope", "https://example.com/other", 2),
        ] {
            registry
                .grant(ConsentGrant {
                    id: id.into(),
                    local_profile: "default".into(),
                    provider: "manual".into(),
                    purpose: REFERENCE_FETCH_PURPOSE.into(),
                    data_categories: vec![PUBLIC_WEB_CATEGORY.into()],
                    url_scope: scope.into(),
                    expires_at: None,
                    version,
                    granted_at: "2026-08-10T00:00:00Z".into(),
                })
                .unwrap();
        }
        connection
            .execute(
                "UPDATE consent_grants SET expires_at = 'zzzz' WHERE id = 'out-of-scope'",
                [],
            )
            .unwrap();

        let decision = registry
            .decide("https://example.com/reference", "2026-08-10T01:00:00Z")
            .unwrap();
        assert!(decision.allowed);
        assert_eq!(decision.reason, "allowed");
    }

    #[test]
    fn out_of_scope_consent_is_denied_and_audited_without_raw_url() {
        let connection = connection();
        grant(&connection, None);
        assert_denied_and_redacted(&connection, "https://example.com/other", "out_of_scope");
    }

    #[test]
    fn matching_revoked_consent_reason_outweighs_later_out_of_scope_row() {
        let connection = connection();
        let registry = ConsentRegistry::new(&connection);
        for (id, scope, version) in [
            ("unrelated", "https://example.com/other", 1),
            ("revoked", "https://example.com/reference", 2),
        ] {
            registry
                .grant(ConsentGrant {
                    id: id.into(),
                    local_profile: "default".into(),
                    provider: "manual".into(),
                    purpose: REFERENCE_FETCH_PURPOSE.into(),
                    data_categories: vec![PUBLIC_WEB_CATEGORY.into()],
                    url_scope: scope.into(),
                    expires_at: None,
                    version,
                    granted_at: "2026-08-10T00:00:00Z".into(),
                })
                .unwrap();
        }
        assert!(registry.revoke("revoked", "2026-08-10T00:30:00Z").unwrap());

        assert_denied_and_redacted(&connection, "https://example.com/reference", "revoked");
    }

    #[test]
    fn rejects_categories_that_cannot_round_trip_through_the_storage_delimiter() {
        let connection = connection();
        let error = ConsentRegistry::new(&connection)
            .grant(ConsentGrant {
                id: "grant-comma".into(),
                local_profile: "default".into(),
                provider: "manual".into(),
                purpose: REFERENCE_FETCH_PURPOSE.into(),
                data_categories: vec!["other,public_web".into()],
                url_scope: "https://example.com/reference".into(),
                expires_at: None,
                version: 1,
                granted_at: "2026-08-10T00:00:00Z".into(),
            })
            .unwrap_err();

        assert!(error.to_string().contains("comma"));
    }

    #[test]
    fn rejects_malformed_grant_timestamps() {
        let connection = connection();
        let registry = ConsentRegistry::new(&connection);
        let grant = |granted_at: &str, expires_at: Option<&str>| ConsentGrant {
            id: format!("grant-{granted_at}"),
            local_profile: "default".into(),
            provider: "manual".into(),
            purpose: REFERENCE_FETCH_PURPOSE.into(),
            data_categories: vec![PUBLIC_WEB_CATEGORY.into()],
            url_scope: "https://example.com/reference".into(),
            expires_at: expires_at.map(str::to_owned),
            version: 1,
            granted_at: granted_at.into(),
        };

        assert!(registry.grant(grant("not-a-date", None)).is_err());
        assert!(registry
            .grant(grant("2026-08-10T00:00:00Z", Some("not-a-date")))
            .is_err());
    }
}
