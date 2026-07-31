import AppKit
import Darwin

final class AppDelegate: NSObject, NSApplicationDelegate {
    private static let showPetNotification = Notification.Name("com.local.tokage-desktop-pet.native.show")
    private var petController: PetController?
    private var menuBarController: MenuBarController?

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.accessory)
        let arguments = CommandLine.arguments
        let isSelfTest = arguments.contains("--self-test")
        if isSelfTest { fputs("native-self-test: launch\n", stderr) }

        if !isSelfTest, activateExistingInstanceIfNeeded() {
            NSApp.terminate(nil)
            return
        }

        do {
            let defaults: UserDefaults
            if isSelfTest, let suite = UserDefaults(suiteName: "com.local.tokage-desktop-pet.native.selftest") {
                suite.removePersistentDomain(forName: "com.local.tokage-desktop-pet.native.selftest")
                defaults = suite
            } else {
                defaults = .standard
            }
            let atlas = try SpriteAtlas()
            if isSelfTest { fputs("native-self-test: atlas loaded\n", stderr) }
            let preferences = PetPreferences(defaults: defaults)
            let pet = try PetController(atlas: atlas, preferences: preferences)
            if isSelfTest { fputs("native-self-test: pet controller ready\n", stderr) }
            let menuBar = MenuBarController(petController: pet)
            if isSelfTest { fputs("native-self-test: status item ready\n", stderr) }
            petController = pet
            menuBarController = menuBar
            DistributedNotificationCenter.default().addObserver(
                self,
                selector: #selector(showPetFromSecondLaunch),
                name: Self.showPetNotification,
                object: nil
            )
            pet.show()

            if isSelfTest {
                let outputPath = value(after: "--self-test-output", in: arguments)
                    ?? NSTemporaryDirectory() + "/tokage-native-self-test.json"
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                    let passed = NativeSelfTest.run(pet: pet, menuBar: menuBar, outputURL: URL(fileURLWithPath: outputPath))
                    fputs("native-self-test: completed passed=\(passed)\n", stderr)
                    exit(passed ? 0 : 1)
                }
            }
        } catch {
            if isSelfTest {
                fputs("native-self-test: startup error: \(error)\n", stderr)
                exit(2)
            }
            let alert = NSAlert(error: error)
            alert.messageText = "无法启动蜥蜴桌宠"
            alert.runModal()
            NSApp.terminate(nil)
        }
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        false
    }

    func applicationWillTerminate(_ notification: Notification) {
        DistributedNotificationCenter.default().removeObserver(self)
    }

    private func activateExistingInstanceIfNeeded() -> Bool {
        guard let bundleIdentifier = Bundle.main.bundleIdentifier else { return false }
        let currentPID = ProcessInfo.processInfo.processIdentifier
        guard let existing = NSRunningApplication.runningApplications(withBundleIdentifier: bundleIdentifier)
            .first(where: { $0.processIdentifier != currentPID }) else {
            return false
        }
        existing.activate(options: [.activateAllWindows])
        DistributedNotificationCenter.default().postNotificationName(Self.showPetNotification, object: nil)
        return true
    }

    @objc private func showPetFromSecondLaunch() {
        petController?.show()
    }

    private func value(after key: String, in arguments: [String]) -> String? {
        guard let index = arguments.firstIndex(of: key), arguments.indices.contains(index + 1) else { return nil }
        return arguments[index + 1]
    }
}
