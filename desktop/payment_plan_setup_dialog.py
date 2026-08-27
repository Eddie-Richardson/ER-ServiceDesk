# ER-ServiceDesk/desktop/payment_plan_setup_dialog.py

"""
Dialog for setting up a new payment plan on an invoice -- enter a
per-installment amount and pick a frequency; the number of
installments and their due dates are worked out from there, not
entered directly.
"""

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDoubleSpinBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from desktop import api_client, layout
from desktop.api_client import ApiError
from desktop.base_dialog import AppDialog

FREQUENCIES = ["weekly", "biweekly", "monthly"]


class PaymentPlanSetupDialog(AppDialog):
    """Modal dialog for setting up a new payment plan."""

    def __init__(self, invoice_id: int, remaining_balance: float, parent=None):
        """
        Args:
            remaining_balance: The current amount owed, shown for
                context so the amount entered here makes sense against
                the total.
        """
        super().__init__(parent)
        self.invoice_id = invoice_id
        self.remaining_balance = remaining_balance
        self.saved_plan: dict | None = None

        self.setWindowTitle("Set Up Payment Plan")
        self.setMinimumWidth(layout.DIALOG_WIDTH)

        self._build_ui()

    def _build_ui(self):
        """Builds the balance reminder, Installment Amount, Frequency, and Start Date fields."""
        content = QWidget()
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
        )
        outer_layout.setSpacing(layout.SPACE_SM)

        balance_label = QLabel(f"Remaining balance: ${self.remaining_balance:.2f}")
        balance_label.setObjectName("subtitle")
        outer_layout.addWidget(balance_label)

        self.amount_input = QDoubleSpinBox()
        self.amount_input.setPrefix("$")
        self.amount_input.setDecimals(2)
        self.amount_input.setMinimum(0.01)
        self.amount_input.setMaximum(999999.99)
        self.amount_input.setValue(min(20.00, self.remaining_balance))

        self.frequency_combo = QComboBox()
        for freq in FREQUENCIES:
            self.frequency_combo.addItem(freq.capitalize(), userData=freq)

        self.start_date_input = QDateEdit()
        self.start_date_input.setCalendarPopup(True)
        self.start_date_input.setDate(QDate.currentDate())

        self.error_label = QLabel("")
        self.error_label.setObjectName("subtitle")
        self.error_label.setStyleSheet("color: #DC2626;")
        self.error_label.setWordWrap(True)
        self.error_label.hide()

        self.save_button = QPushButton("Create Plan")
        self.save_button.setFixedHeight(layout.BUTTON_HEIGHT)
        self.save_button.clicked.connect(self._attempt_save)

        cancel_button = QPushButton("Cancel")
        cancel_button.setObjectName("secondary")
        cancel_button.setFixedHeight(layout.BUTTON_HEIGHT)
        cancel_button.clicked.connect(self.reject)

        for label_text, widget in [
            ("Amount per Installment", self.amount_input),
            ("Frequency", self.frequency_combo),
            ("Start Date", self.start_date_input),
        ]:
            field_label = QLabel(label_text)
            field_label.setObjectName("subtitle")
            outer_layout.addWidget(field_label)
            outer_layout.addWidget(widget)

        outer_layout.addWidget(self.error_label)
        outer_layout.addSpacing(layout.SPACE_SM)
        outer_layout.addWidget(self.save_button)
        outer_layout.addWidget(cancel_button)

        content.setLayout(outer_layout)
        self.set_scrollable_content(content)

    def _attempt_save(self):
        """Validates and creates the plan synchronously -- a small, infrequent action."""
        self.save_button.setEnabled(False)
        self.save_button.setText("Creating...")
        self.error_label.hide()

        start_date_str = self.start_date_input.date().toString("yyyy-MM-dd")

        try:
            self.saved_plan = api_client.create_payment_plan(
                self.invoice_id, f"{self.amount_input.value():.2f}",
                self.frequency_combo.currentData(), start_date_str,
            )
        except ApiError as e:
            self.save_button.setEnabled(True)
            self.save_button.setText("Create Plan")
            self.handle_api_error(e, on_other_error=self._show_error)
            return

        self.accept()
