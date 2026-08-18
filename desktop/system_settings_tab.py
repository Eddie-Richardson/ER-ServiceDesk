# ER-ServiceDesk/desktop/system_settings_tab.py

"""
Settings tab for tunable, server-side runtime settings -- values that
used to be hardcoded constants in the backend, now editable here
without needing file access to the server or a reinstall.

Deliberately synchronous, no QThread -- this is a small, infrequent
action (an admin occasionally tweaking a number), not something
performance-critical, and the simplest safe choice here is not
introducing a background thread at all.

Two settings live here right now:
  - Lock timeout (minutes) -- how long before an abandoned record
    lock becomes reclaimable. Takes effect immediately; read fresh
    from the database on every lock attempt (see
    record_lock_service.py).
  - Inbound email poll interval (seconds) -- how often the server
    checks for customer email replies. Only takes effect the next
    time the server's scheduler process restarts (see
    app/workers/scheduler.py) -- not instant, since rq-scheduler
    fixes the interval at registration time and doesn't re-check it
    afterward.

Only reachable from the Settings window, which is already
superuser-gated before it's ever opened (see settings_window.py) --
matches the backend route's own superuser requirement.
"""

from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from desktop import api_client
from desktop.api_client import ApiError

# (settings key, display label, default shown if never set, help text)
_SETTINGS = [
    (
        "lock_timeout_minutes",
        "Lock Timeout (minutes)",
        "15",
        "How long before an abandoned record lock (someone editing a "
        "ticket/customer/etc. who closed the app without releasing it) "
        "becomes reclaimable by someone else. Takes effect immediately.",
    ),
    (
        "inbound_email_poll_interval_seconds",
        "Inbound Email Poll Interval (seconds)",
        "60",
        "How often the server checks for customer email replies. Only "
        "takes effect the next time the server restarts (or the "
        "scheduler service specifically is restarted) -- not instant.",
    ),
]


class SystemSettingsTab(QWidget):
    """Editable fields for every tunable SystemSetting, with a single Save action."""

    def __init__(self):
        """Builds one labeled field per setting, pre-filled with its current value."""
        super().__init__()
        self._inputs: dict[str, QLineEdit] = {}
        self._build_ui()
        self._load_current_values()

    def _build_ui(self):
        """Builds one form row per setting, each with its own help text underneath."""
        layout = QVBoxLayout()
        form = QFormLayout()

        for key, label, default, help_text in _SETTINGS:
            field = QLineEdit()
            field.setPlaceholderText(default)
            self._inputs[key] = field
            form.addRow(f"{label}:", field)

            help_label = QLabel(help_text)
            help_label.setWordWrap(True)
            help_label.setStyleSheet("color: gray; font-size: 11px;")
            form.addRow("", help_label)

        self.location_combo = QComboBox()
        form.addRow("Part Deduction Location:", self.location_combo)

        location_help_label = QLabel(
            "Where inventory is deducted from when a part is added as a "
            "line item on an invoice (never on a quote -- a quote isn't "
            "a real transaction yet). Takes effect immediately."
        )
        location_help_label.setWordWrap(True)
        location_help_label.setStyleSheet("color: gray; font-size: 11px;")
        form.addRow("", location_help_label)

        layout.addLayout(form)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        save_button = QPushButton("Save")
        save_button.clicked.connect(self._on_save)
        layout.addWidget(save_button)

        layout.addStretch()
        self.setLayout(layout)

    def _load_current_values(self):
        """Fetches every current setting and fills in whichever of ours are already set, plus every location for the deduction-location picker."""
        try:
            settings = api_client.list_system_settings()
        except ApiError as e:
            self.status_label.setText(f"Could not load current values: {e}")
            return

        by_key = {s["key"]: s.get("value") for s in settings}
        for key, field in self._inputs.items():
            if by_key.get(key) is not None:
                field.setText(str(by_key[key]))

        try:
            locations = api_client.list_locations()
        except ApiError as e:
            self.status_label.setText(f"Could not load locations: {e}")
            return

        self.location_combo.clear()
        for location in locations:
            self.location_combo.addItem(location["name"], userData=location["id"])

        current_location_id_str = by_key.get("part_deduction_location_id")
        if current_location_id_str:
            index = self.location_combo.findData(int(current_location_id_str))
            if index >= 0:
                self.location_combo.setCurrentIndex(index)

    def _on_save(self):
        """Validates every numeric field is a real, positive integer, then saves each one plus the selected deduction location."""
        values: dict[str, str] = {}
        for key, label, default, _ in _SETTINGS:
            field = self._inputs[key]
            raw = field.text().strip() or default
            if not raw.isdigit() or int(raw) <= 0:
                QMessageBox.warning(self, "Invalid Value", f"{label} must be a positive whole number.")
                return
            values[key] = raw

        selected_location_id = self.location_combo.currentData()
        if selected_location_id is not None:
            values["part_deduction_location_id"] = str(selected_location_id)

        for key, value in values.items():
            try:
                api_client.save_system_setting(key, value)
            except ApiError as e:
                QMessageBox.critical(self, "Save Failed", str(e))
                return

        self.status_label.setText("Saved.")
