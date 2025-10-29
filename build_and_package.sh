#!/usr/bin/env bash

pyinstaller --noconfirm AzureBacklogSorter.spec sort_sprint_backlog.py

app_name="Azure Backlog Sorter"
app_path="${app_name}.app"

mkdir -p dist/dmg
rm -rf dist/dmg/** # clean dir
rm "dist/Azure Backlog Sorter.dmg" # remove existing/previous DMG
cp -r "dist/${app_path}" dist/dmg

create-dmg \
  --volname "${app_name}r" \
  --volicon "" \
  --window-pos 200 120 \
  --window-size 600 300 \
  --icon-size 100 \
  --icon "${app_path}" 175 120 \
  --hide-extension "${app_path}" \
  --app-drop-link 425 120 \
  "dist/${app_name}.dmg" \
  "dist/dmg/"