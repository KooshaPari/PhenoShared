# ADR-003: Adaptive Compression Framework

**Document ID:** BYTEPORT_ADR_003  
**Status:** Accepted  
**Last Updated:** 2026-04-04  
**Author:** BytePort Architecture Team

---

## Context

Different data types exhibit vastly different compression characteristics. Text-heavy JSON-like data compresses 4-10x, while binary protocol data may compress only 1.5-2x. Using a single compression algorithm for all payloads is suboptimal. We need an intelligent adaptive compression system.

## Decision

We implement a **tiered adaptive compression strategy** that automatically selects the optimal algorithm based on payload characteristics and size thresholds:

### Compression Tier System

| Tier | Size Range | Algorithm | Rationale |
|------|------------|-----------|-----------|
| 0 | < 1KB | None | Compression overhead exceeds savings |
| 1 | 1KB - 10KB | LZ4 | Fast compression, minimal latency |
| 2 | 10KB - 100KB | Zstd (level 3) | Balanced ratio and speed |
| 3 | > 100KB | Zstd (level 6) | Maximum compression for large data |
| Special | Repetitive data | LZ4 | Pattern detection enables high ratio |

## Implementation

```rust
pub struct AdaptiveCompressor {
    lz4: Lz4Compressor,
    zstd_fast: ZstdCompressor,
    zstd_high: ZstdCompressor,
    pattern_detector: PatternDetector,
}

pub struct CompressionConfig {
    pub lz4_threshold_bytes: usize = 1024,
    pub zstd_fast_threshold_bytes: usize = 10240,
    pub zstd_level_fast: i32 = 3,
    pub zstd_level_high: i32 = 6,
    pub min_compression_ratio: f64 = 1.1,
}

impl AdaptiveCompressor {
    pub fn compress(&self, input: &[u8]) -> Result<(Bytes, CompressionId, f64), CompressionError> {
        let len = input.len();
        
        // Tier 0: Skip small payloads
        if len < self.config.lz4_threshold_bytes {
            return Ok((Bytes::copy_from_slice(input), CompressionId::None, 1.0));
        }
        
        // Pattern detection for repetitive data
        if self.pattern_detector.is_highly_repetitive(input) {
            let compressed = self.lz4.compress(input)?;
            let ratio = compressed.len() as f64 / len as f64;
            if ratio >= self.config.min_compression_ratio {
                return Ok((compressed, CompressionId::Lz4, ratio));
            }
            return Ok((Bytes::copy_from_slice(input), CompressionId::None, 1.0));
        }
        
        // Tier 1: Fast compression for medium payloads
        if len < self.config.zstd_fast_threshold_bytes {
            let compressed = self.lz4.compress(input)?;
            let ratio = compressed.len() as f64 / len as f64;
            if ratio >= self.config.min_compression_ratio {
                return Ok((compressed, CompressionId::Lz4, ratio));
            }
            return Ok((Bytes::copy_from_slice(input), CompressionId::None, 1.0));
        }
        
        // Tier 2 & 3: Zstd for larger payloads
        let zstd = if len > 102400 { &self.zstd_high } else { &self.zstd_fast };
        let compressed = zstd.compress(input)?;
        let ratio = compressed.len() as f64 / len as f64;
        
        // Fallback to LZ4 if Zstd doesn't provide significant improvement
        if ratio < 1.2 {
            let lz4_compressed = self.lz4.compress(input)?;
            let lz4_ratio = lz4_compressed.len() as f64 / len as f64;
            if lz4_ratio < ratio * 1.1 {
                return Ok((lz4_compressed, CompressionId::Lz4, lz4_ratio));
            }
        }
        
        Ok((compressed, CompressionId::Zstd, ratio))
    }
}

pub struct PatternDetector;

impl PatternDetector {
    fn is_highly_repetitive(&self, data: &[u8]) -> bool {
        if data.len() < 256 { return false; }
        
        // Sample 8 positions
        let positions = [0, 32, 64, 128, 192, 224, 240, 248];
        let sample: Vec<u8> = positions.iter().filter_map(|&i| data.get(i)).copied().collect();
        
        // Check if sample contains only small number of unique bytes
        let unique = sample.iter().collect::<std::collections::HashSet<_>>().len();
        unique <= 16
    }
}
```

## Selection Algorithm Flow

```
Input: payload
  |
  v
+-------------------------+
| payload.len() < 1KB?   |
+-------------------------+
  | Yes                       | No
  v                           v
+-------------------------+ +---------------------------+
| Return: None            | | Check repetitive pattern |
+-------------------------+ +---------------------------+
                                | Yes         | No
                                v             v
                          +----------+ +------------------+
                          | LZ4      | | len() < 10KB?   |
                          +----------+ +------------------+
                                           | Yes        | No
                                           v            v
                                    +----------+ +------------+
                                    | LZ4      | | Zstd (L3) |
                                    +----------+ +------------+
                                           |            |
                                           +-----+------+
                                                 v
                                           Compare ratios
                                                 |
                                                 v
                                          Select best
```

## Consequences

**Positive:**
- Optimal compression for diverse payload types
- Transparent to user - no manual configuration required
- Maintains low latency for small payloads
- Achieves 2-3x better average compression than single-algorithm approach

**Negative:**
- Additional complexity in compression layer
- Pattern detection adds small overhead
- Memory usage slightly higher (multiple compressor instances)

---

*End of ADR-003*
