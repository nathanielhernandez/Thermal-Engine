"""
Thermal Engine
A visual theme editor for LCD displays.

Entry point for the application.
"""

import sys
import ctypes

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QColor

from sensors import init_sensors
from main_window import ThemeEditorWindow


def is_admin():
    """Check if running with administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def main():
    app = QApplication(sys.argv)

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

    window = ThemeEditorWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
