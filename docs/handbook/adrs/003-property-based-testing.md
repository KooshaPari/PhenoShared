# ADR-003: Property-Based Testing as Default Testing Strategy

## Status

**Accepted** — 2026-04-04

## Context

The Phenotype ecosystem requires robust testing strategies for:

- **heliosCLI**: Command-line tool with complex argument parsing and workflow execution
- **thegent**: Environment management with file system operations
- **portage**: Repository analysis and code generation
- **AgilePlus**: Business logic for spec-driven development
- **All libraries**: 18+ crates in the ecosystem

Current testing challenges:
1. **Example-Based Testing Limitations** — Test cases don't catch edge cases
2. **Maintenance Burden** — Large test suites with repetitive setup
3. **Boundary Testing** — Difficult to exercise all input combinations
4. **Regression Discovery** — Bugs found in production not caught by tests

Testing requirements:
| Requirement | Current State | Target State |
|-------------|---------------|--------------|
| Edge case coverage | ~40% | > 90% |
| Test maintenance time | High | Low |
| Bug discovery phase | Production | CI/CD |
| Regression confidence | Medium | High |
| Developer experience | Mixed | Excellent |

## Decision

We will adopt **Property-Based Testing (PBT)** as the default testing strategy for domain logic, with example-based tests reserved for:
1. Integration tests with specific fixtures
2. Regression tests for specific bugs
3. Documentation examples

### Testing Pyramid (Phenotype)

```
                    Testing Strategy
    
                        /\
                       /  \
                      / E2E \           ~5%
                     /~~~~~~~\          Playwright, real infra
                    /_________\
                   /           \
                  / Integration \       ~15%
                 /~~~~~~~~~~~~~~~\     Example-based, fixtures
                /___________________\
               /                     \
              /  Property-Based Tests \ ~50%
             /~~~~~~~~~~~~~~~~~~~~~~~~~\  Domain invariants
            /_____________________________\
           /                               \
          /      Type System + Compilation   \ ~30%
         /~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\ Rust compiler
        /________________________________________\
```

### Property-Based Testing Approach

#### Domain Invariants

Every domain entity must document its invariants:

```rust
// domain/entities/order.rs
pub struct Order {
    id: OrderId,
    items: Vec<OrderItem>,
    status: OrderStatus,
    created_at: DateTime<Utc>,
}

impl Order {
    /// INVARIANT: An order must have at least one item
    /// INVARIANT: Total must equal sum of line items
    /// INVARIANT: Status transitions are valid
    pub fn new(items: Vec<OrderItem>) -> Result<Self, DomainError> {
        if items.is_empty() {
            return Err(DomainError::OrderMustHaveItems);
        }
        
        let total: Money = items.iter().map(|i| i.line_total()).sum();
        
        Ok(Self {
            id: OrderId::new(),
            items,
            status: OrderStatus::Pending,
            created_at: Utc::now(),
            total,
        })
    }
    
    /// INVARIANT: Can only cancel Pending orders
    pub fn cancel(&mut self) -> Result<(), DomainError> {
        if !self.status.can_cancel() {
            return Err(DomainError::InvalidStatusTransition);
        }
        self.status = OrderStatus::Cancelled;
        Ok(())
    }
}
```

#### Property Tests

```rust
#[cfg(test)]
mod property_tests {
    use super::*;
    use proptest::prelude::*;
    
    // INVARIANT: Order total equals sum of line items
    proptest! {
        #[test]
        fn order_total_equals_sum_of_items(
            items in prop::collection::vec(
                order_item_strategy(),
                1..10  // At least 1 item (invariant)
            )
        ) {
            let order = Order::new(items.clone()).unwrap();
            
            let expected_total: Money = items
                .iter()
                .map(|i| i.line_total())
                .sum();
                
            assert_eq!(order.total(), expected_total);
        }
    }
    
    // INVARIANT: Cannot create order with empty items
    proptest! {
        #[test]
        fn cannot_create_order_without_items(
            _ in Just(())
        ) {
            let result = Order::new(vec![]);
            assert!(matches!(result, Err(DomainError::OrderMustHaveItems)));
        }
    }
    
    // INVARIANT: Status transitions are reversible in some cases
    proptest! {
        #[test]
        fn pending_order_can_be_cancelled(
            items in prop::collection::vec(order_item_strategy(), 1..5)
        ) {
            let mut order = Order::new(items).unwrap();
            assert!(order.cancel().is_ok());
            assert_eq!(order.status(), OrderStatus::Cancelled);
        }
    }
    
    // INVARIANT: Completed orders cannot be cancelled
    proptest! {
        #[test]
        fn completed_order_cannot_be_cancelled(
            items in prop::collection::vec(order_item_strategy(), 1..5)
        ) {
            let mut order = Order::new(items).unwrap();
            order.complete().unwrap();  // Transition to Completed
            assert!(order.cancel().is_err());
        }
    }
    
    // REGRESSION: Discovered overflow bug with large quantities
    proptest! {
        #[test]
        fn order_total_does_not_overflow(
            items in prop::collection::vec(
                (1..1000u32, 0.01..1000.0f64).prop_map(|(qty, price)| {
                    OrderItem::new(qty, Money::new(price))
                }),
                1..100
            )
        ) {
            let order = Order::new(items);
            // Should not panic on overflow
            assert!(order.is_ok() || 
                matches!(order, Err(DomainError::TotalOverflow)));
        }
    }
}
```

#### Custom Strategies

```rust
pub mod strategies {
    use super::*;
    use proptest::prelude::*;
    
    /// Strategy for valid email addresses
    pub fn email_strategy() -> impl Strategy<Value = Email> {
        "[a-zA-Z0-9._%+-]{1,50}@[a-zA-Z0-9.-]{1,50}\.[a-zA-Z]{2,10}"
            .prop_filter("Valid email format", |s| Email::parse(s).is_ok())
            .prop_map(|s| Email::parse(&s).unwrap())
    }
    
    /// Strategy for valid order items
    pub fn order_item_strategy() -> impl Strategy<Value = OrderItem> {
        (1..100u32, 0.01..10000.0f64)
            .prop_map(|(qty, unit_price)| {
                OrderItem::new(
                    qty,
                    ProductId::new(),
                    Money::new(unit_price),
                )
            })
    }
    
    /// Strategy for valid user names
    pub fn user_name_strategy() -> impl Strategy<Value = UserName> {
        proptest::string::string_regex("[A-Za-z][A-Za-z0-9_-]{2,31}")
            .unwrap()
            .prop_map(|s| UserName::parse(&s).unwrap())
    }
    
    /// Strategy for workflow configurations
    pub fn workflow_config_strategy() -> impl Strategy<Value = WorkflowConfig> {
        prop::collection::vec(step_config_strategy(), 1..20)
            .prop_map(|steps| WorkflowConfig::new(steps))
    }
}
```

### State Machine Testing

```rust
// State machine property tests for workflows
use proptest::state_machine::*;

#[derive(Clone, Debug)]
enum WorkflowTransition {
    Start,
    CompleteStep(usize),
    FailStep(usize, String),
    Retry,
    Cancel,
}

struct WorkflowStateMachine {
    workflow: Workflow,
}

impl StateMachineTest for WorkflowStateMachine {
    type SystemUnderTest = WorkflowEngine;
    type Transition = WorkflowTransition;
    
    fn init_system() -> Self::SystemUnderTest {
        WorkflowEngine::new()
    }
    
    fn apply_transition(
        &self,
        sut: &mut Self::SystemUnderTest,
        transition: &Self::Transition,
    ) {
        match transition {
            WorkflowTransition::Start => {
                sut.start(&self.workflow).unwrap();
            }
            WorkflowTransition::CompleteStep(idx) => {
                sut.complete_step(*idx).unwrap();
            }
            WorkflowTransition::FailStep(idx, reason) => {
                sut.fail_step(*idx, reason.clone()).unwrap();
            }
            WorkflowTransition::Retry => {
                sut.retry().unwrap();
            }
            WorkflowTransition::Cancel => {
                sut.cancel().unwrap();
            }
        }
    }
    
    fn check_invariants(&self, sut: &Self::SystemUnderTest) {
        // INVARIANT: Completed workflows have all steps completed
        if sut.status() == WorkflowStatus::Completed {
            assert!(sut.pending_steps().is_empty());
        }
        
        // INVARIANT: Failed workflows have at least one failed step
        if sut.status() == WorkflowStatus::Failed {
            assert!(!sut.failed_steps().is_empty());
        }
        
        // INVARIANT: Terminal states cannot transition
        if matches!(sut.status(), WorkflowStatus::Completed | WorkflowStatus::Cancelled) {
            assert!(sut.can_transition().is_err());
        }
    }
}

proptest! {
    #[test]
    fn workflow_state_machine_test(
        transitions in WorkflowStateMachine::sequential_strategy(1..100)
    ) {
        WorkflowStateMachine::run(transitions);
    }
}
```

## Consequences

### Positive

1. **Edge Case Coverage** — Generated inputs find boundary conditions
2. **Regression Safety** — Shrinking identifies minimal failing cases
3. **Living Documentation** — Properties describe system behavior
4. **Refactoring Confidence** — Properties verify invariants preserved
5. **Developer Efficiency** — Write fewer tests, catch more bugs
6. **Mathematical Rigor** — Properties formalize business rules

### Negative

1. **Learning Curve** — Different mental model from example tests
2. **Debugging Complexity** — Minimal cases may be unintuitive
3. **Performance** — Test execution can be slower
4. **Not All Testable** — Some behaviors need specific fixtures
5. **Strategy Writing** — Custom strategies require expertise

### Mitigations

- Training sessions on PBT mindset
- Hybrid approach: PBT for domain, examples for integration
- CI parallelization for test speed
- Shrinking visualization tools

## Tool Selection

| Tool | Version | Use Case | Notes |
|------|---------|----------|-------|
| **proptest** | 1.x | Rust property testing | Primary tool |
| **hypothesis** | 6.x | Python scripting | thegent extensions |
| **fast-check** | 3.x | TypeScript tests | heliosApp |
| **jqwik** | 1.x | Java interoperability | Future needs |
| **cargo-fuzz** | Latest | Security fuzzing | Security-critical code |

### Cargo Configuration

```toml
[dev-dependencies]
proptest = "1.5"
proptest-state-machine = "0.3"

[[test]]
name = "property"
path = "tests/property.rs"
```

## CI Integration

```yaml
# .github/workflows/test.yml
name: Property Tests

on: [push, pull_request]

jobs:
  property-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run property tests
        run: cargo test --test property --release
        env:
          PROPTEST_CASES: 10000  # More cases in CI
          PROPTEST_MAX_SHRINK_TIME: 30000
          
      - name: Run unit tests (example-based)
        run: cargo test --lib
        
      - name: Fuzz smoke test (5 min)
        run: timeout 300 cargo fuzz run target_smoke || true
```

## Testing Guidelines

### When to Use Property-Based Tests

| Scenario | Use PBT? | Example |
|----------|----------|---------|
| Domain invariants | **Yes** | Order total calculation |
| State machines | **Yes** | Workflow transitions |
| Round-trip properties | **Yes** | Serialize/deserialize |
| Algebraic laws | **Yes** | Monoid/Functor laws |
| Parser/validator | **Yes** | Email validation |
| API integration | No | HTTP client tests |
| Database queries | No | SQL generation tests |
| UI interactions | No | Button click tests |
| Specific bugs | No | Regression tests |

### Property Naming Convention

```rust
// Pattern: {operation}_{condition}_{expected_result}

// Good
fn reverse_twice_returns_original() {}
fn sort_preserves_length() {}
fn encrypt_decrypt_identity() {}

// Bad  
fn test_reverse() {}
fn test_sort() {}
fn test_encryption() {}
```

## Migration Plan

### Phase 1: New Code (Immediate)
- [ ] All new domain code requires property tests
- [ ] PR template includes property test checklist
- [ ] Code review enforces property test coverage

### Phase 2: Critical Paths (Q2 2026)
- [ ] Add property tests to Order domain
- [ ] Add property tests to Workflow engine
- [ ] Add property tests to Spec validation

### Phase 3: Broad Coverage (Q3 2026)
- [ ] Property tests for all value objects
- [ ] Property tests for command validation
- [ ] State machine tests for workflows

### Phase 4: Optimization (Q4 2026)
- [ ] Parallel test execution
- [ ] CI case count tuning
- [ ] Regression case minimization

## Examples by Domain

### Value Objects

```rust
proptest! {
    // Email validation
    #[test]
    fn valid_email_parses_roundtrip(email in valid_email_strategy()) {
        let parsed = Email::parse(email.as_str()).unwrap();
        assert_eq!(parsed.to_string(), email);
    }
    
    // Money arithmetic
    #[test]
    fn money_addition_associative(
        a in money_strategy(),
        b in money_strategy(),
        c in money_strategy()
    ) {
        let left = (a.clone() + b.clone()) + c.clone();
        let right = a + (b + c);
        assert_eq!(left, right);
    }
}
```

### Aggregates

```rust
proptest! {
    // User aggregate
    #[test]
    fn user_email_change_updates_canonical_email(
        user in user_strategy(),
        new_email in email_strategy()
    ) {
        let original_canonical = user.canonical_email();
        user.change_email(new_email.clone()).unwrap();
        assert_ne!(user.canonical_email(), original_canonical);
        assert_eq!(user.email(), &new_email);
    }
}
```

### Services

```rust
proptest! {
    // Pricing service
    #[test]
    fn discount_never_increases_price(
        base_price in money_strategy(),
        discount_percent in 0.0..100.0f64
    ) {
        let discounted = apply_discount(base_price.clone(), discount_percent);
        assert!(discounted <= base_price);
    }
}
```

## References

1. [Proptest Book](https://proptest-rs.github.io/proptest/intro.html)
2. [QuickCheck Paper — Koen Claessen and John Hughes](https://dl.acm.org/doi/10.1145/1988042.1988046)
3. [Property-Based Testing in Practice](https://www.youtube.com/watch?v=IYzDFHbPPwA)
4. [Hypothesis Documentation](https://hypothesis.readthedocs.io/)
5. [Testing the Hard Stuff — John Hughes](https://www.youtube.com/watch?v=zi0rHwfiX1Q)

## Appendix: Quick Reference

### Proptest Macros

| Macro | Purpose | Example |
|-------|---------|---------|
| `proptest!` | Define test block | `proptest! { #[test] fn test() {} }` |
| `prop_oneof!` | Choose from strategies | `prop_oneof![s1, s2, 3 => s3]` |
| `prop_compose!` | Build custom strategies | `prop_compose! { fn name()(x in 1..10) -> T {} }` |
| `prop_assert!` | Assertion with shrinking | `prop_assert!(x > 0)` |
| `prop_assume!` | Skip invalid inputs | `prop_assume!(x != 0)` |

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `PROPTEST_CASES` | 256 | Number of test cases |
| `PROPTEST_MAX_FAILURES` | 0 | Fail after N failures |
| `PROPTEST_MAX_SHRINK_TIME` | 0 | Shrink time limit (ms) |
| `PROPTEST_MAX_SHRINK_ITERS` | usize::MAX | Shrink iterations |
| `PROPTEST_VERBOSE` | 0 | Output verbosity |
| `PROPTEST_RNG_SEED` | random | Reproduce failures |

---

*Decision Date: 2026-04-04*  
*Decision Makers: Phenotype Engineering Team*  
*Next Review: 2026-07-04*