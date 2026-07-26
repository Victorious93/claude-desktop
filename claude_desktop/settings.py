# Claude Desktop — settings dialog
# Victorious Framework | Origin Source Labs

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QCheckBox, QTextEdit, QTabWidget,
    QWidget, QFormLayout, QSlider, QSpinBox,
)
from PyQt6.QtCore import Qt
from . import config


class SettingsDialog(QDialog):
    def __init__(self, cfg: dict, parent=None):
        super().__init__(parent)
        self.cfg = dict(cfg)
        self.setWindowTitle("Settings — Claude Desktop")
        self.setMinimumWidth(520)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        title = QLabel("SETTINGS")
        title.setObjectName("title_label")
        layout.addWidget(title)

        tabs = QTabWidget()
        tabs.addTab(self._api_tab(), "API")
        tabs.addTab(self._model_tab(), "Model")
        tabs.addTab(self._prompt_tab(), "System Prompt")
        layout.addWidget(tabs)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Save")
        save.clicked.connect(self.accept)
        btn_row.addWidget(cancel)
        btn_row.addWidget(save)
        layout.addLayout(btn_row)

    def _api_tab(self):
        w = QWidget()
        form = QFormLayout(w)
        form.setSpacing(12)
        form.setContentsMargins(16, 16, 16, 16)

        self.api_key_edit = QLineEdit(self.cfg.get("api_key", ""))
        self.api_key_edit.setPlaceholderText("sk-ant-...")
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)

        show_cb = QCheckBox("Show")
        show_cb.toggled.connect(
            lambda v: self.api_key_edit.setEchoMode(
                QLineEdit.EchoMode.Normal if v else QLineEdit.EchoMode.Password
            )
        )

        key_row = QHBoxLayout()
        key_row.addWidget(self.api_key_edit)
        key_row.addWidget(show_cb)

        form.addRow("API Key:", key_row)

        note = QLabel(
            'Get your key at <a href="https://console.anthropic.com" '
            'style="color: #00ff41;">console.anthropic.com</a>'
        )
        note.setOpenExternalLinks(True)
        note.setStyleSheet("color: #666; font-size: 11px;")
        form.addRow("", note)

        return w

    def _model_tab(self):
        w = QWidget()
        form = QFormLayout(w)
        form.setSpacing(12)
        form.setContentsMargins(16, 16, 16, 16)

        self.model_combo = QComboBox()
        for label, mid in config.MODELS:
            self.model_combo.addItem(label, mid)
        current = self.cfg.get("model", "claude-opus-4-8")
        for i, (_, mid) in enumerate(config.MODELS):
            if mid == current:
                self.model_combo.setCurrentIndex(i)
                break
        form.addRow("Model:", self.model_combo)

        self.thinking_cb = QCheckBox("Enable adaptive thinking")
        self.thinking_cb.setChecked(self.cfg.get("thinking", True))
        form.addRow("Thinking:", self.thinking_cb)

        self.effort_combo = QComboBox()
        for e in config.EFFORT_LEVELS:
            self.effort_combo.addItem(e)
        effort = self.cfg.get("effort", "high")
        idx = config.EFFORT_LEVELS.index(effort) if effort in config.EFFORT_LEVELS else 2
        self.effort_combo.setCurrentIndex(idx)
        form.addRow("Effort:", self.effort_combo)

        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(256, 128000)
        self.max_tokens_spin.setSingleStep(1000)
        self.max_tokens_spin.setValue(self.cfg.get("max_tokens", 16000))
        form.addRow("Max Tokens:", self.max_tokens_spin)

        note = QLabel("xhigh/max effort: use with max_tokens ≥ 64000 + streaming")
        note.setStyleSheet("color: #555; font-size: 10px;")
        form.addRow("", note)

        return w

    def _prompt_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.addWidget(QLabel("System Prompt:"))
        self.system_edit = QTextEdit()
        self.system_edit.setPlainText(self.cfg.get("system_prompt", "You are a helpful assistant."))
        layout.addWidget(self.system_edit)
        note = QLabel("Cached across requests for cost efficiency.")
        note.setStyleSheet("color: #555; font-size: 10px;")
        layout.addWidget(note)
        return w

    def get_config(self) -> dict:
        self.cfg["api_key"] = self.api_key_edit.text().strip()
        self.cfg["model"] = self.model_combo.currentData()
        self.cfg["thinking"] = self.thinking_cb.isChecked()
        self.cfg["effort"] = self.effort_combo.currentText()
        self.cfg["max_tokens"] = self.max_tokens_spin.value()
        self.cfg["system_prompt"] = self.system_edit.toPlainText()
        return self.cfg
