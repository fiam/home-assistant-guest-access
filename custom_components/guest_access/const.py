"""Deliberately bounded actions: no guest-supplied service data or targets."""

DOMAIN = "guest_access"
ALLOWED_ACTIONS = {
    "lock": ("open", "lock", "unlock"),
    "cover": ("open_cover", "close_cover", "stop_cover"),
    "button": ("press",),
    "input_button": ("press",),
    "light": ("turn_on", "turn_off"),
    "switch": ("turn_on", "turn_off"),
    "fan": ("turn_on", "turn_off"),
}
ACTION_NAMES = {
    "open": "Open door",
    "lock": "Lock",
    "unlock": "Unlock",
    "open_cover": "Open",
    "close_cover": "Close",
    "stop_cover": "Stop",
    "press": "Press",
    "turn_on": "Turn on",
    "turn_off": "Turn off",
}
