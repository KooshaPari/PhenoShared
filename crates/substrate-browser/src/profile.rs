//! Profile store: named per-principal browser profiles made of immutable generations.
//!
//! A profile is a directory tree holding one browser data directory per
//! *generation*. Exactly one generation is `active` and the switch is a
//! compare-and-swap against the value the caller last observed, so two actors
//! cannot both believe they promoted a generation.
//!
//! A generation is only forkable once it is `sealed`, which means "no live
//! process has this data directory open". Forking copies the tree; it never
//! merges two browser databases, because a browser profile has no merge
//! semantics that preserve authenticated state.

use std::{
    fs,
    path::{Path, PathBuf},
    sync::Arc,
};

use serde::{Deserialize, Serialize};

use crate::{
    fsutil::{copy_tree, ensure_private_dir, read_json, write_json_atomic},
    BrowserError, Clock, LeaseGate, Result, SystemClock,
};

/// One immutable snapshot of a profile's browser data directory.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Generation {
    /// Monotonic generation number within the profile, starting at 1.
    pub id: u64,
    /// Generation this one was forked from, if any.
    pub parent: Option<u64>,
    /// A sealed generation has no live reader and may be forked.
    pub sealed: bool,
    /// Creation time, milliseconds since the Unix epoch.
    pub created_at_unix_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct Manifest {
    next_id: u64,
    active: Option<u64>,
    generations: Vec<Generation>,
}

impl Default for Manifest {
    fn default() -> Self {
        Self {
            next_id: 1,
            active: None,
            generations: Vec::new(),
        }
    }
}

impl Manifest {
    fn get(&self, id: u64) -> Option<&Generation> {
        self.generations.iter().find(|g| g.id == id)
    }

    fn get_mut(&mut self, id: u64) -> Option<&mut Generation> {
        self.generations.iter_mut().find(|g| g.id == id)
    }
}

/// Store of per-principal browser profiles.
#[derive(Clone)]
pub struct ProfileStore {
    root: PathBuf,
    gate: Option<Arc<dyn LeaseGate>>,
    clock: Arc<dyn Clock>,
}

impl std::fmt::Debug for ProfileStore {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("ProfileStore")
            .field("root", &self.root)
            .field("gated", &self.gate.is_some())
            .finish_non_exhaustive()
    }
}

impl ProfileStore {
    /// Open a store rooted at `root` without lease enforcement.
    ///
    /// Intended for setup paths and tests. Production callers must use
    /// [`ProfileStore::with_gate`].
    pub fn new(root: impl Into<PathBuf>) -> Result<Self> {
        Self::build(root.into(), None, Arc::new(SystemClock))
    }

    /// Open a store rooted at `root` that refuses profile mutations while a
    /// lease is held on that profile.
    pub fn with_gate(root: impl Into<PathBuf>, gate: Arc<dyn LeaseGate>) -> Result<Self> {
        Self::build(root.into(), Some(gate), Arc::new(SystemClock))
    }

    /// Open a store with both a lease gate and an injected clock.
    pub fn with_gate_and_clock(
        root: impl Into<PathBuf>,
        gate: Arc<dyn LeaseGate>,
        clock: Arc<dyn Clock>,
    ) -> Result<Self> {
        Self::build(root.into(), Some(gate), clock)
    }

    fn build(
        root: PathBuf,
        gate: Option<Arc<dyn LeaseGate>>,
        clock: Arc<dyn Clock>,
    ) -> Result<Self> {
        ensure_private_dir(&root)?;
        ensure_private_dir(&root.join("profiles"))?;
        Ok(Self { root, gate, clock })
    }

    /// Root directory of the store.
    pub fn root(&self) -> &Path {
        &self.root
    }

    /// Directory holding one profile's manifest and generations.
    pub fn profile_dir(&self, principal: &str, profile: &str) -> PathBuf {
        self.root.join("profiles").join(principal).join(profile)
    }

    /// Data directory for one generation; this is the value to hand a browser
    /// as its `--user-data-dir` / profile path.
    pub fn data_dir(&self, principal: &str, profile: &str, generation: u64) -> PathBuf {
        self.profile_dir(principal, profile)
            .join(format!("gen-{generation}"))
    }

    fn manifest_path(&self, principal: &str, profile: &str) -> PathBuf {
        self.profile_dir(principal, profile).join("manifest.json")
    }

    fn load(&self, principal: &str, profile: &str) -> Result<Manifest> {
        Ok(read_json(&self.manifest_path(principal, profile))?.unwrap_or_default())
    }

    fn store(&self, principal: &str, profile: &str, manifest: &Manifest) -> Result<()> {
        write_json_atomic(&self.manifest_path(principal, profile), manifest)
    }

    fn refuse_if_leased(&self, principal: &str, profile: &str) -> Result<()> {
        if let Some(gate) = &self.gate {
            if gate.has_active_lease(principal, profile)? {
                return Err(BrowserError::Refused(format!(
                    "profile {principal}/{profile} is leased; release the lease before \
                     changing its generations"
                )));
            }
        }
        Ok(())
    }

    fn create_generation(
        &self,
        principal: &str,
        profile: &str,
        parent: Option<u64>,
        seed_from: Option<u64>,
        activate: bool,
    ) -> Result<u64> {
        let mut manifest = self.load(principal, profile)?;
        let id = manifest.next_id.max(1);
        let dir = self.data_dir(principal, profile, id);
        match seed_from {
            Some(source) => copy_tree(&self.data_dir(principal, profile, source), &dir)?,
            None => ensure_private_dir(&dir)?,
        }
        manifest.next_id = id + 1;
        manifest.generations.push(Generation {
            id,
            parent,
            sealed: false,
            created_at_unix_ms: self.clock.now_unix_ms(),
        });
        if activate || manifest.active.is_none() {
            manifest.active = Some(id);
        }
        self.store(principal, profile, &manifest)?;
        Ok(id)
    }

    /// Ensure a profile exists and return its active generation.
    ///
    /// Creates generation 1 on first use. Idempotent.
    pub fn ensure(&self, principal: &str, profile: &str) -> Result<u64> {
        if let Some(active) = self.active(principal, profile)? {
            return Ok(active);
        }
        self.create_generation(principal, profile, None, None, true)
    }

    /// The active generation, if the profile exists.
    pub fn active(&self, principal: &str, profile: &str) -> Result<Option<u64>> {
        Ok(self.load(principal, profile)?.active)
    }

    /// Every generation recorded for the profile.
    pub fn generations(&self, principal: &str, profile: &str) -> Result<Vec<Generation>> {
        Ok(self.load(principal, profile)?.generations)
    }

    /// Create a new empty generation and make it active.
    pub fn rotate(&self, principal: &str, profile: &str) -> Result<u64> {
        self.refuse_if_leased(principal, profile)?;
        self.create_generation(principal, profile, None, None, true)
    }

    /// Mark a generation sealed so it may be forked.
    ///
    /// Sealing is refused while the profile is leased, because a live holder
    /// still has the data directory open.
    pub fn seal(&self, principal: &str, profile: &str, generation: u64) -> Result<()> {
        self.refuse_if_leased(principal, profile)?;
        let mut manifest = self.load(principal, profile)?;
        let entry =
            manifest
                .get_mut(generation)
                .ok_or_else(|| BrowserError::UnknownGeneration {
                    principal: principal.to_string(),
                    profile: profile.to_string(),
                    generation,
                })?;
        entry.sealed = true;
        self.store(principal, profile, &manifest)
    }

    /// Fork a sealed generation into a new, unsealed, inactive generation.
    ///
    /// The active generation is left untouched, so the caller decides when to
    /// promote the fork.
    pub fn fork(&self, principal: &str, profile: &str, from: u64) -> Result<u64> {
        self.refuse_if_leased(principal, profile)?;
        let manifest = self.load(principal, profile)?;
        let source = manifest
            .get(from)
            .ok_or_else(|| BrowserError::UnknownGeneration {
                principal: principal.to_string(),
                profile: profile.to_string(),
                generation: from,
            })?;
        if !source.sealed {
            return Err(BrowserError::Refused(format!(
                "generation {from} is not sealed; seal it (no live reader) before forking"
            )));
        }
        self.create_generation(principal, profile, Some(from), Some(from), false)
    }

    /// Promote `generation` to active, but only if `expected_active` is still
    /// what the caller last observed.
    pub fn promote(
        &self,
        principal: &str,
        profile: &str,
        generation: u64,
        expected_active: Option<u64>,
    ) -> Result<()> {
        self.refuse_if_leased(principal, profile)?;
        let mut manifest = self.load(principal, profile)?;
        if manifest.active != expected_active {
            return Err(BrowserError::PromotionConflict {
                expected: expected_active.unwrap_or(0),
                actual: manifest.active,
            });
        }
        if manifest.get(generation).is_none() {
            return Err(BrowserError::UnknownGeneration {
                principal: principal.to_string(),
                profile: profile.to_string(),
                generation,
            });
        }
        manifest.active = Some(generation);
        self.store(principal, profile, &manifest)
    }

    /// Delete a generation and its data directory.
    ///
    /// Refused for the active generation, for a leased profile, and for the last
    /// remaining generation, so a profile can never end up with no data.
    pub fn remove(&self, principal: &str, profile: &str, generation: u64) -> Result<()> {
        self.refuse_if_leased(principal, profile)?;
        let mut manifest = self.load(principal, profile)?;
        if manifest.get(generation).is_none() {
            return Err(BrowserError::UnknownGeneration {
                principal: principal.to_string(),
                profile: profile.to_string(),
                generation,
            });
        }
        if manifest.active == Some(generation) {
            return Err(BrowserError::Refused(format!(
                "generation {generation} is active; promote another generation first"
            )));
        }
        if manifest.generations.len() <= 1 {
            return Err(BrowserError::Refused(
                "refusing to delete the only generation of a profile".to_string(),
            ));
        }
        manifest.generations.retain(|g| g.id != generation);
        let dir = self.data_dir(principal, profile, generation);
        match fs::remove_dir_all(&dir) {
            Ok(()) => {},
            Err(err) if err.kind() == std::io::ErrorKind::NotFound => {},
            Err(err) => return Err(err.into()),
        }
        self.store(principal, profile, &manifest)
    }
}

/// Convenience: the data directory of the profile's active generation.
impl ProfileStore {
    /// Resolve the active generation and return its data directory.
    pub fn active_data_dir(&self, principal: &str, profile: &str) -> Result<PathBuf> {
        let generation =
            self.active(principal, profile)?
                .ok_or_else(|| BrowserError::UnknownGeneration {
                    principal: principal.to_string(),
                    profile: profile.to_string(),
                    generation: 0,
                })?;
        Ok(self.data_dir(principal, profile, generation))
    }
}
