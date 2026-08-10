# ER-ServiceDesk/installer/RestoreDatabaseLocal.spec
#
# PyInstaller build spec for the standalone Local database restore
# tool. Compiled to a real .exe specifically to avoid PowerShell's
# default execution policy blocking an unsigned .ps1 from running at
# all -- confirmed via real testing that this is a genuine barrier for
# exactly the kind of stressed-admin-in-an-emergency scenario this
# tool exists for.
#
# Build on a real Windows machine with:
#     pyinstaller installer/RestoreDatabaseLocal.spec
#
# Produces dist/RestoreDatabaseLocal.exe (onefile -- unlike the main
# app's onedir build, this has zero bundled runtime assets and is
# launched rarely, so a single portable exe is the simpler choice
# here; see ER-ServiceDesk.spec's own comment for why onedir is right
# for that one specifically).
#
# Uses only the Python standard library (subprocess, os, sys,
# datetime) -- no PySide6, no requests, nothing to bundle beyond the
# interpreter itself.

block_cipher = None

a = Analysis(
    ['restore_database_local.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='RestoreDatabaseLocal',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Interactive console tool -- prompts need a real terminal to read input from
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
