"""
Constants and configuration for Thermal Engine.
"""

# Display dimensions
DISPLAY_WIDTH = 1280
DISPLAY_HEIGHT = 480
PREVIEW_SCALE = 0.5

# HID Device settings
VENDOR_ID = 0x35CC
PRODUCT_ID = 0x0104

# Base element types available in the editor
_BASE_ELEMENT_TYPES = [
    "circle_gauge",
    "bar_gauge",
    "text",
    "rectangle",
    "clock",
    "analog_clock",
    "image",
]

# This will be populated with custom elements after they are loaded
ELEMENT_TYPES = _BASE_ELEMENT_TYPES.copy()


def register_custom_element_types(custom_types):
    """Register custom element types from the elements folder."""
    global ELEMENT_TYPES
    ELEMENT_TYPES = _BASE_ELEMENT_TYPES + list(custom_types)

# Data sources for dynamic elements (flat list for backwards compatibility)
DATA_SOURCES = [
    "static",
    "cpu_percent",
    "cpu_temp",
    "cpu_clock",
    "cpu_power",
    "ram_percent",
    "ram_used",
    "ram_available",
    "gpu_percent",
    "gpu_temp",
    "gpu_clock",
    "gpu_memory_clock",
    "gpu_memory_percent",
    "gpu_power",
    "net_upload",
    "net_download",
]

# Categorized data sources for UI display
# Format: (source_id, display_name, unit, unit_symbol)
DATA_SOURCES_CATEGORIZED = {
    "Static": [
        ("static", "Static Value", "percent", "%"),
    ],
    "CPU": [
        ("cpu_percent", "CPU Load", "percent", "%"),
        ("cpu_temp", "CPU Temperature", "temp", "°C"),
        ("cpu_clock", "CPU Clock Speed", "clock", "MHz"),
        ("cpu_power", "CPU Power", "power", "W"),
    ],
    "GPU": [
        ("gpu_percent", "GPU Load", "percent", "%"),
        ("gpu_temp", "GPU Temperature", "temp", "°C"),
        ("gpu_clock", "GPU Clock Speed", "clock", "MHz"),
        ("gpu_memory_percent", "GPU Memory", "percent", "%"),
        ("gpu_memory_clock", "GPU Memory Clock", "clock", "MHz"),
        ("gpu_power", "GPU Power", "power", "W"),
    ],
    "Memory": [
        ("ram_percent", "RAM Usage", "percent", "%"),
        ("ram_used", "RAM Used", "size", "GB"),
        ("ram_available", "RAM Available", "size", "GB"),
    ],
    "Network": [
        ("net_upload", "Upload Speed", "speed", "MB/s"),
        ("net_download", "Download Speed", "speed", "MB/s"),
    ],
}

# Lookup for source units
SOURCE_UNITS = {}
for category, sources in DATA_SOURCES_CATEGORIZED.items():
    for source_info in sources:
        source_id, name, unit_type, unit_symbol = source_info
        SOURCE_UNITS[source_id] = {
            "name": name,
            "type": unit_type,
            "symbol": unit_symbol
        }

# Default element properties by type
DEFAULT_ELEMENT_PROPS = {
    "circle_gauge": {"radius": 120, "x": 200, "y": 240, "text": "GAUGE"},
    "bar_gauge": {"width": 300, "height": 30, "x": 100, "y": 100, "text": "BAR"},
    "text": {"x": 100, "y": 100, "text": "Text Label", "font_size": 36, "width": 200, "height": 50},
    "rectangle": {"width": 200, "height": 100, "x": 100, "y": 100},
    "clock": {"x": 100, "y": 100, "font_size": 48, "width": 200, "height": 60},
    "analog_clock": {"radius": 100, "x": 200, "y": 240, "color": "#ffffff", "background_color": "#1a1a2e"},
    "image": {"width": 200, "height": 200, "x": 100, "y": 100}
}
