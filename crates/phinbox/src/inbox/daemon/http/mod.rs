//! HTTP server loop and request handling for the inbox daemon.
//!
//! This module contains the blocking HTTP server that serves the inbox
//! UI on `http://127.0.0.1:7117/inbox/<id>`. It's deliberately minimal:
//! one thread per connection, no async runtime, no TLS -- the inbox is
//! local-only and binds to `127.0.0.1` only.

pub(crate) mod response;
pub(crate) mod route;

use std::io::{BufRead, BufReader, Read};
use std::net::TcpStream;
use std::path::Path;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::thread;
use std::time::Duration;

use crate::inbox::{list_pending, load, RequestState};
use tracing::warn;

use super::lockfile::LOCKFILE_NAME;
use response::{
    redirect_response, render_inbox_css, render_inbox_html, simple_text, text_response,
    write_response,
};
use route::{parse_route, Route};

/// How long an idle HTTP connection is allowed to live.
const HTTP_KEEPALIVE_TIMEOUT: Duration = Duration::from_secs(30);

/// Get the mtime of a file in seconds since UNIX epoch.
pub(crate) fn mtime_sec(path: &Path) -> Option<u64> {
    std::fs::metadata(path)
        .ok()
        .and_then(|m| m.modified().ok())
        .and_then(|t| t.duration_since(std::time::UNIX_EPOCH).ok())
        .map(|d| d.as_secs())
}

/// Run the HTTP accept loop. Returns when `shutdown` is set.
pub(crate) fn run_http_loop(
    listener: std::net::TcpListener,
    inbox_root: &Path,
    shutdown: &Arc<AtomicBool>,
) -> std::io::Result<()> {
    let mut shutdown_mtime = mtime_sec(&inbox_root.join(LOCKFILE_NAME));
    loop {
        if shutdown.load(Ordering::SeqCst) {
            break;
        }
        // Wake up early if the lockfile was touched by `stop()`.
        let current_mtime = mtime_sec(&inbox_root.join(LOCKFILE_NAME));
        if current_mtime != shutdown_mtime {
            shutdown_mtime = current_mtime;
            if shutdown.load(Ordering::SeqCst) {
                break;
            }
        }

        match listener.accept() {
            Ok((stream, _)) => {
                let inbox_root = inbox_root.to_path_buf();
                let shutdown = Arc::clone(shutdown);
                thread::spawn(move || {
                    let _ = handle_connection(stream, &inbox_root, &shutdown);
                });
            }
            Err(ref e) if e.kind() == std::io::ErrorKind::WouldBlock => {
                thread::sleep(Duration::from_millis(50));
            }
            Err(e) => {
                warn!(error = %e, "accept failed");
                thread::sleep(Duration::from_millis(50));
            }
        }
    }
    Ok(())
}

/// Handle a single HTTP connection.
fn handle_connection(
    mut stream: TcpStream,
    inbox_root: &Path,
    shutdown: &Arc<AtomicBool>,
) -> std::io::Result<()> {
    stream.set_read_timeout(Some(HTTP_KEEPALIVE_TIMEOUT))?;
    stream.set_write_timeout(Some(Duration::from_secs(5)))?;

    let mut reader = BufReader::new(stream.try_clone()?);
    let mut request_line = String::new();
    if reader.read_line(&mut request_line)? == 0 {
        return Ok(());
    }
    let mut headers = Vec::new();
    loop {
        let mut line = String::new();
        let n = reader.read_line(&mut line)?;
        if n == 0 || line == "\r\n" {
            break;
        }
        headers.push(line);
    }

    let mut parts = request_line.split_whitespace();
    let method = parts.next().unwrap_or("");
    let target = parts.next().unwrap_or("");
    let _version = parts.next().unwrap_or("");

    let (rt, id) = parse_route(target);

    let body = match rt {
        Route::Health => Some(simple_text(200, "ok")),
        Route::Index => Some(text_response(
            200,
            &crate::views::render_inbox_index_html(
                &list_pending(inbox_root).unwrap_or_default(),
            ),
        )),
        Route::InboxForm => match id.and_then(|id| load(inbox_root, &id).ok()) {
            Some(req) if matches!(req.state, RequestState::Expired) => {
                Some(text_response(200, &crate::views::render_expired_html(&req)))
            }
            Some(req) => Some(text_response(200, &render_inbox_html(&req))),
            None => Some(simple_text(404, "request not found")),
        },
        Route::Answer => {
            let id = match id {
                Some(id) => id,
                None => {
                    return write_response(
                        &mut stream,
                        400,
                        "Bad Request",
                        "text/plain; charset=utf-8",
                        b"missing id",
                    )
                }
            };
            if method == "GET" {
                match load(inbox_root, &id) {
                    Ok(req) if matches!(req.state, RequestState::Expired) => {
                        Some(text_response(200, &crate::views::render_expired_html(&req)))
                    }
                    Ok(req) => Some(text_response(200, &render_inbox_html(&req))),
                    Err(_) => Some(simple_text(404, "request not found")),
                }
            } else if method != "POST" {
                return write_response(
                    &mut stream,
                    405,
                    "Method Not Allowed",
                    "text/plain; charset=utf-8",
                    b"",
                );
            } else {
                let content_length = headers
                    .iter()
                    .find_map(|h| {
                        let (k, v) = h.split_once(':')?;
                        if k.eq_ignore_ascii_case("content-length") {
                            v.trim().parse::<usize>().ok()
                        } else {
                            None
                        }
                    })
                    .unwrap_or(0);
                let mut buf = vec![0u8; content_length];
                if content_length > 0 {
                    reader.read_exact(&mut buf)?;
                }
                match load(inbox_root, &id) {
                    Ok(req) if matches!(req.state, RequestState::Expired) => {
                        Some(text_response(
                            410,
                            "<h1>Request Expired</h1>\
                                 <p>This request expired and can no longer be answered.</p>\
                                 <a href=/inbox>Return to inbox</a>",
                        ))
                    }
                    _ => match super::form::submit_answer(inbox_root, &id, &buf) {
                        Ok(()) => {
                            redirect_response(&mut stream, &format!("/inbox/{id}/done"))?
                        }
                        Err(e) => Some(text_response(400, &format!("<h1>Error</h1><p>{e}</p>"))),
                    },
                }
            }
        }
        Route::Done => match id.and_then(|id| load(inbox_root, &id).ok()) {
            Some(req) => {
                let html = crate::views::render_answer_html(
                    &req.request_id,
                    matches!(req.state, RequestState::Answered),
                    if matches!(req.state, RequestState::Answered) {
                        "Your answer was recorded."
                    } else {
                        "Request cancelled."
                    },
                );
                Some(text_response(200, &html))
            }
            None => Some(simple_text(404, "request not found")),
        },
        Route::Static(p) => match p.as_str() {
            "" | "index.css" | "index.html" => return write_response(
                &mut stream,
                200,
                "OK",
                "text/css; charset=utf-8",
                render_inbox_css().as_bytes(),
            ),
            other if other.ends_with(".css") => return write_response(
                &mut stream,
                200,
                "OK",
                "text/css; charset=utf-8",
                render_inbox_css().as_bytes(),
            ),
            other => {
                let body = format!("not found: {other}");
                return write_response(
                    &mut stream,
                    404,
                    "Not Found",
                    "text/plain; charset=utf-8",
                    body.as_bytes(),
                );
            }
        },
        Route::NotFound => Some(simple_text(404, "not found")),
        Route::Shutdown => {
            if method == "POST" {
                shutdown.store(true, Ordering::SeqCst);
                Some(simple_text(200, "shutting down"))
            } else {
                Some(simple_text(403, "use POST"))
            }
        }
    };

    let body = body.unwrap_or_else(|| simple_text(500, "internal"));
    write_response(
        &mut stream,
        200,
        "OK",
        "text/html; charset=utf-8",
        body.as_bytes(),
    )?;
    Ok(())
}
