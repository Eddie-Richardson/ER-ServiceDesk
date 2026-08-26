# ER-ServiceDesk/desktop/ticket_types_stages_tab.py

"""
Settings tab combining Ticket Types, Ticket Stages, and the
TicketTypeStage allow-list that pairs them -- these are genuinely one
interconnected system (a stage like "Burn-in Test" only makes sense
paired to a "Custom Build" type, not a plain "Repair"), kept in one
tab rather than split across three, so configuring a type's allowed
stages doesn't mean jumping between unrelated screens.

Types and Stages themselves reuse LookupTab as-is (same simple
name/description shape as every other lookup table in Settings); the
pairing section below them is the genuinely new piece -- select a
type, check which stages should be valid for it. Checking/unchecking
immediately creates or deletes the underlying TicketTypeStage record,
rather than needing a separate Save step.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from desktop import api_client, layout
from desktop.api_client import ApiError, list_ticket_stages, list_ticket_types
from desktop.lookup_tab import LookupTab


class TicketTypesStagesTab(QWidget):
    """Combined management for Ticket Types, Ticket Stages, and which stages are allowed for which type."""

    # Real floor so the two lookup boxes stay readable regardless of
    # how small the Settings window gets -- the whole tab is wrapped
    # in a scroll area below, so this doesn't force the window itself
    # to stay large; it just means this tab's content scrolls once the
    # window shrinks past what fits.
    _LOOKUP_TAB_MIN_HEIGHT = 240

    def __init__(self):
        """Builds the Types/Stages lists and the pairing section, then loads the pairing data."""
        super().__init__()
        self.all_types: list[dict] = []
        self.all_stages: list[dict] = []
        self.current_pairings: list[dict] = []

        self._build_ui()
        self._load_pairing_reference_data()

    def _build_ui(self):
        """Builds the two lookup lists (side by side, each with a real minimum height) and the pairing checklist below, all wrapped in one scroll area."""
        content = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
        )
        content_layout.setSpacing(layout.SPACE_MD)

        lists_row = QHBoxLayout()

        self.types_tab = LookupTab("Ticket Type", api_client.list_ticket_types, "/ticket_types/", "ticket_type")
        self.types_tab.setMinimumHeight(self._LOOKUP_TAB_MIN_HEIGHT)
        lists_row.addWidget(self.types_tab)

        self.stages_tab = LookupTab("Ticket Stage", api_client.list_ticket_stages, "/ticket_stages/", "ticket_stage")
        self.stages_tab.setMinimumHeight(self._LOOKUP_TAB_MIN_HEIGHT)
        lists_row.addWidget(self.stages_tab)

        content_layout.addLayout(lists_row)

        # Types/Stages are managed above via their own New/Edit/Delete
        # flows -- the pairing dropdown and checklist need to reflect
        # whatever's current there, so refresh whenever either list
        # actually changes, not just once at startup.
        self.types_tab.data_changed.connect(self._load_pairing_reference_data)
        self.stages_tab.data_changed.connect(self._load_pairing_reference_data)

        pairing_label = QLabel("Allowed Stages")
        pairing_label.setObjectName("subtitle")
        content_layout.addWidget(pairing_label)

        type_picker_row = QHBoxLayout()
        type_picker_row.addWidget(QLabel("Ticket Type:"))
        self.type_picker = QComboBox()
        self.type_picker.currentIndexChanged.connect(self._on_type_selected)
        type_picker_row.addWidget(self.type_picker)
        type_picker_row.addStretch()
        content_layout.addLayout(type_picker_row)

        self.status_label = QLabel("")
        self.status_label.setObjectName("subtitle")
        content_layout.addWidget(self.status_label)

        self.checkboxes_container = QWidget()
        self.checkboxes_layout = QVBoxLayout()
        self.checkboxes_layout.addStretch()
        self.checkboxes_container.setLayout(self.checkboxes_layout)
        content_layout.addWidget(self.checkboxes_container)

        content.setLayout(content_layout)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(content)

        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll_area)
        self.setLayout(outer_layout)

    # -----------------------------------------------------------------
    # Pairing section
    # -----------------------------------------------------------------
    def _load_pairing_reference_data(self):
        """Fetches every type and stage, refreshes the type picker, and re-renders the checklist for whichever type is currently selected."""
        previously_selected_id = self.type_picker.currentData()

        try:
            self.all_types = list_ticket_types()
            self.all_stages = list_ticket_stages()
        except ApiError as e:
            self.status_label.setText(f"Couldn't load types/stages: {e}")
            return

        self.type_picker.blockSignals(True)
        self.type_picker.clear()
        for t in self.all_types:
            self.type_picker.addItem(t["name"], userData=t["id"])
        restored_index = self.type_picker.findData(previously_selected_id)
        self.type_picker.setCurrentIndex(restored_index if restored_index >= 0 else 0)
        self.type_picker.blockSignals(False)

        self._render_checklist_for_selected_type()

    def _on_type_selected(self):
        """Re-renders the checklist whenever the selected type changes."""
        self._render_checklist_for_selected_type()

    def _render_checklist_for_selected_type(self):
        """Fetches the currently-selected type's allowed stages and builds a checkbox per known stage."""
        while self.checkboxes_layout.count() > 1:
            item = self.checkboxes_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        type_id = self.type_picker.currentData()
        if type_id is None:
            self.status_label.setText("No ticket types configured yet -- add one above first.")
            return

        try:
            self.current_pairings = api_client.list_stages_for_type(type_id)
        except ApiError as e:
            self.status_label.setText(f"Couldn't load allowed stages: {e}")
            return

        allowed_stage_ids = {p["stage_id"] for p in self.current_pairings}
        self.status_label.setText(
            f"{len(allowed_stage_ids)} of {len(self.all_stages)} stage(s) allowed for this type."
        )

        for stage in self.all_stages:
            checkbox = QCheckBox(stage["name"])
            checkbox.setChecked(stage["id"] in allowed_stage_ids)
            checkbox.stateChanged.connect(
                lambda state, s=stage: self._on_stage_checkbox_toggled(s, state)
            )
            self.checkboxes_layout.insertWidget(self.checkboxes_layout.count() - 1, checkbox)

    def _on_stage_checkbox_toggled(self, stage: dict, state: int):
        """
        Immediately creates or deletes the TicketTypeStage pairing to
        match the checkbox's new state -- no separate Save step.

        Args:
            state: The checkbox's new Qt.CheckState value.
        """
        type_id = self.type_picker.currentData()
        if type_id is None:
            return

        is_checked = state == Qt.CheckState.Checked.value

        if is_checked:
            try:
                api_client.create_ticket_type_stage(type_id, stage["id"])
            except ApiError as e:
                self.status_label.setText(f"Couldn't allow this stage: {e}")
                return
        else:
            existing = next(
                (p for p in self.current_pairings if p["stage_id"] == stage["id"]),
                None,
            )
            if existing:
                try:
                    api_client.delete_ticket_type_stage(existing["id"])
                except ApiError as e:
                    self.status_label.setText(f"Couldn't remove this stage: {e}")
                    return

        # Refresh from the server rather than guessing at the new
        # local state -- keeps this correct even if the request
        # partially failed or another session changed something.
        self._render_checklist_for_selected_type()
