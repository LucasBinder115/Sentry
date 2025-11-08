"""Logs view to display latest application logs with auto-refresh."""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPlainTextEdit, QHBoxLayout, QPushButton
from PyQt5.QtCore import QTimer
from ... import config
from pathlib import Path


class LogsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._log_path = Path(config.LOG_FILE)
        self._setup_ui()
        self._setup_timer()
        self.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        header.addWidget(QLabel("🪵 Logs do Sistema (recentes)"))
        self.refresh_btn = QPushButton("Atualizar")
        self.refresh_btn.clicked.connect(self.refresh)
        header.addWidget(self.refresh_btn)
        header.addStretch()
        layout.addLayout(header)

        self.viewer = QPlainTextEdit()
        self.viewer.setReadOnly(True)
        self.viewer.setMaximumBlockCount(2000)  # limit memory
        layout.addWidget(self.viewer)

    def _setup_timer(self):
        self.timer = QTimer(self)
        self.timer.setInterval(4000)  # 4s
        self.timer.timeout.connect(self.refresh)
        self.timer.start()

    def refresh(self):
        try:
            if self._log_path.exists():
                # Tail last ~2000 lines efficiently
                text = self._tail_file(self._log_path, 2000)
                self.viewer.setPlainText(text)
                self.viewer.verticalScrollBar().setValue(self.viewer.verticalScrollBar().maximum())
            else:
                self.viewer.setPlainText("Arquivo de log não encontrado: " + str(self._log_path))
        except Exception as e:
            self.viewer.setPlainText(f"Falha ao carregar logs: {e}")

    def _tail_file(self, path: Path, max_lines: int) -> str:
        try:
            with path.open('r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()[-max_lines:]
                return ''.join(lines)
        except Exception:
            return ""
