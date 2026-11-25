//! Shell-specific helpers for paste handling.
//!
//! Extends `forge_pheno_shell` with:
//! * [`negotiate_bracketed_paste`] — emit CSI ?2004h / CSI ?2004l to opt in/out.
//! * [`detect_bracketed_paste_event`] — parse a raw input chunk for the paste-start/paste-end
//!   sentinel sequences.
//!
//! Used by `forge_main::editor::ForgeEditor` and `forge_main::prompt::Console`.

/// CSI sequences for bracketed paste mode.
pub const BRACKETED_PASTE_ENABLE: &str = "\x1b[?2004h";
pub const BRACKETED_PASTE_DISABLE: &str = "\x1b[?2004l";

/// Begin/end sentinels — terminals emit `ESC[200~` at start and `ESC[201~` at end.
pub const PASTE_START_SENTINEL: &[u8] = b"\x1b[200~";
pub const PASTE_END_SENTINEL: &[u8] = b"\x1b[201~";

/// Returns the byte sequence to enable bracketed paste mode for the current session.
/// The REPL should emit this on startup and again after every prompt submission.
pub fn negotiate_bracketed_paste(enable: bool) -> &'static str {
    if enable {
        BRACKETED_PASTE_ENABLE
    } else {
        BRACKETED_PASTE_DISABLE
    }
}

/// True if `chunk` contains the bracketed-paste start sentinel.
pub fn has_paste_start(chunk: &[u8]) -> bool {
    contains_subslice(chunk, PASTE_START_SENTINEL)
}

/// True if `chunk` contains the bracketed-paste end sentinel.
pub fn has_paste_end(chunk: &[u8]) -> bool {
    contains_subslice(chunk, PASTE_END_SENTINEL)
}

/// Strip the bracketed-paste sentinels from a chunk. Returns the cleaned bytes plus
/// whether a paste was actually detected.
pub fn strip_bracketed_sentinels(chunk: &[u8]) -> (Vec<u8>, bool) {
    let mut out = Vec::with_capacity(chunk.len());
    let mut i = 0;
    let mut stripped_any = false;
    while i < chunk.len() {
        if chunk[i..].starts_with(PASTE_START_SENTINEL) {
            i += PASTE_START_SENTINEL.len();
            stripped_any = true;
        } else if chunk[i..].starts_with(PASTE_END_SENTINEL) {
            i += PASTE_END_SENTINEL.len();
            stripped_any = true;
        } else {
            out.push(chunk[i]);
            i += 1;
        }
    }
    (out, stripped_any)
}

fn contains_subslice(haystack: &[u8], needle: &[u8]) -> bool {
    if needle.is_empty() || needle.len() > haystack.len() {
        return needle.is_empty();
    }
    haystack.windows(needle.len()).any(|w| w == needle)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn negotiate_emits_correct_csi() {
        assert_eq!(negotiate_bracketed_paste(true), "\x1b[?2004h");
        assert_eq!(negotiate_bracketed_paste(false), "\x1b[?2004l");
    }

    #[test]
    fn detects_start_and_end() {
        let chunk = b"hello\x1b[200~pasted\x1b[201~world";
        assert!(has_paste_start(chunk));
        assert!(has_paste_end(chunk));
    }

    #[test]
    fn no_sentinels_in_plain_chunk() {
        let chunk = b"just plain text";
        assert!(!has_paste_start(chunk));
        assert!(!has_paste_end(chunk));
    }

    #[test]
    fn strip_removes_sentinels() {
        let chunk = b"prefix\x1b[200~INSIDE\x1b[201~suffix";
        let (cleaned, stripped) = strip_bracketed_sentinels(chunk);
        assert_eq!(cleaned, b"prefixINSIDEsuffix");
        assert!(stripped);
    }

    #[test]
    fn strip_passthrough_no_sentinels() {
        let chunk = b"plain";
        let (cleaned, stripped) = strip_bracketed_sentinels(chunk);
        assert_eq!(cleaned, chunk);
        assert!(!stripped);
    }

    #[test]
    fn empty_chunk() {
        let (cleaned, stripped) = strip_bracketed_sentinels(b"");
        assert!(cleaned.is_empty());
        assert!(!stripped);
    }
}
