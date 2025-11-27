# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for BluePuppy
Generates both one-folder and one-file distributions
"""

import sys
import tomllib
import subprocess
from pathlib import Path

block_cipher = None

# Application metadata
APP_NAME = "BluePuppy"
APP_AUTHOR = "Bit Byte LLC - Open Source Projects Team"

# Get application root (parent of app_build)
app_root = Path(SPECPATH).parent

# Read version from pyproject.toml
with open(app_root / "pyproject.toml", "rb") as f:
    pyproject_data = tomllib.load(f)
    APP_VERSION = pyproject_data["project"]["version"]

# Generate version_info.txt from pyproject.toml
print(f"Generating version_info.txt for version {APP_VERSION}...")
subprocess.run([sys.executable, str(Path(SPECPATH) / "generate_version_info.py")], check=True)

# Analysis: collect all dependencies
a = Analysis(
    [str(app_root / 'app' / 'main.py')],
    pathex=[str(app_root)],
    binaries=[],
    datas=[
        # Include icon file
        (str(app_root / 'app' / 'assets' / 'icon.ico'), 'assets'),
    ],
    hiddenimports=[
        'bleak',
        'bleak.backends.winrt',
        'cbor2',
        'serial',
        'structlog',
        'qasync',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'PIL',
        'tkinter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Filter out unnecessary packages
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# One-folder build (default for development)
exe_folder = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Windows GUI app (no console)
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=str(Path(SPECPATH) / 'version_info.txt') if (Path(SPECPATH) / 'version_info.txt').exists() else None,
    icon=str(app_root / 'app' / 'assets' / 'icon.ico') if (app_root / 'app' / 'assets' / 'icon.ico').exists() else None,
)

coll = COLLECT(
    exe_folder,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_NAME,
)

# One-file build (for distribution)
exe_onefile = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=f'{APP_NAME}-Portable',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=str(Path(SPECPATH) / 'version_info.txt') if (Path(SPECPATH) / 'version_info.txt').exists() else None,
    icon=str(app_root / 'app' / 'assets' / 'icon.ico') if (app_root / 'app' / 'assets' / 'icon.ico').exists() else None,
)
