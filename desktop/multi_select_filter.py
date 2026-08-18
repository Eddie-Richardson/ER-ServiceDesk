# ER-ServiceDesk/desktop/multi_select_filter.py

"""
Excel-style multi-select filter button.

A button that opens a checklist popup letting the user select zero or
more values to filter a table column by -- the same pattern as clicking
a column header's filter icon in Excel. Selecting nothing means "no
filter" (show everything); selecting one or more values means "show
rows matching any of these."

This is a drop-in upgrade over a single-select QComboBox filter: same
underlying data (id/name pairs), same idea of "what should this column
be filtered to." Only the widget and the matching logic (equality check
vs. set-membership check) change.
"""

from PySide6.QtCore import QPoint, Signal
from PySide6.QtWidgets import QCheckBox, QMenu, QPushButton, QWidgetAction


class MultiSelectFilterButton(QPushButton):
    """
    A button that opens a checklist popup for selecting multiple filter
    values. The button's label shows how many values are currently
    selected, e.g. "Status (2)".

    Signals:
        selection_changed: Emitted whenever the popup closes with a
            possibly-different set of checked values.
    """

    selection_changed = Signal()

    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self._label = label
        self._options: list[tuple[object, str]] = []
        self._checkboxes: dict[object, QCheckBox] = {}
        self.clicked.connect(self._show_popup)
        self._update_label()

    def set_options(self, options: list[tuple[object, str]]):
        """
        Replaces the filterable options. Any previously checked values
        that still exist in the new options list stay checked; this
        matters because reference data can reload (e.g. after a
        Refresh) without the user's filter selection being lost.

        Args:
            options: List of (id_value, display_name) tuples, e.g.
                [(1, "Open"), (2, "Closed")]. id_value is what gets
                compared against each row's field when filtering.
        """
        previously_checked = self.selected_ids()
        self._options = options
        self._checkboxes = {}
        # Checkbox widgets themselves are rebuilt fresh each popup open
        # (see _show_popup) -- this method only needs to remember which
        # ids should start checked next time the popup opens.
        self._pending_checked = previously_checked & {opt[0] for opt in options}
        self._update_label()

    def set_checked_ids(self, ids: set):
        """
        Programmatically sets which ids are checked, e.g. to apply a
        default filter or one requested by another window (such as the
        Dashboard's status cards).

        Args:
            ids: The set of id_values that should start checked.
        """
        self._checkboxes = {}
        self._pending_checked = set(ids) & {opt[0] for opt in self._options}
        self._update_label()

    def selected_ids(self) -> set:
        """
        Returns:
            The set of currently checked id_values. An empty set means
            "no filter" -- every row should be shown.
        """
        if not self._checkboxes:
            return getattr(self, "_pending_checked", set())
        return {id_val for id_val, cb in self._checkboxes.items() if cb.isChecked()}

    def _show_popup(self):
        """Builds and shows the checklist popup below the button."""
        menu = QMenu(self)
        currently_checked = self.selected_ids()
        self._checkboxes = {}

        select_all_button = QPushButton("Select All")
        select_all_button.setFlat(True)
        select_all_button.clicked.connect(lambda: self._set_all_checked(True))
        select_all_action = QWidgetAction(menu)
        select_all_action.setDefaultWidget(select_all_button)
        menu.addAction(select_all_action)

        clear_button = QPushButton("Clear")
        clear_button.setFlat(True)
        clear_button.clicked.connect(lambda: self._set_all_checked(False))
        clear_action = QWidgetAction(menu)
        clear_action.setDefaultWidget(clear_button)
        menu.addAction(clear_action)

        menu.addSeparator()

        for id_val, name in self._options:
            checkbox = QCheckBox(name)
            checkbox.setChecked(id_val in currently_checked)
            widget_action = QWidgetAction(menu)
            widget_action.setDefaultWidget(checkbox)
            menu.addAction(widget_action)
            self._checkboxes[id_val] = checkbox

        menu.aboutToHide.connect(self._on_popup_closed)
        menu.exec(self.mapToGlobal(QPoint(0, self.height())))

    def _set_all_checked(self, checked: bool):
        for checkbox in self._checkboxes.values():
            checkbox.setChecked(checked)

    def _on_popup_closed(self):
        """Updates the button label and notifies listeners once the popup closes."""
        self._update_label()
        self.selection_changed.emit()

    def _update_label(self):
        """Sets the button text to reflect how many values are currently selected."""
        count = len(self.selected_ids())
        if count == 0:
            self.setText(f"{self._label} \u25be")
        else:
            self.setText(f"{self._label} ({count}) \u25be")
