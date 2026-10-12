"""
=====================================================================
Developer: Chance Joaquin Boone
Project: Erudite — Beacon Computing Initiative
Module: PyQt5 Desktop UI & Engine Controller
Developer Seal: BCI-CUSTOM-LLM-CORE-V7-TORCH
=====================================================================
"""

import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout, QGroupBox,
    QLabel, QPlainTextEdit, QLineEdit, QPushButton, QProgressBar, QSplitter
)
from PyQt5.QtCore import Qt
from GUI.workers import TrainingThread, InferenceWorker

class BCIaiMainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.model = None
        self.tokenizer = None
        self.train_thread = None
        self.infer_worker = None
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)

        # Left Panel - Training Engine
        left_box = QGroupBox("⚡ Training Controller")
        left_layout = QVBoxLayout(left_box)

        left_layout.addWidget(QLabel("Corpus Input:"))
        self.corpus_input = QPlainTextEdit()
        self.corpus_input.setPlainText(
            "The quick brown fox jumps over the lazy dog. BCI system metrics report optimal execution status."
        )
        left_layout.addWidget(self.corpus_input)

        self.btn_train = QPushButton("Start Training")
        self.btn_train.setStyleSheet("background-color: #238636; color: white; font-weight: bold;")
        self.btn_train.clicked.connect(self._start_training)
        left_layout.addWidget(self.btn_train)

        self.progress_bar = QProgressBar()
        left_layout.addWidget(self.progress_bar)

        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(120)
        left_layout.addWidget(self.log_output)

        splitter.addWidget(left_box)

        # Right Panel - Inference Terminal
        right_box = QGroupBox("💬 Local Inference Console")
        right_layout = QVBoxLayout(right_box)

        self.chat_display = QPlainTextEdit()
        self.chat_display.setReadOnly(True)
        right_layout.addWidget(self.chat_display)

        input_row = QHBoxLayout()
        self.prompt_input = QLineEdit()
        self.prompt_input.setPlaceholderText("Enter starting prompt...")
        self.prompt_input.returnPressed.connect(self._generate_text)

        self.btn_generate = QPushButton("Generate")
        self.btn_generate.setEnabled(False)
        self.btn_generate.clicked.connect(self._generate_text)

        input_row.addWidget(self.prompt_input)
        input_row.addWidget(self.btn_generate)
        right_layout.addLayout(input_row)

        splitter.addWidget(right_box)
        layout.addWidget(splitter)

    def _start_training(self):
        corpus = self.corpus_input.toPlainText().strip()
        if not corpus:
            return

        self.btn_train.setEnabled(False)
        self.log_output.clear()
        self.log_output.appendPlainText("Initializing LLM Training Sequence...")

        self.train_thread = TrainingThread(corpus=corpus, epochs=500)
        self.train_thread.progress_signal.connect(self._on_train_progress)
        self.train_thread.finished_signal.connect(self._on_train_complete)
        self.train_thread.start()

    def _on_train_progress(self, pct: int, loss: float, msg: str):
        self.progress_bar.setValue(pct)
        self.log_output.appendPlainText(msg)

    def _on_train_complete(self, model, tokenizer):
        self.model = model
        self.tokenizer = tokenizer
        self.btn_train.setEnabled(True)
        self.btn_generate.setEnabled(True)
        self.log_output.appendPlainText("\n✅ Model compiled successfully. Inference ready.")

    def _generate_text(self):
        prompt = self.prompt_input.text().strip()
        # Streaming initiates if and only if prompt text and model instances exist
        if self.model and self.tokenizer and prompt:
            self.btn_generate.setEnabled(False)
            self.chat_display.appendPlainText(f"\nPrompt: {prompt}\nResponse: ")

            self.infer_worker = InferenceWorker(self.model, self.tokenizer, prompt)
            self.infer_worker.token_signal.connect(lambda t: self.chat_display.insertPlainText(t))
            self.infer_worker.finished_signal.connect(lambda: self.btn_generate.setEnabled(True))
            self.infer_worker.start()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BCIaiMainWindow()
    window.setWindowTitle("Erudite")
    window.resize(1000, 600)
    window.show()
    sys.exit(app.exec_())

