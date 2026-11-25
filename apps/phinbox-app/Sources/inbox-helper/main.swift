// Phinbox Inbox Helper — Entry Point
// Compiles: swiftc -parse-as-library -o inbox-helper *.swift -framework SwiftUI -framework AppKit

import SwiftUI
import AppKit

@main
struct PhinboxApp {
    static func main() {
        let app = NSApplication.shared
        app.setActivationPolicy(.regular)

        // Load branded app icon from bundle
        if let iconURL = Bundle.main.url(forResource: "AppIcon", withExtension: "icns"),
           let icon = NSImage(contentsOf: iconURL) {
            app.applicationIconImage = icon
        }

        let manager: InboxManager = MainActor.assumeIsolated { InboxManager() }

        // Restore saved window frame
        let savedFrame = UserDefaults.standard.string(forKey: "PhinboxWindowFrame")
        let screen = NSScreen.main?.visibleFrame ?? NSRect(x: 0, y: 0, width: 1200, height: 800)
        let winW = 720.0, winH = 600.0
        let winX = screen.midX - winW / 2, winY = screen.midY - winH / 2

        var initialFrame = NSRect(x: winX, y: winY, width: winW, height: winH)
        if let saved = savedFrame, let rect = NSRectFromString(saved) as NSRect?, rect.width > 0, rect.height > 0 {
            // Ensure the saved frame is still on a visible screen
            if screen.intersects(rect) {
                initialFrame = rect
            }
        }

        let window = NSWindow(
            contentRect: initialFrame,
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered, defer: false
        )
        window.title = "Phinbox"
        window.minSize = NSSize(width: 520, height: 400)
        window.isReleasedWhenClosed = false
        window.titlebarAppearsTransparent = false
        window.titleVisibility = .visible
        window.isMovableByWindowBackground = true
        window.collectionBehavior = [.moveToActiveSpace, .fullScreenAuxiliary]

        // Set window icon from bundle resource
        if let iconURL = Bundle.main.url(forResource: "AppIcon", withExtension: "icns"),
           let icon = NSImage(contentsOf: iconURL) {
            icon.size = NSSize(width: 16, height: 16)
            window.contentView?.window?.standardWindowButton(.documentIconButton)?.image = icon
        }

        let hosting = NSHostingView(rootView: RootView(mgr: manager))
        hosting.translatesAutoresizingMaskIntoConstraints = false
        window.contentView = hosting
        if let cv = window.contentView {
            NSLayoutConstraint.activate([
                hosting.topAnchor.constraint(equalTo: cv.topAnchor),
                hosting.bottomAnchor.constraint(equalTo: cv.bottomAnchor),
                hosting.leadingAnchor.constraint(equalTo: cv.leadingAnchor),
                hosting.trailingAnchor.constraint(equalTo: cv.trailingAnchor),
            ])
        }

        window.makeKeyAndOrderFront(nil)
        app.activate(ignoringOtherApps: true)
        MainActor.assumeIsolated { manager.start() }

        // Save window frame on move/resize
        NotificationCenter.default.addObserver(
            forName: NSWindow.didMoveNotification,
            object: window,
            queue: .main
        ) { _ in
            UserDefaults.standard.set(NSStringFromRect(window.frame), forKey: "PhinboxWindowFrame")
        }
        NotificationCenter.default.addObserver(
            forName: NSWindow.didResizeNotification,
            object: window,
            queue: .main
        ) { _ in
            UserDefaults.standard.set(NSStringFromRect(window.frame), forKey: "PhinboxWindowFrame")
        }

        // SIGUSR1 handler
        signal(30, SIG_IGN)
        let sigSrc = DispatchSource.makeSignalSource(signal: 30, queue: .main)
        sigSrc.setEventHandler {
            app.activate(ignoringOtherApps: true)
            window.makeKeyAndOrderFront(nil)
        }
        sigSrc.resume()

        // Menu bar
        let mainMenu = NSMenu()
        let appMenuItem = NSMenuItem()
        mainMenu.addItem(appMenuItem)
        let appMenu = NSMenu()
        appMenu.addItem(withTitle: "About Phinbox", action: #selector(NSApplication.orderFrontStandardAboutPanel(_:)), keyEquivalent: "")
        appMenu.addItem(NSMenuItem.separator())
        appMenu.addItem(withTitle: "Quit Phinbox", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        appMenuItem.submenu = appMenu

        let editMenuItem = NSMenuItem()
        mainMenu.addItem(editMenuItem)
        let editMenu = NSMenu(title: "Edit")
        editMenu.addItem(withTitle: "Undo", action: Selector(("undo:")), keyEquivalent: "z")
        editMenu.addItem(withTitle: "Redo", action: Selector(("redo:")), keyEquivalent: "Z")
        editMenu.addItem(NSMenuItem.separator())
        editMenu.addItem(withTitle: "Cut", action: #selector(NSText.cut(_:)), keyEquivalent: "x")
        editMenu.addItem(withTitle: "Copy", action: #selector(NSText.copy(_:)), keyEquivalent: "c")
        editMenu.addItem(withTitle: "Paste", action: #selector(NSText.paste(_:)), keyEquivalent: "v")
        editMenu.addItem(withTitle: "Select All", action: #selector(NSText.selectAll(_:)), keyEquivalent: "a")
        editMenuItem.submenu = editMenu

        let viewMenuItem = NSMenuItem()
        mainMenu.addItem(viewMenuItem)
        let viewMenu = NSMenu(title: "View")
        viewMenuItem.submenu = viewMenu

        app.mainMenu = mainMenu
        app.run()
    }
}
