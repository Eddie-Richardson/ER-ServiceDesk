# ER-ServiceDesk/desktop/business_info_tab.py

"""
Settings tab for the shop's business identity and email configuration
-- business name, phone, the email account used for outbound sends
and inbound polling, and its SMTP/IMAP settings. Every field here is
a real SystemSetting row, edited live -- no .env, no restart needed
to take effect (see app/core/email.py, which reads these fresh on
every send/poll).

Deliberately synchronous, no QThread, same reasoning as
system_settings_tab.py.
"""

from PySide6.QtWidgets import (
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from desktop import api_client
from desktop.api_client import ApiError


class BusinessInfoTab(QWidget):
    """Editable fields for the shop's business identity and email account, with a single Save action."""

    def __init__(self):
        """Builds one labeled field per setting, pre-filled with its current value."""
        super().__init__()
        self._build_ui()
        self._load_current_values()

    def _build_ui(self):
        """Builds the form -- business identity fields, then the email account section."""
        layout = QVBoxLayout()
        form = QFormLayout()

        self.business_name_input = QLineEdit()
        form.addRow("Business Name:", self.business_name_input)

        self.business_phone_input = QLineEdit()
        self.business_phone_input.setPlaceholderText("e.g. (555) 123-4567")
        form.addRow("Business Phone:", self.business_phone_input)

        phone_help_label = QLabel("Shown to customers on quotes, invoices, and other emailed communications -- optional.")
        phone_help_label.setWordWrap(True)
        phone_help_label.setStyleSheet("color: gray; font-size: 11px;")
        form.addRow("", phone_help_label)

        email_section_label = QLabel("Email Account")
        email_section_label.setObjectName("subtitle")
        form.addRow(email_section_label)

        self.email_address_input = QLineEdit()
        form.addRow("Email Address:", self.email_address_input)

        self.email_password_input = QLineEdit()
        self.email_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.email_password_input.setPlaceholderText("Leave blank to keep the current password")
        form.addRow("Email Password:", self.email_password_input)

        password_help_label = QLabel(
            "Write-only -- the current password is never shown here, "
            "not even masked. Leave this blank to keep it unchanged; "
            "enter a new value only to replace it. For providers like "
            "Gmail that require one, this is an App Password, not the "
            "account's real login password."
        )
        password_help_label.setWordWrap(True)
        password_help_label.setStyleSheet("color: gray; font-size: 11px;")
        form.addRow("", password_help_label)

        self.smtp_host_input = QLineEdit()
        form.addRow("SMTP Host:", self.smtp_host_input)

        self.smtp_port_input = QSpinBox()
        self.smtp_port_input.setMinimum(1)
        self.smtp_port_input.setMaximum(65535)
        form.addRow("SMTP Port:", self.smtp_port_input)

        self.imap_host_input = QLineEdit()
        form.addRow("IMAP Host:", self.imap_host_input)

        self.imap_port_input = QSpinBox()
        self.imap_port_input.setMinimum(1)
        self.imap_port_input.setMaximum(65535)
        form.addRow("IMAP Port:", self.imap_port_input)

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
        """Fetches the current business info and fills in every field except the password, which is never returned."""
        try:
            info = api_client.get_business_info()
        except ApiError as e:
            self.status_label.setText(f"Could not load current values: {e}")
            return

        self.business_name_input.setText(info["business_name"])
        self.business_phone_input.setText(info["business_phone"])
        self.email_address_input.setText(info["email_address"])
        self.smtp_host_input.setText(info["smtp_host"])
        self.smtp_port_input.setValue(info["smtp_port"])
        self.imap_host_input.setText(info["imap_host"])
        self.imap_port_input.setValue(info["imap_port"])

        if info["email_password_is_set"]:
            self.email_password_input.setPlaceholderText("(set) Leave blank to keep the current password")
        else:
            self.email_password_input.setPlaceholderText("Not set yet")

    def _on_save(self):
        """Saves every field. An empty password field means leave the currently-stored password unchanged, not clear it."""
        new_password = self.email_password_input.text() or None

        try:
            api_client.save_business_info(
                self.business_name_input.text().strip(),
                self.business_phone_input.text().strip(),
                self.email_address_input.text().strip(),
                new_password,
                self.smtp_host_input.text().strip(),
                self.smtp_port_input.value(),
                self.imap_host_input.text().strip(),
                self.imap_port_input.value(),
            )
        except ApiError as e:
            QMessageBox.critical(self, "Save Failed", str(e))
            return

        self.email_password_input.clear()
        self.status_label.setText("Saved.")
        self._load_current_values()
