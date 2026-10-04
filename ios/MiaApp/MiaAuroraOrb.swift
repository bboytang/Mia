import SwiftUI

struct MiaAuroraOrb: View {
    var level: Float
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Environment(\.scenePhase) private var scenePhase

    var body: some View {
        TimelineView(.animation(minimumInterval: 1.0 / 24,
                                paused: reduceMotion || scenePhase != .active)) { timeline in
            let time: Double = reduceMotion ? 0 : timeline.date.timeIntervalSinceReferenceDate
            let response: Double = min(sqrt(Double(max(Float(0), level))) * 2.2, 1.0)
            Canvas { context, size in
                draw(context: context, size: size, time: time, response: response)
            }
        }
        .accessibilityHidden(true)
    }

    private func draw(context originalContext: GraphicsContext, size: CGSize,
                      time: Double, response: Double) {
        var context = originalContext
        let diameter: Double = Double(min(size.width, size.height))
        let center = CGPoint(x: size.width / 2, y: size.height / 2)
        let movement: Double = reduceMotion ? 0 : response
        let radius: Double = diameter * (0.35 + movement * 0.025)
        let colors: [Color] = [.cyan, .blue, .purple, .pink, .cyan]
        let haloRect = CGRect(x: center.x - CGFloat(diameter * 0.46),
                              y: center.y - CGFloat(diameter * 0.46),
                              width: CGFloat(diameter * 0.92),
                              height: CGFloat(diameter * 0.92))
        let halo = Path(ellipseIn: haloRect)
        let haloColors: [Color] = [.purple.opacity(0.20 + response * 0.12),
                                  .blue.opacity(0.10), .clear]
        let haloShading = GraphicsContext.Shading.radialGradient(
            Gradient(colors: haloColors), center: center,
            startRadius: 0, endRadius: CGFloat(diameter * 0.46)
        )
        context.fill(halo, with: haloShading)

        let gradient = GraphicsContext.Shading.linearGradient(
            Gradient(colors: colors),
            startPoint: CGPoint(x: center.x - CGFloat(radius), y: center.y - CGFloat(radius)),
            endPoint: CGPoint(x: center.x + CGFloat(radius), y: center.y + CGFloat(radius))
        )
        for index in 0..<5 {
            let phase: Double = time * 0.55 + Double(index) * 1.25
            let rotation: Double = Double(index) * .pi / 5 + sin(time * 0.3) * 0.35
            let ribbon = ribbonPath(center: center, radius: radius, phase: phase,
                                    rotation: rotation, movement: movement)
            var glow = context
            glow.addFilter(.blur(radius: CGFloat(diameter * 0.055)))
            glow.opacity = 0.45 + response * 0.25
            glow.stroke(ribbon, with: gradient,
                        lineWidth: CGFloat(diameter * (0.075 + movement * 0.02)))
            context.opacity = 0.56 + response * 0.30
            context.stroke(ribbon, with: gradient,
                           style: StrokeStyle(lineWidth: CGFloat(diameter * 0.025),
                                              lineCap: .round, lineJoin: .round))
            context.opacity = 0.38 + response * 0.25
            context.stroke(ribbon, with: .color(.white), lineWidth: CGFloat(diameter * 0.005))
        }
    }

    private func ribbonPath(center: CGPoint, radius: Double, phase: Double,
                            rotation: Double, movement: Double) -> Path {
        var ribbon = Path()
        let centerX = Double(center.x)
        let centerY = Double(center.y)
        for step in 0...80 {
            let angle: Double = Double(step) / 80 * .pi * 2
            let x: Double = cos(angle) * (0.92 + sin(angle * 2 + phase) * 0.08)
            let y: Double = sin(angle) * 0.42 + sin(angle * 2 + phase) * (0.22 + movement * 0.08)
            let point = CGPoint(
                x: CGFloat(centerX + radius * (x * cos(rotation) - y * sin(rotation))),
                y: CGFloat(centerY + radius * (x * sin(rotation) + y * cos(rotation)))
            )
            if step == 0 { ribbon.move(to: point) }
            else { ribbon.addLine(to: point) }
        }
        ribbon.closeSubpath()
        return ribbon
    }
}
