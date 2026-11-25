//! Lease holder that never releases, for the cross-process reclaim test.
//!
//! Grants a lease on `principal/profile` under a broker-shaped root
//! (`root/leases`), prints one JSON line describing what it holds, then blocks
//! forever. It installs no signal handler and performs no cleanup on drop, so a
//! SIGKILL leaves the lease record on disk with a dead `owner_pid` -- exactly
//! the state [`substrate_browser::LeaseManager::reap_dead`] must reclaim.
//!
//! Usage: `reclaim_holder <root> <principal> <profile> <ttl_ms>`

use std::{io::Write, time::Duration};

use substrate_browser::{LeaseManager, Scope};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.len() != 4 {
        eprintln!("usage: reclaim_holder <root> <principal> <profile> <ttl_ms>");
        std::process::exit(2);
    }
    let root = std::path::PathBuf::from(&args[0]);
    let principal = args[1].clone();
    let profile = args[2].clone();
    let ttl_ms: u64 = args[3].parse()?;

    // Same layout as `Broker::new`: the lease store lives under `root/leases`.
    let leases = LeaseManager::new(root.join("leases"))?;
    let scope = Scope::new(principal, profile, "holder")?;
    let holder = format!("reclaim-holder-{}", std::process::id());
    let lease = leases.grant(&scope, holder, Duration::from_millis(ttl_ms))?;

    let lease_file = root
        .join("leases")
        .join("leases")
        .join(format!("{}.json", lease.id));

    // A single line, flushed immediately: the test polls for it and nothing else.
    println!(
        "{{\"lease\":\"{}\",\"fence\":{},\"pid\":{},\"lease_file\":\"{}\"}}",
        lease.id,
        lease.fencing_token,
        std::process::id(),
        lease_file.display()
    );
    std::io::stdout().flush()?;

    // Hold the lease and never release it. SIGKILL ends this; no drop runs.
    loop {
        std::thread::sleep(Duration::from_secs(1));
    }
}
