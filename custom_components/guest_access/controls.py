"""Supported controls and the small state snapshot exposed to a guest."""

import math

from homeassistant.components.cover import CoverEntityFeature
from homeassistant.components.light import brightness_supported

from .const import ALLOWED_ACTIONS, DEVICE_DOMAINS

COVER_FEATURES = {
    "open_cover": CoverEntityFeature.OPEN,
    "close_cover": CoverEntityFeature.CLOSE,
    "stop_cover": CoverEntityFeature.STOP,
    "set_cover_position": CoverEntityFeature.SET_POSITION,
}


def entity_available(hass, entity_id):
    state = hass.states.get(entity_id)
    if state is None or state.state == "unavailable":
        return False
    return state.state != "unknown" or state.domain in {"button", "input_button"}


def action_supported(hass, entity_id, action):
    state = hass.states.get(entity_id)
    if state is None or action not in ALLOWED_ACTIONS.get(state.domain, ()):
        return False
    service = "turn_on" if action == "set_brightness" else action
    if not hass.services.has_service(state.domain, service):
        return False
    features = state.attributes.get("supported_features", 0)
    if state.domain == "lock" and action == "open":
        return bool(features & 1)
    if state.domain == "cover":
        return bool(features & COVER_FEATURES[action])
    if action == "set_brightness":
        return brightness_supported(state.attributes.get("supported_color_modes"))
    return True


def device_state(hass, entity_id):
    state = hass.states.get(entity_id)
    if state is None or state.domain not in DEVICE_DOMAINS:
        return {}
    # Do not expose attributes, identifiers or device metadata wholesale.
    result = {
        "state": state.state
        if state.state
        in {
            "on",
            "off",
            "open",
            "closed",
            "opening",
            "closing",
        }
        else "unknown"
    }
    value = None
    if state.domain == "light":
        raw = state.attributes.get("brightness")
        if state.state == "off":
            value = 0
        elif isinstance(raw, (int, float)) and math.isfinite(raw) and 0 <= raw <= 255:
            value = round(raw * 100 / 255)
    elif state.domain == "cover":
        raw = state.attributes.get("current_position")
        if isinstance(raw, (int, float)) and math.isfinite(raw) and 0 <= raw <= 100:
            value = round(raw)
    if state.domain in {"light", "cover"}:
        result["value"] = value
    return result


async def dispatch_action(hass, entity_id, action, value=None):
    data = {"entity_id": entity_id}
    service = action
    if action == "set_brightness":
        service = "turn_on"
        data["brightness_pct"] = value
    elif action == "set_cover_position":
        data["position"] = value
    await hass.services.async_call(
        entity_id.split(".", 1)[0], service, data, blocking=True
    )
