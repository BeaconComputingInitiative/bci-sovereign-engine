"""
=====================================================================
Developer: Chance Joaquin Boone
Project: Erudite — Beacon Computing Initiative
Module: Unified System Control Dashboard (PyQt5 port)
Developer Seal: BCI-CORE-UNIFIED-GUI-V3-QT
=====================================================================

Desktop port of the Streamlit BCIai dashboard. Same four subsystems
(Ingestion & Profiler, BCIANTai forecasting, BCIGeo spatial node,
Orbital telemetry), rebuilt as native tabs with a live-updating
QTimer instead of Streamlit's rerun-on-interaction model.

Fixes carried over from the Streamlit review:
  - The system_active / state_locked bi-conditional gate is now a
    real, user-toggleable control (see "System Lock" group box)
    instead of two hardcoded True values that could never fail.
  - SQL DDL generation quotes identifiers to avoid producing invalid
    or injectable SQL from arbitrary column/table names.
  - Schema profiling is cached per-dataframe instead of re-run on
    every widget interaction.

Dependencies: PyQt5, pandas, numpy, matplotlib
    pip install PyQt5 pandas numpy matplotlib
"""

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
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


# ---------------------------------------------------------------------------
# Core engine (schema profiling + DDL) — same logic as the Streamlit version,
# with identifier quoting added.
# ---------------------------------------------------------------------------
class BCIaiPlatformCore:
    """Profiles a mounted dataframe and can emit a matching SQL DDL."""

    def __init__(self, dataframe: Optional[pd.DataFrame] = None, table_name: str = "bci_node"):
        self.df = dataframe
        self.table_name = table_name
        self._manifest_cache: Optional[Dict[str, Any]] = None
        self._cache_key: Optional[int] = None

    @staticmethod
    def _quote_identifier(name: str) -> str:
        # Double-quote SQL identifiers and escape embedded quotes, so odd
        # column/table names can't break or inject into the generated DDL.
        return '"' + str(name).replace('"', '""') + '"'

    def profile_schema(self) -> Dict[str, Any]:
        if self.df is None:
            return {}

        # Cache keyed on dataframe identity + table name so re-selecting the
        # same dataset in a widget doesn't re-profile from scratch.
        cache_key = (id(self.df), self.table_name, len(self.df.columns))
        if self._manifest_cache is not None and self._cache_key == cache_key:
            return self._manifest_cache

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

        manifest = {
            "table_name": self.table_name,
            "total_rows": total_rows,
            "temporal_keys": temporal_keys,
            "metric_keys": metric_keys,
            "geo_keys": geo_keys,
            "columns": cols_meta,
        }
        self._manifest_cache = manifest
        self._cache_key = cache_key
        return manifest

    def generate_sql_ddl(self, manifest: Dict[str, Any]) -> str:
        if not manifest:
            return "-- No dataset loaded."
        table = self._quote_identifier(manifest["table_name"])
        sql_lines = [f"CREATE TABLE {table} ("]
        col_defs = []
        for col, meta in manifest["columns"].items():
            cat = meta["category"]
            sql_type = (
                "TIMESTAMP" if cat == "temporal"
                else "FLOAT" if cat in ("metric", "geospatial")
                else "VARCHAR(255)"
            )
            col_defs.append(f"    {self._quote_identifier(col)} {sql_type}")
        sql_lines.append(",\n".join(col_defs))
        sql_lines.append(");")
        return "\n".join(sql_lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def load_dataframe(path: str) -> pd.DataFrame:
    lower = path.lower()
    if lower.endswith(".csv"):
        return pd.read_csv(path)
    if lower.endswith(".json"):
        return pd.read_json(path)
    if lower.endswith((".xlsx", ".xls")):
        return pd.read_excel(path)
    raise ValueError("Unsupported file type — use .csv, .json, or .xlsx")


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
# Sidebar: mount controls + system lock gate
# ---------------------------------------------------------------------------
class MountPanel(QGroupBox):
    def __init__(self, on_mount, on_gate_changed):
        super().__init__("Mount & System Controls")
        self.on_mount = on_mount
        self.on_gate_changed = on_gate_changed

        layout = QVBoxLayout()

        self.table_name_input = QLineEdit("bci_primary_data")
        layout.addWidget(QLabel("Active System Node"))
        layout.addWidget(self.table_name_input)

        mount_btn = QPushButton("Mount Data Stream (.csv / .json / .xlsx)")
        mount_btn.clicked.connect(self._pick_file)
        layout.addWidget(mount_btn)

        self.status_label = QLabel("No dataset mounted.")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        layout.addSpacing(12)
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
        layout.addWidget(self.gate_label)

        layout.addStretch()
        self.setLayout(layout)
        self._gate_toggled()

    def _pick_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Mount Data Stream", "", "Data files (*.csv *.json *.xlsx *.xls)"
        )
        if not path:
            return
        try:
            df = load_dataframe(path)
        except Exception as e:
            self.status_label.setText(f"Mount error: {e}")
            QMessageBox.critical(self, "Mount Error", str(e))
            return
        self.status_label.setText(f"Mounted: {len(df)} records from {path.split('/')[-1]}")
        self.on_mount(df, self.table_name_input.text().strip() or "bci_node")

    def _gate_toggled(self):
        active = self.active_btn.isChecked()
        locked = self.locked_btn.isChecked()
        self.active_btn.setText(f"System Active: {'ON' if active else 'OFF'}")
        self.locked_btn.setText(f"State Locked: {'ON' if locked else 'OFF'}")

        # Real bi-conditional check: dispatch proceeds iff active == locked
        # AND the system is active. Unlike the original always-true gate,
        # this can genuinely fail (e.g. active ON / locked OFF).
        gate_ok = (active == locked) and active
        if gate_ok:
            self.gate_label.setText("✅ Gate OK — modules enabled.")
            self.gate_label.setStyleSheet("color: #2e7d32; font-weight: bold;")
        else:
            self.gate_label.setText("⛔ EXECUTION HALTED — bi-conditional check failed.")
            self.gate_label.setStyleSheet("color: #c62828; font-weight: bold;")
        self.on_gate_changed(gate_ok)

    def current_table_name(self) -> str:
        return self.table_name_input.text().strip() or "bci_node"


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
        left_layout.addWidget(QLabel("Data Matrix Preview"))
        self.data_table = QTableWidget()
        left_layout.addWidget(self.data_table)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(QLabel("Discovered Schema Manifest"))
        self.schema_table = QTableWidget()
        self.schema_table.setColumnCount(4)
        self.schema_table.setHorizontalHeaderLabels(["Column", "Type", "Category", "Null %"])
        right_layout.addWidget(self.schema_table)

        right_layout.addWidget(QLabel("Generated DDL Architecture"))
        self.ddl_view = QPlainTextEdit()
        self.ddl_view.setReadOnly(True)
        self.ddl_view.setMaximumHeight(160)
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
        self.ddl_view.setPlainText("-- No dataset loaded.")


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

        layout.addWidget(QLabel("Tensor Matrix Preview"))
        self.tensor_table = QTableWidget()
        layout.addWidget(self.tensor_table)

        export_row = QHBoxLayout()
        self.export_btn = QPushButton("Export Tensor Matrix (.CSV)")
        self.export_btn.clicked.connect(self._export)
        self.export_btn.setEnabled(False)
        export_row.addWidget(self.export_btn)
        export_row.addStretch()
        layout.addLayout(export_row)

        self.info_label = QLabel("Mount a dataset containing numeric metrics to initialize BCIANTai tensor mapping.")
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
            # default-select up to first two metric keys, mirroring the
            # Streamlit version's default feature selection
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

        self.figure = Figure(figsize=(6, 5))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        self.status_label = QLabel("Mount a dataset containing spatial coordinate attributes to render map telemetry.")
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
        ax = self.figure.add_subplot(111)
        ax.scatter(geo_df[lon_key], geo_df[lat_key], s=14, alpha=0.7, c="#1f77b4")
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.set_title("BCIGeo Spatial Node Projections")
        ax.grid(True, linestyle="--", alpha=0.3)
        self.canvas.draw()

    def clear_view(self):
        self.df = None
        self.lat_combo.clear()
        self.lon_combo.clear()
        self.figure.clear()
        self.canvas.draw()
        self.status_label.setText("Mount a dataset containing spatial coordinate attributes to render map telemetry.")
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

        layout.addWidget(QLabel("Node Telemetry Log Stream"))
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(2000)  # simulated telemetry every 2s, like a live feed

    def _metric_box(self, title: str, value: str) -> QGroupBox:
        box = QGroupBox(title)
        v = QVBoxLayout()
        label = QLabel(value)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 18px; font-weight: bold;")
        v.addWidget(label)
        box.setLayout(v)
        box._value_label = label  # stash for later updates
        return box

    def set_context(self, table_name: str, gate_ok: bool):
        self.table_name = table_name
        self.gate_ok = gate_ok
        self.active_node._value_label.setText(table_name)

    def _tick(self):
        online = self.gate_ok
        self.node_status._value_label.setText("ONLINE" if online else "HALTED")
        self.node_status._value_label.setStyleSheet(
            f"font-size: 18px; font-weight: bold; color: {'#2e7d32' if online else '#c62828'};"
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
        # keep the log from growing unbounded
        if self.log_view.document().blockCount() > 400:
            cursor = self.log_view.textCursor()
            cursor.movePosition(cursor.Start)
            cursor.movePosition(cursor.Down, cursor.KeepAnchor, 100)
            cursor.removeSelectedText()


# ---------------------------------------------------------------------------
# Main window
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

        # Build tabs first: MountPanel's constructor fires the gate-changed
        # callback immediately, and that callback touches self.orbital_tab.
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

        self.mount_panel = MountPanel(self._on_mount, self._on_gate_changed)
        self.mount_panel.setFixedWidth(360)
        root_layout.addWidget(self.mount_panel)
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
        # When the bi-conditional gate fails, disable the data-dependent
        # tabs rather than silently rendering stale/misleading content.
        for i in range(self.tabs.count() - 1):  # keep Orbital visible always
            self.tabs.setTabEnabled(i, self.gate_ok)
        if not self.gate_ok:
            self.ingestion_tab.clear_view()
            self.bciantai_tab.clear_view()
            self.bcigeo_tab.clear_view()


def main():
    app = QApplication(sys.argv)
    window = BCIaiMainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

