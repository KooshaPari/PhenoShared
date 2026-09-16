# Behavior-Driven Development (BDD) Pattern

## Overview

BDD bridges the gap between technical implementation and business requirements through executable specifications written in natural language.

## Core Principles

1. **Collaboration**: Developers, testers, and business stakeholders write specifications together
2. **Ubiquitous Language**: Domain terms used consistently in code and specs
3. **Outside-In**: Start from user/business value, work inward to implementation
4. **Executable Specifications**: Tests serve as living documentation

## When to Use

- **Complex domain logic**: When requirements involve business rules
- **Team collaboration**: Multiple stakeholders need clarity
- **Long-term projects**: Living documentation that evolves with code
- **Regulatory compliance**: Auditable, traceable requirements

## When NOT to Use

- **Simple CRUD operations**: Overhead doesn't provide value
- **Rapid prototyping**: Ceremony slows iteration
- **Solo projects**: Collaboration benefits not realized
- **Algorithmic code**: Technical, not business-focused

## BDD Structure

### 1. Feature File (Gherkin)

```gherkin
Feature: User Authentication
  As a user
  I want to securely log in to my account
  So that I can access my personal data

  Scenario: Successful login with valid credentials
    Given a registered user with email "user@example.com" and password "SecurePass123!"
    When the user attempts to log in with correct credentials
    Then the login should succeed
    And the user should receive an access token
    And the token should expire in 3600 seconds

  Scenario: Failed login with invalid password
    Given a registered user with email "user@example.com" and password "SecurePass123!"
    When the user attempts to log in with password "WrongPassword"
    Then the login should fail with error "Invalid credentials"
    And the user should receive an error code "AUTH_001"
    And the failed attempt should be logged

  Scenario Outline: Login with various invalid inputs
    Given a registered user with email "<email>" and password "<password>"
    When the user attempts to log in
    Then the login should fail with error "<error>"
    
    Examples:
      | email           | password    | error              |
      |                 | password123 | Email required     |
      | user@test.com   |             | Password required  |
      | invalid-email   | password123 | Invalid email      |
      | user@test.com   | 123         | Password too short |
```

### 2. Step Definitions (Implementation)

**Rust with cucumber crate:**

```rust
use cucumber::{given, when, then, World, Event};
use std::time::Duration;

#[derive(Debug, Default, World)]
pub struct AuthWorld {
    user: Option<User>,
    credentials: Credentials,
    result: Option<Result<AuthResponse, AuthError>>,
    logs: Vec<AuditLog>,
}

#[given(regex = r"^a registered user with email \"(.*)\" and password \"(.*)\"")]
async fn registered_user(world: &mut AuthWorld, email: String, password: String) {
    world.user = Some(User::create(&email, &password).await.unwrap());
    world.credentials = Credentials { email, password };
}

#[when("the user attempts to log in with correct credentials")]
async fn login_correct(world: &mut AuthWorld) {
    let auth_service = AuthService::new();
    world.result = Some(auth_service.authenticate(&world.credentials).await);
}

#[when(regex = r"^the user attempts to log in with password \"(.*)\"")]
async fn login_with_password(world: &mut AuthWorld, password: String) {
    let mut credentials = world.credentials.clone();
    credentials.password = password;
    
    let auth_service = AuthService::new();
    world.result = Some(auth_service.authenticate(&credentials).await);
    
    // Capture logs for assertions
    world.logs = AuditLog::find_by_user(&credentials.email).await;
}

#[when("the user attempts to log in")]
async fn login(world: &mut AuthWorld) {
    let auth_service = AuthService::new();
    world.result = Some(auth_service.authenticate(&world.credentials).await);
}

#[then("the login should succeed")]
async fn login_succeeds(world: &mut AuthWorld) {
    assert!(world.result.as_ref().unwrap().is_ok(), 
            "Expected login to succeed, but got: {:?}", world.result);
}

#[then("the user should receive an access token")]
async fn receive_token(world: &mut AuthWorld) {
    let response = world.result.as_ref().unwrap().as_ref().unwrap();
    assert!(!response.access_token.is_empty());
    assert!(response.token_type == "Bearer");
}

#[then(regex = r"^the token should expire in (\d+) seconds$")]
async fn token_expires_in(world: &mut AuthWorld, seconds: u64) {
    let response = world.result.as_ref().unwrap().as_ref().unwrap();
    assert_eq!(response.expires_in, Duration::from_secs(seconds));
}

#[then(regex = r"^the login should fail with error \"(.*)\"")]
async fn login_fails(world: &mut AuthWorld, expected_error: String) {
    let error = world.result.as_ref().unwrap().as_ref().err().unwrap();
    assert_eq!(error.message, expected_error);
}

#[then(regex = r"^the user should receive an error code \"(.*)\"")]
async fn error_code(world: &mut AuthWorld, expected_code: String) {
    let error = world.result.as_ref().unwrap().as_ref().err().unwrap();
    assert_eq!(error.code, expected_code);
}

#[then("the failed attempt should be logged")]
async fn failed_attempt_logged(world: &mut AuthWorld) {
    let recent_log = world.logs.iter().find(|log| {
        log.event_type == "AUTH_FAILURE" &&
        log.timestamp > chrono::Utc::now() - chrono::Duration::seconds(5)
    });
    
    assert!(recent_log.is_some(), "Failed login should be logged in audit log");
}

#[tokio::main]
async fn main() {
    AuthWorld::cucumber()
        .with_writer(cucumber::writer::Basic::stdout())
        .with_default_cli()
        .with_after_scenario(|_feature, _rule, _scenario, world, result| {
            async move {
                if result.is_err() {
                    if let Some(ref w) = world {
                        println!("Scenario failed with world state: {:?}", w);
                    }
                }
                // Cleanup test data
                if let Some(ref w) = world {
                    if let Some(ref user) = w.user {
                        user.delete().await.ok();
                    }
                }
            }
        })
        .run_and_exit("./tests/features")
        .await;
}
```

**Python with behave:**

```python
from behave import given, when, then
from typing import Dict
import requests

# Context holds state across steps
@given('a registered user with email "{email}" and password "{password}"')
def step_create_user(context, email: str, password: str):
    """Set up a registered user in the test environment."""
    context.user_email = email
    context.user_password = password
    
    # Create user via API or database fixture
    response = requests.post(
        f"{context.base_url}/api/test/users",
        json={"email": email, "password": password}
    )
    assert response.status_code == 201, f"Failed to create test user: {response.text}"
    context.user_id = response.json()["id"]
    
    # Store for cleanup
    context.created_users.append(context.user_id)

@when('the user attempts to log in with correct credentials')
def step_login_correct(context):
    """Execute login with stored credentials."""
    context.response = requests.post(
        f"{context.base_url}/api/auth/login",
        json={
            "email": context.user_email,
            "password": context.user_password
        }
    )

@when('the user attempts to log in with password "{password}"')
def step_login_with_password(context, password: str):
    """Execute login with custom password."""
    context.response = requests.post(
        f"{context.base_url}/api/auth/login",
        json={
            "email": context.user_email,
            "password": password
        }
    )
    
    # Capture audit logs
    context.audit_logs = requests.get(
        f"{context.base_url}/api/test/audit-logs",
        params={"user_email": context.user_email}
    ).json()

@then('the login should succeed')
def step_login_success(context):
    """Assert successful login."""
    assert context.response.status_code == 200, \
        f"Expected 200, got {context.response.status_code}: {context.response.text}"

@then('the user should receive an access token')
def step_receive_token(context):
    """Assert token presence and format."""
    data = context.response.json()
    assert "access_token" in data, "Response missing access_token"
    assert data["token_type"] == "Bearer", f"Expected Bearer, got {data['token_type']}"
    assert len(data["access_token"]) > 0, "Access token is empty"
    context.access_token = data["access_token"]

@then('the token should expire in {seconds:d} seconds')
def step_token_expiry(context, seconds: int):
    """Assert token expiry time."""
    data = context.response.json()
    assert data["expires_in"] == seconds, \
        f"Expected expiry {seconds}s, got {data['expires_in']}s"

@then('the login should fail with error "{message}"')
def step_login_failure(context, message: str):
    """Assert login failure with specific message."""
    assert context.response.status_code in [401, 403], \
        f"Expected 401/403, got {context.response.status_code}"
    
    data = context.response.json()
    assert data.get("error") == message, \
        f"Expected error '{message}', got '{data.get('error')}'"

@then('the user should receive an error code "{code}"')
def step_error_code(context, code: str):
    """Assert error code in response."""
    data = context.response.json()
    assert data.get("error_code") == code, \
        f"Expected error_code '{code}', got '{data.get('error_code')}'"

@then('the failed attempt should be logged')
def step_audit_log(context):
    """Assert failed login is recorded in audit logs."""
    recent_failures = [
        log for log in context.audit_logs
        if log["event_type"] == "AUTH_FAILURE"
        and log["user_email"] == context.user_email
    ]
    
    assert len(recent_failures) > 0, \
        "Expected failed login to be logged in audit log"

# environment.py for setup
def before_all(context):
    """Global test setup."""
    context.base_url = context.config.userdata.get("base_url", "http://localhost:8080")
    context.created_users = []

def after_scenario(context, scenario):
    """Cleanup after each scenario."""
    for user_id in context.created_users:
        requests.delete(f"{context.base_url}/api/test/users/{user_id}")
    context.created_users = []
```

## Feature Organization

```
tests/
├── features/
│   ├── auth/
│   │   ├── login.feature
│   │   ├── logout.feature
│   │   ├── registration.feature
│   │   └── password-reset.feature
│   ├── orders/
│   │   ├── create-order.feature
│   │   ├── cancel-order.feature
│   │   └── order-lifecycle.feature
│   └── gherkin-steps.md
├── steps/
│   ├── auth_steps.py (or .rs)
│   ├── order_steps.py
│   └── common_steps.py
├── fixtures/
│   └── test_data.json
└── environment.py
```

## Phenotype BDD Integration

### 1. Feature-Spec Traceability

```yaml
# kitty-spec frontmatter
---
feature_ref: "auth/login.feature"
scenarios:
  - "Successful login with valid credentials"
  - "Failed login with invalid password"
test_coverage: 
  unit: 15
  integration: 8
  e2e: 3
---
```

### 2. BDD in Hexagonal Architecture

```
┌─────────────────────────────────────────┐
│           BDD Test Layer               │
│  ┌─────────────────────────────────┐   │
│  │  Feature Files (Gherkin)        │   │
│  │  - Business language          │   │
│  │  - Executable specs           │   │
│  └─────────────────────────────────┘   │
│              │                          │
│  ┌───────────┴──────────────────┐      │
│  │      Step Definitions        │      │
│  │  - Map Gherkin to code      │      │
│  │  - Call application layer   │      │
│  └──────────────────────────────┘      │
├─────────────────────────────────────────┤
│         Hexagonal Architecture          │
│  ┌─────────────────────────────────┐     │
│  │         Application Layer       │     │
│  │  - Use cases / Services       │     │
│  │  - Port interfaces           │     │
│  └─────────────────────────────────┘   │
│              │                           │
│    ┌────────┴────────┐                 │
│    ▼                  ▼                  │
│  ┌──────────┐    ┌──────────┐            │
│  │ Primary  │    │ Secondary│            │
│  │ Adapters │    │ Adapters │            │
│  │ (HTTP)   │    │ (DB,MQ)  │            │
│  └──────────┘    └──────────┘            │
└─────────────────────────────────────────┘
```

### 3. Test Pyramid with BDD

```
        /\
       /  \
      / E2E\          ← BDD Features (few)
     /________\         Full system path
    /          \        3-5 scenarios per feature
   / Integration\       ← BDD Scenarios (some)
  /______________\       API-level testing
 /                \       8-10 scenarios per feature
/     Unit         \      ← Unit Tests (many)
/____________________\      Isolated logic
                         15+ tests per feature
```

## Best Practices

### 1. Scenario Quality

```gherkin
# ❌ Bad: Too technical
Scenario: API returns 200 with token
  When POST /api/v1/auth with {"email":"x","password":"y"}
  Then status code is 200
  And response contains "token"

# ✅ Good: Business language
Scenario: User receives access token after successful login
  When the user successfully authenticates
  Then they receive a secure access token
  And the token expires after one hour
```

### 2. Reusable Steps

```gherkin
# Generic step definition
Given "{user_role}" user "{name}" exists
# Matches: "admin user 'Alice' exists"
# Matches: "customer user 'Bob' exists"
```

### 3. Tagging Strategy

```gherkin
@smoke @critical @auth
Feature: User Authentication

  @fast @unit
  Scenario: Password validation rules
    ...

  @slow @integration @database
  Scenario: User creation with database
    ...

  @e2e @external-api
  Scenario: OAuth flow with Google
    ...
```

Run: `behave --tags=smoke --tags=-slow`

### 4. Data Management

```python
# Use fixtures, not hardcoded data
def step_admin_user_exists(context, name):
    context.user = UserFactory.create(
        name=name,
        role="admin",
        permissions=["read", "write", "delete"]
    )

# Table-driven tests
Scenario: Multiple discount rules
  Given the following products exist:
    | name  | price | category |
    | A     | 100   | electronics |
    | B     | 50    | clothing |
  When applying "SUMMER20" discount
  Then prices should be:
    | name  | new_price |
    | A     | 80        |
    | B     | 40        |
```

## CI/CD Integration

```yaml
# .github/workflows/bdd.yml
name: BDD Tests

on: [push, pull_request]

jobs:
  bdd:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup
        run: |
          pip install behave requests
          cargo install cucumber
      
      - name: Run BDD
        run: |
          # Python
          behave --format allure_behave.formatter:AllureFormatter \
                 --outfile reports/bdd-results.json
          
          # Rust
          cargo test --test bdd
      
      - name: Upload Living Documentation
        run: |
          # Generate HTML report from feature files
          behave --format html --outfile docs/living-docs.html
          
          # Upload to GitHub Pages
          gh-pages-deploy --dist docs
```

## Living Documentation

```gherkin
@documented
Feature: Order Processing
  ## Business Context
  Orders are the core revenue driver. This process ensures:
  - Accurate pricing
  - Inventory availability
  - Fraud prevention
  
  ## Technical Context
  - Order service is the source of truth
  - Inventory service is eventually consistent
  - Payment is synchronous

  Scenario: Successful order creation
    ## Flow
    1. Validate inventory
    2. Reserve payment
    3. Create order
    4. Send confirmation
    ...
```

Generate docs: `behave --format sphinx.steps`

## Anti-Patterns

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Testing through UI only | Slow, brittle | Test at API/service level |
| Technical language in scenarios | Not readable by business | Use domain language |
| One giant feature file | Hard to navigate | Split by domain area |
| Scenario per UI element | Maintenance nightmare | Scenario per business rule |
| Hardcoded test data | Flaky tests | Use factories/fixtures |
| Testing implementation | Brittle | Test behavior, not code |