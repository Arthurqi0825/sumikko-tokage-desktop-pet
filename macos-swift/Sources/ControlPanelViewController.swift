import AppKit

final class ControlPanelViewController: NSViewController {
    private let petController: PetController
    private let stateLabel = NSTextField(labelWithString: "")
    private let defaultActionPopup = NSPopUpButton(frame: .zero, pullsDown: false)
    private let speedSlider = NSSlider(value: 1, minValue: PetConstants.minimumAnimationSpeed, maxValue: PetConstants.maximumAnimationSpeed, target: nil, action: nil)
    private let speedValueLabel = NSTextField(labelWithString: "")
    private let sizeSlider = NSSlider(value: 1, minValue: PetConstants.minimumScale, maxValue: PetConstants.maximumScale, target: nil, action: nil)
    private let sizeValueLabel = NSTextField(labelWithString: "")
    private let alwaysOnTopSwitch = NSButton(checkboxWithTitle: "始终置顶（含全屏空间）", target: nil, action: nil)
    private let automaticSwitch = NSButton(checkboxWithTitle: "启用随机自动动作", target: nil, action: nil)
    private let visibilityButton = NSButton(title: "", target: nil, action: nil)

    init(petController: PetController) {
        self.petController = petController
        super.init(nibName: nil, bundle: nil)
        preferredContentSize = NSSize(width: 350, height: 480)
    }

    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }

    override func loadView() {
        view = NSView(frame: NSRect(origin: .zero, size: preferredContentSize))
        buildInterface()
        refresh()
    }

    func refresh() {
        guard isViewLoaded else { return }
        let animationName = petController.currentAnimation.rawValue
        stateLabel.stringValue = "当前动作：\(animationName)"
        speedSlider.doubleValue = petController.preferences.animationSpeed
        speedValueLabel.stringValue = String(format: "%.0f%%", petController.preferences.animationSpeed * 100)
        sizeSlider.doubleValue = petController.preferences.displayScale
        sizeValueLabel.stringValue = String(format: "%.0f%%", petController.preferences.displayScale * 100)
        alwaysOnTopSwitch.state = petController.preferences.alwaysOnTop ? .on : .off
        automaticSwitch.state = petController.preferences.autoActions ? .on : .off
        visibilityButton.title = petController.isVisible ? "隐藏桌宠" : "显示桌宠"
        if let index = DefaultPetAction.allCases.firstIndex(of: petController.preferences.defaultAction) {
            defaultActionPopup.selectItem(at: index)
        }
    }

    private func buildInterface() {
        let title = NSTextField(labelWithString: "蜥蜴桌宠控制")
        title.font = .systemFont(ofSize: 19, weight: .semibold)
        stateLabel.textColor = .secondaryLabelColor

        let actionButtons = NSStackView(views: [
            button("挥手", #selector(wave)),
            button("跳跃", #selector(jump)),
            button("躺下", #selector(rest)),
            button("等待", #selector(wait)),
        ])
        actionButtons.orientation = .horizontal
        actionButtons.distribution = .fillEqually
        actionButtons.spacing = 8

        defaultActionPopup.addItems(withTitles: DefaultPetAction.allCases.map(\.title))
        defaultActionPopup.target = self
        defaultActionPopup.action = #selector(defaultActionChanged)

        speedSlider.isContinuous = true
        speedSlider.numberOfTickMarks = 7
        speedSlider.allowsTickMarkValuesOnly = false
        speedSlider.target = self
        speedSlider.action = #selector(speedChanged)

        sizeSlider.isContinuous = true
        sizeSlider.numberOfTickMarks = 8
        sizeSlider.allowsTickMarkValuesOnly = false
        sizeSlider.target = self
        sizeSlider.action = #selector(sizeChanged)

        alwaysOnTopSwitch.target = self
        alwaysOnTopSwitch.action = #selector(alwaysOnTopChanged)
        automaticSwitch.target = self
        automaticSwitch.action = #selector(automaticChanged)

        visibilityButton.target = self
        visibilityButton.action = #selector(toggleVisibility)
        let homeButton = button("回到右下角", #selector(moveHome))
        let quitButton = button("退出桌宠", #selector(quit))

        let stack = NSStackView(views: [
            title,
            stateLabel,
            separator(),
            sectionLabel("立即互动"),
            actionButtons,
            sectionLabel("默认静态动作"),
            defaultActionPopup,
            sliderRow(label: "动画速度", slider: speedSlider, value: speedValueLabel),
            sliderRow(label: "桌宠大小", slider: sizeSlider, value: sizeValueLabel),
            alwaysOnTopSwitch,
            automaticSwitch,
            separator(),
            visibilityButton,
            homeButton,
            quitButton,
        ])
        stack.orientation = .vertical
        stack.alignment = .leading
        stack.spacing = 10
        stack.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(stack)

        NSLayoutConstraint.activate([
            stack.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 20),
            stack.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -20),
            stack.topAnchor.constraint(equalTo: view.topAnchor, constant: 18),
            defaultActionPopup.widthAnchor.constraint(equalTo: stack.widthAnchor),
            actionButtons.widthAnchor.constraint(equalTo: stack.widthAnchor),
            visibilityButton.widthAnchor.constraint(equalTo: stack.widthAnchor),
            homeButton.widthAnchor.constraint(equalTo: stack.widthAnchor),
            quitButton.widthAnchor.constraint(equalTo: stack.widthAnchor),
        ])
    }

    private func sectionLabel(_ text: String) -> NSTextField {
        let label = NSTextField(labelWithString: text)
        label.font = .systemFont(ofSize: 12, weight: .medium)
        label.textColor = .secondaryLabelColor
        return label
    }

    private func separator() -> NSBox {
        let box = NSBox()
        box.boxType = .separator
        return box
    }

    private func button(_ title: String, _ action: Selector) -> NSButton {
        let control = NSButton(title: title, target: self, action: action)
        control.bezelStyle = .rounded
        return control
    }

    private func sliderRow(label: String, slider: NSSlider, value: NSTextField) -> NSView {
        let title = NSTextField(labelWithString: label)
        title.setContentHuggingPriority(.required, for: .horizontal)
        value.alignment = .right
        value.font = .monospacedDigitSystemFont(ofSize: 11, weight: .regular)
        value.setContentHuggingPriority(.required, for: .horizontal)
        let row = NSStackView(views: [title, slider, value])
        row.orientation = .horizontal
        row.spacing = 8
        row.widthAnchor.constraint(equalToConstant: 310).isActive = true
        value.widthAnchor.constraint(equalToConstant: 44).isActive = true
        return row
    }

    @objc private func wave() { petController.playInteraction(.waving) }
    @objc private func jump() { petController.playInteraction(.jumping) }
    @objc private func rest() { petController.playInteraction(.resting) }
    @objc private func wait() { petController.playInteraction(.waiting) }

    @objc private func defaultActionChanged() {
        let index = clamp(defaultActionPopup.indexOfSelectedItem, minimum: 0, maximum: DefaultPetAction.allCases.count - 1)
        petController.setDefaultAction(DefaultPetAction.allCases[index])
    }

    @objc private func speedChanged() {
        petController.setAnimationSpeed(speedSlider.doubleValue)
        refresh()
    }

    @objc private func sizeChanged() {
        petController.setDisplayScale(sizeSlider.doubleValue)
        refresh()
    }

    @objc private func alwaysOnTopChanged() {
        petController.setAlwaysOnTop(alwaysOnTopSwitch.state == .on)
    }

    @objc private func automaticChanged() {
        petController.setAutoActions(automaticSwitch.state == .on)
    }

    @objc private func toggleVisibility() { petController.toggleVisibility() }
    @objc private func moveHome() { petController.moveToBottomRight() }
    @objc private func quit() { NSApp.terminate(nil) }
}
