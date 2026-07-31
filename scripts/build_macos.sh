#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_VENV="${TOKAGE_BUILD_VENV:-$ROOT_DIR/.build-venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
APP_NAME="Tokage Desktop Pet"
APP_BUNDLE="$ROOT_DIR/dist/macos/$APP_NAME.app"
DMG_PATH="$ROOT_DIR/dist/Tokage-Desktop-Pet-macOS-arm64.dmg"
DMG_ROOT="$ROOT_DIR/build/dmg-root"

if [ ! -x "$BUILD_VENV/bin/python" ]; then
  "$PYTHON_BIN" -m venv "$BUILD_VENV"
fi

"$BUILD_VENV/bin/python" -m pip install -r "$ROOT_DIR/requirements.txt" -r "$ROOT_DIR/requirements-build.txt"

rm -rf "$ROOT_DIR/build/pyinstaller" "$ROOT_DIR/build/spec" "$ROOT_DIR/dist/macos" "$DMG_ROOT"
mkdir -p "$ROOT_DIR/build/pyinstaller" "$ROOT_DIR/build/spec" "$ROOT_DIR/dist/macos" "$DMG_ROOT"

"$BUILD_VENV/bin/pyinstaller" \
  --noconfirm \
  --clean \
  --windowed \
  --name "$APP_NAME" \
  --osx-bundle-identifier "com.local.tokage-desktop-pet" \
  --icon "$ROOT_DIR/assets/app-icon.icns" \
  --add-data "$ROOT_DIR/assets/codex/tokage/spritesheet.webp:assets/codex/tokage" \
  --distpath "$ROOT_DIR/dist/macos" \
  --workpath "$ROOT_DIR/build/pyinstaller" \
  --specpath "$ROOT_DIR/build/spec" \
  "$ROOT_DIR/app.py"

/usr/libexec/PlistBuddy -c "Add :LSUIElement bool true" "$APP_BUNDLE/Contents/Info.plist" 2>/dev/null \
  || /usr/libexec/PlistBuddy -c "Set :LSUIElement true" "$APP_BUNDLE/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Add :CFBundleShortVersionString string 1.0.0" "$APP_BUNDLE/Contents/Info.plist" 2>/dev/null \
  || /usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString 1.0.0" "$APP_BUNDLE/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Add :CFBundleVersion string 1" "$APP_BUNDLE/Contents/Info.plist" 2>/dev/null \
  || /usr/libexec/PlistBuddy -c "Set :CFBundleVersion 1" "$APP_BUNDLE/Contents/Info.plist"

codesign --force --deep --sign - "$APP_BUNDLE"
codesign --verify --deep --strict --verbose=2 "$APP_BUNDLE"

ditto "$APP_BUNDLE" "$DMG_ROOT/$APP_NAME.app"
ln -s /Applications "$DMG_ROOT/Applications"
rm -f "$DMG_PATH"
hdiutil create \
  -volname "$APP_NAME" \
  -srcfolder "$DMG_ROOT" \
  -ov \
  -format UDZO \
  "$DMG_PATH"
hdiutil verify "$DMG_PATH"
shasum -a 256 "$DMG_PATH"
