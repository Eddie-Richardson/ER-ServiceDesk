# ER-ServiceDesk/desktop/payment_dialog.py

"""
Dialog for recording a payment against an invoice.
"""

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from desktop import api_client, layout
from desktop.api_client import ApiError

PAYMENT_METHODS = ["cash", "credit_card", "debit_card", "check", "other"]


class PaymentDialog(QDialog):
    """Modal dialog for recording a payment against an invoice."""

    def __init__(self, invoice_id: int, remaining_balance: float, parent=None):
        """
        Args:
            remaining_balance: The current amount owed, used as the
                default payment amount (the common "paying it off"
                case).
        """
        super().__init__(parent)
        self.invoice_id = invoice_id
        self.saved_payment: dict | None = None

        self.setWindowTitle("Record Payment")
        self.setMinimumWidth(layout.DIALOG_WIDTH)

        self._build_ui()
        self.amount_input.setValue(max(remaining_balance, 0.01))

    def _build_ui(self):
        """Builds the Amount and Method fields."""
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
        )
        outer_layout.setSpacing(layout.SPACE_SM)

        self.amount_input = QDoubleSpinBox()
        self.amount_input.setPrefix("$")
        self.amount_input.setDecimals(2)
        self.amount_input.setMinimum(0.01)
        self.amount_input.setMaximum(999999.99)

        self.method_combo = QComboBox()
        for method in PAYMENT_METHODS:
            self.method_combo.addItem(method.replace("_", " ").title(), userData=method)

        self.error_label = QLabel("")
        self.error_label.setObjectName("subtitle")
        self.error_label.setStyleSheet("color: #DC2626;")
        self.error_label.setWordWrap(True)
        self.error_label.hide()

        self.save_button = QPushButton("Record Payment")
        self.save_button.setFixedHeight(layout.BUTTON_HEIGHT)
        self.save_button.clicked.connect(self._attempt_save)

        cancel_button = QPushButton("Cancel")
        cancel_button.setObjectName("secondary")
        cancel_button.setFixedHeight(layout.BUTTON_HEIGHT)
        cancel_button.clicked.connect(self.reject)

        for label_text, widget in [
            ("Amount", self.amount_input),
            ("Method", self.method_combo),
        ]:
            field_label = QLabel(label_text)
            field_label.setObjectName("subtitle")
            outer_layout.addWidget(field_label)
            outer_layout.addWidget(widget)

        outer_layout.addWidget(self.error_label)
        outer_layout.addSpacing(layout.SPACE_SM)
        outer_layout.addWidget(self.save_button)
        outer_layout.addWidget(cancel_button)

        self.setLayout(outer_layout)

    def _attempt_save(self):
        """Validates and records the payment synchronously -- a small, infrequent action."""
        self.save_button.setEnabled(False)
        self.save_button.setText("Recording...")
        self.error_label.hide()

        try:
            self.saved_payment = api_client.create_payment(
                self.invoice_id, f"{self.amount_input.value():.2f}", self.method_combo.currentData(),
            )
        except ApiError as e:
            self.save_button.setEnabled(True)
            self.save_button.setText("Record Payment")
            self.error_label.setText(str(e))
            self.error_label.show()
            return

        self.accept()
