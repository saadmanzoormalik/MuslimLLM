#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MOBILE_DIR="$ROOT_DIR/mobile"
BUILD_DIR="$MOBILE_DIR/build"
ARCHIVE_PATH="$BUILD_DIR/MuslimLLM.xcarchive"
EXPORT_PATH="$BUILD_DIR/export"
BUILD_NUMBER="${BUILD_NUMBER:-$(date -u +%Y%m%d%H%M)}"

cd "$MOBILE_DIR"
npm ci
npx cap sync ios

cd "$ROOT_DIR"
rm -rf "$ARCHIVE_PATH" "$EXPORT_PATH"
xcodebuild \
  -project mobile/ios/App/App.xcodeproj \
  -scheme App \
  -configuration Release \
  -destination 'generic/platform=iOS' \
  -archivePath "$ARCHIVE_PATH" \
  -allowProvisioningUpdates \
  CURRENT_PROJECT_VERSION="$BUILD_NUMBER" \
  archive

xcodebuild \
  -exportArchive \
  -archivePath "$ARCHIVE_PATH" \
  -exportPath "$EXPORT_PATH" \
  -exportOptionsPlist mobile/ios/ExportOptions.plist \
  -allowProvisioningUpdates

printf 'Exported %s\n' "$EXPORT_PATH/App.ipa"
