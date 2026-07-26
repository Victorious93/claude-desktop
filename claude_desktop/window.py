# Claude Desktop — main window
# Victorious Framework | Origin Source Labs

import json
from datetime import datetime
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QComboBox, QStatusBar, QFileDialog, QListWidget,
    QListWidgetItem, QMessageBox, QPushButton, QInputDialog,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QKeySequence, QShortcut

from . import config
from .chat import ChatWidget
from .worker import StreamWorker, _build_content
from .settings import SettingsDialog


class Conversation:
    """Holds one conversation's messages and display name."""

    _counter = 0

    def __init__(self, name: str = ""):
        Conversation._counter += 1
        self.id = Conversation._counter
        self.name = name or f"Conversation {self.id}"
        self.messages: list[dict] = []


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.cfg = config.load()
        self._convs: list[Conversation] = [Conversation()]
        self._active: Conversation = self._convs[0]
        self._worker: StreamWorker | None = None
        self._current_model = self.cfg.get("model", "claude-opus-4-8")
        self._pending_text = ""

        self._build_ui()
        self._build_menu()
        self._build_shortcuts()
        self.resize(self.cfg.get("window_width", 1200), self.cfg.get("window_height", 780))
        self._refresh_conv_list()
        self._update_status()

    # ── UI ───────────────────────────────────────────────────────────

    def _build_ui(self):
        self.setWindowTitle("Claude Desktop — Victorious Framework")

        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Left sidebar ─────────────────────────────────────────────
        sidebar = QWidget()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet("background:#080808;border-right:1px solid #1a1a1a;")
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(0, 0, 0, 0)
        sb_layout.setSpacing(0)

        sb_header = QLabel(" CHATS")
        sb_header.setStyleSheet(
            "color:#00ff41;font-size:10px;letter-spacing:2px;"
            "padding:10px 8px 6px;border-bottom:1px solid #1a1a1a;"
        )
        sb_layout.addWidget(sb_header)

        self.conv_list = QListWidget()
        self.conv_list.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
                color: #888;
                font-size: 12px;
            }
            QListWidget::item { padding: 8px 10px; border-bottom: 1px solid #111; }
            QListWidget::item:selected { background: #00ff4115; color: #e0e0e0; }
            QListWidget::item:hover { background: #111; }
        """)
        self.conv_list.itemClicked.connect(self._on_conv_selected)
        sb_layout.addWidget(self.conv_list)

        new_conv_btn = QPushButton("+ New Chat")
        new_conv_btn.setStyleSheet(
            "background:#0d0d0d;color:#00ff41;border:none;"
            "border-top:1px solid #1a1a1a;padding:10px;"
            "font-size:12px;text-align:left;"
        )
        new_conv_btn.clicked.connect(self._new_chat)
        sb_layout.addWidget(new_conv_btn)

        root_layout.addWidget(sidebar)

        # ── Main column ───────────────────────────────────────────────
        main_col = QWidget()
        main_layout = QVBoxLayout(main_col)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self._build_toolbar())

        self.chat = ChatWidget()
        self.chat.send_requested.connect(self._send)
        self.chat.set_stop_handler(self._stop)
        main_layout.addWidget(self.chat)

        root_layout.addWidget(main_col)

        self.status = QStatusBar()
        self.setStatusBar(self.status)

    def _build_toolbar(self) -> QWidget:
        bar = QWidget()
        bar.setStyleSheet("background:#0a0a0a;border-bottom:1px solid #1a1a1a;")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(8)

        logo = QLabel("◆ CLAUDE DESKTOP")
        logo.setObjectName("title_label")
        layout.addWidget(logo)

        layout.addSpacing(16)
        layout.addWidget(QLabel("Model:"))

        self.model_combo = QComboBox()
        for label, mid in config.MODELS:
            self.model_combo.addItem(label, mid)
        current = self.cfg.get("model", "claude-opus-4-8")
        for i, (_, mid) in enumerate(config.MODELS):
            if mid == current:
                self.model_combo.setCurrentIndex(i)
                break
        self.model_combo.currentIndexChanged.connect(self._on_model_change)
        layout.addWidget(self.model_combo)

        layout.addStretch()

        rename_btn = QPushButton("Rename")
        rename_btn.clicked.connect(self._rename_conv)
        layout.addWidget(rename_btn)

        settings_btn = QPushButton("Settings")
        settings_btn.clicked.connect(self._open_settings)
        layout.addWidget(settings_btn)

        return bar

    def _build_menu(self):
        mb = self.menuBar()

        file_menu = mb.addMenu("File")
        file_menu.addAction("New Chat", self._new_chat, "Ctrl+N")
        file_menu.addAction("Rename Chat…", self._rename_conv)
        file_menu.addAction("Delete Chat", self._delete_conv)
        file_menu.addSeparator()
        file_menu.addAction("Export Conversation…", self._export)
        file_menu.addSeparator()
        file_menu.addAction("Quit", self.close, "Ctrl+Q")

        edit_menu = mb.addMenu("Edit")
        edit_menu.addAction("Settings…", self._open_settings, "Ctrl+,")
        edit_menu.addSeparator()
        edit_menu.addAction("Clear Chat", self._clear_chat, "Ctrl+L")

        help_menu = mb.addMenu("Help")
        help_menu.addAction("Keyboard Shortcuts", self._show_shortcuts)
        help_menu.addAction("About", self._about)

    def _build_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+L"), self).activated.connect(self._clear_chat)
        QShortcut(QKeySequence("Ctrl+N"), self).activated.connect(self._new_chat)

    # ── Conversation management ──────────────────────────────────────

    def _refresh_conv_list(self):
        self.conv_list.clear()
        for conv in self._convs:
            turns = len([m for m in conv.messages if m["role"] == "user"])
            label = conv.name
            if turns:
                label += f"  ({turns})"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, conv.id)
            self.conv_list.addItem(item)
            if conv is self._active:
                self.conv_list.setCurrentItem(item)

    def _on_conv_selected(self, item: QListWidgetItem):
        cid = item.data(Qt.ItemDataRole.UserRole)
        conv = next((c for c in self._convs if c.id == cid), None)
        if conv and conv is not self._active:
            self._active = conv
            self._reload_chat()
            self._update_status()

    def _reload_chat(self):
        """Rebuild history display for the active conversation."""
        self.chat.clear()
        for msg in self._active.messages:
            if msg["role"] == "user":
                content = msg["content"]
                if isinstance(content, list):
                    text = next((p["text"] for p in content if p["type"] == "text"), "")
                    imgs = [
                        (p["source"]["data"], p["source"]["media_type"])
                        for p in content if p["type"] == "image"
                    ]
                    self.chat.add_user_message(text, imgs)
                else:
                    self.chat.add_user_message(content)
            elif msg["role"] == "assistant":
                content = msg["content"]
                self.chat.history.moveCursor(self.chat.history.textCursor().MoveOperation.End)
                self.chat.history.insertHtml(
                    f'<div style="margin:12px 0 2px 0;color:#888;font-size:10px;">'
                    f'◆ CLAUDE</div>'
                    f'<div style="background:#0f0f0f;border-left:3px solid #222;'
                    f'padding:10px 14px;border-radius:0 4px 4px 0;margin-bottom:8px;'
                    f'color:#e0e0e0;">{content}</div>'
                )

    def _new_chat(self):
        conv = Conversation()
        self._convs.append(conv)
        self._active = conv
        self.chat.clear()
        self._refresh_conv_list()
        self._update_status()

    def _rename_conv(self):
        name, ok = QInputDialog.getText(
            self, "Rename Chat", "Name:", text=self._active.name
        )
        if ok and name.strip():
            self._active.name = name.strip()
            self._refresh_conv_list()

    def _delete_conv(self):
        if len(self._convs) == 1:
            self._active.messages.clear()
            self.chat.clear()
            self._refresh_conv_list()
            return
        self._convs.remove(self._active)
        self._active = self._convs[-1]
        self._reload_chat()
        self._refresh_conv_list()
        self._update_status()

    def _clear_chat(self):
        self._active.messages.clear()
        self.chat.clear()
        self._refresh_conv_list()
        self._update_status()

    # ── Sending messages ─────────────────────────────────────────────

    def _on_model_change(self):
        self._current_model = self.model_combo.currentData()
        self._update_status()

    def _send(self, text: str, images: list[tuple[str, str]]):
        if not self.cfg.get("api_key"):
            self.chat.add_error(
                "No API key set. Open Settings (Ctrl+,) to add your Anthropic API key."
            )
            return

        content = _build_content(text, images)
        self._active.messages.append({"role": "user", "content": content})
        self.chat.add_user_message(text, images)
        self.chat.begin_assistant_message(self._current_model)
        self._pending_text = ""

        model = self._current_model
        use_thinking = self.cfg.get("thinking", True) and model != "claude-haiku-4-5"
        effort = self.cfg.get("effort", "high")
        max_tokens = self.cfg.get("max_tokens", 16000)

        params: dict = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": list(self._active.messages),
            "system": [
                {
                    "type": "text",
                    "text": self.cfg.get("system_prompt", "You are a helpful assistant."),
                    "cache_control": {"type": "ephemeral"},
                }
            ],
        }
        if use_thinking:
            params["thinking"] = {"type": "adaptive"}
        if model != "claude-haiku-4-5" and effort:
            params["output_config"] = {"effort": effort}

        self._worker = StreamWorker(self.cfg["api_key"], params)
        self._worker.chunk.connect(self._on_chunk)
        self._worker.thinking_chunk.connect(self._on_thinking)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _stop(self):
        if self._worker:
            self._worker.stop()

    def _on_chunk(self, text: str):
        self._pending_text += text
        self.chat.append_text(text)

    def _on_thinking(self, text: str):
        self.chat.append_thinking(text)

    def _on_finished(self, usage: dict):
        self.chat.end_assistant_message()
        self._active.messages.append({"role": "assistant", "content": self._pending_text})
        self._refresh_conv_list()

        inp, out = usage.get("input", 0), usage.get("output", 0)
        cr, cw = usage.get("cache_read", 0), usage.get("cache_write", 0)
        parts = [f"Tokens: {inp} in / {out} out"]
        if cr:
            parts.append(f"cache hit: {cr}")
        if cw:
            parts.append(f"cache write: {cw}")
        self.status.showMessage("  ·  ".join(parts), 8000)
        self._update_status()

    def _on_error(self, msg: str):
        self.chat.end_assistant_message()
        self.chat.add_error(msg)
        self._update_status()

    # ── Other actions ────────────────────────────────────────────────

    def _open_settings(self):
        dlg = SettingsDialog(self.cfg, self)
        if dlg.exec():
            self.cfg = dlg.get_config()
            config.save(self.cfg)
            new_model = self.cfg.get("model", "claude-opus-4-8")
            for i, (_, mid) in enumerate(config.MODELS):
                if mid == new_model:
                    self.model_combo.setCurrentIndex(i)
                    break
            self._current_model = new_model
            self._update_status()

    def _export(self):
        if not self._active.messages:
            QMessageBox.information(self, "Export", "No messages to export.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Conversation",
            f"{self._active.name}-{datetime.now():%Y%m%d-%H%M%S}.json",
            "JSON Files (*.json);;Text Files (*.txt)",
        )
        if not path:
            return
        if path.endswith(".txt"):
            lines = []
            for m in self._active.messages:
                role = "You" if m["role"] == "user" else "Claude"
                content = m["content"]
                if isinstance(content, list):
                    content = next((p["text"] for p in content if p["type"] == "text"), "")
                lines.append(f"[{role}]\n{content}\n")
            open(path, "w").write("\n".join(lines))
        else:
            exportable = []
            for m in self._active.messages:
                content = m["content"]
                if isinstance(content, list):
                    content = [
                        p for p in content if p["type"] == "text"
                    ]
                exportable.append({"role": m["role"], "content": content})
            open(path, "w").write(json.dumps(exportable, indent=2))
        self.status.showMessage(f"Exported to {path}", 4000)

    def _show_shortcuts(self):
        QMessageBox.information(
            self, "Keyboard Shortcuts",
            "<b>Ctrl+N</b> — New chat<br>"
            "<b>Ctrl+L</b> — Clear current chat<br>"
            "<b>Ctrl+,</b> — Settings<br>"
            "<b>Ctrl+Q</b> — Quit<br><br>"
            "<b>Enter</b> — Send message<br>"
            "<b>Shift+Enter</b> — New line<br><br>"
            "<b>Drag & drop</b> image into input box to attach",
        )

    def _about(self):
        QMessageBox.about(
            self, "Claude Desktop",
            "<b>Claude Desktop</b><br>"
            "Victorious Framework | Origin Source Labs<br><br>"
            "Native PyQt6 desktop client for Anthropic's Claude API.<br>"
            "Streaming · Vision · Multi-conversation · Prompt caching",
        )

    def _update_status(self):
        turns = len([m for m in self._active.messages if m["role"] == "user"])
        key_ok = "✓ key" if self.cfg.get("api_key") else "✗ no key"
        thinking = (
            "thinking on"
            if self.cfg.get("thinking") and self._current_model != "claude-haiku-4-5"
            else "thinking off"
        )
        self.status.showMessage(
            f"  {key_ok}  ·  {self._current_model}  ·  {thinking}"
            f"  ·  {self._active.name}  ·  {turns} turn{'s' if turns != 1 else ''}"
        )

    def closeEvent(self, e):
        self.cfg["window_width"] = self.width()
        self.cfg["window_height"] = self.height()
        config.save(self.cfg)
        super().closeEvent(e)
