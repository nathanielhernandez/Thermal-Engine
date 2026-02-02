"""
Thermal Engine
A visual theme editor for LCD displays.

Entry point for the application.
"""

import sys
import os
import ctypes
import argparse
import atexit
import signal

from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon, QMenu
from PySide6.QtGui import QColor, QIcon, QPixmap, QPainter, QBrush
from PySide6.QtCore import Qt

from sensors import init_sensors
from main_window import ThemeEditorWindow
from app_path import get_app_dir
import settings


def is_admin():
    """Check if running with administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def create_tray_icon():
    """Create tray icon from file or generate one."""
    # Try to load icon from file
    icon_path = os.path.join(get_app_dir(), 'icon.ico')
    if os.path.exists(icon_path):
        return QIcon(icon_path)

    # Fallback: generate icon programmatically
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QBrush(QColor(0, 200, 255)))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(2, 2, 28, 28)
    painter.setBrush(QBrush(QColor(45, 45, 50)))
    painter.drawEllipse(6, 6, 20, 20)
    painter.setBrush(QBrush(QColor(0, 255, 150)))
    painter.drawPie(6, 6, 20, 20, 90 * 16, -200 * 16)
    painter.end()
    return QIcon(pixmap)


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Thermal Engine')
    parser.add_argument('--minimized', action='store_true', help='Start minimized to system tray')
    args = parser.parse_args()

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Keep running when minimized to tray

    # Check for admin rights
    if not is_admin():
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Administrator Required")
        msg.setText("This application needs administrator privileges to read hardware sensors.")
        msg.setInformativeText("CPU and GPU temperatures will not work without admin rights.")
        msg.addButton("Restart as Admin", QMessageBox.ButtonRole.AcceptRole)
        msg.addButton("Continue Anyway", QMessageBox.ButtonRole.RejectRole)

        if msg.exec() == 0:  # "Restart as Admin" clicked
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, " ".join([f'"{arg}"' for arg in sys.argv]), None, 1
            )
            sys.exit(0)

    # Initialize sensors
    init_sensors()

    # Apply dark theme
    app.setStyle("Fusion")

    palette = app.palette()
    palette.setColor(palette.ColorRole.Window, QColor(45, 45, 50))
    palette.setColor(palette.ColorRole.WindowText, QColor(220, 220, 220))
    palette.setColor(palette.ColorRole.Base, QColor(35, 35, 40))
    palette.setColor(palette.ColorRole.AlternateBase, QColor(45, 45, 50))
    palette.setColor(palette.ColorRole.ToolTipBase, QColor(220, 220, 220))
    palette.setColor(palette.ColorRole.ToolTipText, QColor(220, 220, 220))
    palette.setColor(palette.ColorRole.Text, QColor(220, 220, 220))
    palette.setColor(palette.ColorRole.Button, QColor(55, 55, 60))
    palette.setColor(palette.ColorRole.ButtonText, QColor(220, 220, 220))
    palette.setColor(palette.ColorRole.BrightText, QColor(255, 0, 0))
    palette.setColor(palette.ColorRole.Highlight, QColor(0, 120, 215))
    palette.setColor(palette.ColorRole.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)

    # Create main window
    window = ThemeEditorWindow()

    # Register cleanup handlers to ensure HID device is released on any exit
    def cleanup_on_exit():
        try:
            window.cleanup()
        except:
            pass

    atexit.register(cleanup_on_exit)
    app.aboutToQuit.connect(cleanup_on_exit)

    # Handle Ctrl+C and termination signals
    def signal_handler(signum, frame):
        cleanup_on_exit()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Create system tray icon
    tray_icon = QSystemTrayIcon(create_tray_icon(), app)
    tray_icon.setToolTip("Thermal Engine")

    # Tray menu
    tray_menu = QMenu()
    show_action = tray_menu.addAction("Show")
    show_action.triggered.connect(lambda: (window.showNormal(), window.activateWindow()))
    tray_menu.addSeparator()
    quit_action = tray_menu.addAction("Quit")
    quit_action.triggered.connect(window.force_quit)
    tray_icon.setContextMenu(tray_menu)

    # Double-click tray to show window
    def on_tray_activated(reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            window.showNormal()
            window.activateWindow()

    tray_icon.activated.connect(on_tray_activated)
    tray_icon.show()

    # Store tray reference in window for minimize-to-tray functionality
    window.tray_icon = tray_icon

    # Show window (or minimize based on settings/args)
    if args.minimized:
        # Start minimized to tray - don't show window
        window.hide()
    else:
        window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
