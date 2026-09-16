pub mod clipboard;
pub mod config;
pub mod error;
pub mod image_preview;
pub mod image_processor;
pub mod installer;
pub mod interceptor;
pub mod service;
pub mod shell_hooks;
pub mod stdout_monitor;
pub mod util;

pub use error::{Error, Result};
pub use util::{
    detect_display_server, detect_wayland_compositor, format_duration, format_file_size,
    generate_screenshot_filename, get_app_dir, get_available_clipboard_tools,
    get_available_screenshot_tools, get_config_dir, get_home_dir, is_command_available,
    is_image_file, DisplayServer,
};

// Re-export constants
pub use util::{
    APP_NAME, CONFIG_FILE, DEFAULT_CLEANUP_DAYS, DEFAULT_POLL_INTERVAL, HOOKS_DIR,
    IMAGE_COMMAND_PATTERNS, IMAGE_PROCESS_NAMES, IMAGE_QUALITY, LOG_FILE, MACOS_CLIPBOARD_TOOLS,
    MACOS_SCREENSHOT_TOOLS, MAX_FILE_SIZE, MAX_RECENT_SCREENSHOTS, PID_FILE, SCREENSHOT_DIR,
    SERVICE_CHECK_INTERVAL, SUPPORTED_FORMATS, TEMP_DIR, VERSION, WAYLAND_CLIPBOARD_TOOLS,
    WAYLAND_SCREENSHOT_TOOLS, X11_CLIPBOARD_TOOLS, X11_SCREENSHOT_TOOLS,
};
