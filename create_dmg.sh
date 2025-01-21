#!/bin/bash
# create_dmg.sh

# Değişkenler
APP_NAME="WtoSRT"
DMG_NAME="${APP_NAME}_Installer"
APP_DIR="dist/${APP_NAME}.app"
DMG_DIR="dist"

# Eski DMG'yi temizle
rm -f "${DMG_DIR}/${DMG_NAME}.dmg"

# DMG oluştur
create-dmg \
  --volname "${APP_NAME}" \
  --volicon "icon.icns" \
  --window-pos 200 120 \
  --window-size 600 400 \
  --icon-size 100 \
  --icon "${APP_NAME}.app" 175 120 \
  --hide-extension "${APP_NAME}.app" \
  --app-drop-link 425 120 \
  "${DMG_DIR}/${DMG_NAME}.dmg" \
  "${APP_DIR}"