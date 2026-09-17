# vessel

Container utilities for Rust. Docker, Podman, and containerd abstractions.

## Features

- **Build**: Build container images
- **Run**: Start and manage containers
- **Compose**: Multi-container orchestration
- **Registry**: Push and pull images

## Installation

```toml
[dependencies]
vessel = { git = "https://github.com/KooshaPari/vessel" }
```

## Usage

```rust
use vessel::{Client, Image};

let client = Client::docker()?;
let image = Image::pull("nginx:latest").await?;
let container = client.run(&image).await?;

println!("Container {} running", container.id());
```

## License

MIT
