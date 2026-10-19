import SwiftUI

enum YoumiSkin: String, CaseIterable, Identifiable {
    case glass, holographic

    static let storageKey = "mia.appearance.skin"
    var id: String { rawValue }
    var title: String {
        switch self {
        case .glass: return "玻璃流体"
        case .holographic: return "蓝金星环"
        }
    }
    var detail: String {
        switch self {
        case .glass: return "柔和流体与自然表情"
        case .holographic: return "悬浮星环、流动荧光和声音耳环"
        }
    }
}

struct YoumiAvatarView: View {
    var skin: YoumiSkin
    var emotion: YoumiEmotion = .calm
    var state: YoumiOrbState = .idle
    var intensity: Double = 0.5
    var level: Float = 0

    var body: some View {
        switch skin {
        case .glass:
            YoumiCompanionOrb(emotion: emotion, state: state, intensity: intensity, level: level)
        case .holographic:
            YoumiHolographicOrb(emotion: emotion, state: state, intensity: intensity, level: level)
        }
    }
}

struct YoumiSkinView: View {
    @AppStorage(YoumiSkin.storageKey) private var skin: YoumiSkin = .glass

    var body: some View {
        List {
            ForEach(YoumiSkin.allCases) { candidate in
                Button { skin = candidate } label: {
                    HStack(spacing: 16) {
                        YoumiAvatarView(skin: candidate)
                            .frame(width: 110, height: 125)
                            .background(Color.black, in: RoundedRectangle(cornerRadius: 18))
                        VStack(alignment: .leading, spacing: 8) {
                            Text(candidate.title).font(.headline)
                            Text(candidate.detail).font(.caption).foregroundStyle(.secondary)
                        }
                        Spacer(minLength: 0)
                        if skin == candidate { Image(systemName: "checkmark.circle.fill").foregroundStyle(.cyan) }
                    }
                    .accessibilityElement(children: .ignore)
                    .accessibilityLabel(candidate.title)
                    .accessibilityValue(skin == candidate ? "已选" : "未选")
                    .accessibilityAddTraits(skin == candidate ? [.isButton, .isSelected] : .isButton)
                    .accessibilityIdentifier("youmi-skin-" + candidate.rawValue)
                }
                .buttonStyle(.plain)
            }
            Section {
                Text("选择后立即应用，下次打开 Youmi 也会保留。")
                    .font(.footnote).foregroundStyle(.secondary)
            }
        }
        .navigationTitle("个性化皮肤")
    }
}
