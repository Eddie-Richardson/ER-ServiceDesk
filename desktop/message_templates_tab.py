# ER-ServiceDesk/desktop/message_templates_tab.py

"""
Settings tab for managing reusable notes templates -- create, edit,
and delete the bodies of text available via the Notes composer's
quick-insert dropdown (see notes_dialog.py).
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from desktop import api_client, layout
from desktop.api_client import ApiError
from desktop.message_template_dialog import MessageTemplateDialog

COLUMN_HEADERS = ["Name"]


class MessageTemplatesTab(QWidget):
    """List, create, edit, and delete notes templates."""

    def __init__(self):
        """Builds the toolbar and table, then loads data."""
        super().__init__()
        self.all_templates: list[dict] = []
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        """Builds the toolbar, status label, and table."""
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
        )
        outer_layout.setSpacing(layout.SPACE_SM)

        toolbar = QHBoxLayout()
        new_button = QPushButton("New Notes Template")
        new_button.setFixedHeight(layout.BUTTON_HEIGHT)
        new_button.clicked.connect(self._open_new_template_dialog)
        toolbar.addWidget(new_button)

        refresh_button = QPushButton("Refresh")
        refresh_button.setObjectName("secondary")
        refresh_button.setFixedHeight(layout.BUTTON_HEIGHT)
        refresh_button.clicked.connect(self._load_data)
        toolbar.addWidget(refresh_button)
        toolbar.addStretch()
        outer_layout.addLayout(toolbar)

        self.status_label = QLabel("Loading templates...")
        self.status_label.setObjectName("subtitle")
        outer_layout.addWidget(self.status_label)

        self.table = QTableWidget()
        self.table.setColumnCount(len(COLUMN_HEADERS))
        self.table.setHorizontalHeaderLabels(COLUMN_HEADERS)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self._on_row_double_clicked)
        outer_layout.addWidget(self.table)

        self.setLayout(outer_layout)

    def _load_data(self):
        """Fetches every template and renders the table."""
        self.status_label.setText("Loading templates...")
        try:
            self.all_templates = api_client.list_message_templates()
        except ApiError as e:
            self.status_label.setText(f"Couldn't load templates: {e}")
            return
        self._render_table()

    def _render_table(self):
        """Renders self.all_templates into the table."""
        self.table.setRowCount(len(self.all_templates))
        for row, template in enumerate(self.all_templates):
            values = [template.get("name", "")]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, template)
                self.table.setItem(row, col, item)
        self.status_label.setText(f"{len(self.all_templates)} template(s).")

    def _open_new_template_dialog(self):
        """Opens the template form in create mode; refreshes the list if a template was saved."""
        dialog = MessageTemplateDialog(None, parent=self)
        if dialog.exec():
            self._load_data()

    def _on_row_double_clicked(self):
        """Opens the template form pre-filled with the double-clicked row's template."""
        selected_items = self.table.selectedItems()
        if not selected_items:
            return

        template = selected_items[0].data(Qt.ItemDataRole.UserRole)
        dialog = MessageTemplateDialog(template, parent=self)
        if dialog.exec():
            self._load_data()
