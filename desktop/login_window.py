# ER-ServiceDesk/desktop/login_window.py
# Placeholder Login window.
#
# Still a placeholder for the actual login form (email/password fields,
# calling POST /auth/login, storing the JWT) -- that's built separately.
# What this DOES demonstrate now is the real visual pattern every window
# will follow: a centered card panel, title/subtitle text roles from
# theme.py, and layout.py's spacing constants instead of hand-picked
# numbers. It also includes a live theme toggle so the light/dark system
# is testable end to end before more windows are built on top of it.

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from desktop import layout
from desktop.settings_manager import get_saved_theme, save_theme
from desktop.theme import get_stylesheet


class LoginWindow(QWidget):
    """Placeholder window shown once the backend is confirmed healthy."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ER-ServiceDesk - Login")
        self.setFixedSize(layout.DIALOG_WIDTH, 260)

        # --- Card panel -----------------------------------------------
        # Every window with a focused, single-purpose form (login, a
        # dialog, a settings pane) should sit inside a #card panel rather
        # than floating directly on the window background. It's the
        # visual language the whole app will share.
        card = QWidget()
        card.setObjectName("card")

        title = QLabel("ER-ServiceDesk")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Backend is ready. (Login form goes here.)")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)

        self.theme_toggle_button = QPushButton()
        self.theme_toggle_button.setObjectName("secondary")
        self.theme_toggle_button.clicked.connect(self._toggle_theme)
        self._refresh_toggle_label()

        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(
            layout.CARD_PADDING, layout.CARD_PADDING,
            layout.CARD_PADDING, layout.CARD_PADDING,
        )
        card_layout.setSpacing(layout.SPACE_MD)
        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addSpacing(layout.SPACE_SM)
        card_layout.addWidget(self.theme_toggle_button)
        card.setLayout(card_layout)

        # --- Outer window layout ---------------------------------------
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
        )
        outer_layout.addWidget(card)
        self.setLayout(outer_layout)

    def _current_theme(self) -> str:
        return get_saved_theme()

    def _refresh_toggle_label(self):
        current = self._current_theme()
        next_theme = "dark" if current == "light" else "light"
        self.theme_toggle_button.setText(f"Switch to {next_theme} theme")

    def _toggle_theme(self):
        """
        Flips the theme, persists the choice for this machine, and
        re-applies the stylesheet immediately so the change is visible
        without restarting the app.
        """
        next_theme = "dark" if self._current_theme() == "light" else "light"
        save_theme(next_theme)

        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(get_stylesheet(next_theme))

        self._refresh_toggle_label()
