---
layout: doc
title: Hello World Story
---

# Hello World: Your First Settly Operation

<StoryHeader
    title="First Operation"
    duration="2"
    difficulty="beginner"
    :gif="'/gifs/settly-hello-world.gif'"
/>

## Objective

Execute your first Settly operation successfully.

## Prerequisites

- Rust/Node/Python installed
- Settly CLI installed

## Implementation

```rust
use settly::Client;

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
Success: Hello from Settly!
```

## Next Steps

- [Core Integration](./core-integration)
- [API Reference](../reference/api)
