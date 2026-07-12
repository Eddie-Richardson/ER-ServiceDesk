# ER-ServiceDesk/desktop/theme.py

"""
Light and dark QSS stylesheets for the desktop app.

QSS is Qt's CSS-like styling language. Applying one of these at the
QApplication level (app.setStyleSheet(...)) themes every window in the
app at once, so individual windows don't need their own styling code.

Accent color and both palettes are defined here as the single source of
truth -- change a color once, it updates everywhere.
"""

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
# A vibrant indigo accent -- reads as modern/SaaS rather than flat corporate
# blue, while still looking professional for a business tool.
ACCENT = "#4F46E5"
ACCENT_HOVER = "#4338CA"
ACCENT_PRESSED = "#3730A3"

LIGHT = {
    "bg": "#F7F7FA",
    "surface": "#FFFFFF",
    "border": "#E2E2E9",
    "text": "#1E1E2E",
    "text_muted": "#6B6B7B",
    "accent": ACCENT,
    "accent_hover": ACCENT_HOVER,
    "accent_pressed": ACCENT_PRESSED,
    "accent_text": "#FFFFFF",
}

DARK = {
    "bg": "#1A1A24",
    "surface": "#24242F",
    "border": "#33333F",
    "text": "#EDEDF2",
    "text_muted": "#9A9AAA",
    "accent": ACCENT,
    "accent_hover": "#6366F1",
    "accent_pressed": ACCENT_PRESSED,
    "accent_text": "#FFFFFF",
}


def _build_stylesheet(p: dict) -> str:
    """Builds the full QSS string from a palette dict."""
    return f"""
        /* ---- Base ---- */
        QWidget {{
            background-color: {p['bg']};
            color: {p['text']};
            font-family: "Segoe UI", sans-serif;
            font-size: 10.5pt;
        }}

        /* ---- Cards / panels ---- */
        QWidget#card {{
            background-color: {p['surface']};
            border: 1px solid {p['border']};
            border-radius: 10px;
        }}

        /* ---- Labels ---- */
        QLabel {{
            background: transparent;
        }}
        QLabel#title {{
            font-size: 16pt;
            font-weight: 600;
        }}
        QLabel#subtitle {{
            color: {p['text_muted']};
            font-size: 10pt;
        }}

        /* ---- Buttons ---- */
        QPushButton {{
            background-color: {p['accent']};
            color: {p['accent_text']};
            border: none;
            border-radius: 6px;
            padding: 8px 18px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            background-color: {p['accent_hover']};
        }}
        QPushButton:pressed {{
            background-color: {p['accent_pressed']};
        }}
        QPushButton:disabled {{
            background-color: {p['border']};
            color: {p['text_muted']};
        }}
        QPushButton#secondary {{
            background-color: transparent;
            color: {p['text']};
            border: 1px solid {p['border']};
        }}
        QPushButton#secondary:hover {{
            background-color: {p['surface']};
        }}

        /* ---- Inputs ---- */
        QLineEdit {{
            background-color: {p['surface']};
            border: 1px solid {p['border']};
            border-radius: 6px;
            padding: 8px 10px;
            selection-background-color: {p['accent']};
        }}
        QLineEdit:focus {{
            border: 1px solid {p['accent']};
        }}

        /* ---- Progress bar ---- */
        QProgressBar {{
            background-color: {p['border']};
            border: none;
            border-radius: 4px;
            height: 8px;
            text-align: center;
        }}
        QProgressBar::chunk {{
            background-color: {p['accent']};
            border-radius: 4px;
        }}

        /* ---- Sidebar navigation (used on the Dashboard) ---- */
        QWidget#sidebar {{
            background-color: {p['surface']};
            border-right: 1px solid {p['border']};
        }}
        QPushButton#navButton {{
            background-color: transparent;
            color: {p['text']};
            border: none;
            border-radius: 6px;
            text-align: left;
            padding: 10px 14px;
            font-weight: 500;
        }}
        QPushButton#navButton:hover {{
            background-color: {p['bg']};
        }}
        QPushButton#navButton:checked {{
            background-color: {p['accent']};
            color: {p['accent_text']};
        }}
    """


def get_stylesheet(theme_name: str) -> str:
    """
    Returns the full QSS stylesheet for the given theme.

    Args:
        theme_name: Either "light" or "dark". Falls back to "light" for
            any other value rather than raising, so a corrupted settings
            value can't crash the app on launch.
    """
    palette = DARK if theme_name == "dark" else LIGHT
    return _build_stylesheet(palette)
