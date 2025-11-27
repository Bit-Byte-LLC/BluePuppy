# Application Assets

## Icons

Place application icon here:
- `icon.ico` - Windows icon (256x256, 128x128, 64x64, 48x48, 32x32, 16x16)
- `icon.png` - PNG icon (512x512 recommended)

You can create an icon using:
- Icon converters: https://icoconvert.com/
- Design tools: Figma, Inkscape, GIMP

## Recommended Icon Design

For a DFU/firmware update application:
- Use a microchip or circuit board symbol
- Add wireless signal waves (for BLE)
- Include an upload arrow
- Use blue/cyan color scheme (matches Nordic/tech theme)
- Keep it simple and recognizable at small sizes

## Placeholder

Until you create a custom icon, PyInstaller will use the default Python icon.

To add your icon:
1. Place `icon.ico` in this directory
2. Rebuild with `scripts\build_windows.bat`
3. Icon will be embedded in the executable
