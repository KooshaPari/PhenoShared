//! String normalization utilities
//!
//! Provides Unicode normalization and text cleaning.

use unicode_normalization::UnicodeNormalization;

/// Normalize string to NFC (Canonical Decomposition followed by Canonical Composition)
pub fn normalize_nfc(s: &str) -> String {
    s.nfc().collect()
}

/// Normalize string to NFD (Canonical Decomposition)
pub fn normalize_nfd(s: &str) -> String {
    s.nfd().collect()
}

/// Normalize string to NFKC (Compatibility Decomposition followed by Canonical Composition)
pub fn normalize_nfkc(s: &str) -> String {
    s.nfkc().collect()
}

/// Remove diacritics from characters (e.g., "café" -> "cafe")
pub fn remove_diacritics(s: &str) -> String {
    s.nfd()
        .filter(|c| !matches!(c, '\u{0300}'..='\u{036F}'))
        .collect::<String>()
        .nfc()
        .collect()
}

/// Convert to ASCII, replacing non-ASCII characters
pub fn to_ascii_lossy(s: &str) -> String {
    s.chars()
        .map(|c| {
            if c.is_ascii() {
                c
            } else {
                // Simple ASCII approximation
                match c {
                    'é' | 'è' | 'ê' | 'ë' => 'e',
                    'á' | 'à' | 'â' | 'ä' => 'a',
                    'í' | 'ì' | 'î' | 'ï' => 'i',
                    'ó' | 'ò' | 'ô' | 'ö' => 'o',
                    'ú' | 'ù' | 'û' | 'ü' => 'u',
                    'ñ' => 'n',
                    'ç' => 'c',
                    _ => '?',
                }
            }
        })
        .collect()
}

/// Normalize whitespace and line endings
pub fn normalize_whitespace(s: &str) -> String {
    s.lines()
        .map(|line| line.trim())
        .filter(|line| !line.is_empty())
        .collect::<Vec<_>>()
        .join(" ")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_nfc_normalization() {
        let s = "caf\u{0065}\u{0301}"; // "café" using combining e + acute
        assert_eq!(normalize_nfc(s), "café");
    }

    #[test]
    fn test_remove_diacritics() {
        assert_eq!(remove_diacritics("café"), "cafe");
    }

    #[test]
    fn test_to_ascii_lossy() {
        assert_eq!(to_ascii_lossy("café"), "cafe");
    }

    #[test]
    fn test_nfc_keeps_ascii_unchanged() {
        assert_eq!(normalize_nfc("hello"), "hello");
        assert_eq!(normalize_nfc(""), "");
    }

    #[test]
    fn test_nfd_decomposes_combining_marks() {
        let s = "café"; // composed
        let decomposed = normalize_nfd(s);
        // NFD should split "é" into "e" + combining acute
        assert!(decomposed.chars().count() > s.chars().count());
        assert!(decomposed.contains('\u{0301}'));
    }

    #[test]
    fn test_nfkc_compatibility_decomposition() {
        // "ﬁ" (U+FB01) is a compatibility character that decomposes to "fi"
        let s = "ﬁ";
        let result = normalize_nfkc(s);
        assert_eq!(result, "fi");
    }

    #[test]
    fn test_remove_diacritics_empty() {
        assert_eq!(remove_diacritics(""), "");
        assert_eq!(remove_diacritics("plain"), "plain");
    }

    #[test]
    fn test_to_ascii_lossy_replaces_unknown_with_question() {
        // Japanese kanji is not in the lossless table.
        assert_eq!(to_ascii_lossy("日本"), "??");
    }

    #[test]
    fn test_to_ascii_lossy_passes_ascii() {
        assert_eq!(to_ascii_lossy("hello world 123"), "hello world 123");
    }

    #[test]
    fn test_to_ascii_lossy_handles_all_known_chars() {
        assert_eq!(to_ascii_lossy("ñ"), "n");
        assert_eq!(to_ascii_lossy("ç"), "c");
        assert_eq!(to_ascii_lossy("í"), "i");
        assert_eq!(to_ascii_lossy("ó"), "o");
        assert_eq!(to_ascii_lossy("ú"), "u");
        assert_eq!(to_ascii_lossy("à"), "a");
        assert_eq!(to_ascii_lossy("è"), "e");
        assert_eq!(to_ascii_lossy("ò"), "o");
        assert_eq!(to_ascii_lossy("ù"), "u");
    }

    #[test]
    fn test_normalize_whitespace_collapses_runs() {
        // Multi-line input: blank lines dropped, each line trimmed, joined with " ".
        let input = "  hello  \n\n  world  \n  foo  ";
        let result = normalize_whitespace(input);
        assert_eq!(result, "hello world foo");
    }

    #[test]
    fn test_normalize_whitespace_drops_blank_lines() {
        let input = "a\n\n\nb\n\nc";
        let result = normalize_whitespace(input);
        assert_eq!(result, "a b c");
    }

    #[test]
    fn test_normalize_whitespace_empty() {
        assert_eq!(normalize_whitespace(""), "");
        assert_eq!(normalize_whitespace("   "), "");
        assert_eq!(normalize_whitespace("\n\n\n"), "");
    }
}
