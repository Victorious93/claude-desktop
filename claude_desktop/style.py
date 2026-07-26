# Claude Desktop — stylesheet
# Victorious Framework | Origin Source Labs

STYLESHEET = """
QMainWindow, QDialog, QWidget {
    background-color: #0d0d0d;
    color: #e0e0e0;
    font-family: "JetBrains Mono", "Fira Mono", "Courier New", monospace;
    font-size: 13px;
}

QTextEdit, QTextBrowser, QPlainTextEdit {
    background-color: #111111;
    color: #e0e0e0;
    border: 1px solid #1e1e1e;
    border-radius: 4px;
    padding: 8px;
    selection-background-color: #00ff4130;
}

QPushButton {
    background-color: #1a1a1a;
    color: #00ff41;
    border: 1px solid #00ff41;
    border-radius: 4px;
    padding: 6px 14px;
    font-family: "JetBrains Mono", monospace;
}
QPushButton:hover { background-color: #00ff4115; }
QPushButton:pressed { background-color: #00ff4130; }
QPushButton:disabled {
    color: #333;
    border-color: #333;
}

QPushButton#send_btn {
    background-color: #00ff41;
    color: #0d0d0d;
    font-weight: bold;
    padding: 8px 20px;
}
QPushButton#send_btn:hover { background-color: #00cc33; }
QPushButton#send_btn:disabled {
    background-color: #1a3320;
    color: #2a5a30;
    border: none;
}

QComboBox {
    background-color: #1a1a1a;
    color: #e0e0e0;
    border: 1px solid #2a2a2a;
    border-radius: 4px;
    padding: 4px 8px;
    min-width: 180px;
}
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background-color: #1a1a1a;
    color: #e0e0e0;
    selection-background-color: #00ff4120;
}

QLineEdit {
    background-color: #111111;
    color: #e0e0e0;
    border: 1px solid #2a2a2a;
    border-radius: 4px;
    padding: 6px 10px;
}
QLineEdit:focus { border-color: #00ff41; }

QScrollBar:vertical {
    background: #0d0d0d;
    width: 8px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #2a2a2a;
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover { background: #00ff4140; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QStatusBar {
    background-color: #0a0a0a;
    color: #555;
    border-top: 1px solid #1a1a1a;
    font-size: 11px;
}

QLabel { color: #e0e0e0; }
QLabel#title_label {
    color: #00ff41;
    font-size: 15px;
    font-weight: bold;
}
QLabel#section_label {
    color: #00ff41;
    font-size: 11px;
    letter-spacing: 1px;
}

QCheckBox { color: #e0e0e0; spacing: 6px; }
QCheckBox::indicator {
    width: 14px; height: 14px;
    border: 1px solid #2a2a2a;
    border-radius: 3px;
    background: #111;
}
QCheckBox::indicator:checked {
    background: #00ff41;
    border-color: #00ff41;
}

QFrame#separator {
    background-color: #1a1a1a;
    max-height: 1px;
}

QSplitter::handle { background: #1a1a1a; width: 1px; }

QToolBar {
    background: #0a0a0a;
    border-bottom: 1px solid #1a1a1a;
    spacing: 4px;
    padding: 4px;
}

QMenu {
    background-color: #1a1a1a;
    color: #e0e0e0;
    border: 1px solid #2a2a2a;
}
QMenu::item:selected { background-color: #00ff4120; }
QMenu::separator { background: #2a2a2a; height: 1px; margin: 2px 0; }

QMenuBar {
    background-color: #0a0a0a;
    color: #e0e0e0;
    border-bottom: 1px solid #1a1a1a;
}
QMenuBar::item:selected { background-color: #00ff4120; }

QTabWidget::pane { border: 1px solid #1a1a1a; }
QTabBar::tab {
    background: #111;
    color: #888;
    padding: 6px 14px;
    border: 1px solid #1a1a1a;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}
QTabBar::tab:selected { background: #1a1a1a; color: #00ff41; }
"""

# HTML template for chat messages
USER_MSG_HTML = """
<div style="margin: 12px 0 4px 0; color: #00ff41; font-size: 11px; letter-spacing: 1px;">
  ▶ YOU
</div>
<div style="background: #111; border-left: 3px solid #00ff41; padding: 10px 14px;
            border-radius: 0 4px 4px 0; margin-bottom: 6px; color: #e0e0e0;
            white-space: pre-wrap; font-family: 'JetBrains Mono', monospace;">
{content}
</div>
"""

ASSISTANT_MSG_HTML = """
<div style="margin: 12px 0 4px 0; color: #888; font-size: 11px; letter-spacing: 1px;">
  ◆ CLAUDE  <span style="color: #444; font-size: 10px;">{model}</span>
</div>
<div style="background: #0f0f0f; border-left: 3px solid #333; padding: 10px 14px;
            border-radius: 0 4px 4px 0; margin-bottom: 6px; color: #e0e0e0;">
{content}
</div>
"""

THINKING_HTML = """
<div style="margin: 8px 0 4px 0; color: #444; font-size: 10px; letter-spacing: 1px;">
  ◈ THINKING
</div>
<div style="background: #0a0a0a; border-left: 2px solid #222; padding: 8px 14px;
            border-radius: 0 4px 4px 0; margin-bottom: 4px; color: #444;
            font-style: italic; font-size: 11px; white-space: pre-wrap;">
{content}
</div>
"""

ERROR_HTML = """
<div style="background: #1a0808; border-left: 3px solid #ff3333; padding: 10px 14px;
            border-radius: 0 4px 4px 0; margin: 8px 0; color: #ff6666;">
  ✗ {content}
</div>
"""
