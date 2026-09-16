// Phinbox — Brand Colors + Envelope Icon

import SwiftUI

extension Color {
    static let teal = Color(red: 0.494, green: 0.729, blue: 0.710)
    static let appBG = Color(red: 0.075, green: 0.098, blue: 0.145)
}

struct EnvelopeIcon: View {
    let size: CGFloat
    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: size * 0.15, style: .continuous)
                .fill(Color.teal.opacity(0.15))
                .frame(width: size, height: size * 0.72)
                .overlay(
                    RoundedRectangle(cornerRadius: size * 0.15, style: .continuous)
                        .stroke(Color.teal.opacity(0.4), lineWidth: max(1, size * 0.03))
                )
            Path { p in
                let w = size
                let h = size * 0.72
                let top = -h / 2
                let mid = h * 0.05
                p.move(to: CGPoint(x: -w/2, y: top))
                p.addLine(to: CGPoint(x: 0, y: mid))
                p.addLine(to: CGPoint(x: w/2, y: top))
            }
            .stroke(Color.teal.opacity(0.6), style: StrokeStyle(lineWidth: max(1, size * 0.03), lineCap: .round, lineJoin: .round))
            .frame(width: size * 0.9, height: size * 0.72)
        }
    }
}

func envelopeIcon(size: CGFloat) -> some View {
    EnvelopeIcon(size: size)
}
