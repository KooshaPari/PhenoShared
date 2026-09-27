# ADR-002: Zero-Copy Serialization Strategy

**Document ID:** BYTEPORT_ADR_002  
**Status:** Accepted  
**Last Updated:** 2026-04-04  
**Author:** BytePort Architecture Team

---

## Context

BytePort aims for industry-leading performance in binary serialization. Zero-copy parsing eliminates memory allocation during deserialization, reducing latency and GC pressure. We must decide which encoders to support for zero-copy operations and how to implement the zero-copy guarantee.

## Decision

We adopt **FlatBuffers and Cap'n Proto as the primary zero-copy encoders**, with a clear migration path for users of other formats. Zero-copy is achieved through:

1. **FlatBuffers**: Memory-mapped buffers with offset-based access
2. **Cap'n Proto**: Arena allocation with direct pointer access
3. **Message structure**: Read-only buffers (`bytes::Bytes`) to prevent data races

## Encoder Zero-Copy Capability Matrix

| Encoder | Zero-Copy Encode | Zero-Copy Decode | Complexity |
|---------|-----------------|------------------|------------|
| FlatBuffers | Yes | Yes | Medium |
| Cap'n Proto | Yes | Yes | High |
| Protobuf | No | No | Low |
| MessagePack | No | No | Low |
| CBOR | No | Partial | Medium |

## Implementation

```rust
pub trait ZeroCopyEncoder: Encoder {
    fn encode_zero_copy(&self, message: &dyn Message) -> Result<Bytes, EncodeError>;
    fn decode_zero_copy<'a>(&self, bytes: &'a [u8], schema: &Schema) -> Result<ZeroCopyView<'a>, DecodeError>;
}

pub struct FlatBuffersEncoder;

impl ZeroCopyEncoder for FlatBuffersEncoder {
    fn encode_zero_copy(&self, message: &dyn Message) -> Result<Bytes, EncodeError> {
        // Build FlatBuffer in arena, return owned Bytes
        let mut builder = flatbuffers::FlatBufferBuilder::new();
        // ... build message
        Ok(Bytes::from(builder.finished_data().to_vec()))
    }
    
    fn decode_zero_copy<'a>(&self, bytes: &'a [u8], schema: &Schema) -> Result<ZeroCopyView<'a>, DecodeError> {
        // No copy - return direct reference to buffer
        let root = flatbuffers::get_root::<Message<'a>>(bytes);
        Ok(ZeroCopyView::new(root))
    }
}

pub struct ZeroCopyView<'a> {
    data: &'a [u8],
    _phantom: PhantomData<&'a ()>,
}

impl<'a> ZeroCopyView<'a> {
    pub fn new(data: &'a [u8]) -> Self {
        Self { data, _phantom: PhantomData }
    }
    
    pub fn as_ref(&self) -> &dyn Message {
        // Return message reference without allocation
        unsafe { &*(self.data.as_ptr() as *const dyn Message) }
    }
}
```

## Consequences

**Positive:**
- Sub-10ns deserialization for FlatBuffers/Cap'n Proto
- No GC pressure from deserialization paths
- Memory efficiency for high-throughput scenarios

**Negative:**
- FlatBuffers/Cap'n Proto schemas more complex than Protobuf
- Access patterns differ from standard Rust deserialization
- Larger wire format sizes than Protobuf

**Mitigation:**
- Provide `prost` compatibility layer for Protobuf users
- Clear migration documentation from Protobuf to FlatBuffers
- Performance benchmarks demonstrating zero-copy benefits

---

*End of ADR-002*
