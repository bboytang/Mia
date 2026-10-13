import SwiftUI

struct MiaHolographicMotion {
    let time: Double
    let blink: Double
    let mouthOpening: Double
    let earResponse: Double
    let yaw: Double
    let pitch: Double
    let x: Double
    let y: Double

    init(time: Double, level: Float, state: MiaOrbState, reduceMotion: Bool) {
        let energy = level.isFinite ? min(max(Double(level), 0), 1) : 0
        let voice = sqrt(energy)
        self.time = reduceMotion || !time.isFinite ? 0 : max(0, time)
        let phase = self.time.truncatingRemainder(dividingBy: 4.9)
        blink = reduceMotion || phase < 4.65 ? 1 : max(0.08, abs(phase - 4.775) / 0.125)
        mouthOpening = state == .speaking || state == .listening ? voice * 0.065 : 0
        earResponse = state == .listening ? voice : 0
        yaw = reduceMotion ? 0 : sin(self.time * 0.55) * 12
        pitch = reduceMotion ? 0 : sin(self.time * 0.43) * 5
        x = reduceMotion ? 0 : sin(self.time * 0.55) * 0.012
        y = reduceMotion ? 0 : sin(self.time * 0.78) * 0.018
    }
}

struct MiaHolographicOrb: View {
    var emotion: MiaEmotion = .calm
    var state: MiaOrbState = .idle
    var intensity: Double = 0.5
    var level: Float = 0
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Environment(\.scenePhase) private var scenePhase

    var body: some View {
        TimelineView(.animation(minimumInterval: 1.0 / 30,
                                paused: reduceMotion || scenePhase != .active)) { timeline in
            GeometryReader { geometry in
                let diameter = min(geometry.size.width, geometry.size.height)
                let motion = MiaHolographicMotion(
                    time: timeline.date.timeIntervalSinceReferenceDate.truncatingRemainder(dividingBy: 86_400),
                    level: level, state: state, reduceMotion: reduceMotion)
                let expression = MiaOrbExpression(emotion: emotion, intensity: intensity)
                ZStack {
                    pedestal(diameter: diameter, time: motion.time)
                    ZStack {
                        Image("MiaHolographicShell").resizable().scaledToFit()
                        particles(time: motion.time)
                            .clipShape(Circle().scale(0.82))
                        face(expression: expression, motion: motion, diameter: diameter)
                        ear(diameter: diameter, response: motion.earResponse, side: -1)
                        ear(diameter: diameter, response: motion.earResponse, side: 1)
                    }
                    .rotation3DEffect(.degrees(motion.yaw), axis: (x: 0, y: 1, z: 0), perspective: 0.3)
                    .rotation3DEffect(.degrees(motion.pitch), axis: (x: 1, y: 0, z: 0), perspective: 0.3)
                    .rotationEffect(.degrees(expression.tilt * 0.3))
                    .offset(x: diameter * motion.x, y: diameter * (motion.y - 0.035))
                }
                .frame(width: diameter, height: diameter)
                .frame(width: geometry.size.width, height: geometry.size.height)
                .animation(reduceMotion ? nil : .easeInOut(duration: 0.45), value: emotion)
            }
        }
        .accessibilityHidden(true)
        .allowsHitTesting(false)
    }

    private func ear(diameter: CGFloat, response: Double, side: Double) -> some View {
        Image("MiaHolographicEar").resizable()
            .frame(width: diameter * 0.18, height: diameter * 0.34)
            .brightness(response * 0.12)
            .shadow(color: .orange.opacity(0.2 + response * 0.6), radius: diameter * (0.008 + response * 0.018))
            .scaleEffect(reduceMotion ? 1 : 1 + response * 0.08)
            .offset(x: diameter * side * (0.355 + (reduceMotion ? 0 : response * 0.008)), y: -diameter * 0.008)
            .animation(reduceMotion ? nil : .easeOut(duration: 0.09), value: response)
    }

    private func face(expression: MiaOrbExpression, motion: MiaHolographicMotion, diameter: CGFloat) -> some View {
        let focus = state == .listening ? 1.15 : 1
        let gaze = state == .thinking ? 0.035 : expression.gazeX
        return ZStack {
            HStack(spacing: diameter * 0.16) {
                eye(curve: expression.leftCurve, height: expression.leftHeight, diameter: diameter)
                eye(curve: expression.rightCurve, height: expression.rightHeight, diameter: diameter)
            }
            .scaleEffect(x: 1, y: motion.blink * focus)
            .offset(x: diameter * gaze, y: diameter * (expression.gazeY - 0.035))
            HStack(spacing: diameter * 0.16) {
                MiaOrbMouth(curve: -0.8)
                    .stroke(.cyan, style: StrokeStyle(lineWidth: diameter * 0.018, lineCap: .round))
                    .rotationEffect(.degrees(expression.browTilt))
                MiaOrbMouth(curve: -0.8)
                    .stroke(.cyan, style: StrokeStyle(lineWidth: diameter * 0.018, lineCap: .round))
                    .rotationEffect(.degrees(-expression.browTilt))
            }
            .frame(width: diameter * 0.37, height: diameter * 0.025)
            .shadow(color: .blue, radius: diameter * 0.02)
            .offset(x: diameter * gaze, y: -diameter * 0.18)
            if emotion == .surprised {
                Ellipse().fill(.cyan)
                    .frame(width: diameter * 0.07, height: diameter * (0.06 + motion.mouthOpening))
                    .shadow(color: .blue, radius: diameter * 0.02)
                    .offset(y: diameter * 0.115)
            } else if emotion == .sad || emotion == .confused {
                MiaOrbMouth(curve: expression.mouthCurve)
                    .stroke(.cyan, style: StrokeStyle(lineWidth: diameter * 0.012, lineCap: .round))
                    .frame(width: diameter * 0.12, height: diameter * (0.04 + motion.mouthOpening))
                    .offset(y: diameter * 0.115)
            } else {
                MiaHolographicMouth()
                    .fill(LinearGradient(colors: [.white, .cyan, .blue], startPoint: .top, endPoint: .bottom))
                    .frame(width: diameter * 0.14,
                           height: diameter * (0.03 + motion.mouthOpening + expression.mouthOpen * 0.3))
                    .shadow(color: .blue, radius: diameter * 0.025)
                    .offset(y: diameter * 0.115)
            }
        }
    }

    private func eye(curve: Double, height: Double, diameter: CGFloat) -> some View {
        MiaOrbEye(curve: curve)
            .fill(RadialGradient(colors: [.cyan, .blue, Color(red: 0.015, green: 0.035, blue: 0.18)],
                                 center: .bottomLeading, startRadius: 0, endRadius: diameter * 0.14))
            .overlay {
                MiaOrbEye(curve: curve).stroke(.white, lineWidth: diameter * 0.012)
            }
            .frame(width: diameter * 0.10, height: diameter * height * 1.25)
            .shadow(color: .cyan, radius: diameter * 0.013)
            .shadow(color: .blue, radius: diameter * 0.028)
    }

    private func particles(time: Double) -> some View {
        Canvas { context, size in
            let diameter = min(size.width, size.height)
            let center = CGPoint(x: size.width / 2, y: size.height / 2)
            context.blendMode = .plusLighter
            for band in 0..<3 {
                var path = Path()
                let bandHeight = band == 0 ? -0.28 : 0.20 + Double(band) * 0.04
                for step in 0...72 {
                    let angle = Double(step) / 72 * .pi * 2 + time * 0.15 + Double(band)
                    let point = CGPoint(x: center.x + cos(angle) * diameter * 0.39,
                                        y: center.y + sin(angle) * diameter * 0.085 + diameter * bandHeight)
                    if step == 0 { path.move(to: point) } else { path.addLine(to: point) }
                }
                let color: Color = band == 1 ? .orange : .cyan
                var glow = context
                glow.addFilter(.blur(radius: diameter * 0.012))
                glow.stroke(path, with: .color(color.opacity(0.6)), lineWidth: diameter * 0.016)
                context.stroke(path, with: .color(color.opacity(0.7)), lineWidth: diameter * 0.0025)
            }
            for index in 0..<96 {
                let seed = Double(index)
                let angle = seed * 2.39996 + time * (0.12 + Double(index % 5) * 0.025)
                let radius = diameter * (0.23 + 0.15 * (sin(seed * 37.13) * 0.5 + 0.5))
                let point = CGPoint(x: center.x + cos(angle) * radius,
                                    y: center.y + sin(angle) * radius * 0.9)
                let light = 0.35 + 0.65 * pow(sin(time * 1.2 + seed) * 0.5 + 0.5, 3)
                let dot = diameter * (index % 9 == 0 ? 0.0045 : 0.0018)
                let rect = CGRect(x: point.x - dot, y: point.y - dot, width: dot * 2, height: dot * 2)
                let color: Color = index % 3 == 0 ? .orange : .cyan
                var glow = context
                glow.addFilter(.blur(radius: dot * 3))
                glow.fill(Path(ellipseIn: rect.insetBy(dx: -dot, dy: -dot)), with: .color(color.opacity(light * 0.6)))
                context.fill(Path(ellipseIn: rect), with: .color(color.opacity(light)))
            }
        }
    }

    private func pedestal(diameter: CGFloat, time: Double) -> some View {
        ZStack {
            Ellipse().fill(.blue.opacity(0.15)).blur(radius: diameter * 0.025)
            Ellipse().stroke(.orange.opacity(0.7), lineWidth: diameter * 0.008)
            Ellipse().stroke(.cyan, lineWidth: diameter * 0.006).padding(.horizontal, diameter * 0.05)
            Ellipse().stroke(.white.opacity(0.8), lineWidth: diameter * 0.002).padding(.horizontal, diameter * 0.11)
        }
        .frame(width: diameter * 0.78, height: diameter * 0.08)
        .shadow(color: .blue.opacity(0.6 + sin(time * 0.8) * 0.15), radius: diameter * 0.035)
        .offset(y: diameter * 0.48)
    }
}

private struct MiaHolographicMouth: Shape {
    func path(in rect: CGRect) -> Path {
        var path = Path()
        path.move(to: CGPoint(x: rect.minX, y: rect.minY))
        path.addQuadCurve(to: CGPoint(x: rect.maxX, y: rect.minY),
                          control: CGPoint(x: rect.midX, y: rect.height * 0.15))
        path.addQuadCurve(to: CGPoint(x: rect.minX, y: rect.minY),
                          control: CGPoint(x: rect.midX, y: rect.height * 1.8))
        path.closeSubpath()
        return path
    }
}
