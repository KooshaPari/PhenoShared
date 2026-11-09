//! Lease authority: one writer per browser profile, with TTL and fencing.
//!
//! A lease is the only thing that authorises mutating work on a profile. It is
//! granted with a TTL, carries a monotonic *fencing token* per profile, and must
//! be presented and validated before each mutating action. A holder whose lease
//! expired, or whose token was superseded by a later grant, is rejected even if
//! it still holds a stale copy of the lease record.

use std::{
    fs,
    path::{Path, PathBuf},
    sync::{
        atomic::{AtomicU64, Ordering},
        Arc,
    },
    time::Duration,
};

use fs2::FileExt;
use serde::{Deserialize, Serialize};

use crate::{
    fsutil::{ensure_private_dir, now_unix_ms, read_json, write_json_atomic},
    procutil::{pid_is_alive, process_start_identity},
    BrowserError, Result, Scope,
};

/// Source of wall-clock time, injectable so lease expiry is testable.
pub trait Clock: Send + Sync {
    /// Milliseconds since the Unix epoch.
    fn now_unix_ms(&self) -> u64;
}

/// Real system clock.
#[derive(Debug, Default, Clone, Copy)]
pub struct SystemClock;

impl Clock for SystemClock {
    fn now_unix_ms(&self) -> u64 {
        now_unix_ms()
    }
}

/// Answers "is this profile currently leased by somebody?".
///
/// [`ProfileStore`](crate::ProfileStore) consults this before mutating a profile
/// so a generation cannot be promoted or deleted out from under a live holder.
pub trait LeaseGate: Send + Sync {
    /// Return `true` when an unexpired lease exists for this profile.
    fn has_active_lease(&self, principal: &str, profile: &str) -> Result<bool>;
}

/// A granted, time-bounded claim on one profile.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Lease {
    /// Opaque lease identifier.
    pub id: String,
    /// Principal that owns the profile.
    pub principal: String,
    /// Profile being driven.
    pub profile: String,
    /// Logical session driving it.
    pub session: String,
    /// Tab, when the caller pinned one.
    pub tab: Option<String>,
    /// Human- or agent-readable holder label.
    pub holder: String,
    /// Monotonic per-profile fencing token.
    pub fencing_token: u64,
    /// Issue time, milliseconds since the Unix epoch.
    pub issued_at_unix_ms: u64,
    /// Expiry time, milliseconds since the Unix epoch.
    pub expires_at_unix_ms: u64,
    /// Operating system process that holds this lease.
    ///
    /// Defaulted so records written before this field existed still parse;
    /// such records are never reaped, which fails closed.
    #[serde(default)]
    pub owner_pid: u32,
    /// Start-time identity of the process instance named by `owner_pid`,
    /// recorded when the lease was granted (see [`process_start_identity`]).
    ///
    /// `owner_pid` alone is not an identity: the kernel recycles pids, so a
    /// stale record can point at an unrelated live process and pin the profile
    /// until its TTL expires. This field makes the liveness check
    /// instance-aware. It is `None` for records written by an older build, and
    /// such records keep the conservative pid-only behaviour.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub owner_started_at: Option<String>,
}

impl Lease {
    /// Remaining lifetime in milliseconds, saturating at zero.
    pub fn remaining_ms(&self, now_unix_ms: u64) -> u64 {
        self.expires_at_unix_ms.saturating_sub(now_unix_ms)
    }

    /// `principal/profile`, the exclusivity key.
    pub fn profile_key(&self) -> String {
        format!("{}/{}", self.principal, self.profile)
    }
}

#[derive(Debug, Default, Serialize, Deserialize)]
struct Fences(std::collections::BTreeMap<String, u64>);

/// Whether the process instance that owns `lease` is gone.
///
/// Gone means the pid no longer exists, *or* the pid exists but now names a
/// different process instance than the one the lease was granted to (a
/// recycled pid). A live pid whose identity cannot be read - an old record with
/// no `owner_started_at`, or a platform without a start-time primitive - is
/// treated as the original owner, so nothing is reaped on a guess.
fn owner_is_gone(lease: &Lease) -> bool {
    if lease.owner_pid == 0 || !pid_is_alive(lease.owner_pid) {
        return true;
    }
    let Some(recorded) = lease.owner_started_at.as_deref() else {
        return false;
    };
    match process_start_identity(lease.owner_pid) {
        Some(current) => current != recorded,
        None => false,
    }
}

static SEQUENCE: AtomicU64 = AtomicU64::new(0);

fn unique_id() -> String {
    let seq = SEQUENCE.fetch_add(1, Ordering::Relaxed);
    // The atomic counter is process-local, so include the pid: two processes
    // issuing a lease in the same millisecond would otherwise collide.
    format!("lease-{:x}-{}-{:x}", now_unix_ms(), std::process::id(), seq)
}

/// Grants, renews, revokes and validates profile leases.
#[derive(Clone)]
pub struct LeaseManager {
    root: PathBuf,
    clock: Arc<dyn Clock>,
}

impl std::fmt::Debug for LeaseManager {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("LeaseManager")
            .field("root", &self.root)
            .finish_non_exhaustive()
    }
}

impl LeaseManager {
    /// Open (or create) a lease store rooted at `root`.
    pub fn new(root: impl Into<PathBuf>) -> Result<Self> {
        Self::with_clock(root, Arc::new(SystemClock))
    }

    /// Open a lease store with an injected clock.
    pub fn with_clock(root: impl Into<PathBuf>, clock: Arc<dyn Clock>) -> Result<Self> {
        let root = root.into();
        ensure_private_dir(&root)?;
        ensure_private_dir(&root.join("leases"))?;
        Ok(Self { root, clock })
    }

    fn leases_dir(&self) -> PathBuf {
        self.root.join("leases")
    }

    fn fence_path(&self) -> PathBuf {
        self.root.join("fences.json")
    }

    fn lock_path(&self) -> PathBuf {
        self.root.join("leases.lock")
    }

    /// Run `body` while holding the cross-process store lock.
    fn with_lock<T>(&self, body: impl FnOnce() -> Result<T>) -> Result<T> {
        let file = fs::OpenOptions::new()
            .create(true)
            .read(true)
            .write(true)
            .truncate(false)
            .open(self.lock_path())?;
        file.lock_exclusive()?;
        let outcome = body();
        let _ = FileExt::unlock(&file);
        outcome
    }

    fn read_lease(&self, id: &str) -> Result<Lease> {
        let path = self.leases_dir().join(format!("{id}.json"));
        read_json::<Lease>(&path)?.ok_or_else(|| BrowserError::UnknownLease(id.to_string()))
    }

    fn write_lease(&self, lease: &Lease) -> Result<()> {
        write_json_atomic(&self.leases_dir().join(format!("{}.json", lease.id)), lease)
    }

    fn all_leases(&self) -> Result<Vec<Lease>> {
        let mut out = Vec::new();
        let dir = self.leases_dir();
        if !dir.exists() {
            return Ok(out);
        }
        for entry in fs::read_dir(&dir)? {
            let entry = entry?;
            let path = entry.path();
            if path.extension().and_then(|e| e.to_str()) != Some("json") {
                continue;
            }
            if let Some(lease) = read_json::<Lease>(&path)? {
                out.push(lease);
            }
        }
        Ok(out)
    }

    fn next_fence(&self, profile_key: &str) -> Result<u64> {
        let mut fences: Fences = read_json(&self.fence_path())?.unwrap_or_default();
        let next = fences.0.get(profile_key).copied().unwrap_or(0) + 1;
        fences.0.insert(profile_key.to_string(), next);
        write_json_atomic(&self.fence_path(), &fences)?;
        Ok(next)
    }

    fn current_fence(&self, profile_key: &str) -> Result<u64> {
        let fences: Fences = read_json(&self.fence_path())?.unwrap_or_default();
        Ok(fences.0.get(profile_key).copied().unwrap_or(0))
    }

    /// Grant a lease on the scope's profile, refusing if it is already held.
    ///
    /// Exclusivity is enforced per `principal/profile`, not per session or tab:
    /// a browser profile is one storage jar, so two holders on the same profile
    /// would share cookies regardless of which window they drive.
    pub fn grant(&self, scope: &Scope, holder: impl Into<String>, ttl: Duration) -> Result<Lease> {
        let holder = holder.into();
        let ttl_ms = u64::try_from(ttl.as_millis()).unwrap_or(u64::MAX).max(1);
        self.with_lock(|| {
            self.sweep_expired_locked()?;
            let key = scope.profile_key();
            let now = self.clock.now_unix_ms();
            if let Some(existing) = self.active_for_locked(&key, now)? {
                return Err(BrowserError::Refused(format!(
                    "profile {key} is already leased to `{}` until {}",
                    existing.holder, existing.expires_at_unix_ms
                )));
            }
            let lease = Lease {
                id: unique_id(),
                principal: scope.principal().to_string(),
                profile: scope.profile().to_string(),
                session: scope.session().to_string(),
                tab: scope.tab().map(str::to_string),
                holder,
                fencing_token: self.next_fence(&key)?,
                issued_at_unix_ms: now,
                expires_at_unix_ms: now.saturating_add(ttl_ms),
                owner_pid: std::process::id(),
                owner_started_at: process_start_identity(std::process::id()),
            };
            self.write_lease(&lease)?;
            Ok(lease)
        })
    }

    /// Extend a lease. Fails if it already expired or was revoked.
    pub fn renew(&self, id: &str, ttl: Duration) -> Result<Lease> {
        let ttl_ms = u64::try_from(ttl.as_millis()).unwrap_or(u64::MAX).max(1);
        self.with_lock(|| {
            let mut lease = self.read_lease(id)?;
            let now = self.clock.now_unix_ms();
            if lease.expires_at_unix_ms <= now {
                return Err(BrowserError::LeaseUnusable {
                    id: lease.id.clone(),
                    reason: "expired".to_string(),
                });
            }
            if self.current_fence(&lease.profile_key())? > lease.fencing_token {
                return Err(BrowserError::LeaseUnusable {
                    id: lease.id.clone(),
                    reason: "superseded by a later grant".to_string(),
                });
            }
            lease.expires_at_unix_ms = now.saturating_add(ttl_ms);
            self.write_lease(&lease)?;
            Ok(lease)
        })
    }

    /// Revoke a lease immediately. The fence keeps advancing, so the old holder
    /// cannot resume by re-reading its stale record.
    pub fn revoke(&self, id: &str) -> Result<()> {
        self.with_lock(|| {
            let path = self.leases_dir().join(format!("{id}.json"));
            match fs::remove_file(&path) {
                Ok(()) => Ok(()),
                Err(err) if err.kind() == std::io::ErrorKind::NotFound => {
                    Err(BrowserError::UnknownLease(id.to_string()))
                },
                Err(err) => Err(err.into()),
            }
        })
    }

    /// Validate that `fencing_token` still authorises work under lease `id`.
    pub fn validate(&self, id: &str, fencing_token: u64) -> Result<Lease> {
        // Read the lease and the fence under one lock: a revoke or a newer grant
        // landing between the two reads would otherwise let a stale token pass.
        self.with_lock(|| self.validate_locked(id, fencing_token))
    }

    fn validate_locked(&self, id: &str, fencing_token: u64) -> Result<Lease> {
        let lease = self.read_lease(id)?;
        let now = self.clock.now_unix_ms();
        if lease.expires_at_unix_ms <= now {
            return Err(BrowserError::LeaseUnusable {
                id: lease.id.clone(),
                reason: "expired".to_string(),
            });
        }
        let current = self.current_fence(&lease.profile_key())?;
        if fencing_token != lease.fencing_token || current > lease.fencing_token {
            return Err(BrowserError::StaleFence {
                id: lease.id.clone(),
                presented: fencing_token,
                current,
            });
        }
        Ok(lease)
    }

    /// Remove leases whose owning process instance is gone.
    ///
    /// A broker that crashes leaves its record behind, which would block the
    /// profile until the TTL elapsed. An owner is gone when its pid no longer
    /// exists, or when the pid now belongs to a different process (a recycled
    /// pid must not keep a dead holder's claim alive). A lease held by the
    /// process it was granted to is never touched.
    ///
    /// Returns how many records were removed. On platforms without a pid
    /// liveness primitive this is a no-op and returns 0: reaping is then bounded
    /// by [`LeaseManager::sweep_expired`] alone. Records written before
    /// `owner_started_at` existed are still reaped when their pid is dead.
    pub fn reap_dead(&self) -> Result<usize> {
        self.with_lock(|| {
            let mut reaped = 0;
            for lease in self.all_leases()? {
                if !owner_is_gone(&lease) {
                    continue;
                }
                let path = self.leases_dir().join(format!("{}.json", lease.id));
                if fs::remove_file(path).is_ok() {
                    reaped += 1;
                }
            }
            Ok(reaped)
        })
    }

    /// Remove expired leases and return how many were reaped.
    pub fn sweep_expired(&self) -> Result<usize> {
        self.with_lock(|| self.sweep_expired_locked())
    }

    fn sweep_expired_locked(&self) -> Result<usize> {
        let now = self.clock.now_unix_ms();
        let mut reaped = 0;
        for lease in self.all_leases()? {
            if lease.expires_at_unix_ms <= now {
                let path = self.leases_dir().join(format!("{}.json", lease.id));
                if fs::remove_file(path).is_ok() {
                    reaped += 1;
                }
            }
        }
        Ok(reaped)
    }

    /// The unexpired lease held on `principal/profile`, if any.
    pub fn active_for(&self, principal: &str, profile: &str) -> Result<Option<Lease>> {
        let key = format!("{principal}/{profile}");
        self.active_for_locked(&key, self.clock.now_unix_ms())
    }

    fn active_for_locked(&self, profile_key: &str, now: u64) -> Result<Option<Lease>> {
        let mut found: Option<Lease> = None;
        for lease in self.all_leases()? {
            if lease.profile_key() != profile_key || lease.expires_at_unix_ms <= now {
                continue;
            }
            // Deterministic tie-break: the newest fence wins.
            match &found {
                Some(current) if current.fencing_token >= lease.fencing_token => {},
                _ => found = Some(lease),
            }
        }
        Ok(found)
    }

    /// Every lease record currently on disk, expired or not.
    pub fn list(&self) -> Result<Vec<Lease>> {
        self.all_leases()
    }

    /// Root directory of the lease store.
    pub fn root(&self) -> &Path {
        &self.root
    }
}

impl LeaseGate for LeaseManager {
    fn has_active_lease(&self, principal: &str, profile: &str) -> Result<bool> {
        Ok(self.active_for(principal, profile)?.is_some())
    }
}
