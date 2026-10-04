import SwiftUI

@main
struct MiaApp: App {
    @StateObject private var launch = MiaLaunchPlayback()

    var body: some Scene {
        WindowGroup {
            MiaLaunchView(launch: launch)
        }
    }
}
