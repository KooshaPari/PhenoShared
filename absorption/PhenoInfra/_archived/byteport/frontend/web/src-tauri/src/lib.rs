use byteport_transport::{S3UploadTransport, UploadTransport};

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let _transport: Box<dyn UploadTransport> = Box::new(S3UploadTransport::new(
        "https://uploads.byteport.local",
        "byteport-uploads",
        Some("desktop"),
    ));
    tauri::Builder::default()
        .plugin(tauri_plugin_os::init())
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
