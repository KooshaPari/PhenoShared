// Phinbox — Root View

import SwiftUI

struct RootView: View {
    @ObservedObject var mgr: InboxManager
    @State private var appeared = false
    @State private var searchText = ""
    @State private var pulse = false
    @FocusState private var listFocused: Bool

    var body: some View {
        Group {
            if !appeared { splash } else { mainContent }
        }
        .onAppear { appeared = true }
    }

    // MARK: - Splash

    private var splash: some View {
        ZStack {
            Color.appBG.ignoresSafeArea()
            VStack(spacing: 20) {
                EnvelopeIcon(size: 40)
                Text("Phinbox").font(.system(size: 28, weight: .bold, design: .rounded)).foregroundStyle(.white)
                Text("Connecting to daemon...").font(.subheadline).foregroundStyle(.white.opacity(0.5))
                ProgressView().tint(Color.teal)
            }
        }
    }

    // MARK: - Main Content

    private var mainContent: some View {
        NavigationSplitView {
            sidebar
        } detail: {
            if let r = mgr.selected {
                DetailView(request: r, mgr: mgr)
            } else {
                detailEmptyState
            }
        }
        .background(Color.appBG.ignoresSafeArea())
        .tint(Color.teal)
    }

    // MARK: - Detail Empty State

    private var detailEmptyState: some View {
        VStack(spacing: 16) {
            Spacer()
            EnvelopeIcon(size: 56)
                .foregroundStyle(.white.opacity(0.2))
                .padding(.bottom, 4)
            Text("No Request Selected")
                .font(.title3).fontWeight(.medium)
                .foregroundStyle(.white.opacity(0.6))
            Text("Select a request from the sidebar to view its details.")
                .font(.subheadline)
                .foregroundStyle(.white.opacity(0.35))
                .multilineTextAlignment(.center)
            Spacer()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color.appBG)
    }

    // MARK: - Sidebar

    private var sidebar: some View {
        Group {
            if mgr.requests.isEmpty {
                emptyInboxState
            } else {
                requestList
            }
        }
        .navigationTitle("Inbox (\(mgr.requests.count))")
        .toolbar {
            ToolbarItem(placement: .automatic) {
                Button { mgr.refresh() } label: { Image(systemName: "arrow.clockwise") }
            }
            ToolbarItem(placement: .automatic) {
                Image(systemName: "magnifyingglass")
                    .foregroundStyle(.white.opacity(searchText.isEmpty ? 0.3 : 0.7))
            }
        }
        .searchable(text: $searchText, placement: .sidebar, prompt: "Filter requests...")
    }

    // MARK: - Empty Inbox State

    private var emptyInboxState: some View {
        VStack(spacing: 16) {
            Spacer()
            EnvelopeIcon(size: 48)
                .opacity(0.3)
                .scaleEffect(pulse ? 1.12 : 1.0)
                .animation(
                    .easeInOut(duration: 2).repeatForever(autoreverses: true),
                    value: pulse
                )
                .onAppear { pulse = true }
            Text("Inbox Empty")
                .font(.title2).fontWeight(.medium).foregroundStyle(.white)
            Text("Requests from AI agents\nwill appear here.")
                .font(.subheadline).foregroundStyle(.white.opacity(0.5)).multilineTextAlignment(.center)
            Spacer()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - Filtered Requests

    private var filteredRequests: [PendingRequest] {
        guard !searchText.isEmpty else { return mgr.requests }
        let query = searchText.lowercased()
        return mgr.requests.filter { req in
            req.spec.title.lowercased().contains(query)
                || req.spec.question.lowercased().contains(query)
                || req.origin.process.lowercased().contains(query)
        }
    }

    // MARK: - Request List

    private var requestList: some View {
        List(selection: $mgr.selected) {
            ForEach(filteredRequests) { req in
                RowView(request: req, mgr: mgr)
                    .tag(req)
            }
        }
        .listStyle(.sidebar)
        .scrollContentBackground(.hidden)
        .focused($listFocused)
        .onKeyPress(.upArrow) {
            moveSelection(direction: -1)
            return .handled
        }
        .onKeyPress(.downArrow) {
            moveSelection(direction: 1)
            return .handled
        }
        .onAppear { listFocused = true }
    }

    // MARK: - Keyboard Navigation

    private func moveSelection(direction: Int) {
        let requests = filteredRequests
        guard !requests.isEmpty else { return }

        if let current = mgr.selected,
           let idx = requests.firstIndex(where: { $0.id == current.id }) {
            let next = idx + direction
            if next >= 0, next < requests.count {
                mgr.selected = requests[next]
            }
        } else {
            mgr.selected = direction > 0 ? requests.first : requests.last
        }
    }
}
