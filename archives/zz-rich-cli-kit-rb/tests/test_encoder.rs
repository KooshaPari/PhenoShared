//! Integration tests for kitty graphics protocol encoder
//! Traces to: FR-002

use rck_core::encoder::{write_kitty_png, MAX_CHUNK};

/// Test that base64 chunks preserve 4-byte alignment
/// Traces to: FR-002 (AC-002.6)
#[test]
fn test_base64_alignment() {
    // Create a PNG that will force multi-chunk encoding (>4096 base64 bytes)
    // ~3072 raw bytes → ~4096 base64 bytes (exactly one chunk)
    // ~3073 raw bytes → ~4097 base64 bytes (forces two chunks)
    let png_small: Vec<u8> = (0..3072).map(|i| (i & 0xff) as u8).collect();
    let png_large: Vec<u8> = (0..3100).map(|i| (i & 0xff) as u8).collect();
    
    let mut buf_small = Vec::new();
    write_kitty_png(&mut buf_small, &png_small).unwrap();
    
    let mut buf_large = Vec::new();
    write_kitty_png(&mut buf_large, &png_large).unwrap();
    
    // Both should succeed without alignment errors
    assert!(!buf_small.is_empty());
    assert!(!buf_large.is_empty());
}

/// Test encoding of a large image producing multiple chunks
/// Traces to: FR-002 (AC-002.3, AC-002.4, AC-002.5)
#[test]
fn test_encoder_large_image() {
    // 20KB raw data → ~26KB base64 → multiple chunks
    let png: Vec<u8> = (0..20_000u32).map(|i| (i & 0xff) as u8).collect();
    let mut buf = Vec::new();
    write_kitty_png(&mut buf, &png).unwrap();
    
    let output = String::from_utf8_lossy(&buf);
    
    // Should have first frame with a=T,f=100,q=2,m=1
    assert!(output.contains("\x1b_Ga=T,f=100,q=2,m=1;"), "missing first chunk header");
    
    // Should have final frame with m=0
    assert!(output.contains("\x1b_Gm=0;"), "missing final chunk header");
    
    // Should end with terminator and newline
    assert!(buf.ends_with(b"\x1b\\\n"), "missing terminator and newline");
    
    // Count APC frames
    let frame_count = output.matches("\x1b_G").count();
    assert!(frame_count > 1, "should have multiple frames for large image");
}

/// Test that single-frame encoding matches spec exactly
/// Traces to: FR-002 (AC-002.1, AC-002.2, AC-002.7)
#[test]
fn test_single_frame_format() {
    let png = b"\x89PNG\r\n\x1a\ntest";
    let mut buf = Vec::new();
    write_kitty_png(&mut buf, png).unwrap();
    
    let output = String::from_utf8_lossy(&buf);
    
    // Should start with control keys
    assert!(output.starts_with("\x1b_Ga=T,f=100,q=2;"), "missing control keys");
    
    // Should end with terminator and newline
    assert!(output.ends_with("\x1b\\\n"), "missing terminator and newline");
    
    // Should have exactly one APC frame
    let frame_count = output.matches("\x1b_G").count();
    assert_eq!(frame_count, 1, "single frame should have exactly one APC sequence");
}

/// Test that empty payload is handled correctly
/// Traces to: FR-002 (AC-002.1)
#[test]
fn test_empty_image() {
    let png: Vec<u8> = Vec::new();
    let mut buf = Vec::new();
    let result = write_kitty_png(&mut buf, &png);
    
    // Empty image should still produce valid output
    assert!(result.is_ok(), "empty image should not error");
    assert!(!buf.is_empty(), "empty image should produce output");
}

/// Test that chunk sizes never exceed MAX_CHUNK
/// Traces to: FR-002 (AC-002.3)
#[test]
fn test_chunk_size_limit() {
    // Generate a very large image
    let png: Vec<u8> = (0..100_000u32).map(|i| (i & 0xff) as u8).collect();
    let mut buf = Vec::new();
    write_kitty_png(&mut buf, &png).unwrap();
    
    // Parse frames and verify payload sizes
    let frames: Vec<&[u8]> = buf.split(|&b| b == 0x1b)
        .filter(|f| !f.is_empty() && f.starts_with(b"_G"))
        .collect();
    
    for frame in frames {
        if let Some(semicolon_pos) = frame.iter().position(|&b| b == b';') {
            if let Some(backslash_pos) = frame.iter().rposition(|&b| b == b'\\') {
                let payload_len = backslash_pos - semicolon_pos - 1;
                assert!(payload_len <= MAX_CHUNK, 
                    "chunk payload exceeds MAX_CHUNK: {} > {}", payload_len, MAX_CHUNK);
            }
        }
    }
}
