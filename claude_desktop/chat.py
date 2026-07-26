# Claude Desktop — chat widget
# Victorious Framework | Origin Source Labs

import base64
import html
import re
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QLabel, QSplitter, QApplication,
    QFileDialog, QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData, QUrl
from PyQt6.QtGui import (
    QKeyEvent, QTextCursor, QTextCharFormat, QTextBlockFormat,
    QColor, QFont, QDragEnterEvent, QDropEvent, QPixmap,
)


# ── Markdown renderer ────────────────────────────────────────────────────────

def _escape(text: str) -> str:
    return html.escape(text)


def _format_markdown(text: str) -> str:
    """Plain text → HTML with code fences, inline code, bold, italic."""
    lines = text.split("\n")
    out = []
    in_code = False
    code_buf: list[str] = []
    lang = ""

    for line in lines:
        if line.startswith("```"):
            if not in_code:
                in_code = True
                lang = html.escape(line[3:].strip())
                code_buf = []
            else:
                in_code = False
                code_html = html.escape("\n".join(code_buf))
                label = (
                    f'<span style="color:#555;font-size:10px;">{lang}</span><br>'
                    if lang else ""
                )
                out.append(
                    f'<div style="background:#0a0a0a;border:1px solid #1e1e1e;'
                    f'border-radius:4px;padding:10px 12px;margin:6px 0;'
                    f'font-family:JetBrains Mono,monospace;font-size:12px;'
                    f'white-space:pre;overflow-x:auto;color:#c8e6c9;">'
                    f'{label}{code_html}</div>'
                )
            continue

        if in_code:
            code_buf.append(line)
            continue

        line = html.escape(line)
        line = re.sub(
            r'`([^`]+)`',
            r'<code style="background:#1a1a1a;padding:1px 4px;'
            r'border-radius:3px;color:#80cbc4;">\1</code>',
            line,
        )
        line = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', line)
        line = re.sub(r'\*([^*]+)\*', r'<i>\1</i>', line)
        # Headers
        line = re.sub(
            r'^### (.+)$',
            r'<span style="color:#00ff41;font-size:13px;font-weight:bold;">\1</span>',
            line,
        )
        line = re.sub(
            r'^## (.+)$',
            r'<span style="color:#00ff41;font-size:14px;font-weight:bold;">\1</span>',
            line,
        )
        line = re.sub(
            r'^# (.+)$',
            r'<span style="color:#00ff41;font-size:15px;font-weight:bold;">\1</span>',
            line,
        )
        out.append(line)

    if in_code and code_buf:
        out.append(html.escape("\n".join(code_buf)))

    return "<br>".join(out)


# ── Drag-and-drop image input ────────────────────────────────────────────────

class InputBox(QTextEdit):
    """Multi-line input: Enter = send, Shift+Enter = newline, accepts image drops."""

    submit = pyqtSignal()
    image_attached = pyqtSignal(str, str)  # (base64_data, mime_type)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._attached_images: list[tuple[str, str]] = []

    def keyPressEvent(self, e: QKeyEvent):
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if e.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                super().keyPressEvent(e)
            else:
                self.submit.emit()
        else:
            super().keyPressEvent(e)

    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls() or e.mimeData().hasImage():
            e.acceptProposedAction()
        else:
            super().dragEnterEvent(e)

    def dropEvent(self, e: QDropEvent):
        for url in e.mimeData().urls():
            path = url.toLocalFile()
            if path and Path(path).suffix.lower() in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
                self._load_image(path)
                return
        super().dropEvent(e)

    def _load_image(self, path: str):
        ext = Path(path).suffix.lower().lstrip(".")
        mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg"}.get(ext, f"image/{ext}")
        data = base64.standard_b64encode(open(path, "rb").read()).decode()
        self._attached_images.append((data, mime))
        self.image_attached.emit(data, mime)

    def attach_image_from_picker(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Attach Image", "",
            "Images (*.png *.jpg *.jpeg *.gif *.webp)"
        )
        if path:
            self._load_image(path)

    def pop_images(self) -> list[tuple[str, str]]:
        imgs = list(self._attached_images)
        self._attached_images.clear()
        return imgs


# ── Chat widget ──────────────────────────────────────────────────────────────

class ChatWidget(QWidget):
    """Message history + input area."""

    send_requested = pyqtSignal(str, list)  # (text, [(b64, mime), ...])

    def __init__(self, parent=None):
        super().__init__(parent)
        self._streaming_text = ""
        self._thinking_text = ""
        self._is_streaming = False
        self._stream_cursor: QTextCursor | None = None
        self._stream_start = 0
        self._has_thinking = False
        self._current_model = ""
        self._attached_previews: list[QLabel] = []
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Vertical)

        # ── History ──────────────────────────────────────────────────
        self.history = QTextEdit()
        self.history.setReadOnly(True)
        self.history.setAcceptDrops(False)
        self.history.document().setDefaultStyleSheet(
            "body{font-family:'JetBrains Mono',monospace;font-size:13px;color:#e0e0e0;}"
        )
        splitter.addWidget(self.history)

        # ── Input area ────────────────────────────────────────────────
        input_widget = QWidget()
        il = QVBoxLayout(input_widget)
        il.setContentsMargins(8, 6, 8, 8)
        il.setSpacing(4)

        # Attachment preview strip
        self.attachment_strip = QHBoxLayout()
        self.attachment_strip.setContentsMargins(0, 0, 0, 0)
        il.addLayout(self.attachment_strip)

        # Input row
        row = QHBoxLayout()
        row.setSpacing(6)

        self.input = InputBox()
        self.input.setPlaceholderText("Ask Claude anything… (drag an image to attach)")
        self.input.setMinimumHeight(68)
        self.input.setMaximumHeight(160)
        self.input.submit.connect(self._on_submit)
        self.input.image_attached.connect(self._on_image_attached)
        row.addWidget(self.input)

        btn_col = QVBoxLayout()
        btn_col.setSpacing(4)

        self.send_btn = QPushButton("Send")
        self.send_btn.setObjectName("send_btn")
        self.send_btn.setFixedWidth(70)
        self.send_btn.clicked.connect(self._on_submit)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setFixedWidth(70)
        self.stop_btn.setVisible(False)

        self.attach_btn = QPushButton("📎")
        self.attach_btn.setFixedWidth(70)
        self.attach_btn.setToolTip("Attach image")
        self.attach_btn.clicked.connect(self.input.attach_image_from_picker)

        btn_col.addWidget(self.send_btn)
        btn_col.addWidget(self.stop_btn)
        btn_col.addWidget(self.attach_btn)
        btn_col.addStretch()
        row.addLayout(btn_col)

        il.addLayout(row)

        # Char count hint
        hint_row = QHBoxLayout()
        self.char_label = QLabel("0 chars")
        self.char_label.setStyleSheet("color:#333;font-size:10px;")
        hint_row.addWidget(self.char_label)
        hint_row.addStretch()
        hint = QLabel("Enter to send  ·  Shift+Enter newline  ·  drag image to attach")
        hint.setStyleSheet("color:#2a2a2a;font-size:10px;")
        hint_row.addWidget(hint)
        il.addLayout(hint_row)

        self.input.textChanged.connect(
            lambda: self.char_label.setText(f"{len(self.input.toPlainText())} chars")
        )

        splitter.addWidget(input_widget)
        splitter.setSizes([560, 160])
        layout.addWidget(splitter)

    # ── Event handlers ────────────────────────────────────────────────

    def _on_submit(self):
        text = self.input.toPlainText().strip()
        if not text or self._is_streaming:
            return
        images = self.input.pop_images()
        self._clear_attachment_strip()
        self.input.clear()
        self.char_label.setText("0 chars")
        self.send_requested.emit(text, images)

    def _on_image_attached(self, b64: str, mime: str):
        """Show a small thumbnail in the attachment strip."""
        lbl = QLabel()
        px = QPixmap()
        px.loadFromData(base64.b64decode(b64))
        lbl.setPixmap(px.scaledToHeight(48, Qt.TransformationMode.SmoothTransformation))
        lbl.setToolTip(mime)
        self.attachment_strip.addWidget(lbl)
        self._attached_previews.append(lbl)

    def _clear_attachment_strip(self):
        for lbl in self._attached_previews:
            self.attachment_strip.removeWidget(lbl)
            lbl.deleteLater()
        self._attached_previews.clear()

    # ── Public API ────────────────────────────────────────────────────

    def set_stop_handler(self, fn):
        self.stop_btn.clicked.connect(fn)

    def add_user_message(self, text: str, images: list[tuple[str, str]] | None = None):
        self._insert_html(
            f'<div style="margin:12px 0 2px 0;color:#00ff41;font-size:10px;'
            f'letter-spacing:1px;">▶ YOU</div>'
            f'<div style="background:#111;border-left:3px solid #00ff41;'
            f'padding:10px 14px;border-radius:0 4px 4px 0;margin-bottom:4px;'
            f'color:#e0e0e0;white-space:pre-wrap;">{_escape(text)}</div>'
        )
        if images:
            for b64, mime in images:
                px = QPixmap()
                px.loadFromData(base64.b64decode(b64))
                self._insert_html(
                    f'<div style="margin:2px 0 6px 16px;">'
                    f'<img src="data:{mime};base64,{b64}" '
                    f'style="max-height:200px;border-radius:4px;" /></div>'
                )
        self._scroll_bottom()

    def begin_assistant_message(self, model: str):
        self._is_streaming = True
        self._streaming_text = ""
        self._thinking_text = ""
        self._has_thinking = False
        self._current_model = model
        self.send_btn.setEnabled(False)
        self.stop_btn.setVisible(True)

        # Insert header
        self._insert_html(
            f'<div style="margin:12px 0 2px 0;color:#888;font-size:10px;'
            f'letter-spacing:1px;">◆ CLAUDE '
            f'<span style="color:#333;font-size:9px;">{html.escape(model)}</span>'
            f'</div>'
        )
        # Insert thinking placeholder (hidden until needed)
        self._insert_html(
            '<div id="thinking_block" style="display:none"></div>'
        )

        # Record where streaming content will start
        c = QTextCursor(self.history.document())
        c.movePosition(QTextCursor.MoveOperation.End)
        self._stream_start = c.position()
        self._stream_cursor = c
        self._scroll_bottom()

    def append_thinking(self, text: str):
        self._thinking_text += text
        # Thinking shown as prefix in grey italic before main content
        self._redraw_stream()

    def append_text(self, text: str):
        self._streaming_text += text
        # Append directly at stream cursor — this is what actually makes
        # streaming visible as it arrives
        if self._stream_cursor:
            self._stream_cursor.insertText(text)
        self._scroll_bottom()

    def end_assistant_message(self):
        """Replace streamed plain text with formatted Markdown HTML."""
        self._is_streaming = False
        self.send_btn.setEnabled(True)
        self.stop_btn.setVisible(False)

        if self._stream_cursor and self._streaming_text:
            # Select everything from stream_start to current end
            end_pos = self._stream_cursor.position()
            sel = QTextCursor(self.history.document())
            sel.setPosition(self._stream_start)
            sel.setPosition(end_pos, QTextCursor.MoveMode.KeepAnchor)
            formatted = _format_markdown(self._streaming_text)
            # Wrap in styled div
            full_html = (
                '<div style="background:#0f0f0f;border-left:3px solid #222;'
                'padding:10px 14px;border-radius:0 4px 4px 0;margin-bottom:8px;'
                'color:#e0e0e0;">'
            )
            if self._thinking_text:
                full_html += (
                    '<div style="color:#444;font-size:11px;font-style:italic;'
                    'border-left:2px solid #1a1a1a;padding-left:8px;'
                    'margin-bottom:8px;white-space:pre-wrap;">'
                    + html.escape(self._thinking_text[:400])
                    + ("…" if len(self._thinking_text) > 400 else "")
                    + "</div>"
                )
            full_html += formatted + "</div>"
            sel.removeSelectedText()
            sel.insertHtml(full_html)

        # Add copy button row
        self._insert_html(
            '<div style="text-align:right;margin-bottom:4px;">'
            '<a href="copy:last" style="color:#333;font-size:10px;'
            'text-decoration:none;">⧉ copy</a></div>'
        )
        self.history.anchorClicked.connect(self._on_anchor_clicked)

        self._stream_cursor = None
        self._scroll_bottom()
        self.input.setFocus()

    def add_error(self, text: str):
        self._is_streaming = False
        self.send_btn.setEnabled(True)
        self.stop_btn.setVisible(False)
        self._insert_html(
            f'<div style="background:#1a0808;border-left:3px solid #ff3333;'
            f'padding:10px 14px;border-radius:0 4px 4px 0;margin:8px 0;'
            f'color:#ff6666;">✗ {_escape(text)}</div>'
        )
        self._scroll_bottom()

    def clear(self):
        self.history.clear()
        self._streaming_text = ""
        self._thinking_text = ""
        self._stream_cursor = None

    # ── Internals ─────────────────────────────────────────────────────

    def _insert_html(self, html_str: str):
        c = QTextCursor(self.history.document())
        c.movePosition(QTextCursor.MoveOperation.End)
        c.insertHtml(html_str)

    def _redraw_stream(self):
        """Called only for thinking chunks — just scroll."""
        self._scroll_bottom()

    def _scroll_bottom(self):
        sb = self.history.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_anchor_clicked(self, url: QUrl):
        if url.toString().startswith("copy:"):
            QApplication.clipboard().setText(self._streaming_text or "")
