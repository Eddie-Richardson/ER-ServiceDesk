# ER-ServiceDesk/desktop/installment_action_dialog.py

"""
Dialog for acting on a single payment plan installment -- record a
payment against it (using its planned amount, or a different amount
if the customer is paying more or less than scheduled), or push back
its due date.

These are two genuinely separate actions on the same installment, not
one combined form -- a tech typically does one or the other, not both
at once.
"""

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDoubleSpinBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from desktop import api_client, layout
from desktop.api_client import ApiError
from desktop.payment_dialog import PAYMENT_METHODS


class InstallmentActionDialog(QDialog):
    """Modal dialog for paying or extending a single installment."""

    def __init__(self, installment: dict, parent=None):
        super().__init__(parent)
        self.installment = installment
        self.action_taken = False

        self.setWindowTitle(f"Installment #{installment['sequence_number']}")
        self.setMinimumWidth(layout.DIALOG_WIDTH)

        self._build_ui()

    def _build_ui(self):
        """Builds the payment section and the date-extension section."""
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
        )
        outer_layout.setSpacing(layout.SPACE_SM)

        info_label = QLabel(f"Due {self.installment['due_date']} -- planned ${self.installment['planned_amount']}")
        info_label.setObjectName("subtitle")
        outer_layout.addWidget(info_label)

        self.error_label = QLabel("")
        self.error_label.setObjectName("subtitle")
        self.error_label.setStyleSheet("color: #DC2626;")
        self.error_label.setWordWrap(True)
        self.error_label.hide()

        payment_label = QLabel("Record Payment")
        payment_label.setObjectName("subtitle")
        outer_layout.addWidget(payment_label)

        self.amount_input = QDoubleSpinBox()
        self.amount_input.setPrefix("$")
        self.amount_input.setDecimals(2)
        self.amount_input.setMinimum(0.01)
        self.amount_input.setMaximum(999999.99)
        self.amount_input.setValue(float(self.installment["planned_amount"]))
        outer_layout.addWidget(self.amount_input)

        self.method_combo = QComboBox()
        for method in PAYMENT_METHODS:
            self.method_combo.addItem(method.replace("_", " ").title(), userData=method)
        outer_layout.addWidget(self.method_combo)

        self.pay_button = QPushButton("Record Payment")
        self.pay_button.setFixedHeight(layout.BUTTON_HEIGHT)
        self.pay_button.clicked.connect(self._attempt_pay)
        outer_layout.addWidget(self.pay_button)

        outer_layout.addSpacing(layout.SPACE_SM)

        extend_label = QLabel("Extend Due Date")
        extend_label.setObjectName("subtitle")
        outer_layout.addWidget(extend_label)

        self.new_date_input = QDateEdit()
        self.new_date_input.setCalendarPopup(True)
        current_due_date = QDate.fromString(self.installment["due_date"], "yyyy-MM-dd")
        self.new_date_input.setDate(current_due_date)
        outer_layout.addWidget(self.new_date_input)

        self.extend_button = QPushButton("Extend Date")
        self.extend_button.setObjectName("secondary")
        self.extend_button.setFixedHeight(layout.BUTTON_HEIGHT)
        self.extend_button.clicked.connect(self._attempt_extend)
        outer_layout.addWidget(self.extend_button)

        outer_layout.addWidget(self.error_label)
        outer_layout.addSpacing(layout.SPACE_SM)

        close_button = QPushButton("Close")
        close_button.setObjectName("secondary")
        close_button.clicked.connect(self.accept)
        outer_layout.addWidget(close_button)

        self.setLayout(outer_layout)

    def _attempt_pay(self):
        """
        Records a payment against this installment. Sends None (not
        the explicit value) when the entered amount matches the
        planned amount, since the backend treats None as "use the
        installment's own planned_amount" -- sending an explicit value
        only when it's genuinely different from what was scheduled.
        """
        self.pay_button.setEnabled(False)
        self.pay_button.setText("Recording...")
        self.error_label.hide()

        entered_amount = self.amount_input.value()
        planned_amount = float(self.installment["planned_amount"])
        amount_to_send = None if abs(entered_amount - planned_amount) < 0.005 else str(entered_amount)

        try:
            api_client.record_installment_payment(self.installment["id"], amount_to_send, self.method_combo.currentData())
        except ApiError as e:
            self.pay_button.setEnabled(True)
            self.pay_button.setText("Record Payment")
            self.error_label.setText(str(e))
            self.error_label.show()
            return

        self.action_taken = True
        self.accept()

    def _attempt_extend(self):
        """Pushes back this installment's due date."""
        self.extend_button.setEnabled(False)
        self.extend_button.setText("Extending...")
        self.error_label.hide()

        new_date_str = self.new_date_input.date().toString("yyyy-MM-dd")

        try:
            api_client.extend_installment_date(self.installment["id"], new_date_str)
        except ApiError as e:
            self.extend_button.setEnabled(True)
            self.extend_button.setText("Extend Date")
            self.error_label.setText(str(e))
            self.error_label.show()
            return

        self.action_taken = True
        self.accept()
