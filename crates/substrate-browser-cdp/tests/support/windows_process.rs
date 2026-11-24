//! Windows process-table helpers for `process_tree.rs`.
//!
//! `std` gives no way to read another process's command line on Windows, and the
//! tests need three answers the crate itself does not export: which pids a
//! launch created, whether those pids are still alive, and whether anything
//! still references a throwaway `--user-data-dir`.
//!
//! The table is read with `Get-CimInstance Win32_Process` rather than `wmic`
//! (removed from current Windows images) and rather than
//! `NtQueryInformationProcess` + PEB reads (unsafe, and blocked for protected
//! processes). PowerShell 5.1 and `pwsh` 7 both provide it on every hosted
//! Windows runner.

use std::time::Duration;

/// One row of the Windows process table.
#[derive(Clone, Debug)]
pub struct WinProcess {
    pub pid: u32,
    pub parent: u32,
    pub command_line: String,
}

/// Read the whole table, or `None` if it could not be read.
///
/// `CommandLine` is empty for processes the caller may not inspect. That
/// degrades identification of *foreign* browsers only; the assertions that
/// matter are by pid.
pub fn table() -> Option<Vec<WinProcess>> {
    // Tab-separated rather than JSON: no extra dependency, and command lines are
    // flattened so a stray newline cannot split one process across two rows.
    const SCRIPT: &str = r#"
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
foreach ($p in Get-CimInstance -ClassName Win32_Process) {
  $cl = ''
  if ($p.CommandLine) { $cl = $p.CommandLine -replace "[\t\r\n]", ' ' }
  Write-Output ("{0}`t{1}`t{2}" -f $p.ProcessId, $p.ParentProcessId, $cl)
}
"#;

    let output = std::process::Command::new("powershell")
        .args([
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
        ])
        .args(["-Command", SCRIPT])
        .output()
        .ok()?;
    if !output.status.success() {
        return None;
    }

    let text = String::from_utf8_lossy(&output.stdout);
    let mut rows = Vec::new();
    for line in text.lines() {
        let line = line.trim_end_matches('\r');
        let mut fields = line.splitn(3, '\t');
        let (Some(pid), Some(parent)) = (fields.next(), fields.next()) else {
            continue;
        };
        let (Ok(pid), Ok(parent)) = (pid.trim().parse(), parent.trim().parse()) else {
            continue;
        };
        rows.push(WinProcess {
            pid,
            parent,
            command_line: fields.next().unwrap_or("").to_string(),
        });
    }
    // An empty table is not a valid answer, so report it as unreadable rather
    // than as a clean one.
    (!rows.is_empty()).then_some(rows)
}

/// Read the table, or fail: an unmeasured shutdown is not a pass.
pub fn read_table(context: &str) -> Vec<WinProcess> {
    table().unwrap_or_else(|| {
        panic!(
            "could not read the Windows process table ({context}); refusing to report \
             a shutdown that was not measured"
        )
    })
}

/// Every pid below `root` in the parent/child graph.
///
/// Membership is guarded, so a reused pid cannot turn a tree walk into a cycle.
pub fn descendants(table: &[WinProcess], root: u32) -> Vec<u32> {
    let mut found: Vec<u32> = Vec::new();
    let mut frontier = vec![root];
    while let Some(parent) = frontier.pop() {
        for row in table {
            if row.parent == parent && !found.contains(&row.pid) {
                found.push(row.pid);
                frontier.push(row.pid);
            }
        }
    }
    found
}

/// Pids whose command line mentions `needle`.
pub fn pids_referencing(table: &[WinProcess], needle: &str) -> Vec<u32> {
    table
        .iter()
        .filter(|row| row.command_line.contains(needle))
        .map(|row| row.pid)
        .collect()
}

/// Browsers that run `binary` but not this launch's profile: the user's own.
pub fn unrelated_browsers(table: &[WinProcess], binary: &str, profile: &str) -> Vec<u32> {
    table
        .iter()
        .filter(|row| row.command_line.contains(binary) && !row.command_line.contains(profile))
        .map(|row| row.pid)
        .collect()
}

/// Poll the table until `satisfied` holds, or the budget expires.
///
/// Returns the last table read and whether it satisfied the predicate, so the
/// caller can assert on the final state and print it as evidence.
pub fn poll_until<F>(budget: Duration, mut satisfied: F) -> (Vec<WinProcess>, bool)
where
    F: FnMut(&[WinProcess]) -> bool,
{
    let deadline = std::time::Instant::now() + budget;
    loop {
        let table = read_table("polling for a settled process tree");
        let ok = satisfied(&table);
        if ok || std::time::Instant::now() >= deadline {
            return (table, ok);
        }
        std::thread::sleep(Duration::from_millis(500));
    }
}
