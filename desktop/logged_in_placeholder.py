# ER-ServiceDesk/desktop/logged_in_placeholder.py
# Placeholder window shown after a successful login.
#
# Confirms the full flow works end to end (startup -> login -> authenticated
# session) before the real Dashboard window is built as its own task. Shows
# that a token was actually received, without displaying it.

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from desktop import layout, session


class LoggedInPlaceholder(QWidget):
    """Placeholder window shown once login succeeds."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ER-ServiceDesk - Dashboard")
        self.setFixedSize(layout.DIALOG_WIDTH, 200)

        card = QWidget()
        card.setObjectName("card")

        title = QLabel("You're logged in.")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        status = "Session active." if session.is_logged_in() else "No session found."
        subtitle = QLabel(f"{status}\n\n(Dashboard goes here.)")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)

        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(
            layout.CARD_PADDING, layout.CARD_PADDING,
            layout.CARD_PADDING, layout.CARD_PADDING,
        )
        card_layout.setSpacing(layout.SPACE_MD)
        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card.setLayout(card_layout)

        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
        )
        outer_layout.addWidget(card)
        self.setLayout(outer_layout)
