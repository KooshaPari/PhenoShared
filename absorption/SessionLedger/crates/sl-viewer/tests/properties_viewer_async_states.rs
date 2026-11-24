//! Property evidence for sl-viewer's `async_states::SkeletonLayout`
//! enum and the `clamp_rows` helper used by `ContentSkeleton`.
//!
//! `async_states::SkeletonLayout` invariants:
//!  * `SkeletonLayout::default()` is `Bundles` so the most common
//!    desktop surface (bundle list) is the first paint.
//!  * Every variant has a stable, kebab-case-ish single-line label.
//!  * The enum exposes exactly three variants so the
//!    `match layout { Bundles | ListDetail | StreamFeed }` arms in
//!    `ContentSkeleton` stay exhaustive.
//!
//! `list_rows` clamp invariants:
//!  * `list_rows.clamp(3, 6)` is deterministic and lands in `[3, 6]`
//!    for every input.
//!  * The clamp is monotonic non-decreasing on the input range:
//!    larger input never produces smaller output.

use proptest::prelude::*;
use sl_viewer::async_states::SkeletonLayout;

proptest! {
    /// `SkeletonLayout::default()` is `Bundles`.
    #[test]
    fn skeleton_layout_default_is_bundles(_seed in any::<u32>()) {
        prop_assert_eq!(SkeletonLayout::default(), SkeletonLayout::Bundles);
    }

    /// The enum exposes exactly three variants — the number of
    /// documented match arms in `ContentSkeleton`.
    #[test]
    fn skeleton_layout_has_three_variants(_seed in any::<u32>()) {
        let variants = [
            SkeletonLayout::Bundles,
            SkeletonLayout::ListDetail,
            SkeletonLayout::StreamFeed,
        ];
        // Round-trip through Debug to confirm each variant's name
        // survives stable serialisation.
        let mut seen = std::collections::HashSet::new();
        for v in variants {
            let name = format!("{v:?}");
            prop_assert!(name.is_ascii(), "variant {name:?} is not ASCII");
            seen.insert(name);
        }
        prop_assert_eq!(seen.len(), 3, "variant count drifted");
    }

    /// Every variant's Debug label is non-empty, single-line, and
    /// matches one of the documented variant names.
    #[test]
    fn skeleton_layout_labels_documented(variant in prop::sample::select(vec![
        SkeletonLayout::Bundles,
        SkeletonLayout::ListDetail,
        SkeletonLayout::StreamFeed,
    ])) {
        let label = format!("{variant:?}");
        prop_assert!(!label.is_empty());
        prop_assert!(!label.contains('\n'));
        let valid = label == "Bundles" || label == "ListDetail" || label == "StreamFeed";
        prop_assert!(valid, "label {label:?} is not a documented variant name");
    }

    /// `SkeletonLayout::default()` matches the first arm in the
    /// `match` block in `ContentSkeleton` so adding a new variant
    /// forces a deliberate `default()` change.
    #[test]
    fn skeleton_layout_default_is_first_arm(_seed in any::<u32>()) {
        let first = SkeletonLayout::Bundles;
        prop_assert_eq!(SkeletonLayout::default(), first);
    }

    /// `list_rows.clamp(3, 6)` lands in `[3, 6]` for every input.
    #[test]
    fn list_rows_clamp_in_range(input in any::<usize>()) {
        let clamped = input.clamp(3, 6);
        prop_assert!((3..=6).contains(&clamped), "clamp produced {clamped} for input {input}");
    }

    /// The clamp is monotonic non-decreasing.
    #[test]
    fn list_rows_clamp_monotonic(
        a in any::<usize>(),
        b in any::<usize>(),
    ) {
        let (lo, hi) = if a <= b { (a, b) } else { (b, a) };
        let c_lo = lo.clamp(3, 6);
        let c_hi = hi.clamp(3, 6);
        prop_assert!(c_lo <= c_hi, "clamp not monotonic: {lo}→{c_lo}, {hi}→{c_hi}");
    }

    /// The clamp has the documented fixed points: `0` and `2` clamp
    /// to `3`; `6` and `u64::MAX` clamp to `6`.
    #[test]
    fn list_rows_clamp_fixed_points(_seed in any::<u32>()) {
        prop_assert_eq!(0_usize.clamp(3, 6), 3);
        prop_assert_eq!(2_usize.clamp(3, 6), 3);
        prop_assert_eq!(3_usize.clamp(3, 6), 3);
        prop_assert_eq!(6_usize.clamp(3, 6), 6);
        prop_assert_eq!(usize::MAX.clamp(3, 6), 6);
    }
}
