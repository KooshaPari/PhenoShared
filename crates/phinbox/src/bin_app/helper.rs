//! Own-process Swift inbox helper lifecycle; never activates another session's helper.
use std::{
    path::{Path, PathBuf},
    process::{Child, Command},
    sync::{Mutex, OnceLock},
};
fn child() -> &'static Mutex<Option<Child>> {
    static CHILD: OnceLock<Mutex<Option<Child>>> = OnceLock::new();
    CHILD.get_or_init(|| Mutex::new(None))
}

pub(super) fn launch_inbox_helper(port: u16, root: &Path) {
    let exe_dir = std::env::current_exe()
        .ok()
        .and_then(|p| p.parent().map(Path::to_owned));
    let mut candidates = Vec::new();
    if let Some(path) = std::env::var_os("PHINBOX_HELPER_BINARY") {
        candidates.push(PathBuf::from(path));
    }
    if let Some(dir) = exe_dir {
        candidates.push(dir.join("inbox-helper"));
        candidates.push(dir.join("../Resources/inbox-helper"));
    }
    for path in candidates {
        if !path.is_file() {
            continue;
        }
        match Command::new(path)
            .args([
                "--endpoint",
                &format!("http://127.0.0.1:{port}"),
                "--inbox-root",
            ])
            .arg(root)
            .spawn()
        {
            Ok(process) => {
                if let Ok(mut slot) = child().lock() {
                    *slot = Some(process);
                }
                return;
            },
            Err(_) => eprintln!("phinbox: native inbox helper failed to launch"),
        }
    }
    eprintln!("phinbox: native helper missing; opening local web inbox");
    let _ = phinbox::open_in_default_browser(&format!("http://127.0.0.1:{port}/inbox"));
}
pub(super) fn activate(port: u16, root: &Path) {
    if let Ok(mut slot) = child().lock() {
        if let Some(process) = slot.as_mut() {
            if matches!(process.try_wait(), Ok(None)) {
                // The unreaped owned Child keeps its PID from being reused by another session.
                let _ = Command::new("kill")
                    .args(["-USR1", &process.id().to_string()])
                    .status();
                return;
            }
        }
        *slot = None;
    }
    launch_inbox_helper(port, root);
}
pub(super) fn stop() {
    if let Ok(mut slot) = child().lock() {
        if let Some(mut process) = slot.take() {
            let _ = process.kill();
            let _ = process.wait();
        }
    }
}
