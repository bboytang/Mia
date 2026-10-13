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
                    mouth(expression: expression, diameter: diameter, energy: energy, time: time)
                }
                .scaleEffect(1 + movement)
                .rotationEffect(.degrees(expression.tilt + drift * 80 +
                    (reduceMotion ? 0 : sin(time * 2.2) * (emotion == .playful ? 3 : 1))))
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
        let glance = reduceMotion || state == .listening ? 0 : sin(time * 0.8) * 0.012
        let gazeX = expression.gazeX + (thinking ? 0.06 : glance)
        let gazeY = expression.gazeY + (thinking ? -0.035 : 0)
        let focus = state == .listening ? 1.12 : 1
        let wink = !reduceMotion && emotion == .playful && time.truncatingRemainder(dividingBy: 3.6) > 3.25
        return HStack(spacing: diameter * 0.08) {
            MiaOrbEye(curve: expression.leftCurve)
                .fill(.white)
                .frame(width: diameter * expression.eyeWidth, height: diameter * expression.leftHeight * focus)
                .scaleEffect(x: 1, y: wink ? 0.12 : 1)
            MiaOrbEye(curve: expression.rightCurve)
                .fill(.white)
                .frame(width: diameter * expression.eyeWidth, height: diameter * expression.rightHeight * focus)
        }
        .scaleEffect(x: 1, y: blink)
        .shadow(color: .white.opacity(0.22), radius: diameter * 0.013)
        .offset(x: diameter * gazeX, y: diameter * (gazeY - 0.025))
        .overlay {
            if abs(expression.browTilt) > 0.1 {
                HStack(spacing: diameter * 0.10) {
                    Capsule().rotationEffect(.degrees(expression.browTilt))
                    Capsule().rotationEffect(.degrees(-expression.browTilt))
                }
                .foregroundStyle(.white.opacity(0.8))
                .frame(width: diameter * 0.30, height: diameter * 0.012)
                .offset(x: diameter * gazeX, y: diameter * (gazeY - 0.14))
            }
        }
    }

    private func mouth(expression: MiaOrbExpression, diameter: CGFloat, energy: Double, time: Double) -> some View {
        let speech = state == .speaking ? sqrt(energy) * 0.045 *
            (reduceMotion ? 1 : 0.65 + 0.35 * abs(sin(time * 9))) : 0
        return Group {
            if expression.mouthOpen + speech > 0.012 {
                Ellipse().stroke(.white.opacity(0.9), lineWidth: diameter * 0.012)
                    .frame(width: diameter * 0.065, height: diameter * max(0.015, expression.mouthOpen + speech))
            } else {
                MiaOrbMouth(curve: expression.mouthCurve)
                    .stroke(.white.opacity(0.9), style: StrokeStyle(lineWidth: diameter * 0.012, lineCap: .round))
                    .frame(width: diameter * 0.10, height: diameter * 0.065)
            }
        }
        .offset(x: diameter * expression.gazeX * 0.5, y: diameter * 0.105)
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
        let start = CGPoint(x: rect.minX, y: rect.midY + rect.height * 0.25 * curve)
        let end = CGPoint(x: rect.maxX, y: start.y)
        let upper = rect.midY - rect.height * 0.65 - rect.height * 0.25 * curve
        let lower = upper + rect.height * 1.3 * (1 - spread * 0.8)
        var path = Path()
        path.move(to: start)
        path.addCurve(to: end,
                      control1: CGPoint(x: rect.minX, y: upper),
                      control2: CGPoint(x: rect.maxX, y: upper))
        path.addCurve(to: start,
                      control1: CGPoint(x: rect.maxX, y: lower),
                      control2: CGPoint(x: rect.minX, y: lower))
        path.closeSubpath()
        return path
    }
}

private struct MiaOrbMouth: Shape {
    var curve: Double
    var animatableData: Double {
        get { curve }
        set { curve = newValue }
    }

    func path(in rect: CGRect) -> Path {
        var path = Path()
        path.move(to: CGPoint(x: rect.minX, y: rect.midY))
        path.addQuadCurve(to: CGPoint(x: rect.maxX, y: rect.midY),
                          control: CGPoint(x: rect.midX, y: rect.midY + rect.height * curve))
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
