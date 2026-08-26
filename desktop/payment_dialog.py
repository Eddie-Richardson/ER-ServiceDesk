# ER-ServiceDesk/desktop/payment_dialog.py

"""
Dialog for recording a payment against an invoice.

If the invoice has an active payment plan, the payment applies against
its next unpaid installment (see next_unpaid_installment_id) instead of
being recorded standalone. If there's no plan yet and the entered
amount doesn't cover the full balance, offers setting one up for the
real, full balance before recording anything -- see
PaymentPlanSetupDialog.
"""

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from desktop import api_client, layout
from desktop.api_client import ApiError
from desktop.payment_plan_setup_dialog import PaymentPlanSetupDialog

PAYMENT_METHODS = ["cash", "credit_card", "debit_card", "check", "other"]


class PaymentDialog(QDialog):
    """Modal dialog for recording a payment against an invoice."""

    def __init__(self, invoice_id: int, remaining_balance: float, next_unpaid_installment_id: int | None = None, parent=None):
        """
        Args:
            remaining_balance: The current amount owed, used as the
                default payment amount (the common "paying it off"
                case).
            next_unpaid_installment_id: If this invoice has an active
                payment plan, the id of its next unpaid installment
                (lowest sequence_number with no payment_id yet) --
                the payment applies against the plan itself (and its
                overpayment/redistribution rules) rather than being
                recorded as a standalone payment. None if there's no
                active plan.
        """
        super().__init__(parent)
        self.invoice_id = invoice_id
        self.next_unpaid_installment_id = next_unpaid_installment_id
        self.remaining_balance = remaining_balance
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

        amount = self.amount_input.value()

        # No active plan, and this payment wouldn't cover the full
        # balance -- offer to set one up for the full, real remaining
        # balance before recording anything, so the plan's own
        # installment schedule reflects the actual balance rather than
        # something already reduced by this payment.
        if self.next_unpaid_installment_id is None and amount < self.remaining_balance:
            confirmed = QMessageBox.question(
                self,
                "Set Up Payment Plan?",
                f"This payment doesn't cover the full ${self.remaining_balance:.2f} balance. "
                f"Set up a payment plan for the full balance, then apply this payment to it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if confirmed == QMessageBox.StandardButton.Yes:
                plan_dialog = PaymentPlanSetupDialog(self.invoice_id, self.remaining_balance, parent=self)
                if not plan_dialog.exec():
                    # Backed out of setting up a plan -- re-enable the
                    # form so they can decide again (a different
                    # amount, a standalone payment, or cancel outright)
                    # rather than silently falling through to a
                    # standalone payment they didn't actually choose.
                    self.save_button.setEnabled(True)
                    self.save_button.setText("Record Payment")
                    return

                first_installment = min(plan_dialog.saved_plan["installments"], key=lambda i: i["sequence_number"])
                self.next_unpaid_installment_id = first_installment["id"]

        try:
            if self.next_unpaid_installment_id is not None:
                self.saved_payment = api_client.record_installment_payment(
                    self.next_unpaid_installment_id, f"{amount:.2f}", self.method_combo.currentData(),
                )
            else:
                self.saved_payment = api_client.create_payment(
                    self.invoice_id, f"{amount:.2f}", self.method_combo.currentData(),
                )
        except ApiError as e:
            self.save_button.setEnabled(True)
            self.save_button.setText("Record Payment")
            self.error_label.setText(str(e))
            self.error_label.show()
            return

        self.accept()
