# phenotype-iter Adoption Guide

## Overview

`phenotype-iter` provides canonical iterator and collection utilities.

## Quick Start

### Add Dependency

```toml
[dependencies]
phenotype-iter = { path = "../crates/phenotype-iter" }
```

## Batch Processing

```rust
use phenotype_iter::batch::process_in_batches;

let items = vec![1, 2, 3, 4, 5, 6, 7];
let batches: Vec&lt;Vec&lt;i32&gt;&gt; = process_in_batches(&items, 3).collect();
// Result: [[1, 2, 3], [4, 5, 6], [7]]
```

## Chunk Processing

```rust
use phenotype_iter::chunks::process_chunks;

let data = vec![1u8; 100];
for chunk in process_chunks(&data, 32) {
    // Process 32-byte chunks
}
```

## Collection Utilities

```rust
use phenotype_iter::collect::collect_into_result;

let results: Vec<Result&lt;i32, &str&gt;> = vec![Ok(1), Ok(2), Err("fail")];
let (ok, err): (Vec&lt;i32&gt;, Vec&lt;&str&gt;) = collect_into_result(results)?;
// ok = [1, 2]
// err = ["fail"]
```

## Related Crates

- `phenotype-string` - String utilities
- `phenotype-time` - Time utilities
