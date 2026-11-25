//! W3C TraceContext correlation header.
//!
//! Implements the subset of https://www.w3.org/TR/trace-context/ that
//! PhenoObservability's G2 deterministic-correlation fixture requires.
//!
//! Wire format (`traceparent` header):
//!   `00-{trace_id_32hex}-{span_id_16hex}-{flags_2hex}`
//!
//! Invariants:
//!   * `version` is always `00` (the only version we emit / accept)
//!   * `trace_id` is 16 random bytes (32 lowercase hex chars)
//!   * `span_id` is 8 random bytes (16 lowercase hex chars)
//!   * `flags` is 1 byte; only bit `0x01` (sampled) is defined
//!   * All-zero `trace_id` and all-zero `span_id` are invalid per spec;
//!     constructors reject them
//!   * Parsing is deterministic: the same input always yields the same
//!     `TraceContext`, allowing the G2 fixture to assert byte-identical
//!     round-trips across runs.

use core::fmt;

/// Wire-format version we accept / emit. Fixed at `00`.
pub const VERSION: u8 = 0;

/// Flag bit `0x01` — parent is sampled.
pub const FLAG_SAMPLED: u8 = 0x01;

/// Length of `trace_id` in hex chars.
pub const TRACE_ID_HEX_LEN: usize = 32;

/// Length of `span_id` in hex chars.
pub const SPAN_ID_HEX_LEN: usize = 16;

/// Length of `flags` in hex chars.
pub const FLAGS_HEX_LEN: usize = 2;

/// Errors raised when parsing or constructing a `TraceContext`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum TraceContextError {
    /// The wire string had the wrong length.
    BadLength { got: usize, want: usize },
    /// The version field was not `00`.
    UnsupportedVersion(u8),
    /// A hex field was not lowercase 0-9 a-f.
    BadHex { field: &'static str, byte: u8 },
    /// `trace_id` or `span_id` was all-zero (forbidden by spec).
    AllZero { field: &'static str },
    /// `trace_id` was not exactly 32 hex chars, or `span_id` was not 16.
    BadFieldLength { field: &'static str, got: usize },
}

impl fmt::Display for TraceContextError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::BadLength { got, want } => write!(f, "traceparent length {got} != {want}"),
            Self::UnsupportedVersion(v) => write!(f, "unsupported traceparent version {v:#04x}"),
            Self::BadHex { field, byte } => write!(f, "non-hex byte {byte:#04x} in {field}"),
            Self::AllZero { field } => write!(f, "{field} is all-zero (forbidden by spec)"),
            Self::BadFieldLength { field, got } => write!(f, "{field} length {got} invalid"),
        }
    }
}

impl std::error::Error for TraceContextError {}

/// A parsed / constructed W3C TraceContext.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct TraceContext {
    trace_id: [u8; 16],
    span_id: [u8; 8],
    flags: u8,
}

impl TraceContext {
    /// Construct from raw bytes. Returns `Err` if `trace_id` or `span_id`
    /// are all-zero.
    pub fn new(trace_id: [u8; 16], span_id: [u8; 8], flags: u8) -> Result<Self, TraceContextError> {
        if trace_id == [0u8; 16] {
            return Err(TraceContextError::AllZero { field: "trace_id" });
        }
        if span_id == [0u8; 8] {
            return Err(TraceContextError::AllZero { field: "span_id" });
        }
        Ok(Self {
            trace_id,
            span_id,
            flags,
        })
    }

    /// Parse a `traceparent` header value.
    ///
    /// Accepts only version `00` (the W3C-specified behaviour for
    /// forward compatibility). Lower-case hex is required.
    pub fn from_traceparent(header: &str) -> Result<Self, TraceContextError> {
        // Format: "00-<32 hex>-<16 hex>-<2 hex>"
        // Total length = 2 + 1 + 32 + 1 + 16 + 1 + 2 = 55
        const WANT: usize = 55;
        if header.len() != WANT {
            return Err(TraceContextError::BadLength {
                got: header.len(),
                want: WANT,
            });
        }

        let bytes = header.as_bytes();

        // Split on '-' so we can decode each field independently.
        let mut parts = header.split('-');
        let version_hex = parts.next().expect("split always yields >=1");
        let trace_id_hex = parts.next().expect("len checked");
        let span_id_hex = parts.next().expect("len checked");
        let flags_hex = parts.next().expect("len checked");

        if version_hex.len() != 2 {
            return Err(TraceContextError::BadFieldLength {
                field: "version",
                got: version_hex.len(),
            });
        }
        let version = decode_hex_byte(version_hex.as_bytes(), "version")?;
        if version != VERSION {
            return Err(TraceContextError::UnsupportedVersion(version));
        }
        if trace_id_hex.len() != TRACE_ID_HEX_LEN {
            return Err(TraceContextError::BadFieldLength {
                field: "trace_id",
                got: trace_id_hex.len(),
            });
        }
        if span_id_hex.len() != SPAN_ID_HEX_LEN {
            return Err(TraceContextError::BadFieldLength {
                field: "span_id",
                got: span_id_hex.len(),
            });
        }
        if flags_hex.len() != FLAGS_HEX_LEN {
            return Err(TraceContextError::BadFieldLength {
                field: "flags",
                got: flags_hex.len(),
            });
        }

        let trace_id = decode_hex_bytes::<16>(trace_id_hex.as_bytes(), "trace_id")?;
        let span_id = decode_hex_bytes::<8>(span_id_hex.as_bytes(), "span_id")?;
        let flags_arr = decode_hex_bytes::<1>(flags_hex.as_bytes(), "flags")?;
        let flags = flags_arr[0];

        Self::new(trace_id, span_id, flags)
    }

    /// Emit the wire-format `traceparent` header value.
    pub fn to_traceparent(&self) -> String {
        // 2 (version) + 1 (dash) + 32 (trace_id) + 1 (dash) + 16 (span_id) +
        // 1 (dash) + 2 (flags) = 55
        let mut out = String::with_capacity(55);
        out.push_str("00-");
        for b in &self.trace_id {
            push_hex_byte(&mut out, *b);
        }
        out.push('-');
        for b in &self.span_id {
            push_hex_byte(&mut out, *b);
        }
        out.push('-');
        push_hex_byte(&mut out, self.flags);
        out
    }

    /// Produce a child context: same `trace_id`, new `span_id`, inherited
    /// `flags` (sampling decision propagates).
    pub fn child(&self, new_span_id: [u8; 8]) -> Result<Self, TraceContextError> {
        Self::new(self.trace_id, new_span_id, self.flags)
    }

    /// Whether the parent was sampled (flag bit `0x01`).
    pub fn is_sampled(&self) -> bool {
        self.flags & FLAG_SAMPLED != 0
    }

    pub fn trace_id(&self) -> &[u8; 16] {
        &self.trace_id
    }

    pub fn span_id(&self) -> &[u8; 8] {
        &self.span_id
    }

    pub fn flags(&self) -> u8 {
        self.flags
    }
}

/// Decode exactly two hex chars into a single byte. Returns the byte or a
/// `BadHex` error pointing at the offending byte for diagnostics.
fn decode_hex_byte(field: &[u8], name: &'static str) -> Result<u8, TraceContextError> {
    if field.len() != 2 {
        return Err(TraceContextError::BadFieldLength {
            field: name,
            got: field.len(),
        });
    }
    let hi = hex_nibble(field[0], name)?;
    let lo = hex_nibble(field[1], name)?;
    Ok((hi << 4) | lo)
}

/// Decode `2 * N` hex chars into `N` bytes.
fn decode_hex_bytes<const N: usize>(
    field: &[u8],
    name: &'static str,
) -> Result<[u8; N], TraceContextError> {
    if field.len() != 2 * N {
        return Err(TraceContextError::BadFieldLength {
            field: name,
            got: field.len(),
        });
    }
    let mut out = [0u8; N];
    for (i, chunk) in field.chunks_exact(2).enumerate() {
        out[i] = decode_hex_byte(chunk, name)?;
    }
    Ok(out)
}

fn hex_nibble(b: u8, field: &'static str) -> Result<u8, TraceContextError> {
    match b {
        b'0'..=b'9' => Ok(b - b'0'),
        b'a'..=b'f' => Ok(b - b'a' + 10),
        _ => Err(TraceContextError::BadHex { field, byte: b }),
    }
}

fn push_hex_byte(out: &mut String, b: u8) {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    out.push(HEX[(b >> 4) as usize] as char);
    out.push(HEX[(b & 0x0f) as usize] as char);
}

#[cfg(test)]
mod tests {
    use super::*;

    fn fixed_trace_id() -> [u8; 16] {
        [
            0x0a, 0x1b, 0x2c, 0x3d, 0x4e, 0x5f, 0x60, 0x71, 0x82, 0x93, 0xa4, 0xb5, 0xc6, 0xd7,
            0xe8, 0xf9,
        ]
    }

    fn fixed_span_id() -> [u8; 8] {
        [0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08]
    }

    #[test]
    fn round_trip_is_deterministic() {
        let ctx = TraceContext::new(fixed_trace_id(), fixed_span_id(), FLAG_SAMPLED).unwrap();
        let header = ctx.to_traceparent();
        assert_eq!(
            header,
            "00-0a1b2c3d4e5f60718293a4b5c6d7e8f9-0102030405060708-01"
        );
        let parsed = TraceContext::from_traceparent(&header).unwrap();
        assert_eq!(parsed, ctx);
    }

    #[test]
    fn child_inherits_trace_id_and_flags() {
        let parent = TraceContext::new(fixed_trace_id(), fixed_span_id(), FLAG_SAMPLED).unwrap();
        let child_span = [0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17];
        let child = parent.child(child_span).unwrap();
        assert_eq!(child.trace_id(), parent.trace_id());
        assert_eq!(child.span_id(), &child_span);
        assert_eq!(child.flags(), FLAG_SAMPLED);
        assert!(child.is_sampled());
    }

    #[test]
    fn all_zero_trace_id_rejected() {
        let err = TraceContext::new([0u8; 16], fixed_span_id(), FLAG_SAMPLED).unwrap_err();
        assert_eq!(err, TraceContextError::AllZero { field: "trace_id" });
    }

    #[test]
    fn all_zero_span_id_rejected() {
        let err = TraceContext::new(fixed_trace_id(), [0u8; 8], FLAG_SAMPLED).unwrap_err();
        assert_eq!(err, TraceContextError::AllZero { field: "span_id" });
    }

    #[test]
    fn malformed_length_rejected() {
        let err = TraceContext::from_traceparent("00-0a1b-0102-01").unwrap_err();
        assert!(matches!(err, TraceContextError::BadLength { .. }));
    }

    #[test]
    fn unsupported_version_rejected() {
        // Replace version "00" with "ff" and pad length.
        let bad = "ff-0a1b2c3d4e5f60718293a4b5c6d7e8f9-0102030405060708-01";
        let err = TraceContext::from_traceparent(bad).unwrap_err();
        assert_eq!(err, TraceContextError::UnsupportedVersion(0xff));
    }

    #[test]
    fn uppercase_hex_rejected() {
        // Uppercase hex (W3C mandates lowercase).
        let bad = "00-0A1B2C3D4E5F60718293A4B5C6D7E8F9-0102030405060708-01";
        let err = TraceContext::from_traceparent(bad).unwrap_err();
        assert!(matches!(
            err,
            TraceContextError::BadHex {
                field: "trace_id",
                ..
            }
        ));
    }

    #[test]
    fn round_trip_1000_runs_is_byte_identical() {
        // Determinism anchor for the G2 fixture: same input → same output,
        // every time.
        let ctx = TraceContext::new(fixed_trace_id(), fixed_span_id(), FLAG_SAMPLED).unwrap();
        let first = ctx.to_traceparent();
        for _ in 0..1000 {
            assert_eq!(ctx.to_traceparent(), first);
            let parsed = TraceContext::from_traceparent(&first).unwrap();
            assert_eq!(parsed.to_traceparent(), first);
        }
    }

    #[test]
    fn flags_unsampled() {
        let ctx = TraceContext::new(fixed_trace_id(), fixed_span_id(), 0).unwrap();
        assert!(!ctx.is_sampled());
        let parsed = TraceContext::from_traceparent(&ctx.to_traceparent()).unwrap();
        assert_eq!(parsed.flags(), 0);
    }
}
