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
from PySide6.QtWidgets import QComboBox, QDateEdit, QHBoxLayout, QPushButton, QWidget

# Range of years shown in the year dropdown -- covers a genuinely old
# asset's purchase date on the low end, and a reasonable warranty
# expiration on the high end, without an unwieldy list.
_YEAR_RANGE_PAST = 50
_YEAR_RANGE_FUTURE = 10

_MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


class OptionalDateEdit(QWidget):
    """A QDateEdit (calendar popup, so an invalid date like Feb 30 can't be entered) paired with a Clear button for the "not set" case."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self._date_edit = QDateEdit()
        self._date_edit.setCalendarPopup(True)
        self._date_edit.setDisplayFormat("MM/dd/yyyy")
        self._date_edit.setDate(QDate.currentDate())
        self._build_calendar_nav_bar()
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

    def _build_calendar_nav_bar(self):
        """
        Replaces the calendar popup's own built-in navigation bar with
        a real month dropdown and year dropdown -- Qt's default year
        control is a genuinely tiny spinbox (confirmed too small to
        read on real hardware) that a stylesheet couldn't reliably fix.
        Uses QCalendarWidget's own documented public API
        (setNavigationBarVisible, setCurrentPage, currentPageChanged)
        rather than reaching into its internal widget structure.
        """
        calendar = self._date_edit.calendarWidget()
        calendar.setNavigationBarVisible(False)

        current_year = QDate.currentDate().year()

        prev_button = QPushButton("<")
        prev_button.setFixedWidth(28)
        prev_button.clicked.connect(calendar.showPreviousMonth)

        self._month_combo = QComboBox()
        for index, name in enumerate(_MONTH_NAMES):
            self._month_combo.addItem(name, userData=index + 1)

        self._year_combo = QComboBox()
        for year in range(current_year + _YEAR_RANGE_FUTURE, current_year - _YEAR_RANGE_PAST - 1, -1):
            self._year_combo.addItem(str(year), userData=year)

        next_button = QPushButton(">")
        next_button.setFixedWidth(28)
        next_button.clicked.connect(calendar.showNextMonth)

        self._month_combo.currentIndexChanged.connect(self._on_nav_combo_changed)
        self._year_combo.currentIndexChanged.connect(self._on_nav_combo_changed)
        calendar.currentPageChanged.connect(self._sync_nav_combos_to_calendar)

        nav_row = QHBoxLayout()
        nav_row.addWidget(prev_button)
        nav_row.addWidget(self._month_combo, stretch=1)
        nav_row.addWidget(self._year_combo)
        nav_row.addWidget(next_button)

        # QCalendarWidget lays itself out with a real QVBoxLayout of
        # its own -- inserting this custom row at the very top puts it
        # exactly where the now-hidden built-in nav bar used to be.
        calendar.layout().insertLayout(0, nav_row)

        self._sync_nav_combos_to_calendar(calendar.yearShown(), calendar.monthShown())

    def _on_nav_combo_changed(self):
        """Navigates the calendar to whatever month/year is now selected in the dropdowns."""
        calendar = self._date_edit.calendarWidget()
        calendar.setCurrentPage(self._year_combo.currentData(), self._month_combo.currentData())

    def _sync_nav_combos_to_calendar(self, year: int, month: int):
        """
        Keeps the dropdowns showing whatever month/year the calendar is
        actually on -- needed because the Prev/Next buttons (and
        clicking a date near a month boundary) change the calendar's
        page directly, bypassing the dropdowns entirely.
        """
        month_index = self._month_combo.findData(month)
        if month_index >= 0:
            self._month_combo.setCurrentIndex(month_index)

        year_index = self._year_combo.findData(year)
        if year_index >= 0:
            self._year_combo.setCurrentIndex(year_index)

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
