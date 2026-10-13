import SwiftUI
import AppIntents

@main
struct MiaApp: App {
    @StateObject private var conversation = MiaConversationController.shared
    @Environment(\.scenePhase) private var scenePhase

    init() {
        if #available(iOS 18.0, *) { MiaShortcuts.updateAppShortcutParameters() }
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .onChange(of: scenePhase) { _, phase in
                    if phase == .active {
                        if #available(iOS 18.0, *) { MiaShortcuts.updateAppShortcutParameters() }
                        conversation.showStandby()
                    }
                }
        }
    }
}
