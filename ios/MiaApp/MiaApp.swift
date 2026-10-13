import SwiftUI

@main
struct MiaApp: App {
    @StateObject private var conversation = MiaConversationController.shared

    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}
