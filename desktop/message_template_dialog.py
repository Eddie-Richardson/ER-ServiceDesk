# ER-ServiceDesk/desktop/message_template_dialog.py

"""
Dialog for creating a new notes template or editing an existing one.

A template is a reusable body of text for standardized ticket notes --
inserted into the Notes composer via a quick-pick dropdown (see
notes_dialog.py) rather than typing the same note from scratch every time.
"""

from PySide6.QtCore import QThread
from PySide6.QtWidgets import (
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from desktop import api_client, layout
from desktop.api_client import ApiError
from desktop.base_dialog import AppDialog
from desktop.window_geometry import restore_geometry, save_geometry
from desktop.lookup_save_worker import LookupSaveWorker

ENDPOINT = "/message_templates/"


class MessageTemplateDialog(AppDialog):
    """
    Modal dialog for creating or editing a message template.

    Pass `template=None` to create a new one, or an existing template
    dict to edit it. On a successful save, the dialog closes itself
    and the saved record is available via `self.saved_template`.
    """

    def __init__(self, template: dict | None = None, parent=None):
        super().__init__(parent)
        self.template = template
        self.saved_template: dict | None = None
        self.deleted = False

        self._thread: QThread | None = None
        self._worker: LookupSaveWorker | None = None

        self.setWindowTitle("Edit Notes Template" if template else "New Notes Template")
        self.setMinimumWidth(layout.DIALOG_WIDTH)
        restore_geometry(self, "MessageTemplateDialog")

        self._build_ui()
        if template:
            self._prefill_from_template(template)

    def closeEvent(self, event):
        save_geometry(self, "MessageTemplateDialog")
        super().closeEvent(event)

    def _build_ui(self):
        """Builds the Name, Subject, and Body fields."""
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
        )
        outer_layout.setSpacing(layout.SPACE_SM)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Name, e.g. 'Ticket Created' (required)")
        self.name_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.body_input = QTextEdit()
        self.body_input.setPlaceholderText(
            "Body (required). Supports {ticket_id} and {ticket_title} -- "
            "filled in automatically wherever this template is inserted."
        )
        self.body_input.setFixedHeight(150)

        self.error_label = QLabel("")
        self.error_label.setObjectName("subtitle")
        self.error_label.setStyleSheet("color: #DC2626;")
        self.error_label.setWordWrap(True)
        self.error_label.hide()

        self.save_button = QPushButton("Save")
        self.save_button.setFixedHeight(layout.BUTTON_HEIGHT)
        self.save_button.clicked.connect(self._attempt_save)

        cancel_button = QPushButton("Cancel")
        cancel_button.setObjectName("secondary")
        cancel_button.setFixedHeight(layout.BUTTON_HEIGHT)
        cancel_button.clicked.connect(self.reject)

        self.delete_button = None
        if self.template:
            self.delete_button = QPushButton("Delete Notes Template")
            self.delete_button.setObjectName("danger")
            self.delete_button.setFixedHeight(layout.BUTTON_HEIGHT)
            self.delete_button.clicked.connect(self._attempt_delete)

        for label_text, widget in [
            ("Name", self.name_input),
            ("Body", self.body_input),
        ]:
            field_label = QLabel(label_text)
            field_label.setObjectName("subtitle")
            outer_layout.addWidget(field_label)
            outer_layout.addWidget(widget)

        outer_layout.addWidget(self.error_label)
        outer_layout.addSpacing(layout.SPACE_SM)
        outer_layout.addWidget(self.save_button)
        outer_layout.addWidget(cancel_button)
        if self.delete_button:
            outer_layout.addWidget(self.delete_button)

        self.setLayout(outer_layout)
        self.name_input.setFocus()

    def _prefill_from_template(self, template: dict):
        self.name_input.setText(template.get("name", ""))
        self.body_input.setPlainText(template.get("body", ""))

    # -----------------------------------------------------------------
    # Save
    # -----------------------------------------------------------------
    def _attempt_save(self):
        """Validates the form, then starts the save request on a background thread."""
        name = self.name_input.text().strip()
        body = self.body_input.toPlainText().strip()

        if not name:
            self._show_error("Enter a name.")
            return
        if not body:
            self._show_error("Enter a body.")
            return

        payload = {"name": name, "body": body}

        self.save_button.setEnabled(False)
        self.save_button.setText("Saving...")
        self.error_label.hide()

        template_id = self.template["id"] if self.template else None
        self._thread = QThread()
        self._worker = LookupSaveWorker(ENDPOINT, payload, template_id)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_save_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _on_save_finished(self, success: bool, result):
        """
        Args:
            result: The saved record on success, or the caught
                ApiError on failure.
        """
        self.save_button.setEnabled(True)
        self.save_button.setText("Save")

        if not success:
            self.handle_api_error(result, on_other_error=self._show_error)
            return

        self.saved_template = result
        self.accept()

    def _show_error(self, message: str):
        self.error_label.setText(message)
        self.error_label.show()

    # -----------------------------------------------------------------
    # Delete
    # -----------------------------------------------------------------
    def _attempt_delete(self):
        """
        Confirms, then deletes this template. Synchronous (no QThread)
        -- a small, infrequent action, not worth the complexity of a
        background thread.
        """
        confirmed = QMessageBox.question(
            self,
            "Delete Template",
            f"Delete the '{self.template['name']}' template? This can't be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirmed != QMessageBox.StandardButton.Yes:
            return

        self.delete_button.setEnabled(False)
        try:
            api_client.delete_lookup_item(ENDPOINT, self.template["id"])
        except ApiError as e:
            self.handle_api_error(e, on_other_error=self._show_error)
            return
        finally:
            self.delete_button.setEnabled(True)

        self.deleted = True
        self.accept()
