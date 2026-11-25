# ADR-004: Schema Registry Architecture

**Document ID:** BYTEPORT_ADR_004  
**Status:** Accepted  
**Last Updated:** 2026-04-04  
**Author:** BytePort Architecture Team

---

## Context

BytePort supports multiple encoding formats (Protobuf, MessagePack, FlatBuffers, Cap'n Proto, CBOR). Each format has different schema representation requirements. We need a unified schema registry that can:
1. Store schemas for all supported encoders
2. Enforce schema compatibility rules
3. Support schema evolution without breaking existing clients
4. Enable schema discovery and caching

## Decision

We adopt a **unified schema registry with encoder-specific adapters**:

```
+------------------+     +------------------+     +------------------+
|  Schema Registry | --> |  Adapter Layer   | --> |  Encoder Schemas  |
|  (Unified API)   |     |  (Transform)    |     |  (Protobuf/FB/..)|
+------------------+     +------------------+     +------------------+
```

## Core Interfaces

```rust
pub trait SchemaStore: Send + Sync {
    fn get(&self, id: SchemaId, version: SchemaVersion) -> Result<Schema, SchemaError>;
    fn latest(&self, id: SchemaId) -> Result<Schema, SchemaError>;
    fn versions(&self, id: SchemaId) -> Result<Vec<SchemaVersion>, SchemaError>;
    fn register(&self, schema: Schema) -> Result<SchemaVersion, SchemaError>;
}

pub trait SchemaAdapter: Send + Sync {
    fn to_native(&self, external_schema: &[u8]) -> Result<Schema, SchemaError>;
    fn from_native(&self, schema: &Schema) -> Result<Vec<u8>, SchemaError>;
    fn validate(&self, data: &[u8], schema: &Schema) -> Result<(), ValidationError>;
}

pub struct SchemaRegistry {
    store: Arc<dyn SchemaStore>,
    adapters: HashMap<EncoderId, Arc<dyn SchemaAdapter>>,
    compatibility: CompatibilityChecker,
    cache: Arc<SchemaCache>,
}
```

## Adapter Implementations

### Protobuf Adapter

```rust
pub struct ProtobufSchemaAdapter;

impl SchemaAdapter for ProtobufSchemaAdapter {
    fn to_native(&self, proto_schema: &[u8]) -> Result<Schema, SchemaError> {
        let file = protobuf::parse_from_bytes::<protobuf::descriptor::FileDescriptorProto>(proto_schema)?;
        Schema::from_protobuf(&file)
    }
    
    fn validate(&self, data: &[u8], schema: &Schema) -> Result<(), ValidationError> {
        let msg = protobuf::parse_from_bytes::<protobuf::Message>(data)?;
        // Validate required fields, constraints
        Ok(())
    }
}
```

### FlatBuffers Adapter

```rust
pub struct FlatBuffersSchemaAdapter;

impl SchemaAdapter for FlatBuffersSchemaAdapter {
    fn to_native(&self, fbs_schema: &[u8]) -> Result<Schema, SchemaError> {
        let schema = flatbuffers::get_root::<flatbuffers::Schema>(fbs_schema)?;
        Schema::from_flatbuffers(schema)
    }
    
    fn validate(&self, data: &[u8], schema: &Schema) -> Result<(), ValidationError> {
        let root = flatbuffers::get_root::<flatbuffers::Table>(data)?;
        // Validate table fields
        Ok(())
    }
}
```

## Compatibility Modes

| Mode | Producer Can Add | Producer Can Remove | Consumer Can Add | Consumer Can Remove |
|------|------------------|---------------------|-----------------|--------------------|
| **BACKWARD** | Optional fields | Optional fields | Required fields | Required fields |
| **FORWARD** | Required fields | Required fields | Optional fields | Optional fields |
| **FULL** | Both | Both | Both | Both |
| **NONE** | Any | Any | Any | Any |

## Schema Evolution Rules

```rust
impl CompatibilityChecker {
    pub fn check(&self, old: &Schema, new: &Schema, mode: CompatibilityMode) 
        -> Result<(), CompatibilityError> 
    {
        match mode {
            CompatibilityMode::Backward => self.check_backward(old, new),
            CompatibilityMode::Forward => self.check_forward(old, new),
            CompatibilityMode::Full => {
                self.check_backward(old, new)?;
                self.check_forward(old, new)
            }
            CompatibilityMode::None => Ok(()),
        }
    }
    
    fn check_backward(&self, old: &Schema, new: &Schema) -> Result<(), CompatibilityError> {
        // Old consumer must work with new producer
        for field in &old.fields {
            if field.required {
                if !new.fields.iter().any(|f| f.name == field.name && f.field_type == field.field_type) {
                    return Err(CompatibilityError::BreakingChange { 
                        field: field.name.clone(),
                        reason: "Required field removed or type changed".to_string(),
                    });
                }
            }
        }
        Ok(())
    }
}
```

## Cache Strategy

```rust
pub struct SchemaCache {
    inner: RwLock<LruCache<SchemaId, Arc<Schema>>>,
    max_entries: usize,
}

impl SchemaCache {
    pub fn get(&self, id: SchemaId) -> Option<Arc<Schema>> {
        self.inner.read().unwrap().get(&id).cloned()
    }
    
    pub fn insert(&self, id: SchemaId, schema: Arc<Schema>) {
        let mut cache = self.inner.write().unwrap();
        if cache.len() >= self.max_entries {
            cache.pop_lru();
        }
        cache.put(id, schema);
    }
}
```

## Consequences

**Positive:**
- Single registry API for all encoder types
- Schema evolution safety through compatibility checking
- Performance optimization through caching
- Decoupled encoder implementations

**Negative:**
- Adapter complexity for each encoder
- Cache invalidation challenges
- Version resolution adds latency

---

*End of ADR-004*
