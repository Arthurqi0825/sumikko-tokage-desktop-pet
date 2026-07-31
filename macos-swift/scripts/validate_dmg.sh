#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
PROJECT_ROOT="${SCRIPT_DIR:h:h}"
DMG_PATH="${PROJECT_ROOT}/dist/Tokage-Desktop-Pet-Swift-macOS-universal.dmg"
MOUNT_POINT="${PROJECT_ROOT}/build/swift-dmg-validation-mount"
INSTALL_ROOT="${PROJECT_ROOT}/build/swift-dmg-install-test"
APP_NAME="Tokage Desktop Pet.app"
INSTALLED_APP="${INSTALL_ROOT}/${APP_NAME}"
EXECUTABLE="${INSTALLED_APP}/Contents/MacOS/Tokage Desktop Pet"
REPORT="${PROJECT_ROOT}/qa/swift-dmg-install-validation.txt"
SELF_TEST="${PROJECT_ROOT}/qa/swift-dmg-installed-self-test.json"

cleanup() {
  hdiutil detach "${MOUNT_POINT}" -quiet 2>/dev/null || true
  rm -rf "${MOUNT_POINT}"
}
trap cleanup EXIT

test -f "${DMG_PATH}"
rm -rf "${MOUNT_POINT}" "${INSTALL_ROOT}"
mkdir -p "${MOUNT_POINT}" "${INSTALL_ROOT}"
hdiutil attach "${DMG_PATH}" -readonly -nobrowse -mountpoint "${MOUNT_POINT}" -quiet
test -d "${MOUNT_POINT}/${APP_NAME}"
test -L "${MOUNT_POINT}/Applications"
ditto "${MOUNT_POINT}/${APP_NAME}" "${INSTALLED_APP}"

codesign --verify --deep --strict --verbose=2 "${INSTALLED_APP}"
ARCHITECTURES="$(lipo -archs "${EXECUTABLE}")"
[[ "${ARCHITECTURES}" == *arm64* && "${ARCHITECTURES}" == *x86_64* ]]

if find "${INSTALLED_APP}" -iname '*python*' -o -iname '*pyside*' -o -iname '*qt*' | grep -q .; then
  print -u2 "Python/Qt content was found after installation."
  exit 1
fi

rm -f "${SELF_TEST}"
"${EXECUTABLE}" --self-test --self-test-output "${SELF_TEST}"
[[ "$(plutil -extract all_passed raw "${SELF_TEST}")" == "true" ]]

{
  print "dmg_mount=passed"
  print "applications_link=passed"
  print "relocated_copy=passed"
  print "adhoc_signature=passed"
  print "runtime_self_test=passed"
  print "architectures=${ARCHITECTURES}"
  print "minimum_macos=$(/usr/libexec/PlistBuddy -c 'Print :LSMinimumSystemVersion' "${INSTALLED_APP}/Contents/Info.plist")"
  print "python_qt_entries=0"
  print "linked_libraries:"
  otool -L "${EXECUTABLE}"
} > "${REPORT}"

print "DMG relocation test passed: ${REPORT}"
