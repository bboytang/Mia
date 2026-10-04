import AVFoundation
import SwiftUI

struct MiaLaunchView: View {
    @ObservedObject var launch: MiaLaunchPlayback
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Environment(\.scenePhase) private var scenePhase

    var body: some View {
        ZStack {
            ContentView()
                .allowsHitTesting(!launch.isShowing)
                .accessibilityHidden(launch.isShowing)

            if launch.isShowing {
                ZStack(alignment: .topTrailing) {
                    Color.black.ignoresSafeArea()
                    if let player = launch.player {
                        MiaLaunchVideo(player: player)
                            .ignoresSafeArea()
                            .allowsHitTesting(false)
                            .accessibilityHidden(true)
                    }
                    Button("跳过") { launch.skip() }
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(.white)
                        .frame(minWidth: 64, minHeight: 44)
                        .background(.black.opacity(0.45), in: Capsule())
                        .buttonStyle(.plain)
                        .accessibilityLabel("跳过启动动画")
                        .padding(.trailing, 22)
                        .padding(.top, 14)
                }
                .opacity(launch.videoOpacity)
            }
        }
        .task {
            launch.start(videoURL: Bundle.main.url(forResource: "MiaLaunch", withExtension: "mp4"),
                         reduceMotion: reduceMotion)
        }
        .onChange(of: scenePhase) { _, phase in launch.sceneChanged(phase) }
        .onChange(of: reduceMotion) { _, value in
            if value { launch.finish() }
        }
        .onDisappear { launch.finish() }
    }
}

private struct MiaLaunchVideo: UIViewRepresentable {
    let player: AVPlayer

    func makeUIView(context: Context) -> PlayerView {
        let view = PlayerView()
        view.playerLayer.videoGravity = .resizeAspectFill
        view.playerLayer.player = player
        return view
    }

    func updateUIView(_ uiView: PlayerView, context: Context) {
        uiView.playerLayer.player = player
    }

    static func dismantleUIView(_ uiView: PlayerView, coordinator: ()) {
        uiView.playerLayer.player = nil
    }

    final class PlayerView: UIView {
        override class var layerClass: AnyClass { AVPlayerLayer.self }
        var playerLayer: AVPlayerLayer { layer as! AVPlayerLayer }
    }
}
