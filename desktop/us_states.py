# ER-ServiceDesk/desktop/us_states.py

"""
The fixed list of US states (plus DC and the inhabited territories) for
the Customer address State dropdown -- a small, stable, well-known
real-world vocabulary, same reasoning as Asset's Status/Condition
fields (see asset_form_dialog.py) for using a fixed list instead of
free text: it rules out typos/inconsistent entries ("TX" vs "Texas" vs
"Texs") that would otherwise silently fragment the data for no reason.

US-focused deliberately, matching the rest of the app (billing is
already USD-only) -- true international address support would be a
much larger, separate feature (currency, tax rules, and address format
conventions all vary by country), not something worth half-preparing
for here by making this free text "just in case."
"""

US_STATES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA",
    "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY",
    "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX",
    "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "AS", "GU", "MP", "PR", "VI",
]
