"""Deliberately bounded actions: no guest-supplied service data or targets."""

DOMAIN = "guest_access"
ALLOWED_ACTIONS = {
    "lock": ("open", "lock", "unlock"),
    "cover": ("open_cover", "close_cover", "stop_cover", "set_cover_position"),
    "button": ("press",),
    "input_button": ("press",),
    "light": ("turn_on", "turn_off", "set_brightness"),
    "switch": ("turn_on", "turn_off"),
    "fan": ("turn_on", "turn_off"),
}
ACTION_NAMES = {
    "set_brightness": "Set brightness",
    "set_cover_position": "Set position",
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

VALUE_ACTIONS = {"set_brightness", "set_cover_position"}
DEVICE_DOMAINS = {"light", "cover", "switch", "fan"}
