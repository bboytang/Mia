import SwiftUI

struct MiaCompanionOrb: View {
    var emotion: MiaEmotion = .calm
    var state: MiaOrbState = .idle
    var intensity: Double = 0.5
    var level: Float = 0

    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Environment(\.scenePhase) private var scenePhase

    var body: some View {
        TimelineView(.animation(minimumInterval: 1.0 / 30,
                                paused: reduceMotion || scenePhase != .active)) { timeline in
            let time = reduceMotion ? 0 : timeline.date.timeIntervalSinceReferenceDate
                .truncatingRemainder(dividingBy: 86_400)
            GeometryReader { geometry in
                let diameter = min(geometry.size.width, geometry.size.height)
                let expression = MiaOrbExpression(emotion: emotion, intensity: intensity)
                let energy = level.isFinite ? min(max(Double(level), 0), 1) : 0
                let movement = reduceMotion ? 0 : sqrt(energy) * 0.018
                let drift = reduceMotion ? 0 : sin(time * 0.65) * 0.012
                ZStack {
                    Circle()
                        .fill(Color(red: 0.23, green: 0.20, blue: 0.70).opacity(0.15))
                        .frame(width: diameter * 0.93, height: diameter * 0.93)
                        .blur(radius: diameter * 0.10)
                    MiaOrbMaterial(time: time, energy: energy, warmth: expression.warmth,
                                   speed: state == .thinking ? 1.35 : 1)
                        .frame(width: diameter, height: diameter)
                    eyes(expression: expression, diameter: diameter, time: time)
                }
                .scaleEffect(1 + movement)
                .rotationEffect(.degrees(expression.tilt + drift * 80))
                .offset(y: diameter * drift)
                .animation(reduceMotion ? nil : .easeInOut(duration: 0.65), value: emotion)
                .animation(reduceMotion ? nil : .easeInOut(duration: 0.45), value: intensity)
                .animation(reduceMotion ? nil : .easeInOut(duration: 0.4), value: state)
                .frame(width: geometry.size.width, height: geometry.size.height)
            }
        }
        .accessibilityHidden(true)
        .allowsHitTesting(false)
    }

    private func eyes(expression: MiaOrbExpression, diameter: CGFloat, time: Double) -> some View {
        let blinkPhase = time.truncatingRemainder(dividingBy: 4.8)
        let blink = reduceMotion || blinkPhase < 4.6
            ? 1 : max(0.07, abs(blinkPhase - 4.7) / 0.1)
        let thinking = state == .thinking
        let gazeX = expression.gazeX + (thinking ? 0.06 : 0)
        let gazeY = expression.gazeY + (thinking ? -0.035 : 0)
        let focus = state == .listening ? 1.12 : 1
        return HStack(spacing: diameter * 0.04) {
            MiaOrbEye(curve: expression.leftCurve)
                .stroke(.white, style: StrokeStyle(lineWidth: diameter * 0.035, lineCap: .round))
                .frame(width: diameter * 0.13, height: diameter * expression.leftHeight * focus)
            MiaOrbEye(curve: expression.rightCurve)
                .stroke(.white, style: StrokeStyle(lineWidth: diameter * 0.035, lineCap: .round))
                .frame(width: diameter * 0.13, height: diameter * expression.rightHeight * focus)
        }
        .scaleEffect(x: 1, y: blink)
        .shadow(color: .white.opacity(0.22), radius: diameter * 0.013)
        .offset(x: diameter * gazeX, y: diameter * (gazeY - 0.025))
    }
}

private struct MiaOrbEye: Shape {
    var curve: Double

    var animatableData: Double {
        get { curve }
        set { curve = newValue }
    }

    func path(in rect: CGRect) -> Path {
        let spread = abs(curve)
        let start = CGPoint(x: rect.midX - rect.width * 0.5 * spread,
                            y: rect.midY - rect.height * 0.5 * (1 - spread) + rect.height * 0.25 * curve)
        let end = CGPoint(x: rect.midX + rect.width * 0.5 * spread,
                          y: rect.midY + rect.height * 0.5 * (1 - spread) + rect.height * 0.25 * curve)
        let control = CGPoint(x: rect.midX, y: rect.midY - rect.height * 0.75 * curve)
        var path = Path()
        path.move(to: start)
        path.addQuadCurve(to: end, control: control)
        return path
    }
}

private struct MiaOrbMaterial: View, Animatable {
    var time: Double
    var energy: Double
    var warmth: Double
    var speed: Double

    var animatableData: AnimatablePair<Double, Double> {
        get { AnimatablePair(warmth, speed) }
        set { warmth = newValue.first; speed = newValue.second }
    }

    var body: some View {
        Rectangle()
            .fill(.white)
            .visualEffect { content, geometry in
                content.colorEffect(ShaderLibrary.miaGlassOrb(
                    .float2(Float(geometry.size.width), Float(geometry.size.height)),
                    .float(Float(time)), .float(Float(energy)),
                    .float(Float(warmth)), .float(Float(speed))))
            }
    }
}

#Preview("Mia emotions") {
    ZStack {
        Color(red: 0.015, green: 0.025, blue: 0.07).ignoresSafeArea()
        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 14) {
            ForEach(MiaEmotion.allCases, id: \.self) { emotion in
                VStack(spacing: 0) {
                    MiaCompanionOrb(emotion: emotion, intensity: 1)
                        .frame(height: 145)
                    Text(emotion.displayName).font(.caption).foregroundStyle(.white.opacity(0.7))
                }
            }
        }
        .padding()
    }
}
