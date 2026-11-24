// SPDX-License-Identifier: MIT OR Apache-2.0
// Copyright (c) 2026 Phenotype org (heliosCLI)

//! Utility functions for the verification pipeline.

/// Check if a string contains shell metacharacters that could enable injection.
///
/// Returns `true` if the string contains characters commonly used in command
/// injection attacks: pipe, semicolons, dollar-parentheses, backticks, etc.
pub fn has_shell_metacharacters(s: &str) -> bool {
    const DANGEROUS: &[char] = &['|', ';', '&', '`', '$', '>', '<', '\n', '\r', '\\', '{', '}'];
    s.chars().any(|c| DANGEROUS.contains(&c))
}

/// Parse a duration string like "250ms" or "1500ns" or "2s" into nanoseconds.
pub fn parse_duration_to_ns(s: &str) -> Option<u64> {
    let s = s.trim().to_lowercase();
    if s.ends_with("ns") {
        s[..s.len() - 2].trim().parse::<u64>().ok()
    } else if s.ends_with("ms") {
        s[..s.len() - 2].trim().parse::<u64>().ok().map(|v| v * 1_000_000)
    } else if s.ends_with("us") {
        s[..s.len() - 2].trim().parse::<u64>().ok().map(|v| v * 1_000)
    } else if s.ends_with('s') {
        s[..s.len() - 1].trim().parse::<f64>().ok().map(|v| (v * 1_000_000_000.0) as u64)
    } else {
        s.parse::<u64>().ok()
    }
}

/// Extract benchmark timing from cargo bench output.
///
/// Looks for lines like:
/// - `test result: ok. 0 passed; 0 failed; finished in 0.12s`
/// - `time:   [1.2345 ms 1.2356 ms 1.2367 ms]`
pub fn extract_benchmark_time(stdout: &str, stderr: &str) -> Option<u64> {
    let combined = format!("{}\n{}", stdout, stderr);

    for line in combined.lines() {
        let trimmed = line.trim();
        if trimmed.starts_with("time:") || trimmed.contains("time:") {
            if let Some(start_idx) = trimmed.find('[') {
                let bracket_content = &trimmed[start_idx + 1..];
                if let Some(end_idx) = bracket_content.find(']') {
                    let timing_str = &bracket_content[..end_idx].trim();
                    if let Some(val) = parse_bench_value(timing_str) {
                        return Some(val);
                    }
                }
            }
        }

        if trimmed.contains("bench:") && trimmed.contains("ns/iter") {
            if let Some(bench_idx) = trimmed.find("bench:") {
                let after_bench = trimmed[bench_idx + 6..].trim();
                let num_str: String =
                    after_bench.chars().take_while(|c| c.is_ascii_digit()).collect();
                if let Ok(ns) = num_str.parse::<u64>() {
                    return Some(ns);
                }
            }
        }

        if trimmed.contains("finished in") {
            if let Some(idx) = trimmed.find("finished in") {
                let time_str = &trimmed[idx + 11..].trim();
                if let Ok(secs) = time_str.trim_end_matches('s').parse::<f64>() {
                    return Some((secs * 1_000_000_000.0) as u64);
                }
            }
        }
    }
    None
}

/// Parse a single benchmark value like "1.2345 ms" or "1234 ns" into nanoseconds.
pub fn parse_bench_value(s: &str) -> Option<u64> {
    let parts: Vec<&str> = s.split_whitespace().collect();
    if parts.len() >= 2 {
        let num: f64 = parts[0].parse().ok()?;
        let unit = parts[1].to_lowercase();
        if unit == "ns" {
            return Some(num as u64);
        } else if unit == "us" || unit == "\u{00b5}s" {
            return Some((num * 1_000.0) as u64);
        } else if unit == "ms" {
            return Some((num * 1_000_000.0) as u64);
        } else if unit == "s" {
            return Some((num * 1_000_000_000.0) as u64);
        }
    }
    None
}

/// Try to find a scanner binary on PATH.
pub fn which_scanner(name: &str) -> Option<String> {
    if std::path::Path::new(name).is_file() {
        return Some(name.to_string());
    }

    if let Ok(path_var) = std::env::var("PATH") {
        for dir in path_var.split([':', ';']) {
            let candidate = std::path::Path::new(dir).join(name);
            if candidate.is_file() {
                return Some(candidate.to_string_lossy().to_string());
            }
            #[cfg(windows)]
            {
                let candidate_exe = std::path::Path::new(dir).join(format!("{}.exe", name));
                if candidate_exe.is_file() {
                    return Some(candidate_exe.to_string_lossy().to_string());
                }
            }
        }
    }
    None
}
