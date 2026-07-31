import AppKit

enum NativeSelfTest {
    static func run(pet: PetController, menuBar: MenuBarController, outputURL: URL) -> Bool {
        let originalScale = pet.preferences.displayScale
        let originalSpeed = pet.preferences.animationSpeed
        let originalAction = pet.preferences.defaultAction
        let originalTop = pet.preferences.alwaysOnTop

        var checks: [[String: Any]] = []
        func check(_ name: String, _ passed: Bool, _ detail: String) {
            checks.append(["name": name, "passed": passed, "detail": detail])
        }

        check(
            "sprite_atlas_dimensions",
            Int(pet.atlas.pixelSize.width) == 1536 && Int(pet.atlas.pixelSize.height) == 2288,
            "\(Int(pet.atlas.pixelSize.width))x\(Int(pet.atlas.pixelSize.height))"
        )
        check("transparent_panel", !pet.panel.isOpaque && pet.panel.backgroundColor.alphaComponent == 0, "opaque=\(pet.panel.isOpaque), alpha=\(pet.panel.backgroundColor.alphaComponent)")
        check("shadow_disabled", !pet.panel.hasShadow, "hasShadow=\(pet.panel.hasShadow)")
        check("nonactivating_panel", pet.panel.styleMask.contains(.nonactivatingPanel), "styleMask=\(pet.panel.styleMask.rawValue)")

        let behaviors = pet.panel.collectionBehavior
        let crossSpace = behaviors.contains(.canJoinAllSpaces) && behaviors.contains(.fullScreenAuxiliary) && behaviors.contains(.stationary)
        check("all_spaces_and_fullscreen", crossSpace, "collectionBehavior=\(behaviors.rawValue)")

        pet.setAlwaysOnTop(true)
        check("always_on_top_level", pet.panel.level.rawValue > NSWindow.Level.statusBar.rawValue, "level=\(pet.panel.level.rawValue)")
        check("native_status_item", menuBar.statusItem.isVisible && menuBar.statusItem.button?.image != nil, "visible=\(menuBar.statusItem.isVisible)")
        check("shared_app_and_status_icon", menuBar.statusIconUsesAppIcon, "status icon source=app-icon.icns")

        pet.setDisplayScale(PetConstants.minimumScale)
        let expectedWidth = CGFloat(PetConstants.cellWidth) * PetConstants.minimumScale
        let expectedHeight = CGFloat(PetConstants.cellHeight) * PetConstants.minimumScale
        let minimumSizePassed = abs(pet.panel.frame.width - expectedWidth) <= 1 && abs(pet.panel.frame.height - expectedHeight) <= 1
        check("minimum_size_10_percent", minimumSizePassed, "requested=\(expectedWidth)x\(expectedHeight), AppKit integral frame=\(pet.panel.frame.width)x\(pet.panel.frame.height)")

        pet.play(.idle, loops: Int.max, restart: true)
        pet.setAnimationSpeed(PetConstants.minimumAnimationSpeed)
        check("animation_speed_range", abs(pet.animationInterval - 0.48) < 0.01, "slowest idle interval=\(pet.animationInterval)s")

        let center = NSPoint(x: pet.petView.bounds.midX, y: pet.petView.bounds.midY)
        let north = pet.directionCell(for: NSPoint(x: center.x, y: center.y + 100))
        let south = pet.directionCell(for: NSPoint(x: center.x, y: center.y - 100))
        check("sixteen_direction_mapping", north == (9, 0) && south == (10, 0), "north=\(north), south=\(south)")
        check("all_animation_states", PetAnimation.allCases.count == 10, "states=\(PetAnimation.allCases.map(\.rawValue).joined(separator: ","))")

        pet.setDisplayScale(originalScale)
        pet.setAnimationSpeed(originalSpeed)
        pet.setAlwaysOnTop(originalTop)
        pet.setDefaultAction(originalAction)

        let passed = checks.allSatisfy { ($0["passed"] as? Bool) == true }
        let report: [String: Any] = [
            "app": PetConstants.appName,
            "version": PetConstants.appVersion,
            "native_framework": "AppKit",
            "minimum_macos": "13.0",
            "all_passed": passed,
            "checks": checks,
            "timestamp": ISO8601DateFormatter().string(from: Date()),
        ]
        do {
            let data = try JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys])
            try FileManager.default.createDirectory(at: outputURL.deletingLastPathComponent(), withIntermediateDirectories: true)
            try data.write(to: outputURL, options: .atomic)
        } catch {
            fputs("Unable to write native self-test: \(error)\n", stderr)
            return false
        }
        return passed
    }
}
