// Phinbox — Inbox Manager

import Foundation
import SwiftUI
import AppKit

@MainActor
class InboxManager: ObservableObject {
    @Published var requests: [PendingRequest] = []
    @Published var selected: PendingRequest?
    @Published var submitError: String?

    let inboxDir: URL
    private var fileSource: DispatchSourceFileSystemObject?
    private var timer: Timer?
    private var debounceWorkItem: DispatchWorkItem?
    nonisolated private static let maxDisplayedRequests = 200

    init() {
        let home = FileManager.default.homeDirectoryForCurrentUser
        inboxDir = home.appendingPathComponent("Library/Application Support/phinbox/inbox")
    }

    deinit {
        fileSource?.cancel()
        timer?.invalidate()
    }

    // MARK: - Public

    func start() {
        refresh()
        startWatching()
    }

    func refresh() {
        // Perform file I/O on a background thread, then publish on MainActor.
        let dir = inboxDir
        let fm = FileManager.default
        let expiredDir = dir.appendingPathComponent("expired")

        Task.detached { [weak self] in
            guard let self else { return }

            // Read directory contents off main thread.
            guard let files = try? fm.contentsOfDirectory(
                at: dir, includingPropertiesForKeys: nil, options: .skipsHiddenFiles
            ) else {
                await MainActor.run { self.requests = [] }
                return
            }

            var loaded: [PendingRequest] = []
            for f in files where f.pathExtension == "json" {
                guard let data = try? Data(contentsOf: f),
                      let req = try? JSONDecoder().decode(PendingRequest.self, from: data),
                      req.state == "pending" else { continue }
                loaded.append(req)
            }

            // Disk cleanup: move expired requests to expired/ subdirectory.
            let nowMs = UInt64(Date().timeIntervalSince1970 * 1000)
            let expired = loaded.filter { $0.expires_at_ms < nowMs }
            if !expired.isEmpty {
                try? fm.createDirectory(at: expiredDir, withIntermediateDirectories: true)
                for req in expired {
                    let src = dir.appendingPathComponent("\(req.request_id).json")
                    let dst = expiredDir.appendingPathComponent("\(req.request_id).json")
                    try? fm.moveItem(at: src, to: dst)
                }
                loaded.removeAll { $0.expires_at_ms < nowMs }
            }

            // Urgency sort using the typed enum's Comparable conformance.
            loaded.sort { a, b in
                let ua = a.spec.urgency ?? .info
                let ub = b.spec.urgency ?? .info
                return ua != ub ? ua < ub : a.queued_at_ms > b.queued_at_ms
            }

            // Diff-based: only animate if the request ID set actually changed.
            let newIDs = Set(loaded.map(\.request_id))
            let capped = Array(loaded.prefix(Self.maxDisplayedRequests))

            await MainActor.run { [weak self] in
                guard let self else { return }
                let oldIDs = Set(self.requests.map(\.request_id))
                if newIDs != oldIDs {
                    withAnimation(.spring(response: 0.4)) { self.requests = capped }
                    // Play a subtle beep when new requests arrive.
                    if newIDs.isDisjoint(with: oldIDs) && !newIDs.isEmpty {
                        NSSound.beep()
                    }
                } else {
                    self.requests = capped
                }
            }
        }
    }

    func submit(_ req: PendingRequest, value: String, notes: String?) async {
        submitError = nil
        var comps = URLComponents(string: "http://127.0.0.1:7117/inbox/\(req.request_id)/answer")!
        var items = [URLQueryItem(name: "value", value: value), URLQueryItem(name: "confirm", value: "ok")]
        if let notes, !notes.isEmpty { items.append(URLQueryItem(name: "notes", value: notes)) }
        comps.queryItems = items
        var r = URLRequest(url: comps.url!); r.httpMethod = "POST"
        do {
            let (_, resp) = try await URLSession.shared.data(for: r)
            if let h = resp as? HTTPURLResponse, h.statusCode == 200 {
                withAnimation { selected = nil }
                try? await Task.sleep(for: .seconds(0.5)); refresh()
            } else { submitError = "Server error" }
        } catch { submitError = error.localizedDescription }
    }

    func timeAgo(_ ms: UInt64) -> String {
        let now = UInt64(Date().timeIntervalSince1970 * 1000)
        guard now > ms else { return "just now" }
        let d = now - ms
        if d < 60_000 { return "\(d/1000)s" }
        if d < 3_600_000 { return "\(d/60_000)m" }
        if d < 86_400_000 { return "\(d/3_600_000)h" }
        return "\(d/86_400_000)d"
    }

    // MARK: - File System Watcher

    private func startWatching() {
        // Ensure the directory exists before trying to watch it.
        try? FileManager.default.createDirectory(at: inboxDir, withIntermediateDirectories: true)

        let fd = Darwin.open(inboxDir.path, O_EVTONLY)
        guard fd >= 0 else {
            startTimerFallback(); return
        }

        let source = DispatchSource.makeFileSystemObjectSource(
            fileDescriptor: fd,
            eventMask: [.write, .rename, .delete],
            queue: .global(qos: .utility)
        )
        source.setEventHandler { [weak self] in
            // Dispatch debounce logic back to the main actor.
            Task { @MainActor [weak self] in
                self?.debouncedRefresh()
            }
        }
        source.setCancelHandler {
            Darwin.close(fd)
        }
        source.resume()
        fileSource = source
    }

    private func startTimerFallback() {
        timer?.invalidate()
        timer = Timer.scheduledTimer(withTimeInterval: 5.0, repeats: true) { [weak self] _ in
            Task { @MainActor in self?.refresh() }
        }
    }

    /// Debounce: coalesce rapid file system events into a single refresh after 0.3s.
    /// Runs on MainActor; the actual refresh does file I/O on a background thread.
    private func debouncedRefresh() {
        debounceWorkItem?.cancel()
        let work = DispatchWorkItem { [weak self] in
            Task { @MainActor in self?.refresh() }
        }
        debounceWorkItem = work
        DispatchQueue.global(qos: .utility).asyncAfter(deadline: .now() + 0.3, execute: work)
    }
}
