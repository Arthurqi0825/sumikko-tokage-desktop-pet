#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
NATIVE_ROOT="${SCRIPT_DIR:h}"
PROJECT_ROOT="${NATIVE_ROOT:h}"
DERIVED_DATA="${PROJECT_ROOT}/build/swift-derived"
MODULE_CACHE="${PROJECT_ROOT}/build/swift-module-cache"
APP_NAME="Tokage Desktop Pet.app"
BUILT_APP="${DERIVED_DATA}/Build/Products/Release/${APP_NAME}"
DIST_DIR="${PROJECT_ROOT}/dist"
DIST_APP_DIR="${DIST_DIR}/swift"
DIST_APP="${DIST_APP_DIR}/${APP_NAME}"
DMG_ROOT="${PROJECT_ROOT}/build/swift-dmg-root"
DMG_PATH="${DIST_DIR}/Tokage-Desktop-Pet-Swift-macOS-universal.dmg"
QA_DIR="${PROJECT_ROOT}/qa"
SELF_TEST_REPORT="${QA_DIR}/swift-native-self-test.json"
MANIFEST="${QA_DIR}/swift-native-build-manifest.txt"

mkdir -p "${PROJECT_ROOT}/build" "${MODULE_CACHE}" "${DIST_DIR}" "${QA_DIR}"

xcodebuild \
  -project "${NATIVE_ROOT}/TokageDesktopPet.xcodeproj" \
  -scheme TokageDesktopPet \
  -configuration Release \
  -derivedDataPath "${DERIVED_DATA}" \
  ARCHS="arm64 x86_64" \
  ONLY_ACTIVE_ARCH=NO \
  CLANG_MODULE_CACHE_PATH="${MODULE_CACHE}" \
  CODE_SIGNING_ALLOWED=NO \
  clean build

test -d "${BUILT_APP}"
rm -rf "${DIST_APP_DIR}"
mkdir -p "${DIST_APP_DIR}"
ditto "${BUILT_APP}" "${DIST_APP}"
codesign --force --deep --sign - "${DIST_APP}"
codesign --verify --deep --strict --verbose=2 "${DIST_APP}"

if find "${DIST_APP}" -iname '*python*' -o -iname '*pyside*' -o -iname '*qt*' | grep -q .; then
  print -u2 "Python/Qt content was found in the native application bundle."
  exit 1
fi

EXECUTABLE="${DIST_APP}/Contents/MacOS/Tokage Desktop Pet"
test -x "${EXECUTABLE}"
ARCHITECTURES="$(lipo -archs "${EXECUTABLE}")"
[[ "${ARCHITECTURES}" == *arm64* && "${ARCHITECTURES}" == *x86_64* ]]

rm -f "${SELF_TEST_REPORT}"
"${EXECUTABLE}" --self-test --self-test-output "${SELF_TEST_REPORT}"
[[ "$(plutil -extract all_passed raw "${SELF_TEST_REPORT}")" == "true" ]]

rm -rf "${DMG_ROOT}"
mkdir -p "${DMG_ROOT}"
ditto "${DIST_APP}" "${DMG_ROOT}/${APP_NAME}"
ln -s /Applications "${DMG_ROOT}/Applications"
rm -f "${DMG_PATH}"
hdiutil create \
  -volname "Tokage Desktop Pet" \
  -srcfolder "${DMG_ROOT}" \
  -ov \
  -format UDZO \
  "${DMG_PATH}"
hdiutil verify "${DMG_PATH}"

{
  print "app=${DIST_APP}"
  print "dmg=${DMG_PATH}"
  print "architectures=${ARCHITECTURES}"
  print "minimum_macos=$(/usr/libexec/PlistBuddy -c 'Print :LSMinimumSystemVersion' "${DIST_APP}/Contents/Info.plist")"
  print "app_size=$(du -sh "${DIST_APP}" | awk '{print $1}')"
  print "dmg_size=$(du -sh "${DMG_PATH}" | awk '{print $1}')"
  print "sha256=$(shasum -a 256 "${DMG_PATH}" | awk '{print $1}')"
  print "python_qt_entries=0"
  print "signature=adhoc"
} > "${MANIFEST}"

print "Native DMG ready: ${DMG_PATH}"
print "Validation report: ${SELF_TEST_REPORT}"
