# focus-entitlements

Subscription tier management and feature gates for FocalPoint.

## Overview

This crate provides the single source of truth for subscription semantics across FocalPoint. Every feature gate (rule limits, connector cadence, voice synthesis, analytics tier, etc.) is evaluated here, ensuring:

- iOS app (Swift) and Rust backend agree on entitlements
- Consistent gate enforcement everywhere (no inconsistencies between platforms)
- Easy auditing of tier-to-feature mappings

## Tier Structure

```
Free       → No cost, forever. 3 rules, 3 tasks, 1 connector, fixed sessions.
Plus       → $4.99/mo. Unlimited rules/tasks, all 4 connectors, custom sessions, voice, sync.
Pro        → $9.99/mo. Plus + premium voice, analytics, marketplace, proactive nudges.
Family     → $14.99/mo. Pro + family dashboard, up to 5 members.
```

## Feature Gates

| Feature | Free | Plus | Pro | Family |
|---------|------|------|-----|--------|
| Max rules | 3 | ∞ | ∞ | ∞ |
| Max tasks | 3 | ∞ | ∞ | ∞ |
| Connector cadence | 4h | 15m | 15m | 15m |
| Max connectors | 1 | 4 | 4 | 4 |
| Custom sessions | ✗ | ✓ | ✓ | ✓ |
| Voice (Coachy) | Silent | Native | ElevenLabs | ElevenLabs |
| Live Activity | ✗ | ✓ | ✓ | ✓ |
| CloudKit sync | ✗ | ✓ | ✓ | ✓ |
| Audit retention | 7d | 90d | 180d | 365d |
| Analytics | ✗ | Basic | Advanced | Advanced |
| Proactive nudges | ✗ | ✗ | ✓ | ✓ |
| Custom cosmetics | ✗ | ✗ | ✓ | ✓ |
| Template marketplace | ✗ | ✗ | ✓ | ✓ |
| Family dashboard | ✗ | ✗ | ✗ | ✓ |

## API

### Core Types

```rust
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Tier {
    Free, Plus, Pro, Family,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Entitlement {
    pub tier: Tier,
    pub expires_at: Option<DateTime<Utc>>,
    pub receipt_signature: Option<String>,
}
```

### Feature Gate Functions

Each gate returns `GateResult<T>` (success or `GateError::LimitExceeded`):

```rust
pub fn can_add_rule(current_count: u32, entitlement: &Entitlement) -> GateResult<bool>
pub fn can_add_task(current_count: u32, entitlement: &Entitlement) -> GateResult<bool>
pub fn connector_refresh_cadence_minutes(entitlement: &Entitlement) -> u32
pub fn max_active_connectors(entitlement: &Entitlement) -> u32
pub fn validate_focus_duration(minutes: u32, entitlement: &Entitlement) -> GateResult<()>
pub fn validate_break_duration(minutes: u32, entitlement: &Entitlement) -> GateResult<()>
pub fn voice_provider(entitlement: &Entitlement) -> VoiceProvider
pub fn can_use_live_activity(entitlement: &Entitlement) -> bool
pub fn can_use_homekit_widget(entitlement: &Entitlement) -> bool
pub fn audit_retention_days(entitlement: &Entitlement) -> u32
pub fn can_use_cloudkit_sync(entitlement: &Entitlement) -> bool
pub fn nudge_limit_per_day(entitlement: &Entitlement) -> u32
pub fn has_proactive_nudges(entitlement: &Entitlement) -> bool
pub fn can_customize_coachy(entitlement: &Entitlement) -> bool
pub fn has_template_marketplace(entitlement: &Entitlement) -> bool
pub fn analytics_tier(entitlement: &Entitlement) -> AnalyticsTier
pub fn has_family_dashboard(entitlement: &Entitlement) -> bool
pub fn support_priority(entitlement: &Entitlement) -> SupportPriority
```

### Entitlement Store

Trait for platform-specific storage and receipt verification:

```rust
#[async_trait]
pub trait EntitlementStore: Send + Sync {
    async fn get_current(&self) -> GateResult<Entitlement>;
    async fn set(&self, entitlement: Entitlement) -> GateResult<()>;
    async fn verify_receipt(&self, receipt_signature: &str) -> GateResult<Entitlement>;
}

// Built-in in-memory store for tests
pub struct InMemoryEntitlementStore { ... }
```

### FFI Surface (for Swift)

```rust
pub struct EntitlementsApi;

impl EntitlementsApi {
    pub async fn current_tier(store: &dyn EntitlementStore) -> String
    pub async fn set_tier_from_receipt(
        store: &dyn EntitlementStore,
        receipt_signature: String,
    ) -> Result<String, String>
}
```

## Usage

### Rust (Backend Rule Evaluator)

```rust
use focus_entitlements::{Entitlement, Tier, can_add_rule};

// Get current entitlement from store
let ent = store.get_current().await?;

// Check if user can add another rule
match can_add_rule(current_rule_count, &ent) {
    Ok(true) => { /* allow */ },
    Ok(false) => { /* unreachable */ },
    Err(GateError::LimitExceeded { .. }) => { /* show paywall */ },
    Err(e) => { /* error */ },
}
```

### Swift (iOS App)

```swift
@Environment(\.entitlements) var entitlements: EntitlementModel

// Feature check
if entitlements.canAddRule(current: ruleCount) {
    // Show rule editor
} else {
    // Show paywall
    paywallPresented = true
}

// Voice availability
let voice = entitlements.voiceProvider()
switch voice {
    case .silent:
        // No voice
    case .native:
        // Use AVSpeechSynthesizer
    case .elevenLabs:
        // Use premium ElevenLabs API
}
```

## Testing

Comprehensive test suite with 30+ tests covering all tier × feature combinations:

```bash
cargo test -p focus-entitlements
```

Tests include:
- Individual feature gates (FR-ENTITLEMENTS-001 through FR-ENTITLEMENTS-018)
- Tier matrix (all 4 tiers × all 18 features)
- Subscription lifecycle (purchase → expiry → renewal)
- Edge cases (boundary conditions, offline fallback)
- In-memory store operations
- FFI API (mock Rust → Swift calls)

## StoreKit 2 Integration (v1 Plan)

### On-Device Entitlement Cache

1. **App Launch:**
   - Rust core initializes with `InMemoryEntitlementStore` (default: Free tier)
   - iOS observes `Transaction.currentEntitlements` from StoreKit 2
   - If active subscription found, call `EntitlementsApi::set_tier_from_receipt()`

2. **Receipt Verification:**
   - App sends receipt to Cloudflare Worker endpoint (or lightweight Rust backend)
   - Worker validates StoreKit 2 signature using Apple's JWT decoder
   - Returns tier + expiry; written to on-device store
   - Cache is refresh-time-bucketed; offline fallback is 30-day

3. **Purchase Flow:**
   - User taps paywall "Upgrade to Plus" button
   - StoreKit 2 purchase sheet appears (Apple-native)
   - Transaction verified via `currentEntitlements` loop
   - Receipt signature passed to Rust via FFI
   - Rust store updated; gate re-evaluation allows feature

### Real Product IDs (Post-App-Review)

Until app is approved by App Store, product IDs are stubbed:

```
com.focalpoint.plus.monthly    → $4.99 monthly auto-renewing
com.focalpoint.plus.annual     → $39.99 annual auto-renewing
com.focalpoint.pro.monthly     → $9.99 monthly auto-renewing
com.focalpoint.pro.annual      → $79.99 annual auto-renewing
com.focalpoint.family.monthly  → $14.99 monthly auto-renewing
```

Actual App Store Connect product IDs to be configured during submission.

## Compliance

### Apple Guideline 3.1 (IAP)

- ✅ All digital goods (subscriptions, features) use StoreKit 2 IAP (no external links)
- ✅ Pricing transparent before purchase
- ✅ Cancellation easy (Settings > Subscriptions)
- ✅ Trial periods supported (7d for Plus, 3d for Pro)
- ✅ Refund policy disclosed (Apple's standard)
- ✅ Accessibility: WCAG AA color contrast, readable fonts

### Privacy

FocalPoint **never** sees:
- Card details (Apple handles)
- Unencrypted receipts (only signed JWT)
- User ID from subscription system (only entitlement tier + expiry)

See `PRIVACY.md` in root for full privacy statement.

## Future Work

### Phase 2: Android Parity (RevenueCat)

Once Android ships, migrate to RevenueCat for unified subscription management:

1. Create `EntitlementStore` adapter for RevenueCat SDK (wraps HTTP client)
2. iOS switches from StoreKit 2 native to RevenueCat SDK (API surface unchanged)
3. Android uses RevenueCat Android SDK
4. Same Rust gates apply to both platforms

No breaking changes to Rust core; only the store implementation swaps.

### Phase 3: Advanced Features

- Promo code validation
- Family Sharing seat management
- Metered (usage-based) entitlements
- A/B testing on paywall copy / trial duration

## Architecture Decisions

See `docs/business/subscription_model_2026_04.md` for rationale on:
- Tier pricing and duration
- Free tier generosity vs. conversion pressure
- StoreKit 2 vs. RevenueCat decision
- Receipt verification backend (Cloudflare Worker)
- Feature gate ordering (Free → Plus threshold, Plus → Pro upsell)
