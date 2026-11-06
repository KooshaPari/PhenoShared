//! Grapheme-cluster-aware visible width calculation.
//!
//! Replaces the old codepoint-counting heuristic. Skips CSI / OSC / DCS / APC
//! escape sequences and uses `unicode-width` on each grapheme cluster so emoji,
//! ZWJ, flags, and combining marks are measured correctly.

use unicode_segmentation::UnicodeSegmentation;
use unicode_width::UnicodeWidthStr;

/// Compute the visible terminal-cell width of `s`, skipping ANSI escape
/// sequences. Grapheme-aware.
pub fn visible_width(s: &str) -> usize {
    // Strip escape sequences first, then count graphemes.
    let stripped = strip_escapes(s);
    stripped
        .graphemes(true)
        .map(|g| UnicodeWidthStr::width(g).max(1))
        .sum()
}

/// Remove ANSI CSI / OSC / APC / DCS / SS2 / SS3 sequences from `s`.
/// Conservative: drops everything from `ESC` up to the sequence's terminator.
pub fn strip_escapes(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    let bytes: Vec<char> = s.chars().collect();
    let mut i = 0usize;
    while i < bytes.len() {
        let ch = bytes[i];
        if ch != '\x1b' {
            out.push(ch);
            i += 1;
            continue;
        }
        // ESC consumed. What's next?
        if i + 1 >= bytes.len() {
            break;
        }
        let next = bytes[i + 1];
        i += 2;
        match next {
            // CSI `ESC [ ... final` — final is @ A-Z a-z (0x40..=0x7e).
            '[' => {
                while i < bytes.len() {
                    let c = bytes[i];
                    i += 1;
                    if ('\x40'..='\x7e').contains(&c) {
                        break;
                    }
                }
            }
            // OSC `ESC ] ... ST (ESC \)` or BEL.
            ']' | 'P' | '_' | '^' => {
                // Wait for ST (ESC \) or BEL.
                while i < bytes.len() {
                    let c = bytes[i];
                    if c == '\x07' {
                        i += 1;
                        break;
                    }
                    if c == '\x1b' && i + 1 < bytes.len() && bytes[i + 1] == '\\' {
                        i += 2;
                        break;
                    }
                    i += 1;
                }
            }
            // Single-character controls: ESC N, ESC O, ESC c, etc. — drop 1 char.
            _ => {}
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ascii_is_one_cell_each() {
        assert_eq!(visible_width("hello"), 5);
    }

    #[test]
    fn sgr_is_stripped() {
        assert_eq!(visible_width("\x1b[31mred\x1b[0m"), 3);
    }

    #[test]
    fn osc8_link_is_stripped() {
        let s = "\x1b]8;;https://x\x1b\\click\x1b]8;;\x1b\\";
        assert_eq!(visible_width(s), 5);
    }

    #[test]
    fn emoji_is_two_cells() {
        // Pile of poo: one grapheme, width 2.
        assert_eq!(visible_width("a\u{1f4a9}"), 3);
    }

    #[test]
    fn zwj_family_one_cluster() {
        // family: man + ZWJ + woman + ZWJ + boy -- single grapheme cluster.
        let zwj = "\u{1f468}\u{200d}\u{1f469}\u{200d}\u{1f466}";
        // Width in unicode-width is 2 for the cluster.
        assert_eq!(visible_width(zwj), 2);
    }

    #[test]
    fn flag_is_one_cluster() {
        // US flag: regional indicators U+1F1FA U+1F1F8.
        assert_eq!(visible_width("\u{1f1fa}\u{1f1f8}"), 2);
    }
}
