import SwiftUI
import AppIntents

@main
struct YoumiApp: App {
    @StateObject private var conversation = YoumiConversationController.shared
    @Environment(\.scenePhase) private var scenePhase

    init() {
        if #available(iOS 18.0, *) { YoumiShortcuts.updateAppShortcutParameters() }
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .onChange(of: scenePhase) { _, phase in
                    if phase == .active {
                        if #available(iOS 18.0, *) { YoumiShortcuts.updateAppShortcutParameters() }
                        conversation.showStandby()
                    }
                }
        }
    }
}
