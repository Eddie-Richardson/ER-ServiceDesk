# ER-ServiceDesk/desktop/device_user_account_dialog.py

"""
Dialog for adding a new user account to a device, or editing an
existing one.

The password field is deliberately NOT masked -- unlike a login
password field, this needs to be genuinely readable by a tech looking
at the customer's profile (the whole point of storing it), so showing
dots instead of the real value would defeat the purpose.
"""

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from desktop import api_client, layout
from desktop.api_client import ApiError


class DeviceUserAccountDialog(QDialog):
    """
    Modal dialog for creating or editing a device user account.

    Pass `account=None` to add a new one, or an existing account dict
    to edit it. On a successful save, the dialog closes itself and the
    saved record is available via `self.saved_account`.
    """

    def __init__(self, device_id: int, account: dict | None = None, parent=None):
        """
        Args:
            device_id: The device this account belongs to.
            account: An existing account dict to edit, or None to
                create a new one.
            parent: The parent widget, per normal Qt dialog convention.
        """
        super().__init__(parent)
        self.device_id = device_id
        self.account = account
        self.saved_account: dict | None = None
        self.deleted = False

        self.setWindowTitle("Edit User Account" if account else "Add User Account")
        self.setMinimumWidth(layout.DIALOG_WIDTH)

        self._build_ui()
        if account:
            self._prefill_from_account(account)

    def _build_ui(self):
        """Builds the Account Name, Password, and Administrator fields."""
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
        )
        outer_layout.setSpacing(layout.SPACE_SM)

        self.account_name_input = QLineEdit()
        self.account_name_input.setPlaceholderText("Account name, e.g. john@outlook.com (required)")
        self.account_name_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password (optional)")
        self.password_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.is_admin_checkbox = QCheckBox("Administrator")

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
        if self.account:
            self.delete_button = QPushButton("Remove Account")
            self.delete_button.setObjectName("danger")
            self.delete_button.setFixedHeight(layout.BUTTON_HEIGHT)
            self.delete_button.clicked.connect(self._attempt_delete)

        for label_text, widget in [
            ("Account Name", self.account_name_input),
            ("Password", self.password_input),
        ]:
            field_label = QLabel(label_text)
            field_label.setObjectName("subtitle")
            outer_layout.addWidget(field_label)
            outer_layout.addWidget(widget)

        outer_layout.addWidget(self.is_admin_checkbox)
        outer_layout.addWidget(self.error_label)
        outer_layout.addSpacing(layout.SPACE_SM)
        outer_layout.addWidget(self.save_button)
        outer_layout.addWidget(cancel_button)
        if self.delete_button:
            outer_layout.addWidget(self.delete_button)

        self.setLayout(outer_layout)
        self.account_name_input.setFocus()

    def _prefill_from_account(self, account: dict):
        """
        Args:
            account: The account dict being edited.
        """
        self.account_name_input.setText(account.get("account_name", ""))
        self.password_input.setText(account.get("password") or "")
        self.is_admin_checkbox.setChecked(account.get("is_admin", False))

    # -----------------------------------------------------------------
    # Save
    # -----------------------------------------------------------------
    def _attempt_save(self):
        """Validates the form, then saves synchronously -- a small, infrequent action."""
        account_name = self.account_name_input.text().strip()
        if not account_name:
            self._show_error("Enter an account name.")
            return

        self.save_button.setEnabled(False)
        self.save_button.setText("Saving...")
        self.error_label.hide()

        password = self.password_input.text() or None

        try:
            if self.account:
                result = api_client.update_device_user_account(self.account["id"], {
                    "account_name": account_name, "password": password, "is_admin": self.is_admin_checkbox.isChecked(),
                })
            else:
                result = api_client.create_device_user_account(
                    self.device_id, account_name, password, self.is_admin_checkbox.isChecked(),
                )
        except ApiError as e:
            self.save_button.setEnabled(True)
            self.save_button.setText("Save")
            self._show_error(str(e))
            return

        self.save_button.setEnabled(True)
        self.save_button.setText("Save")
        self.saved_account = result
        self.accept()

    def _show_error(self, message: str):
        """
        Args:
            message: The error text to show below the form.
        """
        self.error_label.setText(message)
        self.error_label.show()

    # -----------------------------------------------------------------
    # Delete
    # -----------------------------------------------------------------
    def _attempt_delete(self):
        """Confirms, then removes this user account from the device."""
        confirmed = QMessageBox.question(
            self,
            "Remove Account",
            f"Remove the account '{self.account['account_name']}'? This can't be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirmed != QMessageBox.StandardButton.Yes:
            return

        self.delete_button.setEnabled(False)
        try:
            api_client.delete_device_user_account(self.account["id"])
        except ApiError as e:
            self._show_error(str(e))
            return
        finally:
            self.delete_button.setEnabled(True)

        self.deleted = True
        self.accept()
