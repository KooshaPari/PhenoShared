---
layout: doc
title: Hello World Story
---

# Hello World: Your First Stashly Operation

<StoryHeader
    title="First Operation"
    duration="2"
    difficulty="beginner"
    :gif="'/gifs/stashly-hello-world.gif'"
/>

## Objective

Execute your first Stashly operation successfully.

## Prerequisites

- Rust/Node/Python installed
- Stashly CLI installed

## Implementation

```rust
use stashly::Client;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let client = Client::new().await?;
    let result = client.hello().await?;
    println!("Success: {}", result);
    Ok(())
}
```

## Expected Output

```
Success: Hello from Stashly!
```

## Next Steps

- [Core Integration](./core-integration)
- [API Reference](../reference/api)
