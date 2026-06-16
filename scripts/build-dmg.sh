#!/bin/bash
# Build BrainSquared.dmg
# Requires: create-dmg (brew install create-dmg)
# Run from repo root after archiving in Xcode

set -euo pipefail

APP_NAME="BrainSquared"
ARCHIVE_PATH="macos/build/${APP_NAME}.xcarchive"
EXPORT_PATH="macos/build/export"
DMG_PATH="dist/${APP_NAME}.dmg"

echo "==> Exporting archive..."
xcodebuild -exportArchive \
  -archivePath "$ARCHIVE_PATH" \
  -exportPath "$EXPORT_PATH" \
  -exportOptionsPlist macos/ExportOptions.plist

echo "==> Building DMG..."
mkdir -p dist
create-dmg \
  --volname "$APP_NAME" \
  --volicon "brain-logo.png" \
  --window-pos 200 120 \
  --window-size 600 400 \
  --icon-size 100 \
  --icon "${APP_NAME}.app" 175 190 \
  --hide-extension "${APP_NAME}.app" \
  --app-drop-link 425 190 \
  "$DMG_PATH" \
  "$EXPORT_PATH/${APP_NAME}.app"

echo "==> Done: $DMG_PATH"
