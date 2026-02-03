# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('presets', 'presets'), ('elements', 'elements'), ('icon.ico', '.'), ('icon.png', '.'), ('LibreHardwareMonitorLib.dll', '.'), ('HidSharp.dll', '.'), ('Microsoft.Win32.Registry.dll', '.'), ('System.IO.FileSystem.AccessControl.dll', '.'), ('System.Security.AccessControl.dll', '.'), ('System.Security.Principal.Windows.dll', '.')]
binaries = []
hiddenimports = ['clr_loader', 'pythonnet', 'clr', 'PySide6.QtSvg']
tmp_ret = collect_all('clr_loader')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    name='ThermalEngine',
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
    icon=['icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ThermalEngine',
)
