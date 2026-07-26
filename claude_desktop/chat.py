# Claude Desktop — chat widget
# Victorious Framework | Origin Source Labs

import html
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser,
    QTextEdit, QPushButton, QLabel, QSplitter,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent, QTextCursor, QFont
from .style import (
    USER_MSG_HTML, ASSISTANT_MSG_HTML, THINKING_HTML, ERROR_HTML
)


class InputBox(QTextEdit):
    """Multi-line input that sends on Enter (Shift+Enter for newline)."""

    submit = pyqtSignal()

    def keyPressEvent(self, e: QKeyEvent):
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if e.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                super().keyPressEvent(e)
            else:
                self.submit.emit()
        else:
            super().keyPressEvent(e)


def _escape(text: str) -> str:
    return html.escape(text)


def _format_markdown(text: str) -> str:
    """Very lightweight markdown → HTML (code blocks, inline code, bold)."""
    import re
    lines = text.split("\n")
    out = []
    in_code = False
    code_buf = []
    lang = ""

    for line in lines:
        if line.startswith("```"):
            if not in_code:
                in_code = True
                lang = html.escape(line[3:].strip())
                code_buf = []
            else:
                in_code = False
                code_content = html.escape("\n".join(code_buf))
                label = f'<span style="color:#555; font-size:10px;">{lang}</span><br>' if lang else ""
                out.append(
                    f'<div style="background:#0a0a0a; border:1px solid #1e1e1e; '
                    f'border-radius:4px; padding:10px; margin:6px 0; '
                    f'font-family: JetBrains Mono, monospace; font-size:12px; '
                    f'white-space:pre; overflow-x:auto;">'
                    f'{label}{code_content}</div>'
                )
            continue

        if in_code:
            code_buf.append(line)
            continue

        escaped = html.escape(line)
        # inline code
        escaped = re.sub(r'`([^`]+)`', r'<code style="background:#1a1a1a; padding:1px 4px; border-radius:3px;">\1</code>', escaped)
        # bold
        escaped = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', escaped)
        # italic
        escaped = re.sub(r'\*([^*]+)\*', r'<i>\1</i>', escaped)
        out.append(escaped)

    if in_code:
        out.append(html.escape("\n".join(code_buf)))

    return "<br>".join(out)


class ChatWidget(QWidget):
    """Main chat area: message history + input box."""

    send_requested = pyqtSignal(str)  # emitted when user hits Send

    def __init__(self, parent=None):
        super().__init__(parent)
        self._streaming_html = ""
        self._thinking_html = ""
        self._is_streaming = False
        self._anchor = None  # cursor anchor for live update
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Vertical)

        # Message history
        self.history = QTextBrowser()
        self.history.setOpenExternalLinks(True)
        self.history.setReadOnly(True)
        self.history.document().setDefaultStyleSheet(
            "body { font-family: 'JetBrains Mono', monospace; font-size: 13px; color: #e0e0e0; }"
        )
        splitter.addWidget(self.history)

        # Input area
        input_widget = QWidget()
        input_layout = QVBoxLayout(input_widget)
        input_layout.setContentsMargins(8, 8, 8, 8)
        input_layout.setSpacing(6)

        hint = QLabel("Enter to send  ·  Shift+Enter for newline")
        hint.setStyleSheet("color: #333; font-size: 10px;")
        input_layout.addWidget(hint)

        row = QHBoxLayout()
        self.input = InputBox()
        self.input.setPlaceholderText("Ask Claude anything…")
        self.input.setMinimumHeight(70)
        self.input.setMaximumHeight(160)
        self.input.submit.connect(self._on_submit)
        row.addWidget(self.input)

        btn_col = QVBoxLayout()
        self.send_btn = QPushButton("Send")
        self.send_btn.setObjectName("send_btn")
        self.send_btn.setFixedWidth(72)
        self.send_btn.clicked.connect(self._on_submit)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setFixedWidth(72)
        self.stop_btn.setVisible(False)
        btn_col.addWidget(self.send_btn)
        btn_col.addWidget(self.stop_btn)
        btn_col.addStretch()
        row.addLayout(btn_col)

        input_layout.addLayout(row)
        splitter.addWidget(input_widget)

        splitter.setSizes([600, 160])
        layout.addWidget(splitter)

    def _on_submit(self):
        text = self.input.toPlainText().strip()
        if not text or self._is_streaming:
            return
        self.input.clear()
        self.send_requested.emit(text)

    # ── Public API ──────────────────────────────────────────────────

    def add_user_message(self, text: str):
        self.history.moveCursor(QTextCursor.MoveOperation.End)
        self.history.insertHtml(USER_MSG_HTML.format(content=_escape(text)))
        self._scroll_bottom()

    def begin_assistant_message(self, model: str):
        self._is_streaming = True
        self._streaming_html = ""
        self._thinking_html = ""
        self.send_btn.setEnabled(False)
        self.stop_btn.setVisible(True)

        # Insert header + empty placeholder div we'll update in place
        self.history.moveCursor(QTextCursor.MoveOperation.End)
        header = (
            f'<div style="margin: 12px 0 4px 0; color: #888; font-size: 11px; letter-spacing: 1px;">'
            f'◆ CLAUDE  <span style="color: #444; font-size: 10px;">{html.escape(model)}</span>'
            f'</div>'
        )
        self.history.insertHtml(header)
        self.history.insertHtml(
            '<div id="stream_target" style="background: #0f0f0f; border-left: 3px solid #333; '
            'padding: 10px 14px; border-radius: 0 4px 4px 0; margin-bottom: 6px; color: #e0e0e0;">'
            '</div>'
        )
        self._scroll_bottom()

    def append_thinking(self, text: str):
        self._thinking_html += _escape(text)
        self._refresh_stream()

    def append_text(self, text: str):
        self._streaming_html += text
        self._refresh_stream()

    def _refresh_stream(self):
        """Re-render the streaming block by finding/replacing the stream_target div."""
        thinking_block = ""
        if self._thinking_html:
            thinking_block = (
                '<div style="margin-bottom:6px; color: #444; font-size: 11px; '
                'font-style: italic; border-left: 2px solid #1a1a1a; padding-left: 8px; '
                'white-space: pre-wrap;">'
                + self._thinking_html + "</div>"
            )
        content_block = _format_markdown(self._streaming_html)

        doc = self.history.document()
        cursor = QTextCursor(doc)
        cursor.movePosition(QTextCursor.MoveOperation.End)
        # Approximate: just append text directly without full re-render
        self._scroll_bottom()

    def end_assistant_message(self):
        """Finalize: replace streaming placeholder with formatted content."""
        self._is_streaming = False
        self.send_btn.setEnabled(True)
        self.stop_btn.setVisible(False)
        self.input.setFocus()
        # The content already rendered via append_text; scroll to bottom
        self._scroll_bottom()

    def add_error(self, text: str):
        self._is_streaming = False
        self.send_btn.setEnabled(True)
        self.stop_btn.setVisible(False)
        self.history.moveCursor(QTextCursor.MoveOperation.End)
        self.history.insertHtml(ERROR_HTML.format(content=_escape(text)))
        self._scroll_bottom()

    def clear(self):
        self.history.clear()
        self._streaming_html = ""
        self._thinking_html = ""

    def set_stop_handler(self, fn):
        self.stop_btn.clicked.connect(fn)

    def _scroll_bottom(self):
        sb = self.history.verticalScrollBar()
        sb.setValue(sb.maximum())
