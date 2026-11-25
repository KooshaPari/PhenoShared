//! Linux window capture via X11 + XCB.

use crate::domain::capture::CaptureError;
use crate::ports::{CapturedFrame, WindowCapturer, WindowDescriptor};

#[cfg(target_os = "linux")]
// xcb 1.7 made the generated protocol bindings a public module (`xcb::x`);
// the old top-level `xcb::xproto` path is private.
use xcb::x as xproto;
#[cfg(target_os = "linux")]
use xcb::{Xid, XidNew};

#[derive(Debug, Default)]
pub struct X11WindowCapturer;

impl X11WindowCapturer {
    pub fn new() -> Self {
        Self
    }
}

#[cfg(target_os = "linux")]
impl WindowCapturer for X11WindowCapturer {
    fn capture(&self, window_id: u64) -> Result<CapturedFrame, CaptureError> {
        let (connection, screen_num) = xcb::Connection::connect(None)
            .map_err(|e| CaptureError::CaptureFailed(e.to_string()))?;
        let setup = connection.get_setup();
        let screen = setup
            .roots()
            .nth(screen_num as usize)
            .ok_or_else(|| CaptureError::CaptureFailed("X11 screen not found".to_string()))?;
        let xid = u32::try_from(window_id).map_err(|_| {
            CaptureError::CaptureFailed(format!(
                "window id {window_id} does not fit in a 32-bit XID"
            ))
        })?;
        let drawable = xproto::Drawable::Window(xproto::Window::new(xid));
        let geometry = connection
            .wait_for_reply(connection.send_request(&xproto::GetGeometry { drawable }))
            .map_err(|e| CaptureError::CaptureFailed(format!("get_geometry: {e}")))?;

        let reply = connection
            .wait_for_reply(connection.send_request(&xproto::GetImage {
                format: xproto::ImageFormat::ZPixmap,
                drawable,
                x: 0,
                y: 0,
                width: geometry.width(),
                height: geometry.height(),
                plane_mask: u32::MAX,
            }))
            .map_err(|e| CaptureError::CaptureFailed(format!("get_image: {e}")))?;

        let bits_per_pixel = bits_per_pixel_for_depth(screen.root_depth()).ok_or_else(|| {
            CaptureError::CaptureFailed(format!(
                "unsupported root depth {} for X11 capture",
                screen.root_depth()
            ))
        })?;
        let pixels = decode_zpixmap_bgra(
            reply.data(),
            geometry.width() as u32,
            geometry.height() as u32,
            bits_per_pixel,
        )?;

        Ok(CapturedFrame {
            width: geometry.width() as u32,
            height: geometry.height() as u32,
            pixels,
        })
    }

    fn list_windows(&self) -> Result<Vec<WindowDescriptor>, CaptureError> {
        let (connection, screen_num) = xcb::Connection::connect(None)
            .map_err(|e| CaptureError::CaptureFailed(e.to_string()))?;
        let setup = connection.get_setup();
        let screen = setup
            .roots()
            .nth(screen_num as usize)
            .ok_or_else(|| CaptureError::CaptureFailed("X11 screen not found".to_string()))?;
        let tree = connection
            .wait_for_reply(connection.send_request(&xproto::QueryTree {
                window: screen.root(),
            }))
            .map_err(|e| CaptureError::CaptureFailed(format!("query_tree: {e}")))?;

        tree.children()
            .iter()
            .copied()
            .filter_map(|window| describe_window(&connection, window).transpose())
            .collect()
    }
}

#[cfg(not(target_os = "linux"))]
impl WindowCapturer for X11WindowCapturer {
    fn capture(&self, _window_id: u64) -> Result<CapturedFrame, CaptureError> {
        Err(CaptureError::CaptureFailed(
            "X11WindowCapturer is only available on Linux".to_string(),
        ))
    }

    fn list_windows(&self) -> Result<Vec<WindowDescriptor>, CaptureError> {
        Err(CaptureError::CaptureFailed(
            "X11WindowCapturer is only available on Linux".to_string(),
        ))
    }
}

#[cfg(target_os = "linux")]
fn describe_window(
    connection: &xcb::Connection,
    window: xproto::Window,
) -> Result<Option<WindowDescriptor>, CaptureError> {
    let geometry = match connection.wait_for_reply(connection.send_request(&xproto::GetGeometry {
        drawable: xproto::Drawable::Window(window),
    })) {
        Ok(geometry) => geometry,
        Err(_) => return Ok(None),
    };
    let title = get_window_title(connection, window)?;
    Ok(Some(WindowDescriptor {
        id: u64::from(window.resource_id()),
        title,
        width: geometry.width() as u32,
        height: geometry.height() as u32,
    }))
}

#[cfg(target_os = "linux")]
fn get_window_title(
    connection: &xcb::Connection,
    window: xproto::Window,
) -> Result<String, CaptureError> {
    let reply = connection
        .wait_for_reply(connection.send_request(&xproto::GetProperty {
            delete: false,
            window,
            property: xproto::ATOM_WM_NAME,
            r#type: xproto::ATOM_STRING,
            long_offset: 0,
            long_length: 1024,
        }))
        .map_err(|e| CaptureError::CaptureFailed(format!("get_property WM_NAME: {e}")))?;
    // WM_NAME is conventionally 8-bit (STRING). A 32-bit property is not a
    // string we can decode here, so it yields an empty title rather than a
    // bogus one.
    if reply.format() == 8 {
        Ok(String::from_utf8_lossy(reply.value::<u8>()).into_owned())
    } else {
        Ok(String::new())
    }
}

fn bits_per_pixel_for_depth(depth: u8) -> Option<u8> {
    match depth {
        32 | 24 => Some(32),
        16 => Some(16),
        _ => None,
    }
}

fn decode_zpixmap_bgra(
    data: &[u8],
    width: u32,
    height: u32,
    bits_per_pixel: u8,
) -> Result<Vec<u8>, CaptureError> {
    let bytes_per_pixel = usize::from(bits_per_pixel / 8);
    if bytes_per_pixel == 0 {
        return Err(CaptureError::CaptureFailed(
            "bits_per_pixel must be at least 8".to_string(),
        ));
    }

    let pixel_count = width
        .checked_mul(height)
        .ok_or_else(|| CaptureError::CaptureFailed("frame dimensions overflow".to_string()))?
        as usize;
    let expected_len = pixel_count
        .checked_mul(bytes_per_pixel)
        .ok_or_else(|| CaptureError::CaptureFailed("frame byte count overflow".to_string()))?;

    if data.len() < expected_len {
        return Err(CaptureError::CaptureFailed(format!(
            "X11 image payload too short: expected at least {expected_len} bytes, got {}",
            data.len()
        )));
    }

    let mut pixels = Vec::with_capacity(pixel_count * 4);
    for chunk in data[..expected_len].chunks_exact(bytes_per_pixel) {
        match bits_per_pixel {
            32 => pixels.extend_from_slice(&[chunk[2], chunk[1], chunk[0], chunk[3]]),
            16 => {
                let value = u16::from_ne_bytes([chunk[0], chunk[1]]);
                let red = ((value >> 11) & 0x1f) as u8;
                let green = ((value >> 5) & 0x3f) as u8;
                let blue = (value & 0x1f) as u8;
                pixels.extend_from_slice(&[
                    (red << 3) | (red >> 2),
                    (green << 2) | (green >> 4),
                    (blue << 3) | (blue >> 2),
                    0xff,
                ]);
            },
            _ => {
                return Err(CaptureError::CaptureFailed(format!(
                    "unsupported bits_per_pixel {bits_per_pixel}"
                )));
            },
        }
    }

    Ok(pixels)
}

#[cfg(test)]
mod tests {
    use super::{bits_per_pixel_for_depth, decode_zpixmap_bgra};

    #[test]
    fn maps_common_x11_depths_to_bpp() {
        assert_eq!(bits_per_pixel_for_depth(24), Some(32));
        assert_eq!(bits_per_pixel_for_depth(16), Some(16));
        assert_eq!(bits_per_pixel_for_depth(8), None);
    }

    #[test]
    fn decodes_32bpp_bgra_pixels_into_rgba() {
        let pixels =
            decode_zpixmap_bgra(&[0x10, 0x20, 0x30, 0x40, 0xaa, 0xbb, 0xcc, 0xdd], 2, 1, 32)
                .expect("32bpp conversion should succeed");

        assert_eq!(pixels, vec![0x30, 0x20, 0x10, 0x40, 0xcc, 0xbb, 0xaa, 0xdd]);
    }
}
