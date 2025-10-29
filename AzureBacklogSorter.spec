# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['sort_sprint_backlog.py'],
    pathex=[],
    binaries=[],
    datas=[ ('config.yml', '.') ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AzureBacklogSorter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['AzureBacklogSorter.icns'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AzureBacklogSorter',
)
app = BUNDLE(
    coll,
    name='Azure Backlog Sorter.app',
    version='1.0.0',
    icon='AzureBacklogSorter.icns',
    bundle_identifier=None,
)
