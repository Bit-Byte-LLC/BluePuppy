#!/usr/bin/env python3
"""
Generate version_info.txt for Windows executable from pyproject.toml
This script is called automatically by BluePuppy.spec during build
"""

import tomllib
from pathlib import Path


def get_version_from_pyproject() -> tuple[int, int, int, int]:
    """Read version from pyproject.toml and parse into components."""
    project_root = Path(__file__).parent.parent
    pyproject_path = project_root / "pyproject.toml"
    
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)
    
    version_str = data["project"]["version"]
    parts = version_str.split('.')
    
    major = int(parts[0]) if len(parts) > 0 else 0
    minor = int(parts[1]) if len(parts) > 1 else 0
    patch = int(parts[2]) if len(parts) > 2 else 0
    build = 0
    
    return major, minor, patch, build


def generate_version_info_txt(output_path: Path) -> None:
    """Generate version_info.txt file."""
    major, minor, patch, build = get_version_from_pyproject()
    version_str = f"{major}.{minor}.{patch}.{build}"
    
    content = f'''# UTF-8
#
# For more details about fixed file info:
# See: http://msdn.microsoft.com/en-us/library/ms646997.aspx

VSVersionInfo(
  ffi=FixedFileInfo(
    # filevers and prodvers should be always a tuple with four items: (1, 2, 3, 4)
    # Set not needed items to zero 0.
    filevers=({major}, {minor}, {patch}, {build}),
    prodvers=({major}, {minor}, {patch}, {build}),
    # Contains a bitmask that specifies the valid bits 'flags'r
    mask=0x3f,
    # Contains a bitmask that specifies the Boolean attributes of the file.
    flags=0x0,
    # The operating system for which this file was designed.
    # 0x4 - NT and there is no need to change it.
    OS=0x40004,
    # The general type of file.
    # 0x1 - the file is an application.
    fileType=0x1,
    # The function of the file.
    # 0x0 - the function is not defined for this fileType
    subtype=0x0,
    # Creation date and time stamp.
    date=(0, 0)
    ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'Bit Byte LLC'),
        StringStruct(u'FileDescription', u'BluePuppy Device BLE Testing Utility'),
        StringStruct(u'FileVersion', u'{version_str}'),
        StringStruct(u'InternalName', u'BluePuppy'),
        StringStruct(u'LegalCopyright', u'Copyright (c) 2025 Bit Byte LLC'),
        StringStruct(u'OriginalFilename', u'BluePuppy.exe'),
        StringStruct(u'ProductName', u'BluePuppy'),
        StringStruct(u'ProductVersion', u'{version_str}')])
      ]), 
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
'''
    
    output_path.write_text(content, encoding="utf-8")
    print(f"Generated {output_path.name} with version {major}.{minor}.{patch}.{build}")


if __name__ == "__main__":
    output_path = Path(__file__).parent / "version_info.txt"
    generate_version_info_txt(output_path)
