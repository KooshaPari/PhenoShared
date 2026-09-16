---
layout: doc
title: Quick Start
---

# Quick Start: Get Running in 5 Minutes

<UserJourney
  :steps="[{ title: '1. Install Settly', description: 'Add via package manager', duration: '1 min', icon: '📦' },
           { title: '2. Configure', description: 'Create config file', duration: '2 min', icon: '⚙️' },
           { title: '3. Run First', description: 'Execute command', duration: '1 min', icon: '🚀' },
           { title: '4. Verify', description: 'Check status', duration: '1 min', icon: '✅' }]"
  :estimatedDuration="5"
  :gifSrc="'/gifs/settly-quickstart.gif'"
/>

## Step 1: Install

```bash
cargo add settly
```

## Step 2: Configure

```yaml
# config.yaml
name: my-project
environment: development
```

## Step 3: Run

```rust
use settly::Client;

#[tokio::main]
async fn main() {
    let client = Client::new().await.unwrap();
    let result = client.process().await.unwrap();
    println!("{result}");
}
```

## Step 4: Verify

```bash
settly --version
settly health
```
