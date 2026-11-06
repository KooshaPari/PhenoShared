//! Cross-process soak worker for the lease and profile authority.
//!
//! Run several copies of this against one state directory. Each worker
//! repeatedly tries to acquire an exclusive lease on the same profile, holds it
//! briefly, validates its fencing token, and releases. Contention and expiry
//! races are the point: the driver checks afterwards that no two workers ever
//! held the profile at the same time.
//!
//! Usage: `soak_worker <root> <principal> <profile> <iterations> <hold_ms> <ttl_ms>`

use std::{sync::Arc, time::Duration};

use substrate_browser::{LeaseManager, ProfileStore, Scope};

fn now_unix_ms() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| u64::try_from(d.as_millis()).unwrap_or(u64::MAX))
        .unwrap_or(0)
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.len() != 6 {
        eprintln!("usage: soak_worker <root> <principal> <profile> <iters> <hold_ms> <ttl_ms>");
        std::process::exit(2);
    }
    let root = std::path::PathBuf::from(&args[0]);
    let principal = args[1].clone();
    let profile = args[2].clone();
    let iterations: u64 = args[3].parse()?;
    let hold_ms: u64 = args[4].parse()?;
    let ttl_ms: u64 = args[5].parse()?;

    let leases = Arc::new(LeaseManager::new(root.join("leases"))?);
    // Mirror Broker::new: the store owns the root and creates profiles/ itself.
    let store = ProfileStore::with_gate(root.clone(), leases.clone())?;
    // Seed the profile so generation bookkeeping is exercised too.
    store.ensure(&principal, &profile)?;

    let holder = format!("soak-{}", std::process::id());
    let scope = Scope::new(principal.clone(), profile.clone(), "soak")?;
    let ttl = Duration::from_millis(ttl_ms);

    let mut granted = 0u64;
    let mut refused = 0u64;
    let mut stale = 0u64;

    for _ in 0..iterations {
        match leases.grant(&scope, holder.clone(), ttl) {
            Ok(lease) => {
                let start = now_unix_ms();
                std::thread::sleep(Duration::from_millis(hold_ms));
                let validated = leases.validate(&lease.id, lease.fencing_token);
                let end = now_unix_ms();
                if validated.is_ok() {
                    granted += 1;
                } else {
                    // Expired or superseded mid-hold: expected under a tight TTL.
                    stale += 1;
                }
                println!(
                    "{{\"holder\":\"{}\",\"lease\":\"{}\",\"fence\":{},\"start\":{},\"end\":{},\"valid\":{}}}",
                    holder,
                    lease.id,
                    lease.fencing_token,
                    start,
                    end,
                    validated.is_ok()
                );
                let _ = leases.revoke(&lease.id);
            },
            Err(_) => {
                refused += 1;
            },
        }
    }

    eprintln!(
        "{{\"worker\":\"{holder}\",\"granted\":{granted},\"refused\":{refused},\"stale\":{stale}}}"
    );
    Ok(())
}
