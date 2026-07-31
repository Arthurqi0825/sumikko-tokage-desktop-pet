import AppKit

enum PetConstants {
    static let appName = "Tokage Desktop Pet"
    static let appVersion = "2.0.0"
    static let cellWidth = 192
    static let cellHeight = 208
    static let atlasColumns = 8
    static let atlasRows = 11
    static let minimumScale = 0.10
    static let maximumScale = 2.00
    static let minimumAnimationSpeed = 0.50
    static let maximumAnimationSpeed = 2.00
    static let jumpHeight: CGFloat = 96
    static let reactionHeight: CGFloat = 22
}

struct AnimationSpec: Equatable {
    let row: Int
    let frames: Int
    let intervalMilliseconds: Int
    let loops: Bool
}

enum PetAnimation: String, CaseIterable {
    case idle
    case runningRight = "running-right"
    case runningLeft = "running-left"
    case waving
    case jumping
    case failed
    case resting
    case waiting
    case running
    case review

    var spec: AnimationSpec {
        switch self {
        case .idle: return AnimationSpec(row: 0, frames: 6, intervalMilliseconds: 240, loops: true)
        case .runningRight: return AnimationSpec(row: 1, frames: 8, intervalMilliseconds: 150, loops: true)
        case .runningLeft: return AnimationSpec(row: 2, frames: 8, intervalMilliseconds: 150, loops: true)
        case .waving: return AnimationSpec(row: 3, frames: 4, intervalMilliseconds: 220, loops: false)
        case .jumping: return AnimationSpec(row: 4, frames: 5, intervalMilliseconds: 220, loops: false)
        case .failed: return AnimationSpec(row: 5, frames: 8, intervalMilliseconds: 230, loops: false)
        case .resting: return AnimationSpec(row: 5, frames: 8, intervalMilliseconds: 300, loops: false)
        case .waiting: return AnimationSpec(row: 6, frames: 6, intervalMilliseconds: 240, loops: false)
        case .running: return AnimationSpec(row: 7, frames: 6, intervalMilliseconds: 190, loops: false)
        case .review: return AnimationSpec(row: 8, frames: 6, intervalMilliseconds: 220, loops: false)
        }
    }
}

enum DefaultPetAction: String, CaseIterable {
    case random
    case idle
    case jumping
    case resting
    case waving
    case waiting

    var title: String {
        switch self {
        case .random: return "随机动作"
        case .idle: return "静态站立"
        case .jumping: return "静态跳跃"
        case .resting: return "静态躺下"
        case .waving: return "静态挥手"
        case .waiting: return "静态等待"
        }
    }

    var fixedCell: (row: Int, column: Int)? {
        switch self {
        case .random: return nil
        case .idle: return (0, 0)
        case .jumping: return (4, 2)
        case .resting: return (5, 4)
        case .waving: return (3, 2)
        case .waiting: return (6, 3)
        }
    }
}

func clamp<T: Comparable>(_ value: T, minimum: T, maximum: T) -> T {
    min(maximum, max(minimum, value))
}
