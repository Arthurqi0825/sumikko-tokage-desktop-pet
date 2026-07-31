# Tokage Desktop Pet — Native macOS

This folder contains the independent macOS desktop pet rewritten in native Swift and AppKit. It does not embed Python, PySide, Qt, or a Python runtime.

## Open and test in Xcode

1. Open `TokageDesktopPet.xcodeproj`.
2. Select the `TokageDesktopPet` scheme and `My Mac`.
3. Press Run.

The app is a menu-bar accessory. Its pet panel is transparent, ignores clicks on transparent pixels, joins every Space, and can appear beside full-screen apps. The menu-bar icon opens the native control panel.

## Native behavior

- Single click: wave; double click: jump.
- Drag: animated left/right running.
- Right click: interaction and settings menu.
- Native menu-bar control panel with action, speed, size, default-action, visibility, auto-action, and always-on-top controls.
- Display scale: 10%–200%; animation speed: 50%–200%.
- Static defaults: idle, jump, rest, wave, and wait.
- Single running instance per user session.
- `NSPanel.collectionBehavior`: `canJoinAllSpaces`, `fullScreenAuxiliary`, `stationary`, `ignoresCycle`.

## Build the ad-hoc DMG

Run `macos-swift/scripts/build_dmg.sh` from Terminal. The output is:

`dist/Tokage-Desktop-Pet-Swift-macOS-universal.dmg`

This Universal 2 DMG is ad-hoc signed because no Apple Developer ID is configured. It can be uploaded to GitHub Releases, but other users may need to right-click Open or allow it in Privacy & Security. Public distribution without that warning requires Developer ID signing and Apple notarization.
