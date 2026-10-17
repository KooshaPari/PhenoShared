// Phinbox — DetailView Helpers

import SwiftUI

// MARK: - Default Initialization

extension DetailView {
    func loadDefaults() {
        notes = request.spec.notes?.defaultValue ?? ""
        switch request.spec.field {
        case .text(_, let def, _, _, _, _):
            textVal = def ?? ""
        case .longText(_, let def, _):
            textVal = def ?? ""
        case .integer(_, _, _, let def):
            intVal = def.map(String.init) ?? ""
        case .boolean(_, let def):
            boolVal = def ?? false
        case .choice(_, let opts, let defaultIndex):
            if let idx = defaultIndex, idx >= 0, idx < opts.count {
                choice = opts[idx].value
            }
        case .dateTime(_, let def, let kind):
            if let def, let parsed = Self.parseDate(def, kind: kind) {
                dateVal = parsed
            }
        case .unknown:
            break
        }
    }
}

// MARK: - Timer

extension DetailView {
    func updateRemaining() {
        let now = UInt64(Date().timeIntervalSince1970 * 1000)
        if request.expires_at_ms <= now {
            remainingSeconds = 0
        } else {
            remainingSeconds = Int((request.expires_at_ms - now) / 1000)
        }
    }
}

// MARK: - State Icons

extension DetailView {
    var urgencyIcon: String {
        switch request.spec.urgency {
        case .error:   return "exclamationmark.circle.fill"
        case .warning: return "exclamationmark.triangle.fill"
        case .secret:  return "lock.fill"
        case .info, .none: return "info.circle.fill"
        }
    }

    var urgencyColor: Color {
        switch request.spec.urgency {
        case .error:   return .red
        case .warning: return .orange
        case .secret:  return .yellow
        case .info, .none: return Color.teal
        }
    }

    var expiryLabel: String {
        if remainingSeconds > 0 {
            let mins = remainingSeconds / 60
            let secs = remainingSeconds % 60
            return String(format: "%d:%02d", mins, secs)
        }
        return "Expired"
    }
}

// MARK: - Field Input

extension DetailView {
    func fieldInput(placeholder: String, binding: Binding<String>,
                    multiline: Bool, maxLength: Int?) -> some View {
        Group {
            if multiline {
                TextEditor(text: binding)
                    .scrollContentBackground(.hidden)
                    .frame(minHeight: 80, maxHeight: 160).padding(12)
            } else {
                TextField(placeholder, text: binding)
                    .textFieldStyle(.plain).padding(12)
            }
        }
        .modifier(MaxLengthModifier(text: binding, maxLength: maxLength))
        .background(
            RoundedRectangle(cornerRadius: 10, style: .continuous)
                .fill(Color.white.opacity(0.04))
                .overlay(RoundedRectangle(cornerRadius: 10, style: .continuous)
                    .stroke(Color.white.opacity(0.1)))
        )
    }
}

// MARK: - Date Utilities

extension DetailView {
    private static let rfc3339: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return f
    }()

    private static let rfc3339NoFractional: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime]
        return f
    }()

    static func rfc3339Date(_ str: String) -> Date? {
        rfc3339.date(from: str) ?? rfc3339NoFractional.date(from: str)
    }
}

// MARK: - MaxLength Modifier

struct MaxLengthModifier: ViewModifier {
    let text: Binding<String>
    let maxLength: Int?

    func body(content: Content) -> some View {
        if let limit = maxLength {
            content
                .onChange(of: text.wrappedValue) { _, new in
                    if new.count > limit {
                        text.wrappedValue = String(new.prefix(limit))
                    }
                }
        } else {
            content
        }
    }
}

extension DetailView {
    static func wireDate(_ date: Date, kind: String?) -> String {
        if kind == "date" || kind == "time" {
            let formatter = DateFormatter()
            formatter.locale = Locale(identifier: "en_US_POSIX")
            formatter.dateFormat = kind == "date" ? "yyyy-MM-dd" : "HH:mm"
            return formatter.string(from: date)
        }
        return ISO8601DateFormatter().string(from: date)
    }
    static func parseDate(_ value: String, kind: String?) -> Date? {
        if kind == "date" || kind == "time" {
            let formatter = DateFormatter()
            formatter.locale = Locale(identifier: "en_US_POSIX")
            formatter.dateFormat = kind == "date" ? "yyyy-MM-dd" : "HH:mm"
            return formatter.date(from: value)
        }
        return rfc3339Date(value)
    }
    @ViewBuilder var detailsCard: some View {
        if let details = request.spec.details {
            VStack(alignment: .leading, spacing: 10) {
                if let command = details.command { Text(command).font(.system(.body, design: .monospaced)) }
                if let reason = details.reason { Text(reason) }
                ForEach(Array((details.items ?? []).enumerated()), id: \.offset) { _, item in Text(item.display) }
                ForEach(Array((details.effects ?? []).enumerated()), id: \.offset) { _, effect in Text("Effect: " + effect) }
            }
            .textSelection(.enabled)
            .padding(20).frame(maxWidth: .infinity, alignment: .leading).background(glass)
        }
    }
}
