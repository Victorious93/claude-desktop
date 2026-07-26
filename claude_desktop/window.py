# Claude Desktop — main window
# Victorious Framework | Origin Source Labs

import json
from datetime import datetime
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QStatusBar, QFileDialog,
    QMessageBox, QToolBar, QPushButton,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction, QIcon, QFont

from . import config
from .chat import ChatWidget
from .worker import StreamWorker
from .settings import SettingsDialog


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.cfg = config.load()
        self._messages: list[dict] = []  # conversation history
        self._worker: StreamWorker | None = None
        self._current_model = self.cfg.get("model", "claude-opus-4-8")
        self._pending_text = ""  # accumulates streamed text for history

        self._build_ui()
        self._build_menu()
        self.resize(self.cfg.get("window_width", 1100), self.cfg.get("window_height", 760))
        self._update_status()

    # ── UI construction ─────────────────────────────────────────────

    def _build_ui(self):
        self.setWindowTitle("Claude Desktop — Victorious Framework")

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar
        toolbar = self._build_toolbar()
        layout.addWidget(toolbar)

        # Chat
        self.chat = ChatWidget()
        self.chat.send_requested.connect(self._send)
        self.chat.set_stop_handler(self._stop)
        layout.addWidget(self.chat)

        # Status bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)

    def _build_toolbar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("toolbar")
        bar.setStyleSheet("background: #0a0a0a; border-bottom: 1px solid #1a1a1a;")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(8)

        # Logo
        logo = QLabel("◆ CLAUDE")
        logo.setObjectName("title_label")
        layout.addWidget(logo)

        layout.addSpacing(16)

        # Model selector
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

        # Buttons
        new_btn = QPushButton("New Chat")
        new_btn.clicked.connect(self._new_chat)
        layout.addWidget(new_btn)

        settings_btn = QPushButton("Settings")
        settings_btn.clicked.connect(self._open_settings)
        layout.addWidget(settings_btn)

        return bar

    def _build_menu(self):
        mb = self.menuBar()

        file_menu = mb.addMenu("File")
        file_menu.addAction("New Chat", self._new_chat, "Ctrl+N")
        file_menu.addSeparator()
        file_menu.addAction("Export Conversation…", self._export)
        file_menu.addSeparator()
        file_menu.addAction("Quit", self.close, "Ctrl+Q")

        edit_menu = mb.addMenu("Edit")
        edit_menu.addAction("Settings…", self._open_settings, "Ctrl+,")

        help_menu = mb.addMenu("Help")
        help_menu.addAction("About", self._about)

    # ── Actions ─────────────────────────────────────────────────────

    def _on_model_change(self):
        self._current_model = self.model_combo.currentData()
        self._update_status()

    def _send(self, text: str):
        if not self.cfg.get("api_key"):
            self.chat.add_error("No API key set. Open Settings (Ctrl+,) to add your Anthropic API key.")
            return

        self._messages.append({"role": "user", "content": text})
        self.chat.add_user_message(text)
        self.chat.begin_assistant_message(self._current_model)
        self._pending_text = ""
        self._pending_thinking = ""

        model = self._current_model
        use_thinking = self.cfg.get("thinking", True)
        effort = self.cfg.get("effort", "high")
        max_tokens = self.cfg.get("max_tokens", 16000)

        # Haiku doesn't support thinking or effort — guard it
        if model == "claude-haiku-4-5":
            use_thinking = False

        params = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": list(self._messages),
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

        # effort only on non-haiku models
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
        self._pending_thinking += text
        self.chat.append_thinking(text)

    def _on_finished(self, usage: dict):
        self.chat.end_assistant_message()
        self._messages.append({
            "role": "assistant",
            "content": self._pending_text,
        })
        inp = usage.get("input", 0)
        out = usage.get("output", 0)
        cr = usage.get("cache_read", 0)
        cw = usage.get("cache_write", 0)
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
        # Remove the empty assistant message we added optimistically
        if self._messages and self._messages[-1]["role"] == "user":
            pass  # user msg stays
        self._update_status()

    def _new_chat(self):
        self._messages.clear()
        self.chat.clear()
        self._update_status()

    def _open_settings(self):
        dlg = SettingsDialog(self.cfg, self)
        if dlg.exec():
            self.cfg = dlg.get_config()
            config.save(self.cfg)
            # Sync model combo
            new_model = self.cfg.get("model", "claude-opus-4-8")
            for i, (_, mid) in enumerate(config.MODELS):
                if mid == new_model:
                    self.model_combo.setCurrentIndex(i)
                    break
            self._current_model = new_model
            self._update_status()

    def _export(self):
        if not self._messages:
            QMessageBox.information(self, "Export", "No conversation to export.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Conversation", f"claude-{datetime.now():%Y%m%d-%H%M%S}.json",
            "JSON Files (*.json);;Text Files (*.txt)"
        )
        if not path:
            return
        if path.endswith(".txt"):
            lines = []
            for m in self._messages:
                role = "You" if m["role"] == "user" else "Claude"
                lines.append(f"[{role}]\n{m['content']}\n")
            open(path, "w").write("\n".join(lines))
        else:
            open(path, "w").write(json.dumps(self._messages, indent=2))
        self.status.showMessage(f"Exported to {path}", 4000)

    def _about(self):
        QMessageBox.about(
            self,
            "Claude Desktop",
            "<b>Claude Desktop</b><br>"
            "Victorious Framework | Origin Source Labs<br><br>"
            "Native PyQt6 desktop client for Anthropic's Claude API.<br>"
            "Uses the official <code>anthropic</code> Python SDK with streaming.",
        )

    def _update_status(self):
        model = self._current_model
        turns = len([m for m in self._messages if m["role"] == "user"])
        key_ok = "✓ API key" if self.cfg.get("api_key") else "✗ No API key"
        thinking = "thinking on" if self.cfg.get("thinking") and model != "claude-haiku-4-5" else "thinking off"
        self.status.showMessage(
            f"  {key_ok}  ·  {model}  ·  {thinking}  ·  {turns} turn{'s' if turns != 1 else ''}"
        )

    def closeEvent(self, e):
        self.cfg["window_width"] = self.width()
        self.cfg["window_height"] = self.height()
        config.save(self.cfg)
        super().closeEvent(e)
