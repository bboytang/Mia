import ActivityKit
import AppIntents
import SwiftUI
import WidgetKit

@main
struct YoumiActivityBundle: WidgetBundle {
    var body: some Widget { YoumiActivityWidget() }
}

struct YoumiActivityWidget: Widget {
    var body: some WidgetConfiguration {
        ActivityConfiguration(for: MiaActivityAttributes.self) { context in
            HStack(spacing: 14) {
                YoumiIslandOrb(emotion: context.state.emotion)
                    .frame(width: 54, height: 54)
                VStack(alignment: .leading, spacing: 4) {
                    Text("Youmi").font(.headline)
                    Label(context.state.phase.title, systemImage: context.state.phase.symbol)
                        .font(.caption).foregroundStyle(.secondary)
                }
                Spacer()
                controls(for: context.state)
            }
            .padding(16)
            .foregroundStyle(.white)
            .activityBackgroundTint(Color(red: 0.025, green: 0.035, blue: 0.10))
            .activitySystemActionForegroundColor(.white)
            .widgetURL(URL(string: "youmi://home"))
        } dynamicIsland: { context in
            DynamicIsland {
                DynamicIslandExpandedRegion(.leading) {
                    YoumiIslandOrb(emotion: context.state.emotion)
                        .frame(width: 48, height: 48)
                }
                DynamicIslandExpandedRegion(.trailing) { controls(for: context.state) }
                DynamicIslandExpandedRegion(.bottom) {
                    Label(context.state.phase.title, systemImage: context.state.phase.symbol)
                        .font(.caption)
                }
            } compactLeading: {
                YoumiIslandOrb(emotion: context.state.emotion)
                    .frame(width: 24, height: 24)
            } compactTrailing: {
                Image(systemName: context.state.phase.symbol)
                    .font(.caption).foregroundStyle(.cyan)
                    .accessibilityLabel(context.state.phase.title)
            } minimal: {
                YoumiIslandOrb(emotion: context.state.emotion)
                    .frame(width: 24, height: 24)
            }
            .widgetURL(URL(string: "youmi://home"))
            .keylineTint(.cyan)
        }
    }

    @ViewBuilder
    private func controls(for state: MiaActivityAttributes.ContentState) -> some View {
        if state.phase != .standby {
            Button(intent: EndMiaConversationIntent()) {
                Image(systemName: "stop.fill").frame(width: 36, height: 36)
            }
            .buttonStyle(.bordered).tint(.white)
            .accessibilityLabel("结束与 Youmi 聊天")
        } else {
            Link(destination: URL(string: "youmi://home")!) {
                Image(systemName: "arrow.up.forward.app").frame(width: 36, height: 36)
            }.accessibilityLabel("打开 Youmi")
        }
    }
}

private struct YoumiIslandOrb: View {
    let emotion: String
    private var bright: Bool { ["happy", "playful", "surprised"].contains(emotion) }
    private var narrow: Bool { ["happy", "playful", "caring"].contains(emotion) }

    var body: some View {
        GeometryReader { geometry in
            ZStack {
                Circle().fill(RadialGradient(colors: [bright ? .pink : .cyan, .indigo, .black],
                                             center: .topLeading, startRadius: 0,
                                             endRadius: geometry.size.width))
                Circle().stroke(.white.opacity(0.5), lineWidth: 0.7)
                Ellipse().fill(.white.opacity(0.35))
                    .frame(width: geometry.size.width * 0.45, height: geometry.size.height * 0.18)
                    .offset(x: -geometry.size.width * 0.12, y: -geometry.size.height * 0.26)
                HStack(spacing: geometry.size.width * 0.17) {
                    eye(in: geometry.size)
                    eye(in: geometry.size)
                }
            }
        }
        .accessibilityLabel("Youmi 表情")
    }

    private func eye(in size: CGSize) -> some View {
        Capsule().fill(.white)
            .frame(width: size.width * 0.09, height: size.height * (narrow ? 0.08 : 0.20))
            .rotationEffect(.degrees(emotion == "sad" ? -15 : 0))
    }
}
