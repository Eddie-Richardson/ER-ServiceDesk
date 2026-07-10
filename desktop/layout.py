# ER-ServiceDesk/desktop/layout.py
# Shared layout constants for the desktop app.
#
# Centralizes spacing, margins, and common sizing so every window follows
# the same visual rhythm instead of each one guessing its own numbers.
# Pair with theme.py, which handles color/typography -- this handles space.

# ---------------------------------------------------------------------------
# Spacing scale (px)
# ---------------------------------------------------------------------------
# A small multiple-of-4 scale keeps things visually consistent. Use the
# smallest value that fits -- reach for XL only for separating major
# sections, not routine widget spacing.
SPACE_XS = 4
SPACE_SM = 8
SPACE_MD = 16
SPACE_LG = 24
SPACE_XL = 32

# ---------------------------------------------------------------------------
# Window margins
# ---------------------------------------------------------------------------
# Standard outer margin for top-level window content. Card panels use a
# smaller inner margin since they're already visually separated by their
# border/background (see theme.py's #card style).
WINDOW_MARGIN = SPACE_LG
CARD_PADDING = SPACE_MD

# ---------------------------------------------------------------------------
# Common widths
# ---------------------------------------------------------------------------
SIDEBAR_WIDTH = 220
FORM_FIELD_WIDTH = 320
DIALOG_WIDTH = 420

# ---------------------------------------------------------------------------
# Component heights
# ---------------------------------------------------------------------------
INPUT_HEIGHT = 36
BUTTON_HEIGHT = 36
NAV_BUTTON_HEIGHT = 40
