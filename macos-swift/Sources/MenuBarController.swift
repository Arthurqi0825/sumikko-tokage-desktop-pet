import AppKit

final class MenuBarController: NSObject, NSPopoverDelegate {
    let statusItem: NSStatusItem
    let popover = NSPopover()
    let controlPanel: ControlPanelViewController
    private(set) var statusIconUsesAppIcon = false

    private let petController: PetController

    init(petController: PetController) {
        self.petController = petController
        controlPanel = ControlPanelViewController(petController: petController)
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)
        super.init()

        popover.behavior = .transient
        popover.animates = true
        popover.contentViewController = controlPanel
        popover.delegate = self

        if let button = statusItem.button {
            button.image = makeStatusIcon()
            button.imagePosition = .imageOnly
            button.toolTip = "蜥蜴桌宠控制"
            button.target = self
            button.action = #selector(togglePopover)
            button.sendAction(on: [.leftMouseUp, .rightMouseUp])
        }
        statusItem.isVisible = true

        petController.onStateChanged = { [weak self] in
            self?.controlPanel.refresh()
        }
    }

    @objc private func togglePopover() {
        guard let button = statusItem.button else { return }
        if popover.isShown {
            popover.performClose(nil)
            return
        }
        controlPanel.refresh()
        popover.show(relativeTo: button.bounds, of: button, preferredEdge: .minY)
    }

    private func makeStatusIcon() -> NSImage? {
        guard let iconURL = Bundle.main.url(forResource: "app-icon", withExtension: "icns"),
              let source = NSImage(contentsOf: iconURL) else {
            return NSImage(systemSymbolName: "pawprint.fill", accessibilityDescription: "蜥蜴桌宠")
        }
        statusIconUsesAppIcon = true
        let icon = NSImage(size: NSSize(width: 18, height: 18))
        icon.lockFocus()
        source.draw(
            in: NSRect(x: 1, y: 1, width: 16, height: 16),
            from: .zero,
            operation: .sourceOver,
            fraction: 1
        )
        icon.unlockFocus()
        icon.isTemplate = false
        return icon
    }
}
