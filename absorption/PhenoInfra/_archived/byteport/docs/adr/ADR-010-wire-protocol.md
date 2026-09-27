# ADR-010: Wire Protocol Specification

**Document ID:** BYTEPORT_ADR_010  
**Status:** Accepted  
**Last Updated:** 2026-04-04  
**Author:** BytePort Architecture Team

---

## Context

BytePort requires a binary wire protocol that:
1. Enables efficient framing of messages
2. Supports multiple encoders and compression algorithms
3. Provides integrity verification
4. Allows for protocol evolution (versioning)
5. Is extensible for future features

## Decision

We implement a **fixed 22-byte header with variable-length payload**:

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                       Magic (4 bytes)                          |
|                           "BPRT"                                |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| Ver |  Flags   |              Schema ID (4 bytes)             |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| Enc |  Comp    |   Reserved  |       Payload Length (4 bytes) |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                        Checksum (4 bytes)                     |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                                                               |
|                        Payload (N bytes)                      |
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

## Header Fields

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0 | 4 | Magic | `0x42 0x50 0x52 0x54` ("BPRT") |
| 4 | 1 | Version | Protocol version (0x01) |
| 5 | 1 | Flags | Request/Response/Compressed/Fragmented |
| 6 | 4 | Schema ID | Schema identifier (big-endian) |
| 10 | 1 | Encoder ID | Encoding format |
| 11 | 1 | Compression ID | Compression algorithm |
| 12 | 2 | Reserved | Future use (must be 0) |
| 14 | 4 | Payload Length | Payload size in bytes |
| 18 | 4 | Checksum | CRC32C of header + payload |
| 22 | N | Payload | Encoded and optionally compressed data |

## Flags Field

```
Bit 7 | Bit 6 | Bit 5 | Bit 4 | Bit 3 | Bit 2 | Bit 1 | Bit 0
------+-------+-------+-------+-------+-------+-------+------
  RSV  |  RSV  |  RSV  |  RSV  | COMP  | FRAG  | RESP  | REQUEST
```

| Bit | Flag | Description |
|-----|------|-------------|
| 0 | REQUEST | Message is a request |
| 1 | RESPONSE | Message is a response |
| 2 | FRAGMENTED | Message requires reassembly |
| 3 | COMPRESSED | Payload is compressed |
| 4-7 | RSV | Reserved |

## Implementation

```rust
pub const MAGIC: [u8; 4] = [0x42, 0x50, 0x52, 0x54];
pub const PROTOCOL_VERSION: u8 = 0x01;
pub const HEADER_SIZE: usize = 22;

bitflags::bitflags! {
    pub struct FrameFlags: u8 {
        const REQUEST    = 0b0000_0001;
        const RESPONSE   = 0b0000_0010;
        const FRAGMENTED = 0b0000_0100;
        const COMPRESSED = 0b0000_1000;
    }
}

pub struct Frame {
    pub header: FrameHeader,
    pub payload: Bytes,
}

pub struct FrameHeader {
    pub version: u8,
    pub flags: FrameFlags,
    pub schema_id: SchemaId,
    pub encoder_id: EncoderId,
    pub compression_id: CompressionId,
    pub payload_length: u32,
    pub checksum: u32,
}

pub struct FrameBuilder {
    schema_id: SchemaId,
    encoder_id: EncoderId,
    compression_id: CompressionId,
    flags: FrameFlags,
    payload: Bytes,
}

impl FrameBuilder {
    pub fn build(&self) -> Result<Bytes, FrameError> {
        let payload_len = self.payload.len() as u32;
        
        // Build header
        let mut header = Vec::with_capacity(HEADER_SIZE);
        header.extend_from_slice(&MAGIC);
        header.push(PROTOCOL_VERSION);
        header.push(self.flags.bits());
        header.extend_from_slice(&self.schema_id.to_be_bytes());
        header.push(self.encoder_id as u8);
        header.push(self.compression_id as u8);
        header.extend_from_slice(&[0u8; 2]); // Reserved
        header.extend_from_slice(&payload_len.to_be_bytes());
        
        // Compute checksum with checksum field zeroed
        let checksum = Self::compute_checksum(&header, &self.payload);
        header.extend_from_slice(&checksum.to_be_bytes());
        
        // Assemble frame
        let mut frame = Vec::with_capacity(HEADER_SIZE + self.payload.len());
        frame.extend_from_slice(&header);
        frame.extend_from_slice(&self.payload);
        
        Ok(Bytes::from(frame))
    }
    
    fn compute_checksum(header: &[u8], payload: &[u8]) -> u32 {
        use crc32fast::Hasher;
        let mut hasher = Hasher::new();
        // Header without checksum bytes (bytes 0-17)
        hasher.update(&header[..18]);
        // Payload
        hasher.update(payload);
        hasher.finalize()
    }
}
```

## Frame Parsing

```rust
pub struct FrameParser {
    buffer: BytesMut,
    state: ParseState,
}

enum ParseState {
    ReadingHeader,
    ReadingPayload { header: FrameHeader },
}

impl FrameParser {
    pub fn parse(&mut self, data: Bytes) -> Result<Option<Frame>, ParseError> {
        self.buffer.extend_from_slice(&data);
        
        loop {
            match self.state {
                ParseState::ReadingHeader => {
                    if self.buffer.len() < HEADER_SIZE {
                        return Ok(None);
                    }
                    
                    let header = self.parse_header()?;
                    self.state = ParseState::ReadingPayload { header };
                }
                ParseState::ReadingPayload { ref header } => {
                    let total_len = HEADER_SIZE + header.payload_length as usize;
                    
                    if self.buffer.len() < total_len {
                        return Ok(None);
                    }
                    
                    // Verify checksum
                    let frame_data = self.buffer.split_to(total_len);
                    let checksum = FrameBuilder::compute_checksum(
                        &frame_data[..HEADER_SIZE],
                        &frame_data[HEADER_SIZE..],
                    );
                    
                    if checksum != header.checksum {
                        return Err(ParseError::ChecksumMismatch {
                            expected: header.checksum,
                            computed: checksum,
                        });
                    }
                    
                    let payload = frame_data.slice(HEADER_SIZE..total_len);
                    return Ok(Some(Frame {
                        header: header.clone(),
                        payload,
                    }));
                }
            }
        }
    }
    
    fn parse_header(&self) -> Result<FrameHeader, ParseError> {
        let buf = &self.buffer[..HEADER_SIZE];
        
        // Validate magic
        if &buf[..4] != MAGIC {
            return Err(ParseError::InvalidMagic {
                expected: MAGIC,
                found: buf[..4].try_into().unwrap(),
            });
        }
        
        // Validate version
        let version = buf[4];
        if version != PROTOCOL_VERSION {
            return Err(ParseError::UnsupportedVersion {
                expected: PROTOCOL_VERSION,
                found: version,
            });
        }
        
        let flags = FrameFlags::from_bits(buf[5])
            .ok_or(ParseError::InvalidFlags(buf[5]))?;
        
        let schema_id = u32::from_be_bytes(buf[6..10].try_into().unwrap());
        let encoder_id = EncoderId::try_from(buf[10])?;
        let compression_id = CompressionId::try_from(buf[11])?;
        let payload_length = u32::from_be_bytes(buf[14..18].try_into().unwrap());
        let checksum = u32::from_be_bytes(buf[18..22].try_into().unwrap());
        
        Ok(FrameHeader {
            version,
            flags,
            schema_id,
            encoder_id,
            compression_id,
            payload_length,
            checksum,
        })
    }
}
```

## Consequences

**Positive:**
- Fixed header size simplifies parsing
- Magic bytes enable quick protocol detection
- Extensible flags field
- CRC32C provides integrity checking
- Schema ID enables schema routing

**Negative:**
- 22-byte overhead per frame (acceptable for payloads > 100 bytes)
- No inline compression selection per-field
- Reserved bytes limit future extensions

---

*End of ADR-010*
