# BluePuppy 🐶

<div align="center">

![BluePuppy Logo](app/assets/icon.ico)

**Bluetooth Low Energy Testing & Development Tool**  
GATT Testing • SMP Protocol • Device Firmware Updates (DFU) • Serial Communication

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.11+-green)
![License](https://img.shields.io/badge/license-MIT-orange)
![Platform](https://img.shields.io/badge/platform-windows-lightgrey)

[Features](#features) • [Installation](#installation) • [Usage](#usage) • [Architecture](#architecture) • [Contributing](#contributing)

</div>

---

## Overview

BluePuppy is a comprehensive, desktop application for Bluetooth Low Energy (BLE) development, testing, and firmware management. BluePuppy provides a complete toolset for working with BLE devices, GATT services, and the mcumgr Simple Management Protocol (SMP).

### What is BluePuppy?

BluePuppy is a full-featured BLE testing and development platform that includes:

- 🔍 **GATT Service Explorer**: Discover, read, write, and monitor BLE GATT characteristics in real-time
- 📡 **SMP Protocol Testing**: Send and receive mcumgr SMP commands with echo testing and debugging
- 🔄 **Device Firmware Updates**: Production-grade DFU workflow for Zephyr RTOS and MCUboot devices
- 🔌 **Dual Transport Support**: BLE (wireless) and Serial UART (wired) communication
- 🛠️ **Development Tool**: Perfect for prototyping, debugging, and testing BLE applications

### Key Highlights

- ✅ **Multi-Purpose**: GATT testing, SMP protocol debugging, and firmware updates in one tool
- 🔍 **GATT Inspector**: Read, write, and subscribe to any GATT characteristic with live updates
- 📡 **SMP Debug Console**: Send custom SMP commands and inspect CBOR-encoded responses
- 🚀 **Reliable DFU**: Production-tested firmware update workflow with resume capability
- 🎨 **Modern UI**: Clean PySide6 interface with tabbed navigation and real-time logging
- 🔌 **Dual Transport**: Seamlessly switch between BLE and Serial connections
- 📦 **Extensible**: Designed for future expansion with plugin architecture

## Features

### Core Functionality

#### 🔍 GATT Service Testing
- **Service Discovery**: Automatically discover all GATT services and characteristics
- **Characteristic Explorer**: Browse services with UUIDs, properties, and descriptors
- **Read Operations**: Read any readable characteristic and display hex/ASCII/decoded values
- **Write Operations**: Write hex, ASCII, or binary data to writable characteristics
- **Notifications/Indications**: Subscribe to characteristics and monitor real-time updates

#### 📡 SMP Protocol Testing & Debugging
- **Echo Testing**: Send SMP echo commands to test protocol connectivity
- **Reset Command**: Manually reset the device with SMP command
- **Read Images Details**: Read the image details in device file system

#### 🔄 Device Firmware Updates (DFU)
- **mcumgr/SMP DFU**: Production-grade firmware updates for Zephyr RTOS with MCUboot
- **Image Upload**: Chunked upload with configurable MTU and retry logic
- **Test & Confirm**: Safe two-step firmware swap with rollback protection
- **Resume Support**: Automatically resume interrupted uploads from last checkpoint
- **Slot Management**: List, erase, and manage firmware slots (primary/secondary)
- **Multi-Format**: Support for `.bin`, `.img`, and `.zip` firmware packages
- **Progress Tracking**: Real-time transfer speed, ETA, and progress percentage

#### 🔌 Device Management
- **BLE Device Discovery**: Scan and filter nearby BLE devices by name, address, or RSSI
- **Serial Port Detection**: Auto-detect COM ports with connected devices
- **Multi-Transport Support**: Seamlessly switch between BLE and Serial UART connections
- **Device Information**: Query firmware version, bootloader info, and slot status via SMP
- **Connection Management**: Connect, disconnect, and reconnect with automatic error recovery

#### 🛠️ SMP Protocol Commands (mcumgr)
- **Image Management** (`img_mgmt` - Group 1):
  - List firmware slots and their states
  - Upload firmware to secondary slot
  - Test image (mark for swap on reboot)
  - Confirm image (make swap permanent)
  - Erase secondary slot
- **OS Management** (`os_mgmt` - Group 5):
  - Device reset/reboot
  - Echo testing for connectivity verification
- **File System Management** (`fs_mgmt` - Group 8):
  - Hash/checksum verification (optional)


## Installation

### Prerequisites

- **Windows 10 or 11** (64-bit)
- **Python 3.11 or higher** (for development)
- **Bluetooth LE adapter** (built-in or USB dongle for wireless DFU)
- **USB Serial adapter** (optional, for wired DFU)

### Option 1: Pre-built Executable (Recommended)

1. Download the latest release from [Releases](https://github.com/Bit-Byte-LLC/BluePuppy/releases)
2. Extract `BluePuppy.zip`
3. Run `BluePuppy.exe`

**No Python installation required!** The executable is fully standalone.

### Option 2: From Source

#### Quick Setup

```powershell
# Clone repository
git clone https://github.com/Bit-Byte-LLC/BluePuppy.git
cd BluePuppy

# Run automated setup (creates venv and installs dependencies)
.\setup.bat

# Start the application
.\run_app.bat
```

## Usage

### Basic Workflows

#### 1. **GATT Characteristic Testing**

1. **Launch Application**
   - Run `BluePuppy.exe` (standalone) or `.\run_app.bat` (from source)

2. **Connect to Device**
   - Go to "Devices" tab → Click "Scan"
   - Select your BLE device from the list
   - Click "Connect"

3. **Test GATT Services**
   - Go to "GATT" tab
   - Browse discovered services and characteristics
   - **Read**: Select characteristic → Click "Read" → View hex/ASCII data
   - **Write**: Select characteristic → Enter data → Click "Write"
   - **Notify**: Select characteristic → Click "Enable Notifications" → Watch live updates

#### 2. **SMP Protocol Testing**

1. **Connect to Device** (BLE or Serial with SMP support)

2. **Send SMP Commands**
   - Go to "SMP" tab
   - **Echo Test**: Click "Send Echo" to verify SMP connectivity


#### 3. **Device Firmware Update (DFU)**

1. **Connect to Device** (BLE or Serial)

2. **Perform DFU**
   - Go to "DFU" tab
   - Click "Browse" and select firmware file (`.bin`, `.img`, or `.zip`)
   - Configure settings (MTU, auto-confirm, resume)
   - Click "Start Upload"
   - Monitor progress, speed, and ETA

3. **Test & Confirm** (if not using auto-confirm)
   - After upload, click "Test Image" to mark for swap
   - Device resets and boots new firmware
   - Click "Confirm Image" to make it permanent

#### 4. **Device Information**

1. **Connect to Device**

2. **Query Device Info**
   - Go to "Info" tab
   - Check slot states (primary/secondary)
   - View MAC, MTU and services details

### Supported Firmware Formats

| Format | Description | Source |
|--------|-------------|--------|
| `.bin` | Raw binary image | Direct MCUboot output |
| `.img` | MCUboot signed image | `west build` or nRF Connect SDK |
| `.zip` | Archive with manifest | nRF Connect for Desktop DFU packages |



## Architecture

### Project Structure

```
app/
├── main.py                 # Application entry point with qasync integration
├── smp/                    # SMP protocol implementation
│   ├── pdu.py             # PDU framing and header parsing (8-byte header)
│   ├── cbor_codec.py      # CBOR encoding/decoding with cbor2
│   ├── client.py          # High-level SMP client with transport abstraction
│   ├── img_mgmt.py        # Image management commands (group 1)
│   └── fs_mgmt.py         # File system management (group 8)
├── transport/             # Transport layer
│   ├── ble.py            # BLE GATT transport using bleak (MTU negotiation)
│   └── serial.py         # Serial UART transport using pyserial
├── dfu/                   # DFU workflow orchestration
│   ├── workflow.py       # State machine (IDLE → UPLOADING → TESTING → COMPLETE)
│   ├── image.py          # Image loading, validation, and chunking
│   └── resume.py         # Resume state management (persisted to disk)
├── ui/                    # User interface (PySide6/Qt)
│   ├── main_window.py    # Main application window with tab navigation
│   ├── devices_tab.py    # Device discovery and connection UI
│   ├── dfu_tab.py        # DFU upload interface with progress tracking
│   ├── info_tab.py       # Device information display (version, slots)
│   ├── gatt_tab.py       # GATT service/characteristic inspector
│   ├── smp_tab.py        # SMP command debugger
│   ├── settings_tab.py   # Configuration (MTU, logging, resume)
│   └── widgets/          # Custom UI widgets (log viewer, progress bars)
└── util/                  # Utilities
    ├── log.py            # Logging setup with structlog (rotating files)
    ├── bytes.py          # Byte manipulation helpers (hex, chunking)
    └── version.py        # Semantic version parsing (1.0.0 format)
```

### Technology Stack

| Component | Library | Version | Purpose |
|-----------|---------|---------|---------|
| **Language** | Python | 3.11+ | Core implementation |
| **UI Framework** | PySide6 | 6.6.0+ | Qt bindings for Python |
| **Async Integration** | qasync | 0.24.0+ | Qt + asyncio event loop |
| **BLE** | bleak | 1.0.0+ | Cross-platform GATT client |
| **Serial** | pyserial | 3.5+ | Serial port communication |
| **Protocol** | cbor2 | 5.6.0+ | CBOR serialization for SMP |
| **Logging** | structlog | 23.0.0+ | Structured logging with context |
| **Packaging** | PyInstaller | 6.0.0+ | Standalone executable generation |

### SMP Protocol Implementation

BluePuppy implements the **mcumgr Simple Management Protocol (SMP)** as specified by the Zephyr Project:

#### PDU Structure

```
┌──────────────────────────────────────────────────────────┐
│                    SMP PDU (N bytes)                     │
├───────────┬──────────────────────────────────────────────┤
│  Header   │              CBOR Payload                    │
│ (8 bytes) │            (variable length)                 │
└───────────┴──────────────────────────────────────────────┘

Header Format:
  Byte 0:    Op (3 bits) + Flags (5 bits)
  Byte 1:    Flags (8 bits)
  Bytes 2-3: Length (uint16 big-endian)
  Bytes 4-5: Group ID (uint16 big-endian)
  Byte 6:    Sequence number (uint8)
  Byte 7:    Command ID (uint8)
```

#### Transport Mapping

- **BLE**: GATT write/notify on SMP characteristic
  - Service UUID: `8D53DC1D-1DB7-4CD3-868B-8A527460AA84`
  - Characteristic UUID: `DA2E7828-FBCE-4E01-AE9E-261174997C48`
  - MTU: 247 bytes (BLE 4.2+), negotiated on connect
  - Chunk size: MTU - 8 (header) - 8 (ATT overhead) = ~231 bytes

- **Serial**: Raw UART framing with Base64 encoding (optional)
  - Baud rate: 115200 (configurable)
  - No MTU limit (uses large chunks, e.g., 512 bytes)

#### Implemented Commands

| Group | Command | ID | Description |
|-------|---------|----|----|
| `img_mgmt` (1) | `STATE` | 0 | List firmware slots and their states |
| `img_mgmt` (1) | `UPLOAD` | 1 | Upload firmware chunks to secondary slot |
| `img_mgmt` (1) | `ERASE` | 5 | Erase secondary slot |
| `img_mgmt` (1) | `ERASE_STATE` | 6 | Clear test/confirm flags |
| `os_mgmt` (5) | `RESET` | 5 | Reboot device |


### Resume Mechanism

BluePuppy can resume interrupted uploads:

1. **State Persistence**: Saves upload offset and image SHA-256 to `.bluepuppy_resume.json`
2. **Validation**: On resume, verifies image hash matches and queries device offset
3. **Resume Upload**: Continues from last successfully written chunk
4. **Error Recovery**: Falls back to full upload if device state is inconsistent

## Configuration

### Settings

All settings are persisted in `QSettings` (Windows Registry):

| Setting | Default | Description |
|---------|---------|-------------|
| `chunk_size` | Auto | Override automatic chunk calculation |
| `auto_confirm` | False | Auto-confirm after test (skip manual step) |
| `enable_resume` | True | Enable upload resume on failure |
| `log_level` | INFO | Logging verbosity (DEBUG, INFO, WARNING, ERROR) |
| `log_to_file` | True | Save logs to `%APPDATA%\BluePuppy\logs\` |



## Development

### Setup Development Environment

```powershell
# Install development dependencies
pip install -r requirements.txt

# Install dev tools
pip install black ruff mypy pytest pytest-asyncio pytest-cov
```

### Code Quality

```powershell
# Format code
black app tests

# Lint code
ruff check app tests

# Type checking
mypy app

# Run all checks
black app tests ; ruff check app tests ; mypy app
```

### Testing

```powershell
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_pdu.py

# Run integration tests (requires device)
pytest tests/integration/
```

## Troubleshooting

### Common Issues

#### Image Validation Errors

**Symptoms**: "Invalid image format" or "SHA-256 mismatch"

**Solutions**:
- Verify firmware file is not corrupted (re-download)
- Ensure image is built for target device (correct board configuration)
- Check image is signed with MCUboot key (if using secure boot)

#### Device Not Found in Scan

**Symptoms**: No devices appear in scan results

**Solutions**:
- Verify device is powered on and advertising
- Check device is within BLE range (~10 meters)

#### Permission Errors (Windows)

**Symptoms**: "Access denied" when connecting to COM port

**Solutions**:
- Check COM port isn't open in another application (Device Manager, PuTTY, etc.)
- Update USB serial driver

### Logs and Debugging

Logs are saved to: `%APPDATA%\BluePuppy\logs\bluepuppy.log`

```powershell
# View logs
notepad $env:APPDATA\BluePuppy\logs\bluepuppy.log

# Enable verbose logging
python -m app.main --log-level DEBUG
```

Log entries include:
- Timestamp
- Log level (DEBUG, INFO, WARNING, ERROR)
- Module/function name
- Structured context (device address, bytes transferred, etc.)



## FAQ

### General

**Q: What can I do with BluePuppy?**  
A: BluePuppy is a comprehensive BLE development tool. You can:
- Test GATT characteristics (read, write, notify)
- Debug SMP protocol commands (echo, reset)
- Perform firmware updates (DFU) via mcumgr/SMP
- Monitor BLE connections and debug communication issues
- Work with both wireless (BLE) and wired (Serial) devices

**Q: Does this work on Linux or macOS?**  
A: The core logic is cross-platform (using `bleak` and PySide6), but BluePuppy is currently tested and packaged only for Windows. Linux/macOS support is planned for future releases.

**Q: What firmware formats are supported for DFU?**  
A: 
- Raw binary (`.bin`) - direct MCUboot output
- MCUboot image (`.img`) - signed/encrypted images
- ZIP archives (`.zip`) - nRF Connect or Zephyr build outputs containing manifest

### Technical

**Q: What's the maximum firmware size?**  
A: Limited by device flash capacity (typically 100KB-1MB for embedded devices). BluePuppy handles any size firmware that fits in the device's secondary slot.

**Q: How fast is the upload?**  
A: BLE transfer speeds vary:
- Typical: 5-15 KB/s (BLE 4.2 with MTU 247)
- Optimal: 15-25 KB/s (BLE 5.0 with larger MTU)
- Serial: 50-100 KB/s (115200 baud)

## Contributing

Contributions are welcome! We appreciate bug reports, feature requests, and pull requests.

### How to Contribute

1. **Fork the Repository**
   ```bash
   git clone https://github.com/Bit-Byte-LLC/BluePuppy.git
   cd BluePuppy
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**
   - Follow code style (black + ruff)
   - Add tests for new functionality
   - Update documentation

3. **Test Your Changes**
   ```powershell
   # Run tests
   pytest
   
   # Check code quality
   black app tests
   ruff check app tests
   mypy app
   ```

4. **Submit Pull Request**
   - Push to your fork
   - Create PR against `dev` branch
   - Describe changes and motivation

### Development Guidelines

- **Code Style**: Follow PEP 8, use `black` (line length 100)
- **Type Hints**: All functions must have type annotations
- **Docstrings**: Use Google-style docstrings for classes and functions
- **Testing**: Aim for >80% code coverage
- **Commits**: Use conventional commits (feat, fix, docs, refactor, test, chore)

### Reporting Issues

When reporting bugs, include:
- OS version (Windows 10/11, build number)
- Python version
- BluePuppy version
- Steps to reproduce
- Relevant logs (from `%APPDATA%\BluePuppy\logs\`)
- Device type and firmware version

### Feature Requests

For new features, describe:
- Use case and motivation
- Expected behavior
- Alternative solutions considered
- Impact on existing functionality

## Support

For questions, issues, or feature requests:

- **GitHub Issues**: [Report a bug](https://github.com/Bit-Byte-LLC/BluePuppy/issues)
- **GitHub Discussions**: [Ask questions](https://github.com/Bit-Byte-LLC/BluePuppy/discussions)

## Acknowledgments

- **Zephyr Project** - For mcumgr protocol specification and MCUboot
- **Nordic Semiconductor** - For excellent nRF devices and comprehensive DFU documentation
- **bleak** - For the robust cross-platform BLE library
- **PySide6** - For Qt Python bindings enabling modern desktop UIs

## Citation

If you use BluePuppy in research or commercial projects, please cite:

```bibtex
@software{bluepuppy2025,
title = {BluePuppy: Bluetooth Low Energy Testing and Development Tool},
   author = {{Bit Byte LLC - Open Source Projects Team}},
   year = {2025},
   url = {https://github.com/Bit-Byte-LLC/BluePuppy},
   version = {1.0.0}
}
```

---

<div align="center">

**Developed by [Bit Byte LLC](https://bit-byte.us)**

[⬆ Back to Top](#bluepuppy-)

</div>
