//! C-ABI FFI surface for sharecli desktop apps (macOS, Windows).
//!
//! FFI choice: plain C ABI via `extern "C"` + `#[no_mangle]`.
//! No uniffi or cxx is needed here because the primary data path goes through
//! the IPC socket (Unix socket on Unix, TCP loopback on Windows); FFI only
//! handles daemon lifecycle and a quick synchronous health peek.
//!
//! Swift bridging header: `desktop/ShareCLITray/sharecli_ffi.h`
//! C# P/Invoke: `windows/ShareCLITray/Interop.cs`
//!
//! Thread-safety: each exported fn is self-contained; the Tokio runtime is
//! created lazily and lives for the process lifetime.

use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_int};
use std::sync::OnceLock;

use tokio::runtime::Runtime;

// The IPC client has exactly two transports: a Unix domain socket on unix and a
// loopback TCP port on windows. On any other target `rt()` would panic before a
// runtime check could report anything, so name the gap at compile time rather
// than leaving an unreachable branch inside `ipc_exchange`.
#[cfg(not(any(unix, windows)))]
compile_error!("sharecli-ffi has no IPC transport for this target");

static RT: OnceLock<Runtime> = OnceLock::new();

fn rt() -> &'static Runtime {
    RT.get_or_init(|| Runtime::new().expect("tokio runtime"))
}

/// # Safety
///
/// Safe to call from any thread. Does not dereference raw pointers. May spawn a
/// child process and block the calling thread for roughly 200 ms. Returns a
/// status code only; no ownership is transferred to or from the caller.
/// Start the IPC daemon in the background (idempotent).
/// Returns 0 on success, non-zero on error.
#[no_mangle]
pub extern "C" fn sharecli_ipc_start() -> c_int {
    // The IPC server is expected to be launched as a separate process
    // (via launchd or explicit spawn from Swift AppDelegate).
    // This function is a hook so Swift can trigger that launch and verify
    // the socket is reachable.
    let sock = socket_path_str();
    if std::path::Path::new(&sock).exists() {
        return 0; // already running
    }

    // Attempt to launch sharecli-ipc as a sidecar process.
    let exe = find_sidecar("sharecli-ipc");
    match exe {
        Some(path) => {
            let _ = spawn_ipc_sidecar(&path);
            // Give it a moment to bind the socket.
            std::thread::sleep(std::time::Duration::from_millis(200));
            0
        },
        None => 1,
    }
}

/// Launch `sharecli-ipc`, injecting W3C `TRACEPARENT` for multi-hop traces.
fn spawn_ipc_sidecar(path: &str) -> std::io::Result<std::process::Child> {
    let mut cmd = std::process::Command::new(path);
    sharecli::otel::apply_traceparent_spawn_env(&mut cmd);
    cmd.spawn()
}

/// # Safety
///
/// Safe to call from any thread. The returned pointer, if non-null, is owned by
/// the caller and must be released exactly once with `sharecli_free_string`. A
/// null return indicates allocation failure; nothing is transferred in that case.
/// The pointer is not valid after it has been freed.
/// Returns the IPC socket path as a null-terminated C string.
/// Caller must free with `sharecli_free_string`.
#[no_mangle]
pub extern "C" fn sharecli_ipc_socket_path() -> *mut c_char {
    let s = socket_path_str();
    CString::new(s)
        .map(|c| c.into_raw())
        .unwrap_or(std::ptr::null_mut())
}

/// # Safety
///
/// `ptr` must be either null or a pointer previously returned by one of this
/// library's allocating functions (`sharecli_ipc_socket_path`,
/// `sharecli_health_json`, `sharecli_request`, `sharecli_serve_get`) that has
/// not already been freed. It must be the exact pointer returned, not an
/// interior or offset pointer, and must not have been allocated by another
/// allocator or freed by any other function. Supplying any other pointer,
/// including a pointer into a Rust `CString` not produced by this library, is
/// undefined behavior. A null pointer is accepted and is ignored. The pointer
/// must not be used after this call returns.
/// Free a string allocated by this library.
///
/// # Safety
///
/// `ptr` must be null or a pointer previously returned by this library that
/// has not already been freed.
#[no_mangle]
pub unsafe extern "C" fn sharecli_free_string(ptr: *mut c_char) {
    if !ptr.is_null() {
        drop(CString::from_raw(ptr));
    }
}
/// Send one newline-terminated RPC payload over the local transport and return
/// the first response line.
///
/// The Unix socket and Windows TCP variants are defined once here so the FFI
/// entry points cannot drift apart: they previously carried byte-identical
/// copies of this block.
async fn ipc_exchange(payload: &[u8]) -> anyhow::Result<String> {
    use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};

    #[cfg(unix)]
    {
        use tokio::net::UnixStream;
        let sock = socket_path_str();
        let mut stream = UnixStream::connect(&sock).await?;
        stream.write_all(payload).await?;
        let (r, _) = stream.into_split();
        let mut lines = BufReader::new(r).lines();
        let line = lines.next_line().await?;
        anyhow::Ok(line.unwrap_or_default())
    }

    #[cfg(windows)]
    {
        use tokio::net::TcpStream;
        let addr = ipc_addr();
        let mut stream = TcpStream::connect(&addr).await?;
        stream.write_all(payload).await?;
        let (r, _) = stream.into_split();
        let mut lines = BufReader::new(r).lines();
        let line = lines.next_line().await?;
        anyhow::Ok(line.unwrap_or_default())
    }
}

/// Hand a Rust string to C: allocate a NUL-terminated copy the caller owns, or
/// return null when the string contains an interior NUL.
fn into_c_string(s: String) -> *mut c_char {
    CString::new(s)
        .map(|c| c.into_raw())
        .unwrap_or(std::ptr::null_mut())
}

/// # Safety
///
/// Safe to call from any thread that is not already executing inside a Tokio
/// runtime worker. The returned pointer, if non-null, is owned by the caller and
/// must be released exactly once with `sharecli_free_string`. A null return
/// indicates a connection, I/O, or allocation failure; nothing is transferred.
/// This function blocks the calling thread while performing I/O.
/// Quick synchronous health snapshot over the IPC socket/TCP.
/// Returns a JSON string (must free with `sharecli_free_string`) or null on error.
#[no_mangle]
pub extern "C" fn sharecli_health_json() -> *mut c_char {
    let req = "{\"id\":1,\"method\":\"health.status\",\"params\":{}}\n";
    match rt().block_on(ipc_exchange(req.as_bytes())) {
        Ok(s) => into_c_string(s),
        Err(_) => std::ptr::null_mut(),
    }
}

/// # Safety
///
/// `request_json` must be either null or a valid, null-terminated C string whose
/// backing storage remains readable and unchanged for the entire duration of this
/// call. It need not be valid UTF-8; invalid UTF-8 causes a null return without
/// dereferencing beyond the terminator. The caller retains ownership of the
/// input buffer; this function does not take ownership of or free it. The
/// returned pointer, if non-null, is owned by the caller and must be released
/// exactly once with `sharecli_free_string`. This function must not be called
/// from within an active Tokio runtime worker thread, as it blocks on the
/// runtime and may deadlock or panic.
/// Send an arbitrary JSON-RPC request string, return the response JSON string.
/// Caller frees the returned string with `sharecli_free_string`.
///
/// # Safety
///
/// `request_json` must be null or point to a valid NUL-terminated C string.
#[no_mangle]
pub unsafe extern "C" fn sharecli_request(request_json: *const c_char) -> *mut c_char {
    if request_json.is_null() {
        return std::ptr::null_mut();
    }
    let mut payload = match CStr::from_ptr(request_json).to_str() {
        Ok(s) => s.to_owned(),
        Err(_) => return std::ptr::null_mut(),
    };
    payload.push('\n');

    match rt().block_on(ipc_exchange(payload.as_bytes())) {
        Ok(s) => into_c_string(s),
        Err(_) => std::ptr::null_mut(),
    }
}

/// # Safety
///
/// `url` must be either null or a valid, null-terminated C string whose backing
/// storage remains readable and unchanged for the entire duration of this call.
/// It need not be valid UTF-8; invalid UTF-8 causes a null return. The caller
/// retains ownership of the input buffer; this function does not take ownership
/// of or free it. The returned pointer, if non-null, is owned by the caller and
/// must be released exactly once with `sharecli_free_string`. A null return
/// indicates an invalid URL, a transport error, or an allocation failure.
/// This function may block the calling thread while performing HTTP I/O.
/// GET an HTTP URL from the tray (e.g. `http://127.0.0.1:9000/healthz`), injecting
/// W3C `traceparent` when the operator env or active OTel context provides one.
/// Returns the response body (must free with `sharecli_free_string`) or null on error.
///
/// # Safety
///
/// `url` must be null or point to a valid NUL-terminated C string.
#[no_mangle]
pub unsafe extern "C" fn sharecli_serve_get(url: *const c_char) -> *mut c_char {
    if url.is_null() {
        eprintln!("sharecli_serve_get: null url pointer");
        return std::ptr::null_mut();
    }
    let url_str = match CStr::from_ptr(url).to_str() {
        Ok(s) => s,
        Err(err) => {
            eprintln!("sharecli_serve_get: url is not valid UTF-8 ({err})");
            return std::ptr::null_mut();
        },
    };
    match sharecli::tray_http::get(url_str) {
        Ok(body) => match CString::new(body) {
            Ok(c) => c.into_raw(),
            Err(err) => {
                eprintln!("sharecli_serve_get: response contains interior NUL ({err})");
                std::ptr::null_mut()
            },
        },
        Err(err) => {
            eprintln!("sharecli_serve_get: {err:#}");
            std::ptr::null_mut()
        },
    }
}

// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------

fn socket_path_str() -> String {
    if let Ok(v) = std::env::var("SHARECLI_IPC_SOCK") {
        return v;
    }
    dirs::data_local_dir()
        .unwrap_or_else(|| std::path::PathBuf::from("/tmp"))
        .join("sharecli")
        .join("ipc.sock")
        .to_string_lossy()
        .into_owned()
}

fn find_sidecar(name: &str) -> Option<String> {
    // Candidate names: on Windows the sidecar ships as `name.exe`; on Unix it's
    // just `name`. Try the platform-appropriate extension first, then the bare name.
    let mut candidates: Vec<String> = Vec::new();
    #[cfg(windows)]
    {
        candidates.push(format!("{name}.exe"));
        candidates.push(name.to_string());
    }
    #[cfg(not(windows))]
    {
        candidates.push(name.to_string());
    }

    // 1. same directory as the current executable (app bundle Resources/bin)
    if let Ok(mut exe) = std::env::current_exe() {
        exe.pop();
        for cand in &candidates {
            let candidate = exe.join(cand);
            if candidate.exists() {
                return Some(candidate.to_string_lossy().into_owned());
            }
        }
    }
    // 2. PATH lookup. `which` is Unix-only; on Windows use the `where` built-in
    //    (via `cmd /c where`) to resolve the executable.
    #[cfg(windows)]
    {
        for cand in &candidates {
            if let Ok(output) = std::process::Command::new("cmd")
                .args(["/c", "where", cand])
                .output()
            {
                if output.status.success() {
                    let path = String::from_utf8_lossy(&output.stdout)
                        .lines()
                        .next()
                        .unwrap_or_default()
                        .trim()
                        .to_string();
                    if !path.is_empty() {
                        return Some(path);
                    }
                }
            }
        }
    }
    #[cfg(not(windows))]
    {
        if let Ok(output) = std::process::Command::new("which").arg(name).output() {
            if output.status.success() {
                let path = String::from_utf8_lossy(&output.stdout).trim().to_string();
                if !path.is_empty() {
                    return Some(path);
                }
            }
        }
    }
    None
}

#[cfg(windows)]
fn ipc_addr() -> String {
    std::env::var("SHARECLI_IPC_ADDR").unwrap_or_else(|_| "127.0.0.1:27182".to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn free_string_accepts_null() {
        // Safety: null is explicitly permitted; this call does nothing.
        unsafe { sharecli_free_string(std::ptr::null_mut()) };
    }

    #[test]
    fn request_null_returns_null() {
        // Safety: null input is explicitly permitted.
        let result = unsafe { sharecli_request(std::ptr::null()) };
        assert!(result.is_null());
    }

    #[test]
    fn serve_get_null_returns_null() {
        // Safety: null input is explicitly permitted.
        let result = unsafe { sharecli_serve_get(std::ptr::null()) };
        assert!(result.is_null());
    }

    #[test]
    fn request_invalid_utf8_returns_null() {
        // Safety: a null-terminated buffer with invalid UTF-8 is permitted.
        let bytes = [0xff_u8, 0x00];
        let result = unsafe { sharecli_request(bytes.as_ptr() as *const c_char) };
        assert!(result.is_null());
    }

    #[test]
    fn socket_path_returns_owned_pointer() {
        let ptr = sharecli_ipc_socket_path();
        assert!(!ptr.is_null());
        // Safety: pointer was returned by this library and is being freed once.
        unsafe { sharecli_free_string(ptr) };
    }
}
