import Foundation

struct MiaPCMFrameBuffer {
    private let frameSize: Int
    private var pending: [Int16] = []

    init(frameSize: Int = 960) {
        self.frameSize = frameSize
    }

    mutating func append(_ samples: [Int16]) -> [[Int16]] {
        pending.append(contentsOf: samples)
        var frames: [[Int16]] = []
        while pending.count >= frameSize {
            frames.append(Array(pending.prefix(frameSize)))
            pending.removeFirst(frameSize)
        }
        return frames
    }

    mutating func reset() {
        pending.removeAll(keepingCapacity: true)
    }
}
