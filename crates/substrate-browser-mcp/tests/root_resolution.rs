//! The state-root contract shared with `brokerd`.
//!
//! `brokerd` resolves its default root in `crates/substrate-browser-broker/src/main.rs`
//! and the MCP bridge resolves it here. If the two ever disagree, the bridge
//! becomes a second lease authority: it would acquire leases the daemon cannot
//! see, and the daemon would serve browsers the bridge believes are free.
//!
//! The two crates cannot share test code (that would be a dependency cycle), so
//! the *same table* is asserted in both places. Both must change together.

use std::{collections::BTreeMap, ffi::OsString, path::PathBuf};

use substrate_browser_mcp::resolve_root_from;

fn lookup(vars: &[(&str, &str)]) -> impl Fn(&str) -> Option<OsString> {
    let vars: BTreeMap<String, String> = vars
        .iter()
        .map(|(key, value)| ((*key).to_string(), (*value).to_string()))
        .collect();
    move |name: &str| vars.get(name).cloned().map(OsString::from)
}

#[test]
fn root_precedence_matches_brokerd() {
    struct Case<'a> {
        vars: &'a [(&'a str, &'a str)],
        expected: &'a str,
    }

    let cases = [
        Case {
            vars: &[
                ("SUBSTRATE_BROKER_ROOT", "/srv/explicit"),
                ("XDG_STATE_HOME", "/srv/xdg"),
                ("HOME", "/srv/home"),
            ],
            expected: "/srv/explicit",
        },
        Case {
            // The override wins even when it is the only thing set. This is the
            // case that used to diverge: brokerd skipped it entirely.
            vars: &[("SUBSTRATE_BROKER_ROOT", "/srv/explicit")],
            expected: "/srv/explicit",
        },
        Case {
            vars: &[("XDG_STATE_HOME", "/srv/xdg"), ("HOME", "/srv/home")],
            expected: "/srv/xdg/browser-broker",
        },
        Case {
            vars: &[("HOME", "/srv/home")],
            expected: "/srv/home/.local/state/browser-broker",
        },
        Case {
            vars: &[],
            expected: "./.local/state/browser-broker",
        },
    ];

    for case in cases {
        assert_eq!(
            resolve_root_from(lookup(case.vars)),
            PathBuf::from(case.expected),
            "vars: {:?}",
            case.vars
        );
    }
}

/// `default_root` must be the same pure resolution applied to the real
/// environment, not a second code path.
#[test]
fn default_root_uses_the_shared_resolution() {
    let expected = resolve_root_from(|name| std::env::var_os(name));
    assert_eq!(substrate_browser_mcp::default_root(), expected);
}
