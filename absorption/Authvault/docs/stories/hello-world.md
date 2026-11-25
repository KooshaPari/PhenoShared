---
layout: doc
title: Hello World Story
---

# Hello World: Your First Authvault Operation

<StoryHeader
    title="First Operation"
    duration="2"
    difficulty="beginner"
    :gif="'/gifs/authvault-hello-world.gif'"
/>

## Objective

Execute your first Authvault operation successfully.

## Prerequisites

- Rust/Node/Python installed
- Authvault CLI installed

## Implementation

```rust
use authvault::Client;

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
Success: Hello from Authvault!
```

## Next Steps

- [Core Integration](./core-integration)
- [API Reference](../reference/api)
