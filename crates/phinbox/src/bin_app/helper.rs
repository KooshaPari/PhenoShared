//! Native Swift inbox-helper launcher for `phinbox-app`.

/// Launch the native Swift inbox helper window.
///
/// Looks for `inbox-helper` in these locations (first found wins):
/// 1. Same directory as the running binary (development / flat layout)
/// 2. `../Resources/inbox-helper` relative to the binary (inside .app bundle)
pub(super) fn launch_inbox_helper(port: u16) {
    use std::process::Command;

    let exe = std::env::current_exe().ok();
    let exe_dir = exe.as_ref().and_then(|p| p.parent());

    let candidates: Vec<String> = {
        let mut v = Vec::new();
        if let Some(dir) = exe_dir {
            // Flat layout: binary and helper side by side
            v.push(dir.join("inbox-helper").to_string_lossy().into_owned());
            // .app bundle: helper in ../Resources/
            v.push(
                dir.join("../Resources/inbox-helper")
                    .to_string_lossy()
                    .into_owned(),
            );
        }
        // Fallback: hope it's on PATH
        v.push("inbox-helper".into());
        v
    };

    for path in &candidates {
        if std::path::Path::new(path).exists() {
            let url = format!("http://127.0.0.1:{}/inbox/", port);
            match Command::new(path).arg(&url).spawn() {
                Ok(child) => {
                    eprintln!(
                        "phinbox: launched inbox helper (PID {})",
                        child.id()
                    );
                    // Detach -- let it run independently
                    std::mem::forget(child);
                    return;
                }
                Err(e) => {
                    eprintln!("phinbox: failed to launch {path}: {e}");
                }
            }
        }
    }
    eprintln!("phinbox: inbox-helper not found, falling back to browser");
    let url = format!("http://127.0.0.1:{}/inbox/", port);
    let _ = phinbox::open_in_default_browser(&url);
}
