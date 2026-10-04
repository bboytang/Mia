import AVFoundation
import SwiftUI

@MainActor
final class MiaLaunchPlayback: ObservableObject {
    @Published private(set) var isShowing = true
    private(set) var player: AVPlayer?
    @Published private(set) var videoOpacity = 1.0

    private var hasStarted = false
    private var statusObservation: NSKeyValueObservation?
    private var notificationObservers: [NSObjectProtocol] = []
    private var timeObserver: Any?
    private var timeoutTask: Task<Void, Never>?

    func start(videoURL: URL?, reduceMotion: Bool) {
        guard !hasStarted else { return }
        hasStarted = true
        guard !reduceMotion, let videoURL else {
            finish()
            return
        }

        let item = AVPlayerItem(url: videoURL)
        let player = AVPlayer(playerItem: item)
        player.isMuted = true
        objectWillChange.send()
        self.player = player

        statusObservation = item.observe(\.status, options: [.initial, .new]) { [weak self] item, _ in
            guard item.status == .failed else { return }
            Task { @MainActor [weak self] in self?.finish() }
        }
        notificationObservers = [AVPlayerItem.didPlayToEndTimeNotification,
                                 AVPlayerItem.failedToPlayToEndTimeNotification].map { name in
            NotificationCenter.default.addObserver(forName: name, object: item, queue: .main) { [weak self] _ in
                Task { @MainActor [weak self] in self?.finish() }
            }
        }
        timeObserver = player.addPeriodicTimeObserver(
            forInterval: CMTime(seconds: 1.0 / 30, preferredTimescale: 600), queue: .main
        ) { [weak self, weak item] time in
            let seconds = time.seconds
            let duration = item?.duration.seconds ?? .nan
            Task { @MainActor [weak self] in
                self?.playbackAdvanced(seconds: seconds, duration: duration)
            }
        }
        timeoutTask = Task { [weak self] in
            do {
                try await Task.sleep(nanoseconds: 7_000_000_000)
            } catch { return }
            self?.finish()
        }
        player.play()
    }

    func playbackAdvanced(seconds: Double, duration: Double) {
        guard isShowing, seconds.isFinite, duration.isFinite, duration > 0 else { return }
        let opacity = min(max((duration - seconds) / 0.25, 0), 1)
        if videoOpacity != opacity { videoOpacity = opacity }
    }

    func finish() {
        hasStarted = true
        timeoutTask?.cancel()
        timeoutTask = nil
        statusObservation?.invalidate()
        statusObservation = nil
        notificationObservers.forEach { NotificationCenter.default.removeObserver($0) }
        notificationObservers.removeAll()
        if let timeObserver { player?.removeTimeObserver(timeObserver) }
        timeObserver = nil
        player?.pause()
        player?.replaceCurrentItem(with: nil)
        player = nil
        isShowing = false
    }

    func skip() {
        finish()
    }

    func sceneChanged(_ phase: ScenePhase) {
        if phase != .active { finish() }
    }

    deinit {
        timeoutTask?.cancel()
        statusObservation?.invalidate()
        notificationObservers.forEach { NotificationCenter.default.removeObserver($0) }
        if let timeObserver { player?.removeTimeObserver(timeObserver) }
        player?.pause()
        player?.replaceCurrentItem(with: nil)
    }
}
