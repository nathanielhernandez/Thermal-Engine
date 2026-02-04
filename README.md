# Thermal Engine

A visual theme editor for **LCD AIO cooler displays** (1280x480). Create custom monitoring themes with real-time CPU/GPU sensor data, gauges, clocks, images, and video backgrounds.

![Preview](https://img.shields.io/badge/Display-1280x480-blue) ![Python](https://img.shields.io/badge/Python-3.10+-green) ![License](https://img.shields.io/badge/License-MIT-yellow)

## Features

- **Visual drag-and-drop editor** with live preview
- **Real-time sensor data**: CPU/GPU temperature, load, clock speed, power
- **Auto-recovery**: Sensors automatically reconnect after sleep/wake
- **Element types**:
  - Circle gauges with auto-color thresholds
  - Bar gauges with rounded corners and gradient fill
  - Text elements (static or sensor-linked)
  - Digital and analog clocks
  - Images and GIFs
  - Line charts for historical data
  - Rectangles
- **Video backgrounds** with fit modes
- **Preset system** for saving and loading themes
- **Multi-select** with alignment tools
- **Element grouping** for organizing complex themes
- **Undo/Redo** support
- **System tray** support with minimize-to-tray

## Supported Displays

- Thermalright Trofeo AIO LCD (1280x480)
- Other HID-based AIO LCD displays (may require configuration)

## Requirements

- Windows 10/11
- Administrator rights (for hardware sensor access)
- Python 3.10+ (only if running from source)

### Hardware Sensor Support

This application uses [LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor) via a helper process (`SensorHelperApp.exe`) to read hardware sensors. Supported hardware includes:

- **CPUs**: Intel Core (all generations), AMD Ryzen (including Zen 4/5)
- **GPUs**: NVIDIA GeForce, AMD Radeon (discrete GPUs prioritized over integrated)

**Important notes:**

1. **Run as Administrator** - Hardware sensor access requires admin privileges. The installer version requests admin automatically.
2. **Antivirus software** - Some antivirus programs may flag the sensor helper. You may need to add the `SensorHelper/` folder to your antivirus exclusions.

## Installation

### Download (Recommended)

1. Go to [Releases](https://github.com/nathanielhernandez/ThermalEngine/releases)
2. Download `ThermalEngine-vX.X.X-Setup.exe`
3. Run the installer
4. Launch ThermalEngine from the Start Menu or Desktop shortcut

The app will automatically request administrator privileges when launched.

### From Source

1. Clone this repository:
   ```bash
   git clone https://github.com/nathanielhernandez/Thermal-Engine.git
   cd Thermal-Engine
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the editor (as Administrator):
   ```bash
   python main.py
   ```

### Local Test Build

Build a standalone executable locally (mirrors the GitHub Actions release build):

```powershell
# Basic build
.\build-local.ps1 -SkipInstaller

# Clean build (removes previous artifacts first)
.\build-local.ps1 -Clean -SkipInstaller

# Build with installer (requires Inno Setup)
.\build-local.ps1
```

**Output:**
- `dist\ThermalEngine\ThermalEngine.exe` - Run directly to test
- `ThermalEngine-local-dev.zip` - Portable distribution

**Requirements:**
- Python 3.11+
- .NET SDK (for SensorHelperApp)
- Inno Setup (optional, for installer)

**Clean up test build:**
```powershell
Remove-Item -Recurse -Force dist, dist_helper, lhm -ErrorAction SilentlyContinue
```

## Usage

### Connecting to Display

1. **Close any manufacturer software** (e.g., TRCC) if running - it locks the display
2. Launch the editor **as Administrator**
3. The editor will auto-connect, or click "Connect" in the toolbar

### Creating a Theme

1. **Add elements** from the Elements panel (left side)
2. **Drag elements** on the canvas to position them
3. **Resize** using corner handles
4. **Configure properties** in the Properties panel (right side)
5. **Save as preset** via File > Save as Preset

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+N | New theme |
| Ctrl+O | Open theme |
| Ctrl+S | Save theme |
| Ctrl+Shift+S | Save as preset |
| Ctrl+Z | Undo |
| Ctrl+Y | Redo |
| Ctrl+G | Group selected elements |
| Ctrl+Shift+G | Ungroup |
| Delete | Delete selected |
| Ctrl+Click | Multi-select elements |

### Sensor Sources

| Source | Description |
|--------|-------------|
| `cpu_percent` | CPU usage (%) |
| `cpu_temp` | CPU temperature (C) |
| `cpu_clock` | CPU clock speed (MHz) |
| `cpu_power` | CPU power draw (W) |
| `gpu_percent` | GPU usage (%) |
| `gpu_temp` | GPU temperature (C) |
| `gpu_clock` | GPU clock speed (MHz) |
| `gpu_memory_clock` | GPU memory clock (MHz) |
| `gpu_power` | GPU power draw (W) |
| `ram_percent` | RAM usage (%) |
| `net_upload` | Network upload (MB/s) |
| `net_download` | Network download (MB/s) |

## Troubleshooting

### "Display not found"
- Make sure manufacturer software is completely closed
- Check USB connection
- Restart the editor

### Sensors showing 0
- **Run as Administrator** - This is the most common cause (installer version requests admin automatically)
- Check that the `SensorHelper/` folder exists and contains `SensorHelperApp.exe`
- Add the `SensorHelper/` folder to your antivirus exclusions if sensors still don't work
- Go to Display > Diagnose Sensors to check sensor status

### Sensors stop working after sleep
- The application automatically recovers sensors after sleep/wake
- If sensors don't recover, restart the application

### Low FPS / Performance issues
- Reduce target FPS (10 FPS is usually sufficient)
- Avoid video backgrounds on older machines
- Simplify theme (fewer elements)

## Project Structure

```
Thermal-Engine/
├── main.py              # Entry point
├── main_window.py       # Main application window
├── canvas.py            # Visual preview widget
├── properties.py        # Properties panel
├── element_list.py      # Element list panel
├── presets.py           # Preset management
├── element.py           # Theme element data model
├── sensors.py           # Hardware sensor polling (with auto-recovery)
├── video_background.py  # Video background support
├── constants.py         # Configuration constants
├── build-local.ps1      # Local build script (mirrors GitHub Actions)
├── SensorHelperApp/     # Sensor helper source code (.NET)
│   ├── Program.cs
│   └── SensorHelperApp.csproj
├── elements/            # Custom element plugins
│   ├── line_chart.py
│   └── gif.py
├── presets/             # Saved presets
└── .github/workflows/   # CI/CD workflows
    └── release.yml      # Automated release build
```

**Build output (not tracked):**
```
dist/ThermalEngine/      # Standalone build output
└── SensorHelper/        # Sensor helper (built from SensorHelperApp/)
    ├── SensorHelperApp.exe
    └── LibreHardwareMonitorLib.dll
```

## Building SensorHelperApp

If you need to rebuild the sensor helper (requires .NET SDK):

```bash
cd SensorHelperApp
dotnet publish -c Release -o ../SensorHelper
```

## Custom Elements

You can create custom elements by adding Python files to the `elements/` folder. See `elements/line_chart.py` for an example.

## License

MIT License - See LICENSE file for details.

## Credits

- [LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor) - Hardware sensor library
- [PySide6](https://www.qt.io/qt-for-python) - Qt GUI framework
- [Pillow](https://pillow.readthedocs.io/) - Image processing

## Contributing

Contributions welcome! Please open an issue or PR.
