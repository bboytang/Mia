import ActivityKit
import Foundation

@MainActor
final class MiaLiveActivityController {
    private var activity: Activity<MiaActivityAttributes>?
    private var monitor: Task<Void, Never>?
    private var updateTask: Task<Void, Never>?
    private var pending: MiaActivityAttributes.ContentState?
    private var lastState: MiaActivityAttributes.ContentState?
    var onUnavailable: (() -> Void)?

    init() {
        if let current = Activity<MiaActivityAttributes>.activities.first(where: { $0.activityState == .active }) {
            observe(current)
            update(.init(phase: .standby))
        }
    }

    func start(_ state: MiaActivityAttributes.ContentState) throws {
        guard ActivityAuthorizationInfo().areActivitiesEnabled else {
            throw MiaConversationStartError.liveActivitiesDisabled
        }
        if let current = activity, current.activityState == .active {
            update(state)
            return
        }
        // A process relaunched by an intent reuses its existing activity.
        let current = try Activity<MiaActivityAttributes>.activities.first(where: { $0.activityState == .active })
            ?? Activity.request(attributes: MiaActivityAttributes(),
                                content: ActivityContent(state: state, staleDate: nil), pushType: nil)
        observe(current)
        update(state)
    }

    deinit { monitor?.cancel(); updateTask?.cancel() }

    private func observe(_ current: Activity<MiaActivityAttributes>) {
        activity = current
        lastState = nil
        monitor?.cancel()
        monitor = Task { [weak self] in
            for await status in current.activityStateUpdates {
                guard !Task.isCancelled else { return }
                if status == .ended || status == .dismissed {
                    self?.activity = nil
                    self?.onUnavailable?()
                    return
                }
            }
        }
    }

    func update(_ state: MiaActivityAttributes.ContentState) {
        guard activity != nil, state != lastState else { return }
        lastState = state
        pending = state
        guard updateTask == nil else { return }
        updateTask = Task { [weak self] in
            guard let self else { return }
            while let state = self.pending, let activity = self.activity {
                self.pending = nil
                await activity.update(ActivityContent(state: state, staleDate: nil))
            }
            self.updateTask = nil
        }
    }
}
