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
    let configuration: InboxConfiguration
    private var fileSource: DispatchSourceFileSystemObject?
    private var timer: Timer?
    private var debounceWorkItem: DispatchWorkItem?
    nonisolated private static let maxDisplayedRequests = 200

    init(configuration: InboxConfiguration) {
        self.configuration = configuration
        inboxDir = configuration.root.appendingPathComponent("inbox")
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
                      ["pending", "seen"].contains(req.state) else { continue }
                loaded.append(req)
            }

            // Rust owns expiry/finalization. The native client never moves queue files.
            let nowMs = UInt64(Date().timeIntervalSince1970 * 1000)
            loaded.removeAll { $0.expires_at_ms <= nowMs }

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
                if let selected = self.selected, !newIDs.contains(selected.request_id) { self.selected = nil }
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

    func submit(_ req: PendingRequest, value: String?, notes: String?,
                action: RequestTransport.Action = .confirm) async {
        submitError = nil
        do {
            let request = try RequestTransport.request(configuration: configuration,
                id: req.request_id, action: action, value: value, notes: notes)
            let (_, response) = try await URLSession.shared.data(for: request)
            guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
                let status = (response as? HTTPURLResponse)?.statusCode ?? 0
                submitError = "Request refused (HTTP \(status)). Refresh to check expiry or an earlier answer."
                refresh(); return
            }
            withAnimation { selected = nil }
            refresh()
        } catch { submitError = "Unable to submit to the local inbox daemon." }
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
