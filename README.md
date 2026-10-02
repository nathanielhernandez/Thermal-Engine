# Thermal Engine

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/nathanielh)

A visual theme editor for **LCD AIO cooler displays** (1280x480). Create custom monitoring themes with real-time CPU/GPU sensor data, gauges, clocks, images, and video backgrounds.

![Preview](https://img.shields.io/badge/Display-1280x480-blue) ![Electron](https://img.shields.io/badge/Electron-44-green) ![License](https://img.shields.io/badge/License-MIT-yellow)

<img width="1306" height="732" alt="image" src="https://github.com/user-attachments/assets/d6eafe44-8ea3-4f00-a6bd-2c0b672de1d8" />


## Features

- **Visual drag-and-drop editor** with live preview
- **Real-time sensor data**: CPU/GPU temperature, utilization, clock speed, power
- **No admin required** - runs as a standard user application
- **Auto-recovery**: Sensors automatically reconnect after sleep/wake or if HWiNFO restarts
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
- **System tray** support with minimize-to-tray (the display keeps updating while hidden)

## Supported Displays

- Thermalright Trofeo AIO LCD (1280x480)
- Other HID-based AIO LCD displays (may require configuration)

## Requirements

- Windows 10/11
- **HWiNFO** (for hardware sensor data) - [Download here](https://www.hwinfo.com/)
- Node.js 24+ (only if running from source)

### Hardware Sensor Support

ThermalEngine uses **HWiNFO Shared Memory** to read hardware sensors. This approach:
- Requires no admin privileges
- Has no driver blocklist issues
- Works with all CPUs and GPUs that HWiNFO supports

**Supported hardware** (via HWiNFO):
- **CPUs**: Intel Core (all generations), AMD Ryzen (all generations)
- **GPUs**: NVIDIA GeForce, AMD Radeon

**Setup HWiNFO for ThermalEngine:**

1. Download [HWiNFO](https://www.hwinfo.com/) (installer or portable)
2. Run HWiNFO and select "Sensors-only" mode
3. Go to **Settings** (gear icon)
4. Check **"Shared Memory Support"**
5. Click OK
6. Keep HWiNFO running while using ThermalEngine

> **Tip:** Configure HWiNFO to start with Windows and run minimized to tray. ThermalEngine will automatically connect when HWiNFO becomes available.

> **Note:** The free version of HWiNFO has a **12-hour limit** on Shared Memory Support. After 12 hours, shared memory will be disabled and sensors will stop updating. To restore sensors, restart HWiNFO. For uninterrupted monitoring, consider [HWiNFO Pro](https://www.hwinfo.com/licenses/) which removes this limitation.

## Installation

### Download (Recommended)

1. Go to [Releases](https://github.com/nathanielhernandez/ThermalEngine/releases)
2. Download `ThermalEngine-X.X.X.zip` (portable) or `ThermalEngine-X.X.X-Setup.exe` (installer)
3. **Portable**: Extract the ZIP and run `ThermalEngine.exe`
4. **Installer**: Run the setup and launch from Start Menu
5. Make sure HWiNFO is running with Shared Memory enabled

### From Source

1. Clone this repository:
   ```bash
   git clone https://github.com/nathanielhernandez/Thermal-Engine.git
   cd Thermal-Engine
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Run the editor:
   ```bash
   npm start
   ```

4. Run the tests:
   ```bash
   npm test
   ```

### Local Build

```bash
# Unpacked app for quick testing: dist\win-unpacked\ThermalEngine.exe
npm run dist:dir

# Installer and portable ZIP in dist\
npm run dist
```

Pushing a `vX.Y.Z` tag builds both and publishes a GitHub release.

### Upgrading from 0.8.x (Python)

Settings and presets now live in `%APPDATA%\ThermalEngine`. On first launch, presets from a previous install in `%LOCALAPPDATA%\ThermalEngine\presets` are copied over automatically. Theme `.json` files are compatible in both directions.

## Usage

### Connecting to Display

1. **Close any manufacturer software** (e.g., TRCC) if running - it locks the display
2. Launch the editor
3. The editor will auto-connect, or click "Connect" in the toolbar

### Setting Up Sensors

1. **Start HWiNFO** with "Sensors-only" mode
2. **Enable Shared Memory** in HWiNFO Settings
3. Launch ThermalEngine - it will automatically detect HWiNFO

ThermalEngine and HWiNFO can start in any order - sensors will connect automatically when both are running.

Go to **Display > Diagnose Sensors** to verify sensor connection.

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

### Sensors showing 0 or not working
1. **Check HWiNFO is running** - ThermalEngine requires HWiNFO for sensor data
2. **Enable Shared Memory** in HWiNFO Settings
3. Go to **Display > Diagnose Sensors** to check connection status
4. Sensors will auto-connect when HWiNFO becomes available

### Low FPS / Performance issues
- Reduce target FPS (10 FPS is usually sufficient)
- Avoid video backgrounds on older machines
- Simplify theme (fewer elements)

## Project Structure

```
Thermal-Engine/
├── src/
│   ├── main/                 # Electron main process (Node.js)
│   │   ├── main.js           # App lifecycle, window, tray, IPC
│   │   ├── display.js        # USB HID driver for the LCD (node-hid)
│   │   ├── hwinfo.js         # HWiNFO shared memory reader (koffi FFI)
│   │   ├── system-stats.js   # CPU, RAM and network stats
│   │   ├── sensors.js        # Sensor polling and smoothing
│   │   ├── presets.js        # Preset storage
│   │   ├── settings.js       # Persistent settings and autostart
│   │   ├── validation.js     # Theme file validation
│   │   ├── protocol.js       # te:// protocol for app files and local media
│   │   ├── menu.js           # Application menu
│   │   └── preload.js        # Renderer bridge (window.te)
│   └── renderer/             # UI (plain ES modules, no build step)
│       ├── index.html
│       ├── styles.css
│       └── js/
│           ├── app.js        # Wiring, commands, shortcuts
│           ├── engine.js     # Frame loop: render once, preview + send to LCD
│           ├── render.js     # Scene renderer (Canvas 2D at 1280x480)
│           ├── store.js      # Editor state and undo/redo
│           ├── model.js      # Element data model
│           ├── elements/     # One module per element type
│           └── ui/           # Canvas view, layer list, properties, presets
├── test/                     # Unit tests (node --test)
├── assets/                   # Icons
├── presets/                  # Bundled presets
└── .github/workflows/        # Release build
```

### Adding an element type

Create a module in `src/renderer/js/elements/` that exports `type`, `name`, `defaults` and `draw(ctx, element, env)`, register it in `elements/index.js`, and list its editable properties in `src/renderer/js/ui/property-schema.js`. The same `draw` function renders both the editor preview and the LCD frame.

## License

MIT License - See LICENSE file for details.

## Credits

- [HWiNFO](https://www.hwinfo.com/) - Hardware sensor data provider
- [Electron](https://www.electronjs.org/) - Desktop app framework
- [node-hid](https://github.com/node-hid/node-hid) - USB HID access
- [Koffi](https://koffi.dev/) - Native Windows API calls

## Contributing

Contributions welcome! Please open an issue or PR.
