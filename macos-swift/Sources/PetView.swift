import AppKit

protocol PetViewDelegate: AnyObject {
    func petViewDidSingleClick(_ view: PetView)
    func petViewDidDoubleClick(_ view: PetView)
    func petView(_ view: PetView, beganDragAt screenPoint: NSPoint)
    func petView(_ view: PetView, draggedTo screenPoint: NSPoint)
    func petViewDidEndDrag(_ view: PetView, wasDragged: Bool)
    func petView(_ view: PetView, mouseMovedTo point: NSPoint)
    func petViewMouseExited(_ view: PetView)
    func petView(_ view: PetView, contextMenuFor event: NSEvent) -> NSMenu?
}

private struct Particle {
    var position: NSPoint
    var velocity: CGVector
    let color: NSColor
    let radius: CGFloat
    var life: CGFloat
}

private struct InteractionRing {
    let center: NSPoint
    var radius: CGFloat
    let color: NSColor
    var life: CGFloat
}

final class PetView: NSView {
    weak var interactionDelegate: PetViewDelegate?

    var spriteFrame: SpriteFrame? {
        didSet { needsDisplay = true }
    }

    private var trackingAreaReference: NSTrackingArea?
    private var mouseDownScreenPoint: NSPoint?
    private var dragged = false
    private var pendingSingleClick: DispatchWorkItem?
    private var particles: [Particle] = []
    private var rings: [InteractionRing] = []
    private var effectTimer: Timer?

    override init(frame frameRect: NSRect) {
        super.init(frame: frameRect)
        wantsLayer = true
        layer?.backgroundColor = NSColor.clear.cgColor
        layer?.isOpaque = false
    }

    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }

    override var acceptsFirstResponder: Bool { false }
    override var isOpaque: Bool { false }

    override func updateTrackingAreas() {
        super.updateTrackingAreas()
        if let trackingAreaReference {
            removeTrackingArea(trackingAreaReference)
        }
        let area = NSTrackingArea(
            rect: bounds,
            options: [.mouseMoved, .mouseEnteredAndExited, .activeAlways, .inVisibleRect],
            owner: self,
            userInfo: nil
        )
        addTrackingArea(area)
        trackingAreaReference = area
    }

    override func draw(_ dirtyRect: NSRect) {
        guard let context = NSGraphicsContext.current?.cgContext else { return }
        context.clear(bounds)
        spriteFrame?.image.draw(
            in: bounds,
            from: .zero,
            operation: .sourceOver,
            fraction: 1,
            respectFlipped: false,
            hints: [.interpolation: NSImageInterpolation.high.rawValue]
        )

        for particle in particles {
            let alpha = clamp(particle.life, minimum: 0, maximum: 1) * 0.85
            particle.color.withAlphaComponent(alpha).setFill()
            let size = particle.radius * (0.7 + particle.life * 0.3)
            NSBezierPath(
                ovalIn: NSRect(
                    x: particle.position.x - size,
                    y: particle.position.y - size,
                    width: size * 2,
                    height: size * 2
                )
            ).fill()
        }

        for ring in rings {
            ring.color.withAlphaComponent(clamp(ring.life, minimum: 0, maximum: 1) * 0.8).setStroke()
            let path = NSBezierPath(
                ovalIn: NSRect(
                    x: ring.center.x - ring.radius,
                    y: ring.center.y - ring.radius,
                    width: ring.radius * 2,
                    height: ring.radius * 2
                )
            )
            path.lineWidth = max(1.5, 3.5 * ring.life)
            path.stroke()
        }
    }

    func alpha(at point: NSPoint) -> CGFloat {
        guard bounds.contains(point), let bitmap = spriteFrame?.bitmap else { return 0 }
        let x = clamp(
            Int(point.x * CGFloat(PetConstants.cellWidth) / max(1, bounds.width)),
            minimum: 0,
            maximum: PetConstants.cellWidth - 1
        )
        let y = clamp(
            Int(point.y * CGFloat(PetConstants.cellHeight) / max(1, bounds.height)),
            minimum: 0,
            maximum: PetConstants.cellHeight - 1
        )
        return bitmap.colorAt(x: x, y: y)?.alphaComponent ?? 0
    }

    func spawnFeedback(intense: Bool) {
        let origin = NSPoint(x: bounds.width * 0.52, y: bounds.height * 0.66)
        let colors: [NSColor] = [
            NSColor(hex: 0xF6A9C5),
            NSColor(hex: 0xB9E8ED),
            NSColor(hex: 0xF9D98C),
            NSColor(hex: 0xD2C1EF),
        ]
        let particleCount = intense ? 28 : 18
        for _ in 0..<particleCount {
            particles.append(
                Particle(
                    position: NSPoint(
                        x: origin.x + .random(in: -15...15),
                        y: origin.y + .random(in: -8...8)
                    ),
                    velocity: CGVector(
                        dx: .random(in: -1.8...1.8),
                        dy: .random(in: 1.8...4.0)
                    ),
                    color: colors.randomElement() ?? .systemPink,
                    radius: .random(in: 5...10),
                    life: 1
                )
            )
        }
        let ringColors = [NSColor(hex: 0xF6A9C5), NSColor(hex: 0x8EDBE3), NSColor(hex: 0xF7C95C)]
        for index in 0..<(intense ? 3 : 2) {
            rings.append(
                InteractionRing(
                    center: origin,
                    radius: 8 + CGFloat(index) * 6,
                    color: ringColors[index % ringColors.count],
                    life: 1
                )
            )
        }
        startEffectTimerIfNeeded()
        needsDisplay = true
    }

    private func startEffectTimerIfNeeded() {
        guard effectTimer == nil else { return }
        let timer = Timer(timeInterval: 1.0 / 30.0, repeats: true) { [weak self] _ in
            self?.advanceEffects()
        }
        RunLoop.main.add(timer, forMode: .common)
        effectTimer = timer
    }

    private func advanceEffects() {
        for index in particles.indices {
            particles[index].position.x += particles[index].velocity.dx
            particles[index].position.y += particles[index].velocity.dy
            particles[index].velocity.dy -= 0.035
            particles[index].life -= 0.045
        }
        particles.removeAll { $0.life <= 0 }
        for index in rings.indices {
            rings[index].radius += 2.8
            rings[index].life -= 0.06
        }
        rings.removeAll { $0.life <= 0 }
        if particles.isEmpty && rings.isEmpty {
            effectTimer?.invalidate()
            effectTimer = nil
        }
        needsDisplay = true
    }

    override func mouseDown(with event: NSEvent) {
        mouseDownScreenPoint = NSEvent.mouseLocation
        dragged = false
        interactionDelegate?.petView(self, beganDragAt: NSEvent.mouseLocation)
    }

    override func mouseDragged(with event: NSEvent) {
        guard let start = mouseDownScreenPoint else { return }
        let current = NSEvent.mouseLocation
        if hypot(current.x - start.x, current.y - start.y) > 5 {
            dragged = true
        }
        interactionDelegate?.petView(self, draggedTo: current)
    }

    override func mouseUp(with event: NSEvent) {
        interactionDelegate?.petViewDidEndDrag(self, wasDragged: dragged)
        defer {
            mouseDownScreenPoint = nil
            dragged = false
        }
        guard !dragged else { return }
        if event.clickCount >= 2 {
            pendingSingleClick?.cancel()
            pendingSingleClick = nil
            interactionDelegate?.petViewDidDoubleClick(self)
            return
        }
        let work = DispatchWorkItem { [weak self] in
            guard let self else { return }
            self.interactionDelegate?.petViewDidSingleClick(self)
        }
        pendingSingleClick?.cancel()
        pendingSingleClick = work
        DispatchQueue.main.asyncAfter(
            deadline: .now() + NSEvent.doubleClickInterval,
            execute: work
        )
    }

    override func rightMouseDown(with event: NSEvent) {
        guard let menu = interactionDelegate?.petView(self, contextMenuFor: event) else { return }
        NSMenu.popUpContextMenu(menu, with: event, for: self)
    }

    override func mouseMoved(with event: NSEvent) {
        interactionDelegate?.petView(self, mouseMovedTo: convert(event.locationInWindow, from: nil))
    }

    override func mouseExited(with event: NSEvent) {
        interactionDelegate?.petViewMouseExited(self)
    }
}

private extension NSColor {
    convenience init(hex: Int) {
        self.init(
            calibratedRed: CGFloat((hex >> 16) & 0xFF) / 255,
            green: CGFloat((hex >> 8) & 0xFF) / 255,
            blue: CGFloat(hex & 0xFF) / 255,
            alpha: 1
        )
    }
}
