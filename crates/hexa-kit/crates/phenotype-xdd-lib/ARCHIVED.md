# Archived: phenotype-xdd-lib

This repository has been **archived**. The code has been moved to [gauge](https://github.com/KooshaPari/gauge).

## Why

Both `phenotype-xdd-lib` and `gauge` were Rust testing-related libraries. They have been consolidated into a single `gauge` package that provides:
- Benchmarking (was gauge)
- Property testing (was xdd-lib)
- Contract testing (was xdd-lib)
- Mutation testing (was xdd-lib)

## Migration

Replace:
```toml
[dependencies]
phenotype-xdd-lib = { git = "..." }
```

With:
```toml
[dependencies]
gauge = { git = "https://github.com/KooshaPari/gauge" }
```

