import SwiftUI

struct MiaAuroraOrb: View {
    var level: Float
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Environment(\.scenePhase) private var scenePhase

    var body: some View {
        TimelineView(.animation(minimumInterval: 1.0 / 24,
                                paused: reduceMotion || scenePhase != .active)) { timeline in
            let time = reduceMotion ? 0 : timeline.date.timeIntervalSinceReferenceDate
            let response = min(sqrt(Double(max(0, level))) * 2.2, 1)
            Canvas { context, size in
                let diameter = min(size.width, size.height)
                let center = CGPoint(x: size.width / 2, y: size.height / 2)
                let movement = reduceMotion ? 0 : response
                let radius = diameter * (0.35 + movement * 0.025)
                let colors: [Color] = [.cyan, .blue, .purple, .pink, .cyan]

                let halo = Path(ellipseIn: CGRect(x: center.x - diameter * 0.46,
                                                  y: center.y - diameter * 0.46,
                                                  width: diameter * 0.92,
                                                  height: diameter * 0.92))
                context.fill(halo, with: .radialGradient(
                    Gradient(colors: [.purple.opacity(0.20 + response * 0.12),
                                      .blue.opacity(0.10), .clear]),
                    center: center, startRadius: 0, endRadius: diameter * 0.46
                ))

                for index in 0..<5 {
                    let phase = time * 0.55 + Double(index) * 1.25
                    let rotation = Double(index) * .pi / 5 + sin(time * 0.3) * 0.35
                    var ribbon = Path()
                    for step in 0...80 {
                        let angle = Double(step) / 80 * .pi * 2
                        let x = cos(angle) * (0.92 + sin(angle * 2 + phase) * 0.08)
                        let y = sin(angle) * 0.42 + sin(angle * 2 + phase) * (0.22 + movement * 0.08)
                        let point = CGPoint(
                            x: center.x + radius * (x * cos(rotation) - y * sin(rotation)),
                            y: center.y + radius * (x * sin(rotation) + y * cos(rotation))
                        )
                        if step == 0 { ribbon.move(to: point) }
                        else { ribbon.addLine(to: point) }
                    }
                    ribbon.closeSubpath()
                    let gradient = GraphicsContext.Shading.linearGradient(
                        Gradient(colors: colors),
                        startPoint: CGPoint(x: center.x - radius, y: center.y - radius),
                        endPoint: CGPoint(x: center.x + radius, y: center.y + radius)
                    )
                    var glow = context
                    glow.addFilter(.blur(radius: diameter * 0.055))
                    glow.opacity = 0.45 + response * 0.25
                    glow.stroke(ribbon, with: gradient,
                                lineWidth: diameter * (0.075 + movement * 0.02))
                    context.opacity = 0.56 + response * 0.30
                    context.stroke(ribbon, with: gradient,
                                   style: StrokeStyle(lineWidth: diameter * 0.025,
                                                      lineCap: .round, lineJoin: .round))
                    context.opacity = 0.38 + response * 0.25
                    context.stroke(ribbon, with: .color(.white), lineWidth: diameter * 0.005)
                }
            }
        }
        .accessibilityHidden(true)
    }
}
