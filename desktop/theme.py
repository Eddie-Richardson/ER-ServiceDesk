# ER-ServiceDesk/desktop/theme.py

"""
Light and dark QSS stylesheets for the desktop app.

QSS is Qt's CSS-like styling language. Applying one of these at the
QApplication level (app.setStyleSheet(...)) themes every window in the
app at once, so individual windows don't need their own styling code.

Palette based on a design direction explored in Claude Design: a
near-black/cyan dark theme with a light-mode counterpart built to match
(Claude Design only produced the dark variant; the light palette below
follows the same visual logic -- same accent hue family, contrast
adapted for a light background -- rather than being a separate design).

Consolas is used for "data" text (ids, timestamps, counts) elsewhere in
the app -- it's bundled with Windows by default (via Office/.NET since
Vista), so no font installation step is needed. That distinction is
applied per-widget in each window's own code (see MONO_FONT_FAMILY
below), not something a global stylesheet alone can express, since
table cells are plain QTableWidgetItem text rather than styleable
widgets.

Accent color and both palettes are defined here as the single source of
truth -- change a color once, it updates everywhere.
"""

# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------
BODY_FONT_FAMILY = "Segoe UI"
MONO_FONT_FAMILY = "Consolas"

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
LIGHT = {
    "bg": "#F4F6F8",
    "surface": "#FFFFFF",
    "sidebar": "#FFFFFF",
    "border": "#DDE3EA",
    "border_subtle": "#EAEEF2",
    "text": "#12161D",
    "text_secondary": "#4A5568",
    "text_muted": "#6B7688",
    "text_faint": "#94A0AF",
    "accent": "#0891B2",
    "accent_hover": "#0E7490",
    "accent_pressed": "#155E75",
    "accent_text": "#FFFFFF",
    "success": "#16A34A",
    "danger": "#DC2626",
    "danger_bg": "#FEF2F2",
    "danger_border": "#FECACA",
}

DARK = {
    "bg": "#0A0D12",
    "surface": "#12161D",
    "sidebar": "#0D1117",
    "border": "#232A36",
    "border_subtle": "#1F2630",
    "text": "#F3F5F8",
    "text_secondary": "#C7CEDA",
    "text_muted": "#8993A4",
    "text_faint": "#5C6779",
    "accent": "#22D3EE",
    "accent_hover": "#67E8F9",
    "accent_pressed": "#0891B2",
    "accent_text": "#05171B",
    "success": "#4ADE80",
    "danger": "#F87171",
    "danger_bg": "#2A1518",
    "danger_border": "#7F1D1D",
}


def _build_stylesheet(p: dict) -> str:
    """Builds the full QSS string from a palette dict."""
    return f"""
        /* ---- Base ---- */
        QWidget {{
            background-color: {p['bg']};
            color: {p['text']};
            font-family: "{BODY_FONT_FAMILY}", sans-serif;
            font-size: 10.5pt;
        }}

        /* ---- Cards / panels ---- */
        QWidget#card {{
            background-color: {p['surface']};
            border: 1px solid {p['border']};
            border-radius: 8px;
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
        QLabel#dataMono {{
            font-family: "{MONO_FONT_FAMILY}", "Courier New", monospace;
            color: {p['text_faint']};
            font-size: 9.5pt;
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
        QPushButton#danger {{
            background-color: transparent;
            color: {p['danger']};
            border: 1px solid {p['danger_border']};
        }}
        QPushButton#danger:hover {{
            background-color: {p['danger_bg']};
        }}

        /* ---- Inputs ---- */
        QLineEdit, QTextEdit, QComboBox, QSpinBox {{
            background-color: {p['surface']};
            border: 1px solid {p['border']};
            border-radius: 6px;
            padding: 8px 10px;
            selection-background-color: {p['accent']};
        }}
        QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
            border: 1px solid {p['accent']};
        }}

        /* ---- Tables ---- */
        QTableWidget {{
            background-color: {p['surface']};
            border: 1px solid {p['border']};
            border-radius: 8px;
            gridline-color: {p['border_subtle']};
        }}
        QHeaderView::section {{
            background-color: {p['surface']};
            color: {p['text_muted']};
            border: none;
            border-bottom: 1px solid {p['border']};
            padding: 6px 8px;
            font-weight: 600;
            font-size: 9pt;
        }}
        QTableWidget::item {{
            padding: 4px;
            border-bottom: 1px solid {p['border_subtle']};
        }}
        QTableWidget::item:selected {{
            background-color: {p['accent']};
            color: {p['accent_text']};
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
            background-color: {p['sidebar']};
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


# ---------------------------------------------------------------------------
# Status / Priority text colors
# ---------------------------------------------------------------------------
# Used to color-code Status and Priority text in table cells (bold +
# colored, not a pill shape -- see the module docstring's note on why
# literal pill badges are a separate, deliberately-tested follow-on
# rather than built alongside this). Colors are theme-aware since a
# shade that reads well on near-black can wash out on white and vice
# versa. Status names are admin-editable via Settings, so an unmapped
# name (a custom status someone adds later) falls back to text_muted
# rather than being left uncolored or crashing.

_STATUS_COLORS_DARK = {
    "Open": "#FBBF24",
    "In Progress": "#22D3EE",
    "Waiting on Parts": "#A78BFA",
    "Waiting on Customer": "#FB923C",
    "Resolved": "#4ADE80",
    "Closed": "#8993A4",
}
_STATUS_COLORS_LIGHT = {
    "Open": "#B45309",
    "In Progress": "#0891B2",
    "Waiting on Parts": "#7C3AED",
    "Waiting on Customer": "#C2410C",
    "Resolved": "#16A34A",
    "Closed": "#6B7688",
}

_PRIORITY_COLORS_DARK = {
    "Low": "#8993A4",
    "Medium": "#FBBF24",
    "High": "#FB923C",
    "Urgent": "#F87171",
}
_PRIORITY_COLORS_LIGHT = {
    "Low": "#6B7688",
    "Medium": "#B45309",
    "High": "#C2410C",
    "Urgent": "#DC2626",
}

# Asset.status is a different fixed vocabulary from Ticket status
# (Active/In Repair/Retired), so it gets its own mapping rather than
# sharing _STATUS_COLORS_* above.
_ASSET_STATUS_COLORS_DARK = {
    "Active": "#4ADE80",
    "In Repair": "#FBBF24",
    "Retired": "#8993A4",
}
_ASSET_STATUS_COLORS_LIGHT = {
    "Active": "#16A34A",
    "In Repair": "#B45309",
    "Retired": "#6B7688",
}


def get_status_color(status_name: str, theme_name: str) -> str:
    """
    Args:
        status_name: The status's display name, e.g. "Open".
        theme_name: "light" or "dark".

    Returns:
        A hex color string appropriate for that status in that theme.
        Unmapped status names (e.g. a custom one added via Settings)
        fall back to the theme's muted text color.
    """
    colors = _STATUS_COLORS_DARK if theme_name == "dark" else _STATUS_COLORS_LIGHT
    fallback = DARK["text_muted"] if theme_name == "dark" else LIGHT["text_muted"]
    return colors.get(status_name, fallback)


def get_priority_color(priority_name: str, theme_name: str) -> str:
    """
    Args:
        priority_name: One of "Low", "Medium", "High", "Urgent".
        theme_name: "light" or "dark".

    Returns:
        A hex color string appropriate for that priority in that theme.
        Unmapped values fall back to the theme's muted text color.
    """
    colors = _PRIORITY_COLORS_DARK if theme_name == "dark" else _PRIORITY_COLORS_LIGHT
    fallback = DARK["text_muted"] if theme_name == "dark" else LIGHT["text_muted"]
    return colors.get(priority_name, fallback)


def get_asset_status_color(status_name: str, theme_name: str) -> str:
    """
    Args:
        status_name: One of "Active", "In Repair", "Retired".
        theme_name: "light" or "dark".

    Returns:
        A hex color string appropriate for that asset status in that
        theme. Unmapped values fall back to the theme's muted text color.
    """
    colors = _ASSET_STATUS_COLORS_DARK if theme_name == "dark" else _ASSET_STATUS_COLORS_LIGHT
    fallback = DARK["text_muted"] if theme_name == "dark" else LIGHT["text_muted"]
    return colors.get(status_name, fallback)
