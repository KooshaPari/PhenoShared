// Phinbox — Row View

import SwiftUI

struct RowView: View {
    let request: PendingRequest
    let mgr: InboxManager

    @State private var isHovered = false

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(spacing: 8) {
                Image(systemName: urgencyIcon).font(.system(size: 11)).foregroundStyle(urgencyColor)
                Text(request.spec.title).font(.system(.body, weight: .semibold))
                    .foregroundStyle(.white).lineLimit(1)
                Spacer()
                Text(mgr.timeAgo(request.queued_at_ms)).font(.caption).foregroundStyle(.white.opacity(0.35))
            }
            Text(request.spec.question).font(.subheadline)
                .foregroundStyle(.white.opacity(0.55)).lineLimit(2)
            HStack(spacing: 10) {
                Label(request.origin.process, systemImage: "terminal")
                Label(request.spec.field.kind, systemImage: fieldIcon)
            }.font(.caption).foregroundStyle(.white.opacity(0.35))
        }
        .padding(.vertical, 6)
        .contentShape(Rectangle())
        .background(isHovered ? Color.teal.opacity(0.08) : Color.clear)
        .animation(.easeInOut(duration: 0.15), value: isHovered)
        .onHover { hovering in withAnimation { self.isHovered = hovering } }
    }

    private var urgencyColor: Color {
        switch request.spec.urgency {
        case .error:   return .red
        case .warning: return .orange
        case .secret:  return .yellow
        case .info, .none: return Color.teal
        }
    }

    private var urgencyIcon: String {
        switch request.spec.urgency {
        case .error:   return "exclamationmark.circle.fill"
        case .warning: return "exclamationmark.triangle.fill"
        case .secret:  return "lock.fill"
        case .info, .none: return "envelope.fill"
        }
    }

    private var fieldIcon: String {
        switch request.spec.field.kind {
        case "bool":       return "switch.2"
        case "choice":     return "list.bullet"
        case "text", "long_text": return "text.alignleft"
        case "integer":    return "number"
        case "date_time":  return "calendar"
        default:           return "questionmark.circle"
        }
    }
}
