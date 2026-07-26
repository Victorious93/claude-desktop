#!/usr/bin/env python3
# Claude Desktop — entry point
# Victorious Framework | Origin Source Labs

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
from claude_desktop.window import MainWindow
from claude_desktop.style import STYLESHEET


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Claude Desktop")
    app.setOrganizationName("Origin Source Labs")
    app.setStyleSheet(STYLESHEET)

    # Prefer JetBrains Mono; fall back gracefully
    font = QFont("JetBrains Mono")
    if not font.exactMatch():
        font = QFont("Fira Mono")
    if not font.exactMatch():
        font = QFont("Courier New")
    font.setPointSize(11)
    app.setFont(font)

    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
