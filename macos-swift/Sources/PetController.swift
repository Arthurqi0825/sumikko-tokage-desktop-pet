import AppKit

final class PetController: NSObject {
    let panel: PetPanel
    let petView: PetView
    let atlas: SpriteAtlas
    let preferences: PetPreferences

    private(set) var currentAnimation: PetAnimation = .idle
    private(set) var currentCell = (row: 0, column: 0)
    private(set) var isVisible = true

    var onStateChanged: (() -> Void)?

    private var frameTimer: Timer?
    private var autoActionTimer: Timer?
    private var motionTimer: Timer?
    private var hitTestTimer: Timer?
    private var animationFrame = 0
    private var remainingLoops = 0
    private var dragOffset = NSPoint.zero
    private var previousDragPoint = NSPoint.zero
    private var wasPlayingBeforeLook = false

    init(atlas: SpriteAtlas, preferences: PetPreferences) throws {
        self.atlas = atlas
        self.preferences = preferences
        let initialSize = NSSize(
            width: CGFloat(PetConstants.cellWidth) * preferences.displayScale,
            height: CGFloat(PetConstants.cellHeight) * preferences.displayScale
        )
        panel = PetPanel(contentSize: initialSize)
        petView = PetView(frame: NSRect(origin: .zero, size: initialSize))
        super.init()

        petView.autoresizingMask = [.width, .height]
        petView.interactionDelegate = self
        panel.contentView = petView
        setCell(row: 0, column: 0)
        applyWindowLevel()
        moveToBottomRight()
        applyDefaultAction(scheduleAutomaticActions: true)
        startTransparentHitTesting()
    }

    deinit {
        frameTimer?.invalidate()
        autoActionTimer?.invalidate()
        motionTimer?.invalidate()
        hitTestTimer?.invalidate()
    }

    var animationInterval: TimeInterval {
        let milliseconds = Double(currentAnimation.spec.intervalMilliseconds)
        return milliseconds / 1_000.0 / preferences.animationSpeed
    }

    func show() {
        isVisible = true
        panel.orderFrontRegardless()
        onStateChanged?()
    }

    func hide() {
        isVisible = false
        panel.orderOut(nil)
        onStateChanged?()
    }

    func toggleVisibility() {
        isVisible ? hide() : show()
    }

    func moveToBottomRight() {
        let screen = panel.screen ?? NSScreen.main
        guard let visible = screen?.visibleFrame else { return }
        let margin: CGFloat = 22
        let origin = NSPoint(
            x: visible.maxX - panel.frame.width - margin,
            y: visible.minY + margin
        )
        panel.setFrameOrigin(origin)
    }

    func setAnimationSpeed(_ value: Double) {
        preferences.animationSpeed = value
        if frameTimer != nil {
            play(currentAnimation, loops: max(1, remainingLoops), restart: false)
        }
        onStateChanged?()
    }

    func setDisplayScale(_ value: Double) {
        preferences.displayScale = value
        let newSize = NSSize(
            width: CGFloat(PetConstants.cellWidth) * preferences.displayScale,
            height: CGFloat(PetConstants.cellHeight) * preferences.displayScale
        )
        var frame = panel.frame
        frame.origin.y += frame.height - newSize.height
        frame.size = newSize
        panel.setFrame(frame, display: true)
        clampToVisibleScreen()
        onStateChanged?()
    }

    func setAlwaysOnTop(_ enabled: Bool) {
        preferences.alwaysOnTop = enabled
        applyWindowLevel()
        if isVisible { panel.orderFrontRegardless() }
        onStateChanged?()
    }

    func setAutoActions(_ enabled: Bool) {
        preferences.autoActions = enabled
        if enabled, preferences.defaultAction == .random {
            scheduleAutomaticAction()
        } else {
            autoActionTimer?.invalidate()
            autoActionTimer = nil
        }
        onStateChanged?()
    }

    func setDefaultAction(_ action: DefaultPetAction) {
        preferences.defaultAction = action
        applyDefaultAction(scheduleAutomaticActions: true)
        onStateChanged?()
    }

    func playInteraction(_ animation: PetAnimation) {
        autoActionTimer?.invalidate()
        autoActionTimer = nil
        petView.spawnFeedback(intense: animation == .jumping || animation == .failed)
        switch animation {
        case .jumping:
            startVerticalMotion(height: PetConstants.jumpHeight, duration: duration(of: animation))
        case .failed:
            startVerticalMotion(height: PetConstants.reactionHeight, duration: duration(of: animation) * 0.55)
        default:
            break
        }
        play(animation, loops: 1, restart: true)
    }

    func play(_ animation: PetAnimation, loops: Int = 1, restart: Bool = true) {
        let priorFrame = animationFrame
        frameTimer?.invalidate()
        frameTimer = nil
        currentAnimation = animation
        remainingLoops = max(1, loops)
        animationFrame = restart ? 0 : min(priorFrame, animation.spec.frames - 1)
        setCell(row: animation.spec.row, column: animationFrame)

        let timer = Timer(timeInterval: animationInterval, repeats: true) { [weak self] _ in
            self?.advanceAnimationFrame()
        }
        RunLoop.main.add(timer, forMode: .common)
        frameTimer = timer
        onStateChanged?()
    }

    func applyDefaultAction(scheduleAutomaticActions: Bool) {
        frameTimer?.invalidate()
        frameTimer = nil
        motionTimer?.invalidate()
        motionTimer = nil

        if let cell = preferences.defaultAction.fixedCell {
            currentAnimation = animation(for: preferences.defaultAction)
            setCell(row: cell.row, column: cell.column)
            autoActionTimer?.invalidate()
            autoActionTimer = nil
        } else {
            play(.idle, loops: Int.max, restart: true)
            if scheduleAutomaticActions, preferences.autoActions {
                scheduleAutomaticAction()
            }
        }
        onStateChanged?()
    }

    func advanceFrameForTesting() {
        advanceAnimationFrame()
    }

    func directionCell(for point: NSPoint) -> (row: Int, column: Int) {
        let center = NSPoint(x: petView.bounds.midX, y: petView.bounds.midY)
        let dx = point.x - center.x
        let dy = point.y - center.y
        var degrees = atan2(dx, dy) * 180 / .pi
        if degrees < 0 { degrees += 360 }
        let direction = Int((degrees + 11.25) / 22.5) % 16
        if direction < 8 {
            return (9, direction)
        }
        return (10, direction - 8)
    }

    func contextMenu() -> NSMenu {
        let menu = NSMenu(title: PetConstants.appName)
        menu.addItem(menuItem("挥手", action: #selector(menuWave)))
        menu.addItem(menuItem("明显跳跃", action: #selector(menuJump)))
        menu.addItem(menuItem("躺下休息", action: #selector(menuRest)))
        menu.addItem(menuItem("等待", action: #selector(menuWait)))
        menu.addItem(.separator())

        let topItem = menuItem("始终置顶", action: #selector(menuToggleAlwaysOnTop))
        topItem.state = preferences.alwaysOnTop ? .on : .off
        menu.addItem(topItem)

        let autoItem = menuItem("自动动作", action: #selector(menuToggleAutoActions))
        autoItem.state = preferences.autoActions ? .on : .off
        menu.addItem(autoItem)
        menu.addItem(menuItem("回到右下角", action: #selector(menuMoveHome)))
        menu.addItem(.separator())
        menu.addItem(menuItem("隐藏桌宠", action: #selector(menuHide)))
        menu.addItem(menuItem("退出", action: #selector(menuQuit)))
        return menu
    }

    private func animation(for action: DefaultPetAction) -> PetAnimation {
        switch action {
        case .random, .idle: return .idle
        case .jumping: return .jumping
        case .resting: return .resting
        case .waving: return .waving
        case .waiting: return .waiting
        }
    }

    private func setCell(row: Int, column: Int) {
        currentCell = (row, column)
        petView.spriteFrame = try? atlas.frame(row: row, column: column)
    }

    private func advanceAnimationFrame() {
        let spec = currentAnimation.spec
        animationFrame += 1
        if animationFrame >= spec.frames {
            if spec.loops || remainingLoops > 1 {
                animationFrame = 0
                if remainingLoops != Int.max { remainingLoops -= 1 }
            } else {
                animationDidFinish()
                return
            }
        }
        setCell(row: spec.row, column: animationFrame)
    }

    private func animationDidFinish() {
        frameTimer?.invalidate()
        frameTimer = nil
        applyDefaultAction(scheduleAutomaticActions: true)
    }

    private func scheduleAutomaticAction() {
        autoActionTimer?.invalidate()
        guard preferences.autoActions, preferences.defaultAction == .random else { return }
        let timer = Timer(timeInterval: .random(in: 4.5...8.0), repeats: false) { [weak self] _ in
            guard let self else { return }
            let actions: [PetAnimation] = [.waving, .jumping, .resting, .waiting, .running, .review]
            self.playInteraction(actions.randomElement() ?? .waving)
        }
        RunLoop.main.add(timer, forMode: .common)
        autoActionTimer = timer
    }

    private func duration(of animation: PetAnimation) -> TimeInterval {
        TimeInterval(animation.spec.frames) * TimeInterval(animation.spec.intervalMilliseconds) / 1_000.0 / preferences.animationSpeed
    }

    private func startVerticalMotion(height: CGFloat, duration: TimeInterval) {
        motionTimer?.invalidate()
        let startOrigin = panel.frame.origin
        let start = ProcessInfo.processInfo.systemUptime
        let timer = Timer(timeInterval: 1.0 / 60.0, repeats: true) { [weak self] timer in
            guard let self else { timer.invalidate(); return }
            let elapsed = ProcessInfo.processInfo.systemUptime - start
            let progress = clamp(elapsed / max(0.1, duration), minimum: 0, maximum: 1)
            let lift = 4 * height * CGFloat(progress * (1 - progress))
            self.panel.setFrameOrigin(NSPoint(x: startOrigin.x, y: startOrigin.y + lift))
            if progress >= 1 {
                timer.invalidate()
                self.motionTimer = nil
                self.panel.setFrameOrigin(startOrigin)
            }
        }
        RunLoop.main.add(timer, forMode: .common)
        motionTimer = timer
    }

    private func applyWindowLevel() {
        panel.level = preferences.alwaysOnTop
            ? NSWindow.Level(rawValue: NSWindow.Level.statusBar.rawValue + 1)
            : .normal
    }

    private func clampToVisibleScreen() {
        guard let visible = (panel.screen ?? NSScreen.main)?.visibleFrame else { return }
        var origin = panel.frame.origin
        origin.x = clamp(origin.x, minimum: visible.minX, maximum: max(visible.minX, visible.maxX - panel.frame.width))
        origin.y = clamp(origin.y, minimum: visible.minY, maximum: max(visible.minY, visible.maxY - panel.frame.height))
        panel.setFrameOrigin(origin)
    }

    private func startTransparentHitTesting() {
        let timer = Timer(timeInterval: 1.0 / 30.0, repeats: true) { [weak self] _ in
            guard let self, self.isVisible else { return }
            let screenPoint = NSEvent.mouseLocation
            let windowPoint = self.panel.convertPoint(fromScreen: screenPoint)
            let viewPoint = self.petView.convert(windowPoint, from: nil)
            let shouldPassThrough = !self.petView.bounds.contains(viewPoint) || self.petView.alpha(at: viewPoint) < 0.08
            if self.panel.ignoresMouseEvents != shouldPassThrough {
                self.panel.ignoresMouseEvents = shouldPassThrough
            }
        }
        RunLoop.main.add(timer, forMode: .common)
        hitTestTimer = timer
    }

    private func menuItem(_ title: String, action: Selector) -> NSMenuItem {
        let item = NSMenuItem(title: title, action: action, keyEquivalent: "")
        item.target = self
        return item
    }

    @objc private func menuWave() { playInteraction(.waving) }
    @objc private func menuJump() { playInteraction(.jumping) }
    @objc private func menuRest() { playInteraction(.resting) }
    @objc private func menuWait() { playInteraction(.waiting) }
    @objc private func menuToggleAlwaysOnTop() { setAlwaysOnTop(!preferences.alwaysOnTop) }
    @objc private func menuToggleAutoActions() { setAutoActions(!preferences.autoActions) }
    @objc private func menuMoveHome() { moveToBottomRight() }
    @objc private func menuHide() { hide() }
    @objc private func menuQuit() { NSApp.terminate(nil) }
}

extension PetController: PetViewDelegate {
    func petViewDidSingleClick(_ view: PetView) {
        playInteraction(.waving)
    }

    func petViewDidDoubleClick(_ view: PetView) {
        playInteraction(.jumping)
    }

    func petView(_ view: PetView, beganDragAt screenPoint: NSPoint) {
        dragOffset = NSPoint(x: screenPoint.x - panel.frame.minX, y: screenPoint.y - panel.frame.minY)
        previousDragPoint = screenPoint
    }

    func petView(_ view: PetView, draggedTo screenPoint: NSPoint) {
        let horizontal = screenPoint.x - previousDragPoint.x
        previousDragPoint = screenPoint
        panel.setFrameOrigin(NSPoint(x: screenPoint.x - dragOffset.x, y: screenPoint.y - dragOffset.y))
        let nextAnimation: PetAnimation = horizontal < 0 ? .runningLeft : .runningRight
        if currentAnimation != nextAnimation || frameTimer == nil {
            play(nextAnimation, loops: Int.max, restart: currentAnimation != nextAnimation)
        }
    }

    func petViewDidEndDrag(_ view: PetView, wasDragged: Bool) {
        if wasDragged {
            clampToVisibleScreen()
            applyDefaultAction(scheduleAutomaticActions: true)
        }
    }

    func petView(_ view: PetView, mouseMovedTo point: NSPoint) {
        guard preferences.defaultAction == .random, currentAnimation == .idle else { return }
        wasPlayingBeforeLook = frameTimer != nil
        let cell = directionCell(for: point)
        frameTimer?.invalidate()
        frameTimer = nil
        setCell(row: cell.row, column: cell.column)
    }

    func petViewMouseExited(_ view: PetView) {
        guard preferences.defaultAction == .random else { return }
        if wasPlayingBeforeLook || currentAnimation == .idle {
            play(.idle, loops: Int.max, restart: false)
        }
    }

    func petView(_ view: PetView, contextMenuFor event: NSEvent) -> NSMenu? {
        contextMenu()
    }
}
