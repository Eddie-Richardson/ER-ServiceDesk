# ER-ServiceDesk/desktop/optional_date_edit.py

"""
A date-picker widget for genuinely optional date fields.

Plain QDateEdit always shows some date -- there's no built-in way to
represent "not set." This wraps one with an explicit Clear button so an
optional field (Asset purchase date, warranty expiration, etc.) can
have a real calendar-popup picker instead of free text, while still
supporting a clean "nothing entered" state.
"""

from PySide6.QtCore import QDate
from PySide6.QtWidgets import QDateEdit, QHBoxLayout, QPushButton, QWidget


class OptionalDateEdit(QWidget):
    """A QDateEdit (calendar popup, so an invalid date like Feb 30 can't be entered) paired with a Clear button for the "not set" case."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self._date_edit = QDateEdit()
        self._date_edit.setCalendarPopup(True)
        self._date_edit.setDisplayFormat("MM/dd/yyyy")
        self._date_edit.setDate(QDate.currentDate())
        # Qt's calendar popup has a genuinely tiny built-in year editor
        # by default (a QSpinBox around 52x17px) that clips the number
        # -- this widens/heightens it via a stylesheet on the calendar
        # itself, not the QDateEdit field, since the popup is a
        # separate widget the field's own stylesheet doesn't cascade to.
        self._date_edit.calendarWidget().setStyleSheet(
            "QSpinBox { min-height: 28px; min-width: 70px; font-size: 13px; }"
        )
        # Starts cleared -- see is_set's docstring for why a separate
        # flag is needed rather than inferring this from the date value.
        self._is_set = False
        self._update_display()

        clear_button = QPushButton("Clear")
        clear_button.setObjectName("secondary")
        clear_button.clicked.connect(self.clear)

        self._date_edit.dateChanged.connect(self._on_date_changed)

        outer_layout = QHBoxLayout()
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(self._date_edit, stretch=1)
        outer_layout.addWidget(clear_button)
        self.setLayout(outer_layout)

    def date_string(self) -> str | None:
        """Returns the picked date as "YYYY-MM-DD" (the backend's expected format), or None if cleared/never set."""
        if not self._is_set:
            return None
        return self._date_edit.date().toString("yyyy-MM-dd")

    def set_date_string(self, value: str | None):
        """Prefills from a backend value, e.g. when editing an existing record. None (or an unparseable value) leaves it cleared."""
        if not value:
            self.clear()
            return

        date = QDate.fromString(value, "yyyy-MM-dd")
        if not date.isValid():
            self.clear()
            return

        self._date_edit.setDate(date)
        self._is_set = True
        self._update_display()

    def clear(self):
        """Resets to the "not set" state."""
        self._is_set = False
        self._update_display()

    def _on_date_changed(self):
        """Picking a date via the calendar popup (or typing into the field) counts as setting it."""
        self._is_set = True
        self._update_display()

    def _update_display(self):
        """
        Dims the date field's text while unset, so it's visually clear
        this is "not set" rather than a real date that happens to be
        today -- QDateEdit itself has no concept of an empty state to
        rely on for this.
        """
        self._date_edit.setStyleSheet("color: gray;" if not self._is_set else "")
