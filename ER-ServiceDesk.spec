# ER-ServiceDesk/ER-ServiceDesk.spec
#
# PyInstaller build spec for the desktop app.
#
# Build on a real Windows machine (or the eventual test VM) with:
#     pip install -r desktop/requirements.txt
#     pyinstaller ER-ServiceDesk.spec
#
# Produces dist/ER-ServiceDesk/ER-ServiceDesk.exe (onedir build -- see
# note below on why onedir rather than onefile).
#
# This only packages desktop/ and its own dependencies (PySide6,
# requests) -- confirmed separately that desktop/ never imports
# anything from app/, the backend package, so none of FastAPI,
# SQLAlchemy, or any other backend dependency needs to be bundled here
# at all.

block_cipher = None

a = Analysis(
    ['desktop/main.py'],
    pathex=[],
    binaries=[],
    # Bundles desktop/assets/ (icon.ico, icon.png) into the build,
    # readable at runtime via app_paths.get_icon_path() -- see that
    # module for how it locates this both in a onedir and onefile build.
    datas=[('desktop/assets', 'assets')],
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
    [],
    exclude_binaries=True,
    name='ER-ServiceDesk',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # GUI app -- no console window should appear
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='desktop/assets/icon.ico',
    manifest='''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
  <application xmlns="urn:schemas-microsoft-com:asm.v3">
    <windowsSettings>
      <dpiAwareness xmlns="http://schemas.microsoft.com/SMI/2016/WindowsSettings">PerMonitorV2</dpiAwareness>
      <dpiAware xmlns="http://schemas.microsoft.com/SMI/2005/WindowsSettings">true/PM</dpiAware>
    </windowsSettings>
  </application>
</assembly>''',
)

# onedir (COLLECT), not onefile: a onefile build re-extracts its entire
# bundle into a fresh temp directory on every single launch, which is
# slower to start and means sys._MEIPASS is a different, disposable
# path each run. onedir keeps everything in one stable folder that WiX
# installs once and the app finds in the same place every time --
# a meaningfully simpler, more robust story for app_paths.get_icon_path()
# and for the installer itself.
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ER-ServiceDesk',
)
