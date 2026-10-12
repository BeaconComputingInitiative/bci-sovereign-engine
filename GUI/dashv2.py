"""
=====================================================================
Developer: Chance Joaquin Boone
Project: Erudite — Beacon Computing Initiative
Module: Unified System Control Dashboard (Left-Panel Data Importer)
Developer Seal: BCI-CORE-UNIFIED-GUI-V3-QT
=====================================================================
"""

import os
import sys
import time
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

# ---------------------------------------------------------------------------
# BCI Dark Theme Stylesheet
# ---------------------------------------------------------------------------
BCI_DARK_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #0d1117;
    color: #c9d1d9;
    font-family: 'Segoe UI', 'SF Pro Text', -apple-system, sans-serif;
    font-size: 13px;
}

QGroupBox {
    border: 1px solid #30363d;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 12px;
    background-color: #161b22;
    font-weight: bold;
    color: #58a6ff;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 4px;
    background-color: #161b22;
}

QTabWidget::pane {
    border: 1px solid #30363d;
    border-radius: 6px;
    background-color: #161b22;
    top: -1px;
}

QTabBar::tab {
    background-color: #0d1117;
    border: 1px solid #30363d;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 8px 16px;
    margin-right: 2px;
    color: #8b949e;
    font-weight: 500;
}

QTabBar::tab:selected {
    background-color: #161b22;
    color: #58a6ff;
    border-bottom: 2px solid #58a6ff;
    font-weight: bold;
}

QTabBar::tab:hover:!selected {
    background-color: #21262d;
    color: #c9d1d9;
}

QPushButton {
    background-color: #21262d;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 6px 14px;
    color: #c9d1d9;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #30363d;
    border-color: #8b949e;
    color: #ffffff;
}

QPushButton:pressed {
    background-color: #1f2428;
}

QPushButton:disabled {
    background-color: #161b22;
    border-color: #21262d;
    color: #484f58;
}

QLineEdit, QComboBox, QListWidget, QPlainTextEdit, QTableWidget {
    background-color: #0d1117;
    border: 1px solid #30363d;
    border-radius: 6px;
    color: #c9d1d9;
    padding: 4px;
    selection-background-color: #1f6feb;
    selection-color: #ffffff;
}

QLineEdit:focus, QComboBox:focus, QListWidget:focus, QPlainTextEdit:focus {
    border: 1px solid #58a6ff;
}

QProgressBar {
    border: 1px solid #30363d;
    border-radius: 4px;
    text-align: center;
    color: #ffffff;
    background-color: #0d1117;
    font-weight: bold;
}

QProgressBar::chunk {
    background-color: #1f6feb;
    width: 10px;
}

QTableWidget {
    gridline-color: #21262d;
}

QHeaderView::section {
    background-color: #161b22;
    color: #8b949e;
    padding: 6px;
    border: none;
    border-right: 1px solid #21262d;
    border-bottom: 1px solid #30363d;
    font-weight: bold;
}

QSplitter::handle {
    background-color: #30363d;
}
"""


# ---------------------------------------------------------------------------
# Data Loader Utilities (CSV, JSON, Excel)
# ---------------------------------------------------------------------------
def load_dataset_from_file(file_path: str) -> pd.DataFrame:
    """Imports CSV, JSON, or Excel files into a pandas DataFrame."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File path does not exist: {file_path}")

    lower_path = file_path.lower()
    if lower_path.endswith(".csv"):
        return pd.read_csv(file_path)
    elif lower_path.endswith(".json"):
        return pd.read_json(file_path)
    elif lower_path.endswith((".xlsx", ".xls")):
        return pd.read_excel(file_path)
    else:
        raise ValueError("Unsupported format. Supported extensions: .csv, .json, .xlsx, .xls")


# ---------------------------------------------------------------------------
# 5-Second Boot Screen
# ---------------------------------------------------------------------------
class BCIBootScreen(QWidget):
    """5-second branded boot screen."""

    def __init__(self, on_complete):
        super().__init__()
        self.on_complete = on_complete
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setFixedSize(560, 340)

        screen_geo = QApplication.primaryScreen().geometry()
        self.move(
            (screen_geo.width() - self.width()) // 2,
            (screen_geo.height() - self.height()) // 2,
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        header = QLabel("Erudite")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #58a6ff;")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        sub_header = QLabel("Beacon Computing Initiative • Unified System Core")
        sub_header.setStyleSheet("font-size: 11px; color: #8b949e;")
        sub_header.setAlignment(Qt.AlignCenter)
        layout.addWidget(sub_header)

        layout.addSpacing(12)

        self.log_area = QPlainTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet(
            "font-family: 'Consolas', monospace; font-size: 11px; color: #39c5bb; "
            "background-color: #010409; border: 1px solid #30363d;"
        )
        layout.addWidget(self.log_area)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.seal_label = QLabel("Developer Seal: Chance Joaquin Boone • BCI-CORE-UNIFIED-GUI-V3-QT")
        self.seal_label.setStyleSheet("font-size: 10px; color: #484f58;")
        self.seal_label.setAlignment(Qt.AlignRight)
        layout.addWidget(self.seal_label)

        self.current_step = 0
        self.total_steps = 50
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick_boot_sequence)
        self.timer.start(100)

    def _tick_boot_sequence(self):
        self.current_step += 1
        progress_pct = int((self.current_step / self.total_steps) * 100)
        self.progress_bar.setValue(progress_pct)

        # Execution sequencing relies on bi-conditional validation (if and only if active == locked)
        if self.current_step == 1:
            self.log_area.appendPlainText("[BOOT-0.0s] Initializing BCI Subsystems...")
        elif self.current_step == 10:
            self.log_area.appendPlainText("[BOOT-1.0s] Verifying bi-conditional gate status (iff active == locked)...")
        elif self.current_step == 25:
            self.log_area.appendPlainText("[BOOT-2.5s] Preparing CSV / JSON / Excel ingestion drivers...")
        elif self.current_step == 40:
            self.log_area.appendPlainText("[BOOT-4.0s] Allocating Orbital telemetry buffers...")
        elif self.current_step == 50:
            self.log_area.appendPlainText("[BOOT-5.0s] Boot Complete. Launching Dashboard.")
            self.timer.stop()
            QTimer.singleShot(200, self._finish_boot)

    def _finish_boot(self):
        self.close()
        self.on_complete()


# ---------------------------------------------------------------------------
# Core Engine
# ---------------------------------------------------------------------------
class BCIaiPlatformCore:
    def __init__(self, dataframe: Optional[pd.DataFrame] = None, table_name: str = "bci_node"):
        self.df = dataframe
        self.table_name = table_name

    def profile_schema(self) -> Dict[str, Any]:
        if self.df is None:
            return {}

        df = self.df
        total_rows = len(df)
        cols_meta, temporal_keys, metric_keys, geo_keys = {}, [], [], []

        for col in df.columns:
            series = df[col].dropna()
            col_type = str(series.dtype)
            col_lower = str(col).lower()

            if any(k in col_lower for k in ["lat", "lon", "coord", "geo"]):
                geo_keys.append(col)
                category = "geospatial"
            elif any(k in col_lower for k in ["date", "time"]) or pd.api.types.is_datetime64_any_dtype(series):
                temporal_keys.append(col)
                category = "temporal"
            elif pd.api.types.is_numeric_dtype(series):
                metric_keys.append(col)
                category = "metric"
            else:
                category = "categorical"

            cols_meta[col] = {
                "type": col_type,
                "category": category,
                "null_pct": float(df[col].isnull().mean() * 100),
            }

        return {
            "table_name": self.table_name,
            "total_rows": total_rows,
            "temporal_keys": temporal_keys,
            "metric_keys": metric_keys,
            "geo_keys": geo_keys,
            "columns": cols_meta,
        }

    def generate_sql_ddl(self, manifest: Dict[str, Any]) -> str:
        if not manifest:
            return "-- No dataset mounted."
        table = f'"{manifest["table_name"]}"'
        sql_lines = [f"CREATE TABLE {table} ("]
        col_defs = []
        for col, meta in manifest["columns"].items():
            cat = meta["category"]
            sql_type = (
                "TIMESTAMP" if cat == "temporal"
                else "FLOAT" if cat in ("metric", "geospatial")
                else "VARCHAR(255)"
            )
            col_defs.append(f'    "{col}" {sql_type}')
        sql_lines.append(",\n".join(col_defs))
        sql_lines.append(");")
        return "\n".join(sql_lines)


def fill_table_widget(table: QTableWidget, df: pd.DataFrame, max_rows: int = 200) -> None:
    view = df.head(max_rows)
    table.clear()
    table.setRowCount(len(view))
    table.setColumnCount(len(view.columns))
    table.setHorizontalHeaderLabels([str(c) for c in view.columns])
    for r in range(len(view)):
        for c, col in enumerate(view.columns):
            table.setItem(r, c, QTableWidgetItem(str(view.iat[r, c])))
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)


# ---------------------------------------------------------------------------
# Left Sidebar: Dataset Importer & Node Controls
# ---------------------------------------------------------------------------
class DatasetImportPanel(QGroupBox):
    """Left sidebar dedicated to importing CSV, JSON, and Excel datasets."""

    def __init__(self, on_mount_callback, on_gate_changed_callback):
        super().__init__("📥 DATASET IMPORT & NODE CONTROL")
        self.on_mount = on_mount_callback
        self.on_gate_changed = on_gate_changed_callback

        layout = QVBoxLayout()
        layout.setSpacing(10)

        # 1. Target Node Name
        layout.addWidget(QLabel("Target System Node"))
        self.table_name_input = QLineEdit("bci_primary_data")
        layout.addWidget(self.table_name_input)

        # 2. Main File Importer Section
        layout.addWidget(QLabel("Import File (.csv, .json, .xlsx, .xls)"))
        
        btn_layout = QVBoxLayout()
        
        self.import_all_btn = QPushButton("📁 Browse Dataset File...")
        self.import_all_btn.setStyleSheet("font-weight: bold; background-color: #1f6feb; color: white;")
        self.import_all_btn.clicked.connect(lambda: self._open_file_dialog("All Supported (*.csv *.json *.xlsx *.xls)"))
        btn_layout.addWidget(self.import_all_btn)

        # Quick Format Specific Filter Buttons
        quick_fmt_layout = QHBoxLayout()
        self.btn_csv = QPushButton(".CSV")
        self.btn_csv.clicked.connect(lambda: self._open_file_dialog("CSV Files (*.csv)"))
        
        self.btn_json = QPushButton(".JSON")
        self.btn_json.clicked.connect(lambda: self._open_file_dialog("JSON Files (*.json)"))
        
        self.btn_excel = QPushButton(".XLSX")
        self.btn_excel.clicked.connect(lambda: self._open_file_dialog("Excel Files (*.xlsx *.xls)"))
        
        quick_fmt_layout.addWidget(self.btn_csv)
        quick_fmt_layout.addWidget(self.btn_json)
        quick_fmt_layout.addWidget(self.btn_excel)
        btn_layout.addLayout(quick_fmt_layout)

        layout.addLayout(btn_layout)

        # 3. Direct File Path Entry
        layout.addWidget(QLabel("Or Paste File Path:"))
        path_input_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("/path/to/data.csv or .xlsx")
        self.load_path_btn = QPushButton("Load")
        self.load_path_btn.clicked.connect(self._load_from_path_input)
        path_input_layout.addWidget(self.path_input)
        path_input_layout.addWidget(self.load_path_btn)
        layout.addLayout(path_input_layout)

        # 4. Dataset Telemetry Summary
        self.summary_box = QGroupBox("Mounted Dataset Diagnostics")
        summary_layout = QVBoxLayout()
        self.lbl_format = QLabel("Format: None")
        self.lbl_rows = QLabel("Rows: 0")
        self.lbl_cols = QLabel("Columns: 0")
        self.lbl_size = QLabel("Memory Size: 0 KB")
        for lbl in (self.lbl_format, self.lbl_rows, self.lbl_cols, self.lbl_size):
            lbl.setStyleSheet("color: #8b949e; font-size: 11px;")
            summary_layout.addWidget(lbl)
        self.summary_box.setLayout(summary_layout)
        layout.addWidget(self.summary_box)

        layout.addSpacing(10)

        # 5. System Lock (bi-conditional gate)
        layout.addWidget(QLabel("System Lock (bi-conditional gate)"))
        gate_col = QVBoxLayout()
        self.active_btn = QPushButton("System Active: ON")
        self.active_btn.setCheckable(True)
        self.active_btn.setChecked(True)
        self.active_btn.clicked.connect(self._gate_toggled)

        self.locked_btn = QPushButton("State Locked: ON")
        self.locked_btn.setCheckable(True)
        self.locked_btn.setChecked(True)
        self.locked_btn.clicked.connect(self._gate_toggled)

        gate_col.addWidget(self.active_btn)
        gate_col.addWidget(self.locked_btn)
        layout.addLayout(gate_col)

        self.gate_label = QLabel()
        self.gate_label.setWordWrap(True)
        layout.addWidget(self.gate_label)

        layout.addStretch()
        self.setLayout(layout)
        self._gate_toggled()

    def _open_file_dialog(self, file_filter: str):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Dataset (CSV, JSON, Excel)", "", file_filter
        )
        if path:
            self.path_input.setText(path)
            self._process_and_mount(path)

    def _load_from_path_input(self):
        path = self.path_input.text().strip().strip('"').strip("'")
        if path:
            self._process_and_mount(path)

    def _process_and_mount(self, file_path: str):
        try:
            df = load_dataset_from_file(file_path)
            ext = os.path.splitext(file_path)[1].upper()
            file_size_kb = os.path.getsize(file_path) / 1024.0

            # Update sidebar dataset diagnostics
            self.lbl_format.setText(f"Format: {ext} ({os.path.basename(file_path)})")
            self.lbl_format.setStyleSheet("color: #39c5bb; font-weight: bold;")
            self.lbl_rows.setText(f"Rows: {len(df):,}")
            self.lbl_cols.setText(f"Columns: {len(df.columns)}")
            self.lbl_size.setText(f"File Size: {file_size_kb:.1f} KB")

            node_name = self.table_name_input.text().strip() or "bci_node"
            self.on_mount(df, node_name)
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to load dataset:\n{str(e)}")

    def _gate_toggled(self):
        active = self.active_btn.isChecked()
        locked = self.locked_btn.isChecked()
        self.active_btn.setText(f"System Active: {'ON' if active else 'OFF'}")
        self.locked_btn.setText(f"State Locked: {'ON' if locked else 'OFF'}")

        # Execution proceeds if and only if active equals locked and active is True
        gate_ok = (active == locked) and active
        if gate_ok:
            self.gate_label.setText("✅ GATE VERIFIED — modules operational.")
            self.gate_label.setStyleSheet("color: #238636; font-weight: bold; padding-top: 4px;")
        else:
            self.gate_label.setText("⛔ EXECUTION HALTED — bi-conditional gate mismatch.")
            self.gate_label.setStyleSheet("color: #da3633; font-weight: bold; padding-top: 4px;")
        self.on_gate_changed(gate_ok)


# ---------------------------------------------------------------------------
# Module 1: Ingestion & Profiler
# ---------------------------------------------------------------------------
class IngestionTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("DATA MATRIX PREVIEW"))
        self.data_table = QTableWidget()
        left_layout.addWidget(self.data_table)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(QLabel("DISCOVERED SCHEMA MANIFEST"))
        self.schema_table = QTableWidget()
        self.schema_table.setColumnCount(4)
        self.schema_table.setHorizontalHeaderLabels(["Column", "Type", "Category", "Null %"])
        right_layout.addWidget(self.schema_table)

        right_layout.addWidget(QLabel("GENERATED DDL ARCHITECTURE"))
        self.ddl_view = QPlainTextEdit()
        self.ddl_view.setReadOnly(True)
        self.ddl_view.setMaximumHeight(160)
        self.ddl_view.setStyleSheet("font-family: 'Consolas', monospace; color: #39c5bb;")
        right_layout.addWidget(self.ddl_view)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

    def update_view(self, df: pd.DataFrame, engine: BCIaiPlatformCore, manifest: Dict[str, Any]):
        fill_table_widget(self.data_table, df)

        self.schema_table.setRowCount(len(manifest["columns"]))
        for r, (col, meta) in enumerate(manifest["columns"].items()):
            self.schema_table.setItem(r, 0, QTableWidgetItem(str(col)))
            self.schema_table.setItem(r, 1, QTableWidgetItem(meta["type"]))
            self.schema_table.setItem(r, 2, QTableWidgetItem(meta["category"]))
            self.schema_table.setItem(r, 3, QTableWidgetItem(f"{meta['null_pct']:.1f}%"))
        self.schema_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self.ddl_view.setPlainText(engine.generate_sql_ddl(manifest))

    def clear_view(self):
        self.data_table.clear()
        self.data_table.setRowCount(0)
        self.data_table.setColumnCount(0)
        self.schema_table.setRowCount(0)
        self.ddl_view.setPlainText("-- No dataset mounted.")


# ---------------------------------------------------------------------------
# Module 2: BCIANTai (ML Forecasting)
# ---------------------------------------------------------------------------
class BciantaiTab(QWidget):
    def __init__(self):
        super().__init__()
        self.df: Optional[pd.DataFrame] = None
        self.table_name = "bci_node"

        layout = QVBoxLayout(self)

        controls = QHBoxLayout()
        target_box = QVBoxLayout()
        target_box.addWidget(QLabel("Target Metric (y)"))
        self.target_combo = QComboBox()
        self.target_combo.currentTextChanged.connect(self._rebuild_preview)
        target_box.addWidget(self.target_combo)

        feature_box = QVBoxLayout()
        feature_box.addWidget(QLabel("Feature Set (X) — multi-select"))
        self.feature_list = QListWidget()
        self.feature_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.feature_list.itemSelectionChanged.connect(self._rebuild_preview)
        feature_box.addWidget(self.feature_list)

        controls.addLayout(target_box, 1)
        controls.addLayout(feature_box, 2)
        layout.addLayout(controls)

        layout.addWidget(QLabel("TENSOR MATRIX PREVIEW"))
        self.tensor_table = QTableWidget()
        layout.addWidget(self.tensor_table)

        export_row = QHBoxLayout()
        self.export_btn = QPushButton("Export Tensor Matrix (.CSV)")
        self.export_btn.clicked.connect(self._export)
        self.export_btn.setEnabled(False)
        export_row.addWidget(self.export_btn)
        export_row.addStretch()
        layout.addLayout(export_row)

        self.info_label = QLabel("Import a dataset on the left panel containing numeric metrics to initialize BCIANTai.")
        self.info_label.setStyleSheet("color: #8b949e;")
        layout.addWidget(self.info_label)

    def update_view(self, df: pd.DataFrame, table_name: str, manifest: Dict[str, Any]):
        self.df = df
        self.table_name = table_name
        metric_keys: List[str] = manifest.get("metric_keys", [])

        self.target_combo.blockSignals(True)
        self.target_combo.clear()
        self.target_combo.addItems(metric_keys)
        self.target_combo.blockSignals(False)

        self.feature_list.blockSignals(True)
        self.feature_list.clear()
        self.feature_list.addItems([str(c) for c in df.columns])
        self.feature_list.blockSignals(False)

        has_metrics = bool(metric_keys)
        self.info_label.setVisible(not has_metrics)
        if has_metrics:
            for i in range(self.feature_list.count()):
                item = self.feature_list.item(i)
                item.setSelected(item.text() in metric_keys[:2])
        self._rebuild_preview()

    def _selected_target(self) -> Optional[str]:
        return self.target_combo.currentText() or None

    def _selected_features(self) -> List[str]:
        return [i.text() for i in self.feature_list.selectedItems()]

    def _rebuild_preview(self):
        if self.df is None:
            return
        target = self._selected_target()
        features = [f for f in self._selected_features() if f != target]
        if not target or not features:
            self.tensor_table.clear()
            self.tensor_table.setRowCount(0)
            self.tensor_table.setColumnCount(0)
            self.export_btn.setEnabled(False)
            return
        tensor_df = self.df[features + [target]].dropna()
        fill_table_widget(self.tensor_table, tensor_df, max_rows=50)
        self.export_btn.setEnabled(True)

    def _export(self):
        target = self._selected_target()
        features = [f for f in self._selected_features() if f != target]
        if not target or not features or self.df is None:
            return
        tensor_df = self.df[features + [target]].dropna()
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Tensor Matrix", f"{self.table_name}_bciantai_tensor.csv", "CSV files (*.csv)"
        )
        if path:
            tensor_df.to_csv(path, index=False)
            QMessageBox.information(self, "Export Complete", f"Tensor matrix saved to:\n{path}")

    def clear_view(self):
        self.df = None
        self.target_combo.clear()
        self.feature_list.clear()
        self.tensor_table.clear()
        self.tensor_table.setRowCount(0)
        self.tensor_table.setColumnCount(0)
        self.export_btn.setEnabled(False)
        self.info_label.setVisible(True)


# ---------------------------------------------------------------------------
# Module 3: BCIGeo (Spatial Node)
# ---------------------------------------------------------------------------
class BciGeoTab(QWidget):
    def __init__(self):
        super().__init__()
        self.df: Optional[pd.DataFrame] = None

        layout = QVBoxLayout(self)

        controls = QHBoxLayout()
        lat_box = QVBoxLayout()
        lat_box.addWidget(QLabel("Latitude Column"))
        self.lat_combo = QComboBox()
        self.lat_combo.currentTextChanged.connect(self._replot)
        lat_box.addWidget(self.lat_combo)

        lon_box = QVBoxLayout()
        lon_box.addWidget(QLabel("Longitude Column"))
        self.lon_combo = QComboBox()
        self.lon_combo.currentTextChanged.connect(self._replot)
        lon_box.addWidget(self.lon_combo)

        controls.addLayout(lat_box)
        controls.addLayout(lon_box)
        layout.addLayout(controls)

        self.figure = Figure(figsize=(6, 5), facecolor="#0d1117")
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        self.status_label = QLabel("Import a dataset containing spatial coordinate attributes to render map telemetry.")
        self.status_label.setStyleSheet("color: #8b949e;")
        layout.addWidget(self.status_label)

    def update_view(self, df: pd.DataFrame):
        self.df = df
        lat_cols = [c for c in df.columns if "lat" in str(c).lower()]
        lon_cols = [c for c in df.columns if "lon" in str(c).lower() or "lng" in str(c).lower()]

        self.lat_combo.blockSignals(True)
        self.lon_combo.blockSignals(True)
        self.lat_combo.clear()
        self.lon_combo.clear()
        self.lat_combo.addItems(lat_cols)
        self.lon_combo.addItems(lon_cols)
        self.lat_combo.blockSignals(False)
        self.lon_combo.blockSignals(False)

        if not lat_cols or not lon_cols:
            self.status_label.setText("No explicit latitude/longitude columns detected in mounted dataset.")
            self.status_label.setVisible(True)
            self.figure.clear()
            self.canvas.draw()
        else:
            self.status_label.setVisible(False)
            self._replot()

    def _replot(self):
        if self.df is None:
            return
        lat_key, lon_key = self.lat_combo.currentText(), self.lon_combo.currentText()
        if not lat_key or not lon_key:
            return
        geo_df = self.df[[lat_key, lon_key]].dropna()
        self.figure.clear()
        ax = self.figure.add_subplot(111, facecolor="#161b22")
        ax.scatter(geo_df[lon_key], geo_df[lat_key], s=18, alpha=0.8, c="#39c5bb", edgecolors="#58a6ff", linewidths=0.5)
        ax.set_xlabel("Longitude", color="#8b949e")
        ax.set_ylabel("Latitude", color="#8b949e")
        ax.set_title("BCIGeo Spatial Node Projections", color="#58a6ff", fontweight="bold")
        ax.tick_params(colors="#8b949e")
        for spine in ax.spines.values():
            spine.set_color("#30363d")
        ax.grid(True, linestyle="--", alpha=0.2, color="#8b949e")
        self.canvas.draw()

    def clear_view(self):
        self.df = None
        self.lat_combo.clear()
        self.lon_combo.clear()
        self.figure.clear()
        self.canvas.draw()
        self.status_label.setText("Import a dataset containing spatial coordinate attributes to render map telemetry.")
        self.status_label.setVisible(True)


# ---------------------------------------------------------------------------
# Module 4: Orbital (Real-Time Telemetry)
# ---------------------------------------------------------------------------
class OrbitalTab(QWidget):
    def __init__(self):
        super().__init__()
        self.table_name = "bci_node"
        self.gate_ok = True

        layout = QVBoxLayout(self)

        metrics_row = QHBoxLayout()
        self.node_status = self._metric_box("Node Status", "OFFLINE")
        self.buffer_status = self._metric_box("Memory Buffer", "Unlocked")
        self.load_status = self._metric_box("System Load", "0%")
        self.active_node = self._metric_box("Active Node", self.table_name)
        for box in (self.node_status, self.buffer_status, self.load_status, self.active_node):
            metrics_row.addWidget(box)
        layout.addLayout(metrics_row)

        layout.addWidget(QLabel("NODE TELEMETRY LOG STREAM"))
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet("font-family: 'Consolas', monospace; color: #58a6ff;")
        layout.addWidget(self.log_view)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(2000)

    def _metric_box(self, title: str, value: str) -> QGroupBox:
        box = QGroupBox(title)
        v = QVBoxLayout()
        label = QLabel(value)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 18px; font-weight: bold; color: #c9d1d9;")
        v.addWidget(label)
        box.setLayout(v)
        box._value_label = label
        return box

    def set_context(self, table_name: str, gate_ok: bool):
        self.table_name = table_name
        self.gate_ok = gate_ok
        self.active_node._value_label.setText(table_name)

    def _tick(self):
        online = self.gate_ok
        self.node_status._value_label.setText("ONLINE" if online else "HALTED")
        self.node_status._value_label.setStyleSheet(
            f"font-size: 18px; font-weight: bold; color: {'#238636' if online else '#da3633'};"
        )
        self.buffer_status._value_label.setText("Locked" if self.gate_ok else "Unlocked")
        load = np.random.randint(12, 28) if online else 0
        self.load_status._value_label.setText(f"{load}%")

        ts = time.strftime("%H:%M:%S")
        gate_msg = "verified" if online else "FAILED"
        lines = [
            f"[{ts}] [ORBITAL] Gatekeeper check: bi-conditional {gate_msg}.",
            f"[{ts}] [BCI-CORE] Memory buffer assigned to target '{self.table_name}'.",
            f"[{ts}] [BCIANTai] Tensor engine heartbeat.",
            f"[{ts}] [BCIGeo] Coordinate listener armed.",
        ]
        self.log_view.appendPlainText("\n".join(lines))


# ---------------------------------------------------------------------------
# Main Window
# ---------------------------------------------------------------------------
class BCIaiMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Erudite")
        self.resize(1280, 800)

        self.df: Optional[pd.DataFrame] = None
        self.engine = BCIaiPlatformCore(table_name="bci_primary_data")
        self.gate_ok = True

        central = QWidget()
        root_layout = QHBoxLayout(central)

        self.tabs = QTabWidget()
        self.ingestion_tab = IngestionTab()
        self.bciantai_tab = BciantaiTab()
        self.bcigeo_tab = BciGeoTab()
        self.orbital_tab = OrbitalTab()
        self.orbital_tab.set_context(self.engine.table_name, self.gate_ok)

        self.tabs.addTab(self.ingestion_tab, "📥 Ingestion & Profiler")
        self.tabs.addTab(self.bciantai_tab, "🧠 BCIANTai (ML Forecasting)")
        self.tabs.addTab(self.bcigeo_tab, "🗺️ BCIGeo (Spatial Node)")
        self.tabs.addTab(self.orbital_tab, "🛰️ Orbital (Real-Time Telemetry)")

        # Left sidebar dataset importer
        self.import_panel = DatasetImportPanel(self._on_mount, self._on_gate_changed)
        self.import_panel.setFixedWidth(330)

        root_layout.addWidget(self.import_panel)
        root_layout.addWidget(self.tabs, 1)
        self.setCentralWidget(central)

        self._apply_gate_state()

    def _on_mount(self, df: pd.DataFrame, table_name: str):
        self.df = df
        self.engine = BCIaiPlatformCore(dataframe=df, table_name=table_name)
        manifest = self.engine.profile_schema()

        self.ingestion_tab.update_view(df, self.engine, manifest)
        self.bciantai_tab.update_view(df, table_name, manifest)
        self.bcigeo_tab.update_view(df)
        self.orbital_tab.set_context(table_name, self.gate_ok)

    def _on_gate_changed(self, gate_ok: bool):
        self.gate_ok = gate_ok
        self.orbital_tab.set_context(self.engine.table_name, gate_ok)
        self._apply_gate_state()

    def _apply_gate_state(self):
        for i in range(self.tabs.count() - 1):
            self.tabs.setTabEnabled(i, self.gate_ok)
        if not self.gate_ok:
            self.ingestion_tab.clear_view()
            self.bciantai_tab.clear_view()
            self.bcigeo_tab.clear_view()


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(BCI_DARK_STYLESHEET)

    main_window = BCIaiMainWindow()

    def launch_dashboard():
        main_window.show()

    boot_screen = BCIBootScreen(on_complete=launch_dashboard)
    boot_screen.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

