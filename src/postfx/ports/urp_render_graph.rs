// SPDX-License-Identifier: MIT OR Apache-2.0
// SPDX-FileCopyrightText: 2026 <REDACTED> <<REDACTED>@gmail.com>

//! URP 17 `RecordRenderGraph` adapter contract.
//!
//! URP 17 (Unity 6) replaces the `OnRenderImage` callback with the
//! `ScriptableRenderPass.RecordRenderGraph` API. This file is the
//! specification of the adapter port trait that the 7 existing passes
//! must implement when migrating from BRP (`OnRenderImage`) to URP 17.
//!
//! # Contract
//!
//! - [`PostFxUrpPass::name`] is a stable profiling/ordering key.
//! - [`PostFxUrpPass::is_enabled`] gates whether the pass is recorded
//!   in the current frame's RenderGraph.
//! - [`PostFxUrpPass::record_render_graph`] records the pass into
//!   the supplied [`PostFxUrpContext`]. Implementations must:
//!   1. Read camera-scoped resources via `ctx` only; do not capture
//!      cross-frame state.
//!   2. Honour `ctx.quality` and the pass's own `is_enabled` gate
//!      (the URP graph is recorded even for disabled passes so the
//!      engine can choose at frame time; the adapter's `is_enabled`
//!      is the authoritative gate).
//!   3. Return a [`PostFxError::BackendUnavailable`] if the URP 17
//!      SDK is not actually loaded in the host process. The trait
//!      uses a typed `Result<()>` so the failure is loud and
//!      attributable, never a silent no-op.
//!
//! # Backend availability
//!
//! The real implementation requires the Unity 6 + URP 17 packages,
//! which are unavailable in this Rust workspace. The
//! [`UrpBackendUnavailable`] marker returned by
//! [`BrpToUrpAdapter::record_render_graph`] makes that dependency
//! explicit and traceable: every code path through the adapter
//! surfaces the named dependency requirement.

use crate::postfx::error::{PostFxError, PostFxResult};
use crate::postfx::ports::post_fx_pass::{PassQuality, PostFxPass};

/// Marker for "URP 17 backend is not loaded in this host process".
///
/// Returned by the in-tree adapter shim so the dependency on the
/// Unity 6 + URP 17 packages is observable at the type level, not
/// hidden behind a silent no-op.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct UrpBackendUnavailable {
    pub backend: &'static str,
    pub required_runtime: &'static str,
}

impl std::fmt::Display for UrpBackendUnavailable {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "URP adapter backend `{}` is not loaded (required runtime: {}); \
             this crate is a Rust port and does not link the Unity SDK",
            self.backend, self.required_runtime
        )
    }
}

impl std::error::Error for UrpBackendUnavailable {}

impl From<UrpBackendUnavailable> for PostFxError {
    fn from(marker: UrpBackendUnavailable) -> Self {
        PostFxError::BackendUnavailable {
            backend: marker.backend,
            required_runtime: marker.required_runtime,
        }
    }
}

/// Hexagonal port: a post-fx pass that can record itself into a URP 17
/// RenderGraph. Each existing BRP pass will gain an adapter implementing
/// this port without changing the BRP-side implementation.
pub trait PostFxUrpPass: Send + Sync {
    /// Stable name of the pass, used for profiling and ordering.
    fn name(&self) -> &str;

    /// Whether the pass should run in the current frame.
    fn is_enabled(&self) -> bool;

    /// Record the pass into the supplied RenderGraph.
    ///
    /// Returns `Ok(())` on success, or [`UrpBackendUnavailable`] if
    /// the URP 17 SDK is not loaded. Real adapters (in the Unity
    /// package) override this and return `Ok(())` after
    /// `CommandBuffer` / `RenderGraphBuilder` calls.
    fn record_render_graph(&self, ctx: &PostFxUrpContext) -> PostFxResult<()>;
}

/// Per-camera context for the URP 17 adapter.
#[derive(Debug, Clone)]
pub struct PostFxUrpContext {
    /// Camera being rendered (opaque handle).
    pub camera: u64,
    /// Per-frame quality level.
    pub quality: PassQuality,
}

impl Default for PostFxUrpContext {
    fn default() -> Self {
        Self {
            camera: 0,
            quality: PassQuality::Off,
        }
    }
}

/// Adapter that bridges an existing [`PostFxPass`] (BRP-side) to the
/// URP 17 `RecordRenderGraph` API.
///
/// The in-tree shim is a *contract*, not an implementation. Calling
/// [`BrpToUrpAdapter::record_render_graph`] always returns
/// [`UrpBackendUnavailable`] because the URP 17 SDK is not loaded in
/// this Rust workspace. The adapter exists so the rest of the BRP
/// pipeline can be ported, the trait can be implemented per-pass,
/// and the missing-backend error is surfaced at every code path that
/// tries to dispatch a URP recording.
pub struct BrpToUrpAdapter<P: PostFxPass> {
    brp_pass: P,
}

impl<P: PostFxPass> BrpToUrpAdapter<P> {
    /// Wrap a BRP pass so it can be added to a URP 17 RenderGraph.
    pub fn new(brp_pass: P) -> Self {
        Self { brp_pass }
    }

    /// Borrow the wrapped BRP pass.
    pub fn brp(&self) -> &P {
        &self.brp_pass
    }
}

impl<P: PostFxPass> PostFxUrpPass for BrpToUrpAdapter<P> {
    fn name(&self) -> &str {
        self.brp_pass.name()
    }

    fn is_enabled(&self) -> bool {
        self.brp_pass.is_enabled()
    }

    fn record_render_graph(&self, _ctx: &PostFxUrpContext) -> PostFxResult<()> {
        // Fail loud: the URP 17 SDK is not loaded in this Rust workspace.
        // Real Unity packages override this method; the in-tree shim must
        // never silently swallow a URP call.
        Err(UrpBackendUnavailable {
            backend: "urp-17",
            required_runtime: "Unity 6 + com.unity.render-pipelines.universal@17.x",
        }
        .into())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::postfx::ports::post_fx_pass::{PassEffect, PostFxContext};

    struct Stub;
    impl PostFxPass for Stub {
        fn name(&self) -> &str {
            "Stub"
        }
        fn effect(&self) -> PassEffect {
            PassEffect::Bloom
        }
        fn cost(&self) -> f32 {
            0.1
        }
        fn is_enabled(&self) -> bool {
            true
        }
        fn set_enabled(&mut self, _: bool) {}
        fn on_setup(&mut self, _: &PostFxContext) -> PostFxResult<()> {
            Ok(())
        }
        fn on_render(&mut self, _: &PostFxContext) -> PostFxResult<()> {
            Ok(())
        }
        fn on_dispose(&mut self) {}
        fn validate_variants(
            &self,
            _: &dyn crate::postfx::ports::shader_availability::PostFxShaderAvailability,
        ) -> Result<(), PostFxError> {
            Ok(())
        }
    }

    #[test]
    fn brp_to_urp_adapter_delegates_metadata() {
        let adapter = BrpToUrpAdapter::new(Stub);
        assert_eq!(adapter.name(), "Stub");
        assert!(adapter.is_enabled());
        assert_eq!(adapter.brp().effect(), PassEffect::Bloom);
    }

    #[test]
    fn record_render_graph_returns_backend_unavailable_marker() {
        let adapter = BrpToUrpAdapter::new(Stub);
        let result = adapter.record_render_graph(&PostFxUrpContext::default());

        let err = result.expect_err("URP backend must be unavailable in the Rust shim");
        match err {
            PostFxError::BackendUnavailable {
                backend,
                required_runtime,
            } => {
                assert_eq!(backend, "urp-17");
                assert!(required_runtime.contains("Unity 6"));
            }
            other => panic!("expected BackendUnavailable, got {other:?}"),
        }
    }

    #[test]
    fn urp_backend_unavailable_display_is_diagnostic() {
        let marker = UrpBackendUnavailable {
            backend: "urp-17",
            required_runtime: "Unity 6",
        };
        let text = marker.to_string();
        assert!(text.contains("urp-17"));
        assert!(text.contains("Unity 6"));
    }

    #[test]
    fn post_fx_urp_context_default() {
        let ctx = PostFxUrpContext::default();
        assert_eq!(ctx.camera, 0);
        assert_eq!(ctx.quality, PassQuality::Off);
    }
}
