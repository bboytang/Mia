import SwiftUI

struct ContentView: View {
    var body: some View {
        ZStack {
            LinearGradient(
                colors: [Color(red: 0.04, green: 0.07, blue: 0.19),
                         Color(red: 0.17, green: 0.08, blue: 0.31)],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .ignoresSafeArea()

            VStack(spacing: 16) {
                Spacer()
                Text("Mia")
                    .font(.system(size: 52, weight: .light, design: .rounded))
                    .foregroundStyle(.white)
                Text("你的语音伙伴")
                    .font(.title3)
                    .foregroundStyle(Color(red: 0.62, green: 0.88, blue: 1.0))
                Spacer()
                Text("语音功能正在接入")
                    .font(.footnote)
                    .foregroundStyle(.white.opacity(0.7))
            }
            .padding(24)
        }
    }
}

#Preview {
    ContentView()
}
