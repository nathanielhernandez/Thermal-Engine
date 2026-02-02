# Thermal Engine

A visual theme editor for **LCD AIO cooler displays** (1280x480). Create custom monitoring themes with real-time CPU/GPU sensor data, gauges, clocks, images, and video backgrounds.

![Preview](https://img.shields.io/badge/Display-1280x480-blue) ![Python](https://img.shields.io/badge/Python-3.10+-green) ![License](https://img.shields.io/badge/License-MIT-yellow)

## Features

- **Visual drag-and-drop editor** with live preview
- **Real-time sensor data**: CPU/GPU temperature, load, clock speed, power
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
- **Undo/Redo** support
- **Performance optimized** with background sensor polling

## Supported Displays

- Thermalright Trofeo AIO LCD (1280x480)
- Other HID-based AIO LCD displays (may require configuration)

## Requirements

- Windows 10/11
- Python 3.10 or later
- Administrator rights (for hardware sensor access)

## Installation

### Quick Install

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/ThermalEngine.git
   cd ThermalEngine
   ```

2. Run the install script:
   ```bash
   install.bat
   ```

3. Run the editor (as Administrator):
   ```bash
   run.bat
   ```

### Manual Install

1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Download LibreHardwareMonitor libraries:
   ```bash
   python download_lhm.py
   ```

3. Run the editor:
   ```bash
   python main.py
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
5. **Save as preset** via File → Save as Preset

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+N | New theme |
| Ctrl+O | Open theme |
| Ctrl+S | Save theme |
| Ctrl+Shift+S | Save as preset |
| Ctrl+Z | Undo |
| Ctrl+Y | Redo |
| F5 | Send to display |
| Ctrl+Click | Multi-select elements |

### Sensor Sources

| Source | Description |
|--------|-------------|
| `cpu_percent` | CPU usage (%) |
| `cpu_temp` | CPU temperature (°C) |
| `cpu_clock` | CPU clock speed (MHz) |
| `cpu_power` | CPU power draw (W) |
| `gpu_percent` | GPU usage (%) |
| `gpu_temp` | GPU temperature (°C) |
| `gpu_clock` | GPU clock speed (MHz) |
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
- Run as Administrator
- Go to Display → Diagnose Sensors to check status
- Ensure LibreHardwareMonitor DLLs are present (run `python download_lhm.py`)

### Low FPS / Performance issues
- Reduce target FPS (10 FPS is usually sufficient)
- Avoid video backgrounds on older machines
- Simplify theme (fewer elements)

## Project Structure

```
ThermalEngine/
├── main.py              # Entry point
├── main_window.py       # Main application window
├── canvas.py            # Visual preview widget
├── properties.py        # Properties panel
├── element_list.py      # Element list panel
├── presets.py           # Preset management
├── element.py           # Theme element data model
├── sensors.py           # Hardware sensor polling
├── video_background.py  # Video background support
├── constants.py         # Configuration constants
├── download_lhm.py      # DLL downloader
├── elements/            # Custom element plugins
│   ├── line_chart.py
│   └── gif.py
└── presets/             # Saved presets
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
