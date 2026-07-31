import Foundation

final class PetPreferences {
    private enum Key {
        static let animationSpeed = "native.animationSpeed"
        static let displayScale = "native.displayScale"
        static let defaultAction = "native.defaultAction"
        static let alwaysOnTop = "native.alwaysOnTop"
        static let autoActions = "native.autoActions"
    }

    private let defaults: UserDefaults

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
        defaults.register(defaults: [
            Key.animationSpeed: 1.0,
            Key.displayScale: 1.0,
            Key.defaultAction: DefaultPetAction.random.rawValue,
            Key.alwaysOnTop: true,
            Key.autoActions: true,
        ])
    }

    var animationSpeed: Double {
        get {
            clamp(
                defaults.double(forKey: Key.animationSpeed),
                minimum: PetConstants.minimumAnimationSpeed,
                maximum: PetConstants.maximumAnimationSpeed
            )
        }
        set {
            defaults.set(
                clamp(newValue, minimum: PetConstants.minimumAnimationSpeed, maximum: PetConstants.maximumAnimationSpeed),
                forKey: Key.animationSpeed
            )
        }
    }

    var displayScale: Double {
        get {
            clamp(
                defaults.double(forKey: Key.displayScale),
                minimum: PetConstants.minimumScale,
                maximum: PetConstants.maximumScale
            )
        }
        set {
            defaults.set(
                clamp(newValue, minimum: PetConstants.minimumScale, maximum: PetConstants.maximumScale),
                forKey: Key.displayScale
            )
        }
    }

    var defaultAction: DefaultPetAction {
        get { DefaultPetAction(rawValue: defaults.string(forKey: Key.defaultAction) ?? "") ?? .random }
        set { defaults.set(newValue.rawValue, forKey: Key.defaultAction) }
    }

    var alwaysOnTop: Bool {
        get { defaults.bool(forKey: Key.alwaysOnTop) }
        set { defaults.set(newValue, forKey: Key.alwaysOnTop) }
    }

    var autoActions: Bool {
        get { defaults.bool(forKey: Key.autoActions) }
        set { defaults.set(newValue, forKey: Key.autoActions) }
    }
}
