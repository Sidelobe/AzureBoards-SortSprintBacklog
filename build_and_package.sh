#!/usr/bin/env bash

pyinstaller --noconfirm AzureBacklogSorter.spec sort_sprint_backlog.py

identity="MY SIGNING IDENTITY"
app_name="Azure Backlog Sorter"
app_filename="${app_name}.app"

mkdir -p dist/dmg
rm -rf dist/dmg/** # clean dir
rm "dist/Azure Backlog Sorter.dmg" # remove existing/previous DMG
cp -R "dist/${app_filename}" dist/dmg

create-dmg \
  --volname "${app_name}" \
  --volicon "" \
  --window-pos 200 120 \
  --window-size 600 300 \
  --icon-size 100 \
  --icon "${app_filename}" 175 120 \
  --hide-extension "${app_filename}" \
  --app-drop-link 425 120 \
  --no-internet-enable \
  "dist/${app_name}.dmg" \
  "dist/dmg/"



# TODO: sign and notarize

# Best to update 'codesign_identity' in .spec file; this recursively signs all executables in the .app, including e.g. Python

# NOTE: consider using create-dmg's --codesign and --notarize options

codesign --verify "dist/${app_name}.dmg"
