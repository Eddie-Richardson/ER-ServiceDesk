# ER-ServiceDesk/installer/RestoreDatabaseServer.spec
#
# PyInstaller build spec for the standalone Server database restore
# tool. Same reasoning as RestoreDatabaseLocal.spec -- see that file's
# own header.
#
# Build on a real Windows machine with:
#     pyinstaller installer/RestoreDatabaseServer.spec
#
# Produces dist/RestoreDatabaseServer.exe (onefile).

block_cipher = None

a = Analysis(
    ['restore_database_server.py'],
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
    name='RestoreDatabaseServer',
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
